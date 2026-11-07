"""
Does the simulator overrate decks in general, or just Crustle?

Plays lower-meta archetypes (below the 14-deck gauntlet, but playable in the CABT engine) against the
gauntlet, using the same agent and meta weighting as `meta_round_robin`. Then it ranks them with the
gauntlet decks by simulated win rate versus real top-16 conversion.

  python src/tail_check.py --games 8 --workers 8
  python src/tail_check.py --archetypes Crustle --lists 3 --sub "Pokémon Center Lady=Cook"

--sub swaps a card the engine doesn't have for a stand-in, so more lists of an archetype can be played.
Results go to matches/regression_results/tail_<timestamp>.json.
"""
from __future__ import annotations

import argparse
import glob
import json
import math
import random
import re
import sys
import time
from collections import defaultdict
from multiprocessing import Pool
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

ROOT = Path(__file__).resolve().parents[1]
META = ROOT / "meta" / "decklists_2026-09-19_to_10-31.json"
OUT_DIR = ROOT / "matches" / "regression_results"
MISSING_RE = re.compile(r"^(\d+)x (.+?) \(")

_W: dict = {}


def _init() -> None:
    from cabt_bridge import CardMap, Engine
    from card_compiler import StandardCardDatabase
    db = StandardCardDatabase(ROOT / "pokemon-tcg-data-standard", META)
    eng = Engine.get()
    _W.update(db=db, eng=eng, cmap=CardMap(eng, db))


def engine_ids(cmap, eng, deck, subs: dict[str, str]) -> list[int] | None:
    """Engine card ids for a 60-card deck. Missing cards are replaced via `subs` (name -> name),
    or None if something is still missing."""
    ids, missing = cmap.deck_ids(deck)
    by_name = {c["name"]: i for i, c in sorted(eng.cards.items())}
    for m in missing:
        mm = MISSING_RE.match(m)
        stand_in = subs.get(mm.group(2)) if mm else None
        if stand_in not in by_name:
            return None
        ids += [by_name[stand_in]] * int(mm.group(1))
    return ids if len(ids) == 60 else None


def _job(args: tuple) -> tuple[str, str, float, int]:
    test_label, test_ids, opp_name, opp_ids, games, seed, kw = args
    from cabt_bridge import SearchAgent, play_engine_game
    eng = _W["eng"]
    rng = random.Random(seed)
    w = 0.0
    for g in range(games):
        a, b = (test_ids, opp_ids) if g % 2 == 0 else (opp_ids, test_ids)
        r = play_engine_game(a, b, (SearchAgent(eng, a, b, rng, **kw), SearchAgent(eng, b, a, rng, **kw)))
        seat = 0 if g % 2 == 0 else 1
        w += 0.5 if r["winner"] is None else (1.0 if r["winner"] == seat else 0.0)
    return test_label, opp_name, w, games


def _rank(v: list[float]) -> list[float]:
    """Ranks from 0, ties sharing their average rank."""
    order = sorted(range(len(v)), key=lambda k: v[k])
    rk = [0.0] * len(v)
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and v[order[j + 1]] == v[order[i]]:
            j += 1
        for k in order[i:j + 1]:
            rk[k] = (i + j) / 2
        i = j + 1
    return rk


