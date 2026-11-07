"""
Acceptance test for our own decisions: Lopunny Dusknoir vs Crustle.

Tracks, for the Lopunny Dusknoir player: Bench size and Benched Pokemon ex at the start of its turns 1-3,
share of its turns with an attack, Spiky Hopper uses (the attack that damages Crustle), and win rate.

  python src/lopunny_check.py --games 16            # current code
  python src/lopunny_check.py --games 16 --old DIR  # a different cabt_bridge.py (e.g. the committed one)
"""
from __future__ import annotations

import argparse
import random
import statistics
import sys
from collections import defaultdict
from multiprocessing import Pool
from pathlib import Path

_ARGS: dict = {}


def _setup(old: str | None) -> None:
    if old:
        sys.path.insert(0, old)
    sys.path.insert(1, str(Path(__file__).resolve().parent))


def _init(old: str | None, agent: str = "search", iters: int = 150, turns: int = 3) -> None:
    _setup(old)
    from cabt_bridge import Engine
    _ARGS.update(eng=Engine.get(2), agent=agent, iters=iters, turns=turns)


def _make(eng, mine, theirs, rng):
    if _ARGS.get("agent") == "mcts":
        from mcts import MCTSAgent
        return MCTSAgent(eng, mine, theirs, rng, iterations=_ARGS["iters"], n_turns=_ARGS["turns"])
    from cabt_bridge import SearchAgent
    return SearchAgent(eng, mine, theirs, rng)


def _job(a: tuple) -> dict:
    lop, cru, seed, lop_first = a
    from cabt_bridge import OT_ATTACK, ST_MAIN, _prize_value
    eng = _ARGS["eng"]
    rng = random.Random(seed)
    d0, d1 = (lop, cru) if lop_first else (cru, lop)
    me = 0 if lop_first else 1
    agents = (_make(eng, d0, d1, rng), _make(eng, d1, d0, rng))
    obs, _ = eng.game.battle_start(d0, d1)
    bench_by_turn, ex_by_turn = {}, {}
    my_turns, attack_turns, hopper = set(), set(), 0
    nth = 0
    last = None
    try:
        while obs["current"]["result"] < 0:
            cur = obs["current"]
            who = cur["yourIndex"]
            if who == me and cur["turn"] >= 1 and cur["turn"] != last:
                last = cur["turn"]
                nth += 1
                my_turns.add(cur["turn"])
                bench = cur["players"][me].get("bench") or []
                if nth <= 3:
                    bench_by_turn[nth] = len(bench)
                    ex_by_turn[nth] = sum(1 for b in bench if _prize_value(eng, b["id"]) >= 2)
            act = agents[who](obs)
            sel = obs.get("select")
            if who == me and sel and sel["type"] == ST_MAIN and act:
                o = sel["option"][act[0]]
                if o["type"] == OT_ATTACK:
                    attack_turns.add(cur["turn"])
                    if eng.attacks.get(o.get("attackId"), {}).get("name") == "Spiky Hopper":
                        hopper += 1
            obs = eng.game.battle_select(act)
            for _ag in agents:
                getattr(_ag, "observe", lambda o: None)(obs)
        res = obs["current"]["result"]
    except OSError:
        return {}
    finally:
        eng.game.battle_finish()
    return {"win": 1.0 if res == me else (0.0 if res in (0, 1) else 0.5), "bench": bench_by_turn, "ex": ex_by_turn,
            "attack_share": len(attack_turns) / max(1, len(my_turns)), "hopper": hopper,
            "counts": dict(getattr(agents[me], "counts", {}))}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--games", type=int, default=16)
    ap.add_argument("--old", default=None)
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--agent", default="search", choices=["search", "mcts"])
    ap.add_argument("--iters", type=int, default=150)
    ap.add_argument("--turns", type=int, default=3)
    args = ap.parse_args()
    _setup(args.old)
    from cabt_bridge import CardMap, Engine
    from card_compiler import StandardCardDatabase
    from gauntlet import load_meta_decks
    from tail_check import META, ROOT, engine_ids
    db = StandardCardDatabase(ROOT / "pokemon-tcg-data-standard", META)
    eng = Engine.get(2)
    cmap = CardMap(eng, db)
    best = {}
    for d, dk in sorted(load_meta_decks(db, META), key=lambda x: x[0]["rank"]):
        if d["deck"] in ("Lopunny Dusknoir", "Crustle") and d["deck"] not in best:
            ids = engine_ids(cmap, eng, dk, {"Pokémon Center Lady": "Cook"})
            if ids:
                best[d["deck"]] = ids
    jobs = [(best["Lopunny Dusknoir"], best["Crustle"], 101 + g, g % 2 == 0) for g in range(args.games)]
    with Pool(args.workers, initializer=_init, initargs=(args.old, args.agent, args.iters, args.turns)) as p:
        rows = [r for r in p.map(_job, jobs) if r]
    print(f"code: {'committed (' + args.old + ')' if args.old else 'current'}; agent {args.agent}"
          f"{f' ({args.iters} iterations, {args.turns} turns deep)' if args.agent == 'mcts' else ''}; {len(rows)} games")
    for t in (1, 2, 3):
        b = [r["bench"][t] for r in rows if t in r["bench"]]
        e = [r["ex"][t] for r in rows if t in r["ex"]]
        print(f"  start of Lopunny's turn {t}: Bench {statistics.mean(b):.1f}, Benched ex {statistics.mean(e):.1f}")
    print(f"  Lopunny turns with an attack: {statistics.mean(r['attack_share'] for r in rows) * 100:.0f}%")
    print(f"  Spiky Hopper uses per game:  {statistics.mean(r['hopper'] for r in rows):.2f}")
    print(f"  Lopunny Dusknoir win rate:   {statistics.mean(r['win'] for r in rows) * 100:.0f}%")
    if rows and rows[0]["counts"]:
        tot = {k: sum(r["counts"].get(k, 0) for r in rows) for k in ("reused", "fresh", "surprises")}
        n = max(1, tot["reused"] + tot["fresh"])
        print(f"  tree reuse: {tot['reused'] / n * 100:.0f}% of searched decisions started from a kept tree; "
              f"{tot['surprises']} opponent turns were surprises (tree discarded)")


if __name__ == "__main__":
    main()
