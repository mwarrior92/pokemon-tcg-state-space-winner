"""
Pokemon TCG State-Space Deck Discovery & Evaluation CLI.

Usage examples:
  python discover_deck.py --build "Dhelmise"
  python discover_deck.py --build "Alakazam" --save decks/alakazam_state_opt.txt
  python discover_deck.py --build "Dawn"
  python discover_deck.py --evaluate decks/raging_bolt_fortress.txt
  python discover_deck.py --states
  python discover_deck.py --demo
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))

from card_compiler import MACRO_ACTIONS, StandardCardDatabase
from deck_optimizer import StateGuidedDeckOptimizer, format_ptcgl_decklist
from state_evaluator import StateSpaceEvaluator, parse_ptcgl_decklist
from state_space import (
    ACTIVE_TIERS,
    BENCH_STRUCTURES,
    LOCK_CONDITIONS,
    PHASE_WINDOWS,
    PRESSURE_MODES,
    PRIZE_CONTEXTS,
    build_competitive_state_space,
    export_state_space,
)


def print_state_taxonomy(scenarios) -> None:
    print("=" * 88)
    print("POKEMON TCG FINITE BOARD-STATE & MACRO-ACTION TAXONOMY")
    print("=" * 88)
    total_grid = (
        len(PHASE_WINDOWS)
        * len(ACTIVE_TIERS)
        * len(PRESSURE_MODES)
        * len(BENCH_STRUCTURES)
        * len(LOCK_CONDITIONS)
        * len(PRIZE_CONTEXTS)
    )
    print(f"Factored State Grid |S| = {len(PHASE_WINDOWS)} Phases x {len(ACTIVE_TIERS)} ActiveTiers x "
          f"{len(PRESSURE_MODES)} PressureModes x {len(BENCH_STRUCTURES)} BenchStates x "
          f"{len(LOCK_CONDITIONS)} Locks x {len(PRIZE_CONTEXTS)} PrizeContexts = {total_grid:,} discrete states")
    print(f"Canonical Competitive Meta States (Prioritized): {len(scenarios)} states (covering 512 tournament decks)")
    print(f"Macro-Action Capability Space |A| = {len(MACRO_ACTIONS)} dimensions:\n  {', '.join(MACRO_ACTIONS)}\n")

    print(f"{'ID':4s} | {'Weight':6s} | {'Competitive Board State Scenario':48s} | {'Factored State Coordinates'}")
    print("-" * 110)
    for s in scenarios[:20]:
        coords = f"{s.active_tier} / {s.pressure_mode} / {s.lock_condition}"
        print(f"{s.state_id:4s} | {s.state_weight*100:5.2f}% | {s.name:48s} | {coords}")


def print_evaluation_report(title: str, rep) -> None:
    print("=" * 88)
    print(f"STATE-SPACE EVALUATION REPORT: {title}")
    print("=" * 88)
    print(f"Legality          : {'LEGAL (60 cards)' if rep.is_legal else 'ILLEGAL - ' + '; '.join(rep.legality_issues)}")
    print(f"Overall Blended   : {rep.overall_score:.2f} / 100.0  (Est. Win Rate: {rep.expected_win_rate*100:.1f}% | Setup: {rep.consistency_score:.1f}%)")
    print(f"Going First (P1)  : {rep.going_first_score:.2f} / 100.0  (Est. Win Rate: {rep.going_first_win_rate*100:.1f}% | Setup: {rep.consistency_first:.1f}%)")
    print(f"Going Second (P2) : {rep.going_second_score:.2f} / 100.0  (Est. Win Rate: {rep.going_second_win_rate*100:.1f}% | Setup: {rep.consistency_second:.1f}%)")
    print(f"Preferred Seat    : {rep.preferred_seat} ({rep.seat_delta_wr*100:+.1f}% WR First vs Second)\n")

    print(f"{'Game Phase Window':24s} | {'Blended':>8s} | {'1st (P1)':>8s} | {'2nd (P2)':>8s}")
    print("-" * 58)
    for ph in PHASE_WINDOWS:
        if ph in rep.phase_scores:
            print(f"  {ph:22s} | {rep.phase_scores[ph]:8.1f} | {rep.phase_scores_first[ph]:8.1f} | {rep.phase_scores_second[ph]:8.1f}")

    print(f"\n{'Competitive Meta Archetype':40s} | {'Blended':>8s} | {'1st (P1)':>8s} | {'2nd (P2)':>8s}")
    print("-" * 74)
    for arch, sc in sorted(rep.archetype_scores.items(), key=lambda x: -x[1]):
        print(f"  {arch:38s} | {sc:8.1f} | {rep.archetype_scores_first[arch]:8.1f} | {rep.archetype_scores_second[arch]:8.1f}")

    print("\nMacro-Action Capability Profile (0.00 - 1.00):")
    row_items = [f"{act}: {val:.2f}" for act, val in rep.macro_capabilities.items()]
    for i in range(0, len(row_items), 4):
        print("  " + " | ".join(f"{x:22s}" for x in row_items[i:i+4]))

    print("\nHighest-Priority Bottleneck States (Remaining Vulnerability):")
    for sid, sname, sw, ssc in rep.worst_states[:5]:
        print(f"  [{sid}] w={sw*100:5.2f}% | Score={ssc*100:5.1f}/100 | {sname}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Pokemon TCG State-Space Deck Discovery & Optimizer")
    parser.add_argument("--build", type=str, help="Pokemon or Trainer card name/ID to build a 60-card deck around")
    parser.add_argument("--evaluate", type=str, help="Path to a PTCGL decklist .txt file to evaluate")
    parser.add_argument("--save", type=str, help="Optional path to save the discovered PTCGL decklist")
    parser.add_argument("--states", action="store_true", help="Print the finite Board-State taxonomy and top prioritized states")
    parser.add_argument("--demo", action="store_true", help="Run a discovery benchmark across multiple Pokemon & Trainer cards")
    args = parser.parse_args()

    t0 = time.perf_counter()
    db = StandardCardDatabase(
        ROOT / "pokemon-tcg-data-standard",
        ROOT / "meta" / "decklists_2026-09-19_to_10-31.json",
    )
    scenarios = build_competitive_state_space(
        db,
        ROOT / "meta" / "decklists_2026-09-19_to_10-31.json",
        ROOT / "matches" / "parsed_turn_trajectories.json",
    )
    export_state_space(ROOT / "meta" / "competitive_board_states.json", scenarios)
    evaluator = StateSpaceEvaluator(db, scenarios)
    optimizer = StateGuidedDeckOptimizer(db, evaluator)
    load_ms = (time.perf_counter() - t0) * 1000.0

    if args.states:
        print_state_taxonomy(scenarios)
        return

    if args.evaluate:
        dpath = Path(args.evaluate)
        deck = parse_ptcgl_decklist(dpath.read_text(encoding="utf-8"), db)
        rep = evaluator.evaluate_deck(deck)
        print_evaluation_report(dpath.name, rep)
        return

    if args.build:
        t_start = time.perf_counter()
        res = optimizer.optimize_deck(args.build)
        elapsed_ms = (time.perf_counter() - t_start) * 1000.0
        header = (
            f"Built around: {res.seed_card.name} ({res.seed_card.uid})\n"
            f"Archetype Style: {res.archetype_style} | Preferred Seat: {res.report.preferred_seat}\n"
            f"Blended Score: {res.report.overall_score:.2f}/100 ({res.report.expected_win_rate*100:.1f}% WR) | "
            f"Going First: {res.report.going_first_score:.2f} ({res.report.going_first_win_rate*100:.1f}% WR) | "
            f"Going Second: {res.report.going_second_score:.2f} ({res.report.going_second_win_rate*100:.1f}% WR)\n"
            f"Evaluated {res.iterations_evaluated} candidate decks x {len(scenarios)} states in {elapsed_ms:.0f} ms"
        )
        deck_txt = format_ptcgl_decklist(res.deck, header_comment=header)
        print_evaluation_report(f"Discovered Deck for '{res.seed_card.name}' ({res.archetype_style})", res.report)
        print("\n" + "=" * 88)
        print("DISCOVERED 60-CARD PTCGL DECKLIST")
        print("=" * 88)
        print(deck_txt)
        if args.save:
            out_p = Path(args.save)
            out_p.parent.mkdir(parents=True, exist_ok=True)
            out_p.write_text(deck_txt + "\n", encoding="utf-8")
            print(f"\nSaved decklist to {out_p}")
        return

    # Default or --demo: showcase state taxonomy + evaluate user decks + discover new decks
    print(f"[Initialized 3,108 Standard cards & {len(scenarios)} Competitive Board States in {load_ms:.0f} ms]\n")
    print_state_taxonomy(scenarios)
    print("\n" + "=" * 88)
    print("MULTI-SEED DECK DISCOVERY BENCHMARK (POKEMON & TRAINER SEEDS)")
    print("=" * 88)
    seeds = [
        ("Dhelmise", "decks/discovered_dhelmise_anchor.txt"),
        ("Alakazam", "decks/discovered_alakazam_hand.txt"),
        ("Mega Lopunny ex", "decks/discovered_mega_lopunny.txt"),
        ("Hydrapple ex", "decks/discovered_hydrapple_vitality.txt"),
        ("Dawn", "decks/discovered_dawn_stage2_engine.txt"),
    ]
    for seed_name, save_rel in seeds:
        t_s = time.perf_counter()
        res = optimizer.optimize_deck(seed_name)
        dt_ms = (time.perf_counter() - t_s) * 1000.0
        header = (
            f"Built around: {res.seed_card.name} ({res.seed_card.uid})\n"
            f"Archetype Style: {res.archetype_style} | Preferred Seat: {res.report.preferred_seat}\n"
            f"Blended Score: {res.report.overall_score:.2f}/100 ({res.report.expected_win_rate*100:.1f}% WR) | "
            f"Going First: {res.report.going_first_score:.2f} ({res.report.going_first_win_rate*100:.1f}% WR) | "
            f"Going Second: {res.report.going_second_score:.2f} ({res.report.going_second_win_rate*100:.1f}% WR)"
        )
        deck_txt = format_ptcgl_decklist(res.deck, header_comment=header)
        out_path = ROOT / save_rel
        out_path.write_text(deck_txt + "\n", encoding="utf-8")
        print(f"  Seed '{seed_name:16s}' -> Blended: {res.report.overall_score:5.2f} ({res.report.expected_win_rate*100:4.1f}% WR) | "
              f"1st: {res.report.going_first_score:5.2f} ({res.report.going_first_win_rate*100:4.1f}%) | "
              f"2nd: {res.report.going_second_score:5.2f} ({res.report.going_second_win_rate*100:4.1f}%) | "
              f"Pref: {res.report.preferred_seat}")


if __name__ == "__main__":
    main()
