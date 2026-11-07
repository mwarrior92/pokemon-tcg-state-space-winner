"""
Fit the board score to DECISIONS: at each real decision, the winner's move should lead to the position
the score rates highest among the alternatives.

Why: a score fitted only to outcomes learns what goes along with winning (a big hand, for instance),
not what wins, and plays worse even though it predicts better. Here the score is fitted where the
agent uses it - ranking the positions its options lead to.

Data (built once, cached): for every main-phase decision of the WINNER in the real replays on disk
(engine v1 reads them reliably), every legal option is played and THE REST OF THE TURN IS FINISHED
GREEDILY (as the one-turn agent does), and the END-OF-TURN position is scored from the decider's side
with cabt_bridge.board_features (+ separate early-game copies, turns 1-4).
Why end of turn: choices within a turn are sequential and winners attack last, so comparing positions
one action later teaches "attacking is worse than playing another card". At the end of the turn,
"attack now" and "play a card, then attack" both have attacked.

Objective: conditional logit (softmax over each decision's options) for the winner's choice
  + lambda x the turn-start outcome fit (matches/eval_positions.jsonl.gz), to keep the score anchored to
winning. L2-regularised; 5-fold cross-validation by game.

  python src/fit_choice.py --build        # generate the option positions (multiprocess)
  python src/fit_choice.py                # fit, report held-out agreement, save matches/eval_weights_choice.json
"""
from __future__ import annotations

import argparse
import json
import random
import sys
from multiprocessing import Pool
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
DATA = ROOT / "matches" / "choice_data_endturn.npz"
OUT = ROOT / "matches" / "eval_weights_choice.json"
EARLY = 4

_W: dict = {}


def _init() -> None:
    from cabt_bridge import Engine
    _W["eng"] = Engine.get(1)


def _game(path: str) -> list[tuple]:
    """(episode, turn, chosen index, option feature matrix) for each of the winner's main-phase decisions."""
    from cabt_bridge import HAND_WEIGHTS, ST_MAIN, SearchAgent, board_features
    from decision_benchmark import decision_points, winner_seat
    eng = _W["eng"]
    rep = json.loads(Path(path).read_text(encoding="utf-8"))
    w = winner_seat(rep)
    if w is None:
        return []
    names = list(HAND_WEIGHTS)
    out = []
    rng = random.Random(0)
    for _, seat, ob, act, decks in decision_points(rep, only_seat=w):
        sel = ob["select"]
        if sel["type"] != ST_MAIN or len(sel["option"]) < 2 or not act or act[0] >= len(sel["option"]):
            continue
        agent = SearchAgent(eng, decks[seat], decks[1 - seat], rng, sub_search=False)
        turn = ob["current"]["turn"]
        try:
            root = eng.search_begin(ob, *agent._guesses(ob))
            if root is None:
                continue
            rows = []
            for i in range(len(sel["option"])):
                ch = eng.search_step(root["searchId"], [i])
                if ch is not None:
                    ch, _ = agent._complete_turn(ch, seat, turn)
                if ch is None:
                    rows.append(None)
                    continue
                f = board_features(eng, ch["observation"]["current"], seat)
                rows.append([f[k] for k in names])
        except OSError:
            continue
        finally:
            try:
                eng.search_end()
            except OSError:
                pass
        if rows[act[0]] is None or sum(r is not None for r in rows) < 2:
            continue
        keep = [i for i, r in enumerate(rows) if r is not None]
        out.append((int(Path(path).stem), turn, keep.index(act[0]), np.array([rows[i] for i in keep], float)))
    return out


