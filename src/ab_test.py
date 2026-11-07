"""
Head-to-head test between two agent configurations (the way chess engines test changes).

Each PAIR is two games on the same two decks with the same seats; in the second game the agents swap
which deck they pilot, so deck strength and going first cancel out. After every pair a sequential
probability ratio test (SPRT, as in Stockfish's fishtest) checks
    H0: B is no better than A (elo0)   vs   H1: B is better by elo1,
and stops as soon as either is clear (alpha = beta = 0.05), or at --max-pairs.

Agent specs:  NAME[:key=value,...]
  search                      one-turn search agent (cabt_bridge.SearchAgent); keys are its arguments
  mcts                        tree search (mcts.MCTSAgent): iterations, n_turns, c_explore, reuse, ...
  any spec may add eval=hand | eval=fitted (matches/eval_weights.json) | eval=<path>

  python src/ab_test.py --a search --b "search:eval=fitted" --elo1 30
  python src/ab_test.py --a "mcts:iterations=100" --b "mcts:iterations=100,eval=fitted" --workers 10
"""
from __future__ import annotations

import argparse
import json
import math
import random
import sys
import time
from multiprocessing import Pool
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
OUT_DIR = ROOT / "matches" / "regression_results"
FITTED = ROOT / "matches" / "eval_weights.json"


def parse_spec(spec: str) -> tuple[str, dict[str, Any], str | None]:
    name, _, rest = spec.partition(":")
    kw: dict[str, Any] = {}
    ev = None
    for part in filter(None, rest.split(",")):
        k, _, v = part.partition("=")
        if k == "eval":
            ev = v
            continue
        if v.lower() in ("true", "false", "yes", "no"):
            kw[k] = v.lower() in ("true", "yes")
        elif v.lstrip("-").isdigit():
            kw[k] = int(v)
        elif v.replace(".", "", 1).lstrip("-").isdigit():
            kw[k] = float(v)
        else:
            kw[k] = v
    return name, kw, ev


class _WithEval:
    """Runs an agent with its own evaluation weights swapped in for the duration of each call."""

    def __init__(self, agent: Any, ev: str | None) -> None:
        import cabt_bridge as cb
        self.agent, self.cb = agent, cb
        self.state = None
        if ev and ev != "hand":
            saved = dict(cb._EVAL)
            cb.load_eval_weights(FITTED if ev == "fitted" else ev)
            self.state = dict(cb._EVAL)
            cb._EVAL.clear()
            cb._EVAL.update(saved)

    def _swap(self):
        if self.state is None:
            return None
        saved = dict(self.cb._EVAL)
        self.cb._EVAL.clear()
        self.cb._EVAL.update(self.state)
        return saved

    def _restore(self, saved) -> None:
        if saved is not None:
            self.cb._EVAL.clear()
            self.cb._EVAL.update(saved)

    def __call__(self, obs):
        saved = self._swap()
        try:
            return self.agent(obs)
        finally:
            self._restore(saved)

    def observe(self, obs) -> None:
        if hasattr(self.agent, "observe"):
            self.agent.observe(obs)


def make_agent(spec: str, eng, mine, theirs, rng):
    name, kw, ev = parse_spec(spec)
    if name == "mcts":
        from mcts import MCTSAgent
        ag = MCTSAgent(eng, mine, theirs, rng, **kw)
    elif name == "search":
        from cabt_bridge import SearchAgent
        ag = SearchAgent(eng, mine, theirs, rng, **kw)
    else:
        raise ValueError(f"unknown agent {name}")
    return _WithEval(ag, ev)


_W: dict = {}


def _init() -> None:
    from cabt_bridge import Engine
    _W["eng"] = Engine.get(2)


def _play(eng, d0, d1, a0, a1) -> float | None:
    """One game; returns seat 0's points (1 / 0.5 / 0), None if the engine faulted."""
    obs, _ = eng.game.battle_start(d0, d1)
    agents = (a0, a1)
    steps = 0
    try:
        while obs["current"]["result"] < 0 and steps < 5000:
            act = agents[obs["current"]["yourIndex"]](obs)
            obs = eng.game.battle_select(act)
            for ag in agents:
                ag.observe(obs)
            steps += 1
        r = obs["current"]["result"]
    except OSError:
        return None
    finally:
        eng.game.battle_finish()
    return 1.0 if r == 0 else (0.0 if r == 1 else 0.5)


def _pair(job: tuple) -> dict[str, Any] | None:
    spec_a, spec_b, dx, dy, names, seed = job
    eng = _W["eng"]
    # game 1: A pilots deck X (seat 0), B pilots Y;  game 2: B pilots X (seat 0), A pilots Y
    g1 = _play(eng, dx, dy, make_agent(spec_a, eng, dx, dy, random.Random(seed)),
               make_agent(spec_b, eng, dy, dx, random.Random(seed + 1)))
    g2 = _play(eng, dx, dy, make_agent(spec_b, eng, dx, dy, random.Random(seed)),
               make_agent(spec_a, eng, dy, dx, random.Random(seed + 1)))
    if g1 is None or g2 is None:
        return None
    return {"decks": names, "b_points": (1.0 - g1) + g2}     # B's points over the pair (0..2)


