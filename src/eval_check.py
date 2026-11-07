"""
Does our board evaluation predict who wins?

For every turn-start position in the real top-vs-top Kaggle games on disk, score the board for the
player to move with `evaluate_state` and check how well the score separates eventual winners from
losers (AUC: 0.5 = coin flip, 1.0 = perfect), overall and by game stage. A search can only be as good
as the evaluation at the end of its paths, so this is the first check on any change to it.

  python src/eval_check.py                     # current evaluation
  python src/eval_check.py --old DIR           # another cabt_bridge.py (e.g. the committed one)
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def auc(pos: list[float], neg: list[float]) -> float:
    """P(score of a random winner position > score of a random loser position)."""
    if not pos or not neg:
        return float("nan")
    allv = sorted([(v, 1) for v in pos] + [(v, 0) for v in neg])
    rank_sum, i = 0.0, 0
    while i < len(allv):
        j = i
        while j + 1 < len(allv) and allv[j + 1][0] == allv[i][0]:
            j += 1
        r = (i + j) / 2 + 1
        rank_sum += r * sum(1 for k in range(i, j + 1) if allv[k][1] == 1)
        i = j + 1
    return (rank_sum - len(pos) * (len(pos) + 1) / 2) / (len(pos) * len(neg))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--old", default=None, help="directory holding another cabt_bridge.py to evaluate")
    args = ap.parse_args()
    if args.old:
        sys.path.insert(0, args.old)
    sys.path.insert(1, str(ROOT / "src"))
    from cabt_bridge import Engine, evaluate_state
    from decision_benchmark import decision_points, winner_seat
    eng = Engine.get(2)                                   # evaluation only reads card data (v2 is a superset)
    files = {f.name: f for d in ("kaggle_episodes", "kaggle_episodes_deck/crustle")
             for f in (ROOT / "matches" / d).glob("*.json") if f.stem.isdigit()}
    stages = {"turns 1-4": (1, 4), "turns 5-8": (5, 8), "turns 9+": (9, 999)}
    win: dict[str, list[float]] = {k: [] for k in stages}
    lose: dict[str, list[float]] = {k: [] for k in stages}
    games = 0
    for f in sorted(files.values()):
        rep = json.loads(f.read_text(encoding="utf-8"))
        w = winner_seat(rep)
        if w is None:
            continue
        games += 1
        seen = set()
        for _, seat, ob, _, _ in decision_points(rep):
            cur = ob["current"]
            t = cur.get("turn", 0)
            if t < 1 or (seat, t) in seen or ob["select"]["type"] != 0:
                continue
            seen.add((seat, t))                               # first main-phase decision of the turn
            v = evaluate_state(eng, cur, seat)
            for k, (lo, hi) in stages.items():
                if lo <= t <= hi:
                    (win if seat == w else lose)[k].append(v)
    allw = [v for k in stages for v in win[k]]
    alll = [v for k in stages for v in lose[k]]
    print(f"evaluation: {'from ' + args.old if args.old else 'current'}; {games} games, {len(allw) + len(alll)} turn-start positions")
    print(f"  AUC overall: {auc(allw, alll):.3f}")
    for k in stages:
        print(f"  AUC {k:10s}: {auc(win[k], lose[k]):.3f}   (n={len(win[k]) + len(lose[k])})")


if __name__ == "__main__":
    main()