def build(workers: int) -> None:
    files = sorted({f.name: str(f) for d in ("kaggle_episodes", "kaggle_episodes_deck/crustle")
                    for f in (ROOT / "matches" / d).glob("*.json") if f.stem.isdigit()}.values())
    decisions = []
    with Pool(workers, initializer=_init) as p:
        for k, res in enumerate(p.imap_unordered(_game, files), 1):
            decisions += res
            if k % 10 == 0:
                print(f"  {k}/{len(files)} games, {len(decisions)} decisions", flush=True)
    ep = np.array([d[0] for d in decisions])
    turn = np.array([d[1] for d in decisions])
    chosen = np.array([d[2] for d in decisions])
    sizes = np.array([len(d[3]) for d in decisions])
    X = np.vstack([d[3] for d in decisions])
    np.savez_compressed(DATA, ep=ep, turn=turn, chosen=chosen, sizes=sizes, X=X)
    print(f"saved {len(decisions)} decisions ({X.shape[0]} option positions) from {len(set(ep))} games -> {DATA.relative_to(ROOT)}")


def expand(X: np.ndarray, turns: np.ndarray) -> np.ndarray:
    return np.hstack([X, X * (turns <= EARLY)[:, None]])


def fit(Xc, dec_of, chosen_rows, n_dec, Xo, yo, lam_out, l2, iters=400):
    """Multi-task fit on standardised features (L-BFGS on the exact loss and gradient):
    choice softmax over each decision's options + lam_out x outcome logistic (own intercept) + L2."""
    from scipy.optimize import minimize
    d = Xc.shape[1]
    allX = np.vstack([Xc, Xo]) if len(Xo) else Xc
    mu, sd = allX.mean(0), allX.std(0)
    sd[sd < 1e-9] = 1.0
    Zc = (Xc - mu) / sd
    Zo = (Xo - mu) / sd if len(Xo) else Xo
    n_o = max(1, len(yo))

    def f(theta):
        w, b = theta[:d], theta[d]
        s = Zc @ w
        s_max = np.full(n_dec, -np.inf)
        np.maximum.at(s_max, dec_of, s)
        e = np.exp(s - s_max[dec_of])
        den = np.zeros(n_dec)
        np.add.at(den, dec_of, e)
        p = e / den[dec_of]
        loss = -np.sum(s[chosen_rows] - s_max - np.log(den)) / n_dec
        g = (Zc.T @ p - Zc[chosen_rows].sum(0)) / n_dec
        gb = 0.0
        if len(Xo) and lam_out:
            z = Zo @ w + b
            q = 1 / (1 + np.exp(-np.clip(z, -30, 30)))
            loss += lam_out * -np.mean(yo * np.log(q + 1e-12) + (1 - yo) * np.log(1 - q + 1e-12))
            g = g + lam_out * (Zo.T @ (q - yo)) / n_o
            gb = lam_out * float(np.mean(q - yo))
        loss += 0.5 * l2 * (w @ w) / n_dec
        g = g + l2 * w / n_dec
        return loss, np.concatenate([g, [gb]])

    res = minimize(f, np.zeros(d + 1), jac=True, method="L-BFGS-B", options={"maxiter": iters})
    return res.x[:d], mu, sd


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--build", action="store_true")
    ap.add_argument("--workers", type=int, default=10)
    ap.add_argument("--lam-out", type=float, default=0.3, help="weight of the outcome loss")
    ap.add_argument("--l2", type=float, default=30.0)
    ap.add_argument("--iters", type=int, default=400)
    args = ap.parse_args()
    if args.build or not DATA.exists():
        build(args.workers)
    from cabt_bridge import HAND_WEIGHTS
    names = list(HAND_WEIGHTS)
    D = np.load(DATA)
    ep, turn, chosen, sizes, X = D["ep"], D["turn"], D["chosen"], D["sizes"], D["X"]
    n_dec = len(sizes)
    starts = np.concatenate([[0], np.cumsum(sizes)[:-1]])
    dec_of = np.repeat(np.arange(n_dec), sizes)
    row_turn = np.repeat(turn, sizes)
    Xc = expand(X, row_turn)
    chosen_rows = starts + chosen
    # outcome data (turn-start positions) for the auxiliary loss
    Xo = yo = np.zeros((0, Xc.shape[1]))
    op = np.load(ROOT / "matches" / "eval_features.npz", allow_pickle=True)
    if list(op["names"]) == names:
        Xo, yo, go = expand(op["X"], op["turn"]), op["y"], op["game"]
    else:
        go = np.zeros(0)
    games = np.unique(ep)
    rng = np.random.default_rng(0)
    fold_of = dict(zip(games, rng.permutation(len(games)) % 5))
    fold_dec = np.array([fold_of[g] for g in ep])
    print(f"{n_dec} winner decisions from {len(games)} games ({Xc.shape[0]} option positions), "
          f"{len(yo)} outcome positions; mean options per decision {sizes.mean():.1f} (chance {np.mean(1 / sizes) * 100:.1f}%)")

    def agreement(score: np.ndarray, mask: np.ndarray) -> float:
        hits = []
        for k in np.where(mask)[0]:
            sl = slice(starts[k], starts[k] + sizes[k])
            hits.append(int(np.argmax(score[sl]) == chosen[k]))
        return float(np.mean(hits))

    hand_w = np.array([HAND_WEIGHTS[n] for n in names] + [0.0] * len(names))
    hand_score = Xc @ hand_w
    try:
        ow = json.loads((ROOT / "matches" / "eval_weights.json").read_text(encoding="utf-8"))
        out_w = np.array([ow["weights"].get(n, 0.0) for n in names] + [ow.get("early_extra", {}).get(n, 0.0) for n in names])
        out_score = Xc @ out_w
    except FileNotFoundError:
        out_score = None
    pred = np.zeros(Xc.shape[0])
    for k in range(5):
        tr_dec = fold_dec != k
        test_games = games[[fold_of[g] == k for g in games]]
        o_tr = ~np.isin(go, test_games) if len(go) else np.zeros(0, bool)   # outcome data minus the test games
        # fit on the training folds
        idx_dec = np.where(tr_dec)[0]
        rows = np.concatenate([np.arange(starts[j], starts[j] + sizes[j]) for j in idx_dec])
        local_dec = np.repeat(np.arange(len(idx_dec)), sizes[idx_dec])
        local_chosen = np.concatenate([[0], np.cumsum(sizes[idx_dec])[:-1]]) + chosen[idx_dec]
        w, mu, sd = fit(Xc[rows], local_dec, local_chosen, len(idx_dec),
                        Xo[o_tr] if len(go) else Xo, yo[o_tr] if len(go) else yo, args.lam_out, args.l2, iters=args.iters)
        te_rows = ~np.isin(dec_of, idx_dec)
        pred[te_rows] = ((Xc[te_rows] - mu) / sd) @ w
    early = turn <= EARLY
    print(f"\nheld-out agreement with the winner's move     all    turns 1-4   turns 5+")
    for label, sc in (("hand-set weights", hand_score), ("outcome-fitted weights", out_score), ("decision-fitted weights", pred)):
        if sc is None:
            continue
        print(f"  {label:42s} {agreement(sc, np.ones(n_dec, bool)) * 100:5.1f}%   {agreement(sc, early) * 100:7.1f}%   "
              f"{agreement(sc, ~early) * 100:7.1f}%")
    # final fit on everything
    w, mu, sd = fit(Xc, dec_of, chosen_rows, n_dec, Xo, yo, args.lam_out, args.l2, iters=args.iters)
    raw = w / sd
    cols = names + [n + " (early extra)" for n in names]
    print("\nlargest effects on the decision score (per standard deviation; + = the winner prefers more of it):")
    for i in np.argsort(-np.abs(w))[:14]:
        print(f"  {cols[i]:34s} {w[i]:+.3f}   (hand-set raw {HAND_WEIGHTS.get(cols[i], 0.0):+.2f}, fitted raw {raw[i]:+.3f})")
    k = len(names)
    OUT.write_text(json.dumps({"kind": "choice", "weights": {n: float(raw[i]) for i, n in enumerate(names)},
                               "early_extra": {n: float(raw[k + i]) for i, n in enumerate(names)}, "early_turns": EARLY,
                               "lam_out": args.lam_out, "l2": args.l2, "decisions": int(n_dec), "games": int(len(games))},
                              indent=1), encoding="utf-8")
    print(f"\nsaved {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