def elo(score: float) -> float:
    score = min(max(score, 1e-6), 1 - 1e-6)
    return -400.0 * math.log10(1.0 / score - 1.0)


def sprt_llr(pair_scores: list[float], elo0: float, elo1: float) -> float:
    """Generalised SPRT log-likelihood ratio on per-pair scores in [0, 1] (fishtest's normal approximation)."""
    n = len(pair_scores)
    if n < 2:
        return 0.0
    m = sum(pair_scores) / n
    var = max(sum((x - m) ** 2 for x in pair_scores) / n, 0.02)   # floor: a few pairs can't fake certainty
    s0, s1 = 1 / (1 + 10 ** (-elo0 / 400)), 1 / (1 + 10 ** (-elo1 / 400))
    return n * (s1 - s0) * (2 * m - s0 - s1) / (2 * var)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--a", default="search", help="baseline agent spec")
    ap.add_argument("--b", required=True, help="candidate agent spec")
    ap.add_argument("--elo0", type=float, default=0.0)
    ap.add_argument("--elo1", type=float, default=30.0)
    ap.add_argument("--alpha", type=float, default=0.05)
    ap.add_argument("--beta", type=float, default=0.05)
    ap.add_argument("--max-pairs", type=int, default=400)
    ap.add_argument("--min-pairs", type=int, default=20, help="no verdict before this many pairs")
    ap.add_argument("--workers", type=int, default=10)
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--label", default="ab")
    args = ap.parse_args()
    from cabt_bridge import CardMap, Engine
    from card_compiler import StandardCardDatabase
    from gauntlet import build_gauntlet
    from tail_check import META, engine_ids
    db = StandardCardDatabase(ROOT / "pokemon-tcg-data-standard", META)
    eng = Engine.get(2)
    cmap = CardMap(eng, db)
    opps = build_gauntlet(db, META, playable=lambda dk: engine_ids(cmap, eng, dk, {}) is not None)
    decks = [(o.archetype, engine_ids(cmap, eng, o.deck, {}), o.weight) for o in opps]
    rng = random.Random(args.seed)
    jobs = []
    for k in range(args.max_pairs):
        x, y = rng.choices(decks, weights=[d[2] for d in decks], k=2)   # meta-weighted, mirrors allowed
        jobs.append((args.a, args.b, x[1], y[1], (x[0], y[0]), 10007 * (k + 1) + args.seed))
    lo, hi = math.log(args.beta / (1 - args.alpha)), math.log((1 - args.beta) / args.alpha)
    print(f"A = {args.a}\nB = {args.b}\nSPRT elo0={args.elo0} elo1={args.elo1}, bounds [{lo:.2f}, {hi:.2f}], "
          f"up to {args.max_pairs} pairs on {len(decks)} meta decks, {args.workers} workers", flush=True)
    scores: list[float] = []
    rows = []
    verdict = "inconclusive (pair limit reached)"
    t0 = time.perf_counter()
    with Pool(args.workers, initializer=_init) as p:
        for r in p.imap_unordered(_pair, jobs):
            if r is None:
                continue
            rows.append(r)
            scores.append(r["b_points"] / 2)
            llr = sprt_llr(scores, args.elo0, args.elo1)
            n = len(scores)
            if n % 5 == 0:
                m = sum(scores) / n
                print(f"  {n:4d} pairs: B scores {m * 100:5.1f}%  (Elo {elo(m):+5.0f}), LLR {llr:+.2f}  "
                      f"[{time.perf_counter() - t0:.0f}s]", flush=True)
            if n < args.min_pairs:
                continue
            if llr >= hi:
                verdict = f"H1 accepted: B is better (by >= ~{args.elo1:g} Elo)"
                break
            if llr <= lo:
                verdict = f"H0 accepted: B is not better than A by {args.elo1:g} Elo"
                break
        p.terminate()
    n = len(scores)
    m = sum(scores) / max(1, n)
    sd = (sum((x - m) ** 2 for x in scores) / max(1, n - 1)) ** 0.5
    ci = 1.96 * sd / max(1, n) ** 0.5
    print(f"\n{n} pairs ({2 * n} games): B scores {m * 100:.1f}% +/- {ci * 100:.1f}  "
          f"(Elo {elo(m):+.0f}, 95% CI {elo(max(1e-3, m - ci)):+.0f} to {elo(min(1 - 1e-3, m + ci)):+.0f})")
    print(f"verdict: {verdict}")
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out = OUT_DIR / f"{args.label}_{time.strftime('%Y%m%d-%H%M%S')}.json"
    out.write_text(json.dumps({"a": args.a, "b": args.b, "elo0": args.elo0, "elo1": args.elo1, "pairs": rows,
                               "score": m, "verdict": verdict}, indent=1), encoding="utf-8")
    print(f"saved {out.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
