"""
Fit the board evaluation's weights to who actually won real top-vs-top games.

Data: matches/eval_positions.jsonl.gz (src/fetch_positions.py) - turn-start positions with the mover and
whether the mover went on to win. Features: cabt_bridge.board_features (both sides separately).
Model: L2-regularised logistic regression P(mover wins) (numpy, Newton steps), optionally with separate
early-game weights (turns 1-4) where Bench decisions happen. Validation: 5-fold cross-validation BY GAME,
so no game contributes to both the fit and the test. Compared on the same held-out games with the
hand-set weights.

  python src/fit_eval.py                  # fit, report, save matches/eval_weights.json
  python src/fit_eval.py --no-early       # one set of weights for the whole game
"""
from __future__ import annotations

import argparse
import gzip
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
POS = ROOT / "matches" / "eval_positions.jsonl.gz"
CACHE = ROOT / "matches" / "eval_features.npz"
OUT = ROOT / "matches" / "eval_weights.json"
EARLY = 4


def load(refresh: bool = False):
    from cabt_bridge import HAND_WEIGHTS, Engine, board_features
    names = [k for k in HAND_WEIGHTS]
    if CACHE.exists() and not refresh and CACHE.stat().st_mtime > POS.stat().st_mtime:
        d = np.load(CACHE, allow_pickle=True)
        if list(d["names"]) == names:
            return names, d["X"], d["y"], d["game"], d["turn"]
    eng = Engine.get(2)
    X, y, game, turn = [], [], [], []
    with gzip.open(POS, "rt", encoding="utf-8") as f:
        for line in f:
            r = json.loads(line)
            ft = board_features(eng, r["cur"], r["seat"])
            X.append([ft[k] for k in names])
            y.append(r["won"])
            game.append(r["episode"])
            turn.append(r["turn"])
    X, y, game, turn = np.array(X, float), np.array(y, float), np.array(game), np.array(turn)
    np.savez_compressed(CACHE, X=X, y=y, game=game, turn=turn, names=np.array(names, dtype=object))
    return names, X, y, game, turn


def design(X: np.ndarray, turn: np.ndarray, early: bool) -> np.ndarray:
    return np.hstack([X, X * (turn <= EARLY)[:, None]]) if early else X


def fit(X: np.ndarray, y: np.ndarray, lam: float) -> np.ndarray:
    """L2-regularised logistic regression on standardised columns (bias column unpenalised)."""
    mu, sd = X.mean(0), X.std(0)
    sd[sd < 1e-9] = 1.0
    bias = np.all(X == 1.0, axis=0)
    mu[bias], sd[bias] = 0.0, 1.0
    Z = (X - mu) / sd
    w = np.zeros(Z.shape[1])
    pen = np.full(Z.shape[1], lam)
    pen[bias] = 0.0
    for _ in range(50):
        p = 1 / (1 + np.exp(-np.clip(Z @ w, -30, 30)))
        g = Z.T @ (p - y) + pen * w
        H = (Z * (p * (1 - p))[:, None]).T @ Z + np.diag(pen + 1e-9)
        step = np.linalg.solve(H, g)
        w -= step
        if np.abs(step).max() < 1e-7:
            break
    return None, mu, sd, w


def to_raw(w_std: np.ndarray, mu: np.ndarray, sd: np.ndarray, bias_idx: int) -> np.ndarray:
    """Weights on the raw features (so logit = raw @ w)."""
    w = w_std / sd
    w[bias_idx] -= float((w_std / sd * mu).sum())
    return w