def spearman(x: list[float], y: list[float]) -> float:
    a, b = _rank(x), _rank(y)
    n = len(x)
    return 1 - 6 * sum((p - q) ** 2 for p, q in zip(a, b)) / (n * (n * n - 1)) if n > 2 else 0.0


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--archetypes", nargs="*", help="default: every non-gauntlet archetype with >= --min-lists playable lists")
    ap.add_argument("--min-lists", type=int, default=3)
    ap.add_argument("--lists", type=int, default=1, help="best-placing playable lists to test per archetype")
    ap.add_argument("--games", type=int, default=8, help="games per (test deck, gauntlet opponent)")
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--sub", action="append", default=[], help='stand-in for a card the engine lacks: "Name=Stand-in"')
    ap.add_argument("--no-sub-search", action="store_true")
    ap.add_argument("--compare", default="sub-search", help="regression label whose round-robin rows to rank against")
    ap.add_argument("--label", default="tail")
    args = ap.parse_args()
    subs = dict(s.split("=", 1) for s in args.sub)
    kw = {"sub_search": not args.no_sub_search}

    from gauntlet import build_gauntlet, load_meta_decks
    _init()
    db, eng, cmap = _W["db"], _W["eng"], _W["cmap"]
    opps = build_gauntlet(db, META, playable=lambda dk: engine_ids(cmap, eng, dk, {}) is not None)
    gauntlet_names = {o.archetype for o in opps}
    opp_ids = {o.archetype: engine_ids(cmap, eng, o.deck, {}) for o in opps}
    weights = {o.archetype: o.weight for o in opps}

    by_arch: dict[str, list] = defaultdict(list)
    for d, dk in load_meta_decks(db, META):
        by_arch[d["deck"]].append((d, dk))
    archs = args.archetypes or [a for a, v in by_arch.items() if a not in gauntlet_names
                                and sum(engine_ids(cmap, eng, dk, subs) is not None for _, dk in v) >= args.min_lists]

    tests = []                                       # (label, archetype, ids, source)
    for a in archs:
        pool = sorted(by_arch[a], key=lambda x: x[0]["rank"])
        n = 0
        for d, dk in pool:
            ids = engine_ids(cmap, eng, dk, subs)
            if ids is None:
                continue
            swapped = bool(cmap.deck_ids(dk)[1])
            tests.append((f"{a} #{d['rank']}{' (sub)' if swapped else ''}", a, ids, f"{d['event']} #{d['rank']}"))
            n += 1
            if n >= args.lists:
                break
    if not tests:
        sys.exit("no playable test decks")
    print(f"{len(tests)} test decks x {len(opps)} gauntlet opponents x {args.games} games, {args.workers} workers")
    for t in tests:
        print("  ", t[0], "|", t[3])

    jobs = [(lbl, ids, o, opp_ids[o], args.games, 1000 * k + j, kw)
            for k, (lbl, arch, ids, _) in enumerate(tests) for j, o in enumerate(opp_ids) if o != arch]
    t0 = time.perf_counter()
    res: dict[str, dict[str, float]] = defaultdict(dict)
    with Pool(args.workers, initializer=_init) as p:
        for k, (lbl, o, w, g) in enumerate(p.imap_unordered(_job, jobs), 1):
            res[lbl][o] = w / g
            if k % 10 == 0 or k == len(jobs):
                print(f"  {k}/{len(jobs)} matchups ({time.perf_counter() - t0:.0f}s)", flush=True)

    rows = []
    for lbl, arch, _, src in tests:
        xs = by_arch[arch]
        top16 = sum(1 for d, _ in xs if d["rank"] <= 16)
        conv = top16 / len(xs) / 0.25
        p = max(top16, 0.5) / len(xs)
        wr = sum(weights[o] * v for o, v in res[lbl].items()) / sum(weights[o] for o in res[lbl])
        rows.append({"deck": lbl, "archetype": arch, "tier": "tail", "sim_wr": wr, "top16_conversion": conv,
                     "conversion_se": math.sqrt(p * (1 - p) / len(xs)) / 0.25, "lists": len(xs),
                     "matchups": res[lbl], "source": src})

    prev = sorted(glob.glob(str(OUT_DIR / f"{args.compare}_*.json")))
    base_rows = json.loads(Path(prev[-1]).read_text(encoding="utf-8"))["round_robin"]["rows"] if prev else []
    for r in base_rows:
        xs = by_arch[r["archetype"]]
        p = max(r["top16_conversion"] * 0.25, 0.5 / len(xs))
        rows.append({"deck": r["archetype"], "archetype": r["archetype"], "tier": "gauntlet", "sim_wr": r["sim_wr"],
                     "top16_conversion": r["top16_conversion"],
                     "conversion_se": math.sqrt(p * (1 - p) / len(xs)) / 0.25, "lists": len(xs)})

    # Overrating: a deck's simulated rank minus its real-conversion rank, over all decks (0 = rank agrees).
    sim_rk = _rank([r["sim_wr"] for r in rows])
    real_rk = _rank([r["top16_conversion"] for r in rows])
    for r, a, b in zip(rows, sim_rk, real_rk):
        r["rank_gap"] = a - b
    rows.sort(key=lambda r: -r["sim_wr"])
    print(f"\nAll decks by simulated win rate vs the gauntlet (comparison rows from {Path(prev[-1]).name if prev else 'none'}):")
    print(f"  {'deck':34s} {'tier':8s} {'sim WR':>6s}  {'real conv':>9s} {'+/-':>5s} {'lists':>5s}  rank gap")
    for r in rows:
        flag = "  OVERRATED" if r["rank_gap"] >= len(rows) / 3 else ("  underrated" if r["rank_gap"] <= -len(rows) / 3 else "")
        print(f"  {r['deck']:34s} {r['tier']:8s} {r['sim_wr']:6.3f}  {r['top16_conversion']:9.2f} {r['conversion_se']:5.2f} "
              f"{r['lists']:5d}  {r['rank_gap']:+5.0f}{flag}")
    tail = [r for r in rows if r["tier"] == "tail"]
    rho_all = spearman([r["sim_wr"] for r in rows], [r["top16_conversion"] for r in rows])
    print(f"\nSpearman (sim WR vs real conversion): all decks {rho_all:+.2f}"
          + (f", tail only {spearman([r['sim_wr'] for r in tail], [r['top16_conversion'] for r in tail]):+.2f}" if len(tail) > 2 else ""))
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out = OUT_DIR / f"{args.label}_{time.strftime('%Y%m%d-%H%M%S')}.json"
    out.write_text(json.dumps({"agent": kw, "games": args.games, "subs": subs, "rows": rows,
                               "spearman_all": rho_all}, indent=1), encoding="utf-8")
    print(f"saved {out.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
