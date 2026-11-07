"""
Matchup-by-matchup check of the simulator against real tournament results.

A deck's overall results depend on which decks it happened to face, so instead of comparing overall
win rates this compares each simulated matchup (tail_check runs: matches/regression_results/) with the
real head-to-head record of the same two archetypes (meta/matchups_*.json, from Limitless Labs).

Real records are best-of-3 matches; the simulator plays single games. A game win probability p gives a
Bo3 match win probability m = p^2 (3 - 2p), so real match rates are converted to the implied per-game
rate before comparing (ties are left out of that conversion).

  python src/matchup_check.py                       # latest tail_* and gauntlet-matrix_* runs
"""
from __future__ import annotations

import argparse
import glob
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REAL = ROOT / "meta" / "matchups_2026-09-19_to_10-31.json"
RUNS = ROOT / "matches" / "regression_results"


def game_rate(m: float) -> float:
    """Per-game win probability implied by a Bo3 match win probability."""
    lo, hi = 0.0, 1.0
    for _ in range(50):
        p = (lo + hi) / 2
        if p * p * (3 - 2 * p) < m:
            lo = p
        else:
            hi = p
    return (lo + hi) / 2


def real_matchup(total: dict, a: str, b: str) -> dict | None:
    r = total.get(a, {}).get(b)
    if not r or r[0] + r[1] == 0:
        return None
    w, l, t = r
    m = (w + 0.5) / (w + l + 1)                    # light smoothing so 0-n records stay finite
    p = game_rate(m)
    se_m = math.sqrt(m * (1 - m) / (w + l))
    se_p = se_m / max(1e-3, 6 * p * (1 - p))       # delta method through m = p^2 (3 - 2p)
    return {"w": w, "l": l, "t": t, "match": w / (w + l), "game": p, "se": min(se_p, 0.5)}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs", nargs="*", help="tail_check result files (default: latest tail_* and gauntlet-matrix_*)")
    ap.add_argument("--games", type=int, default=8, help="simulated games per matchup in those runs")
    args = ap.parse_args()
    real = json.loads(REAL.read_text(encoding="utf-8"))["total"]
    files = args.runs or [sorted(glob.glob(str(RUNS / f"{p}_*.json")))[-1] for p in ("gauntlet-matrix", "tail")
                          if glob.glob(str(RUNS / f"{p}_*.json"))]
    rows = []
    for f in files:
        for r in json.loads(Path(f).read_text(encoding="utf-8"))["rows"]:
            if "matchups" in r:
                rows.append(r)

    # meta weights of the opponents, as in the gauntlet
    meta = json.loads((ROOT / "meta" / "decklists_2026-09-19_to_10-31.json").read_text(encoding="utf-8"))
    share: dict[str, int] = {}
    for d in meta:
        share[d["deck"]] = share.get(d["deck"], 0) + 1

    out, flagged = [], []
    for r in rows:
        sim_w = real_w = wsum = 0.0
        n_real = 0
        for opp, sim in r["matchups"].items():
            rm = real_matchup(real, r["archetype"], opp)
            if rm is None:
                continue
            w = share.get(opp, 0)
            sim_w += w * sim
            real_w += w * rm["game"]
            wsum += w
            n_real += rm["w"] + rm["l"] + rm["t"]
            se_sim = math.sqrt(max(sim * (1 - sim), 0.05) / args.games)
            z = (sim - rm["game"]) / math.sqrt(se_sim ** 2 + rm["se"] ** 2)
            if abs(z) >= 2:
                flagged.append((r["deck"], opp, sim, rm, z))
        if wsum:
            out.append({"deck": r["deck"], "archetype": r["archetype"], "sim": sim_w / wsum, "real": real_w / wsum,
                        "gap": (sim_w - real_w) / wsum, "real_matches": n_real})

    out.sort(key=lambda x: -x["gap"])
    print("Each deck vs the SAME opponents it played in the sim, opponents weighted by meta share.")
    print("Real = per-game win rate implied by the archetypes' real Bo3 records (all rounds, 8 Regionals).\n")
    print(f"  {'deck':32s} {'sim':>6s} {'real':>6s} {'gap':>7s}  {'real matches':>12s}")
    for x in out:
        tag = "  OVERRATED" if x["gap"] >= 0.10 else ("  UNDERRATED" if x["gap"] <= -0.10 else "")
        print(f"  {x['deck']:32s} {x['sim']:6.2f} {x['real']:6.2f} {x['gap'] * 100:+6.0f}pt  {x['real_matches']:12d}{tag}")

    print(f"\nIndividual matchups where sim and reality differ by 2+ standard errors ({len(flagged)}):")
    print(f"  {'deck':32s} {'vs':24s} {'sim':>5s} {'real':>5s}  {'real W-L-T':>14s}")
    for deck, opp, sim, rm, z in sorted(flagged, key=lambda f: -abs(f[2] - f[3]["game"])):
        print(f"  {deck:32s} {opp:24s} {sim:5.2f} {rm['game']:5.2f}  {rm['w']:5d}-{rm['l']}-{rm['t']:<5d} z={z:+.1f}")
    res = RUNS / "matchup_check.json"
    res.write_text(json.dumps({"decks": out, "flagged": [
        {"deck": d, "opponent": o, "sim": s, "real_game": rm["game"], "real_record": [rm["w"], rm["l"], rm["t"]], "z": z}
        for d, o, s, rm, z in flagged]}, indent=1), encoding="utf-8")
    print(f"\nsaved {res.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
