"""
Agent regression check: run after every change to the playing agent.

  1. Decision benchmark on the HOLDOUT games (winner's decisions only): agreement + paired regret.
  2. Meta round-robin in the CABT engine: does simulated archetype strength track real
     top-16 conversion (Spearman)?

Results are saved to matches/regression_results/<label>_<timestamp>.json and compared with
the previous saved run.

  python src/regression.py --label sub-search --playouts 16 --regret 30 --games 12
  python src/regression.py --label quick --skip-round-robin
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from card_compiler import StandardCardDatabase  # noqa: E402
from decision_benchmark import run as run_benchmark  # noqa: E402
from gauntlet import meta_round_robin  # noqa: E402

OUT = ROOT / "matches" / "regression_results"
META = ROOT / "meta" / "decklists_2026-09-19_to_10-31.json"


def summarize(r: dict) -> dict:
    b = r.get("benchmark", {})
    rr = r.get("round_robin", {})
    rg = b.get("regret", {})
    main = b.get("by_kind", {}).get("main", {})
    return {
        "agreement (all)": b.get("agreement_all"),
        "agreement (main)": main.get("agree"),
        "main order-insensitive": b.get("main_order_insensitive"),
        "regret mean (pts)": None if not rg else 100 * rg["mean"],
        "regret: sig. worse": rg.get("significantly_worse"),
        "regret: sig. better": rg.get("significantly_better"),
        "round-robin spearman": rr.get("spearman_vs_conversion"),
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--label", default="run")
    ap.add_argument("--regret", type=int, default=30)
    ap.add_argument("--playouts", type=int, default=16)
    ap.add_argument("--games", type=int, default=12, help="round-robin games per archetype pair")
    ap.add_argument("--skip-round-robin", action="store_true")
    ap.add_argument("--horizon", default="turn", choices=["turn", "step"])
    ap.add_argument("--no-sub-search", action="store_true")
    ap.add_argument("--ko-model", action="store_true", help="KO reachability classes in the state value")
    ap.add_argument("--race-values", action="store_true", help="score moves with the solved race graph")
    args = ap.parse_args()
    agent_kwargs = {"horizon": args.horizon, "sub_search": not args.no_sub_search, "ko_model": args.ko_model}
    if args.race_values:
        from race_graph import RaceValues
        agent_kwargs["race_values"] = RaceValues()

    OUT.mkdir(parents=True, exist_ok=True)
    previous = sorted(OUT.glob("*.json"), key=lambda p: p.stat().st_mtime)
    result = {"label": args.label, "time": time.strftime("%Y-%m-%d %H:%M:%S"),
              "agent": {k: (v if isinstance(v, (bool, str, int, float)) else type(v).__name__) for k, v in agent_kwargs.items()}}
    print("== decision benchmark (holdout games, winner's decisions) ==")
    result["benchmark"] = run_benchmark("holdout", 0, args.regret, args.playouts, 1, 0, agent_kwargs)
    if not args.skip_round_robin:
        print("\n== meta round-robin (CABT engine) ==")
        db = StandardCardDatabase(ROOT / "pokemon-tcg-data-standard", META)
        result["round_robin"] = meta_round_robin(db, META, args.games, agent_kwargs=agent_kwargs, progress=True)
        for row in result["round_robin"]["rows"]:
            print(f"  {row['archetype']:24s} sim WR {row['sim_wr']:.3f}  real top-16 conversion {row['top16_conversion']:.2f}")
    path = OUT / f"{args.label}_{time.strftime('%Y%m%d-%H%M%S')}.json"
    path.write_text(json.dumps(result, indent=1, default=str), encoding="utf-8")

    now = summarize(result)
    prev = summarize(json.loads(previous[-1].read_text(encoding="utf-8"))) if previous else {}
    print(f"\n== summary ({path.name}) ==")
    print(f"{'metric':26s} {'this run':>10s} {'previous':>10s}")
    for k, v in now.items():
        pv = prev.get(k)
        fmt = (lambda x: "-" if x is None else (f"{x:.3f}" if isinstance(x, float) else str(x)))
        print(f"{k:26s} {fmt(v):>10s} {fmt(pv):>10s}")


if __name__ == "__main__":
    main()