def auc(score: np.ndarray, y: np.ndarray) -> float:
    order = np.argsort(score, kind="mergesort")
    s, yy = score[order], y[order]
    ranks = np.empty(len(s))
    i = 0
    while i < len(s):
        j = i
        while j + 1 < len(s) and s[j + 1] == s[i]:
            j += 1
        ranks[i:j + 1] = (i + j) / 2 + 1
        i = j + 1
    npos, nneg = yy.sum(), len(yy) - yy.sum()
    return float((ranks[yy == 1].sum() - npos * (npos + 1) / 2) / (npos * nneg)) if npos and nneg else float("nan")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-early", action="store_true", help="no separate early-game weights")
    ap.add_argument("--lam", type=float, default=0.0, help="L2 strength (0 = choose by cross-validation)")
    ap.add_argument("--refresh", action="store_true", help="recompute cached features")
    args = ap.parse_args()
    from cabt_bridge import HAND_WEIGHTS
    names, X, y, game, turn = load(args.refresh)
    early = not args.no_early
    D = design(X, turn, early)
    cols = names + ([f"{n} (early extra)" for n in names] if early else [])
    bias_idx = names.index("bias")
    hand = X @ np.array([HAND_WEIGHTS[n] for n in names])
    games = np.unique(game)
    rng = np.random.default_rng(0)
    fold_of = dict(zip(games, rng.permutation(len(games)) % 5))
    folds = np.array([fold_of[g] for g in game])
    print(f"{len(games)} games, {len(y)} turn-start positions, {D.shape[1]} weights"
          f"{' (separate early-game weights, turns 1-' + str(EARLY) + ')' if early else ''}")

    def cv(lam: float) -> np.ndarray:
        pred = np.zeros(len(y))
        for k in range(5):
            tr, te = folds != k, folds == k
            _, mu, sd, w_std = fit(D[tr], y[tr], lam)
            pred[te] = ((D[te] - mu) / sd) @ w_std
        return pred

    lams = [args.lam] if args.lam else [1.0, 10.0, 30.0, 100.0, 300.0, 1000.0]
    best = None
    for lam in lams:
        pred = cv(lam)
        a = auc(pred, y)
        ll = float(-np.mean(y * np.log(1 / (1 + np.exp(-pred)) + 1e-12) + (1 - y) * np.log(1 - 1 / (1 + np.exp(-pred)) + 1e-12)))
        print(f"  L2 {lam:7.1f}: held-out AUC {a:.3f}, log-loss {ll:.4f}")
        if best is None or a > best[1]:
            best = (lam, a, pred)
    lam, _, pred = best
    stages = [("turns 1-4", turn <= 4), ("turns 5-8", (turn >= 5) & (turn <= 8)), ("turns 9+", turn >= 9)]
    print(f"\nheld-out AUC (same games)       overall  " + "  ".join(f"{n:>9s}" for n, _ in stages))
    print(f"  Prize difference only         {auc(X[:, names.index('my_taken')] - X[:, names.index('op_taken')], y):.3f}   "
          + "  ".join(f"{auc((X[m, names.index('my_taken')] - X[m, names.index('op_taken')]), y[m]):9.3f}" for _, m in stages))
    print(f"  hand-set weights              {auc(hand, y):.3f}   " + "  ".join(f"{auc(hand[m], y[m]):9.3f}" for _, m in stages))
    print(f"  fitted weights (L2 {lam:g})      {auc(pred, y):.3f}   " + "  ".join(f"{auc(pred[m], y[m]):9.3f}" for _, m in stages))

    _, mu, sd, w_std = fit(D, y, lam)
    w = to_raw(w_std, mu, sd, bias_idx)
    imp = np.abs(w_std)
    print("\nlargest fitted effects (per standard deviation of the feature; + favours the player to move):")
    for i in np.argsort(-imp)[:16]:
        print(f"  {cols[i]:34s} {w_std[i]:+.3f}   (hand-set raw weight {HAND_WEIGHTS.get(cols[i], 0.0):+.2f}, fitted raw {w[i]:+.3f})")
    weights = {n: float(w[i]) for i, n in enumerate(names)}
    early_w = {n: float(w[len(names) + i]) for i, n in enumerate(names)} if early else {}
    OUT.write_text(json.dumps({"weights": weights, "early_extra": early_w, "early_turns": EARLY, "l2": lam,
                               "games": int(len(games)), "positions": int(len(y)),
                               "cv_auc": float(auc(pred, y))}, indent=1), encoding="utf-8")
    print(f"\nsaved {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
