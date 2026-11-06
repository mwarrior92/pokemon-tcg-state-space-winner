"""
Build the game graph from real games and report what it says.

  python src/build_state_graph.py --kaggle 40 --selfplay 100

Sources:
  * Kaggle top-vs-top replays (matches/kaggle_episodes/, engine v1): every decision of both players;
  * engine self-play between meta decklists (engine v2, search agent on both sides).
Saves matches/state_graph.json.gz and prints graph size, a 60-card accounting check, and win rates
by prize race (turns-to-take-all-Prizes difference) and by turns to the next Prize.
"""
from __future__ import annotations

import argparse
import json
import random
import statistics
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from cabt_bridge import CardMap, Engine, SearchAgent  # noqa: E402
from decision_benchmark import EP_DIR, winner_seat  # noqa: E402
from state_graph import EffectTracker, StateGraph, describe_node, encode, move_label  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "matches" / "state_graph.json.gz"


def kaggle_games(n: int):
    eng = Engine.get(1)
    files = sorted((f for f in EP_DIR.glob("*.json") if f.name != "index.json"), key=lambda f: int(f.stem))[:n]
    for f in files:
        rep = json.loads(f.read_text(encoding="utf-8"))
        win = winner_seat(rep)
        steps = rep["steps"]
        seq = []
        for i in range(1, len(steps) - 1):
            for seat in (0, 1):
                ob = steps[i][seat].get("observation") or {}
                if not ob.get("select") or steps[i][seat].get("status") != "ACTIVE":
                    continue
                if (ob.get("current") or {}).get("yourIndex") != seat or ob["current"].get("turn", 0) < 1:
                    continue
                act = steps[i + 1][seat].get("action")
                if isinstance(act, dict):
                    act = act.get("action")
                if isinstance(act, list):
                    seq.append((ob, act))
        yield eng, seq, win


def selfplay_games(n: int, seed: int = 3):
    from card_compiler import StandardCardDatabase
    from gauntlet import build_gauntlet
    meta = ROOT / "meta" / "decklists_2026-09-19_to_10-31.json"
    db = StandardCardDatabase(ROOT / "pokemon-tcg-data-standard", meta)
    eng = Engine.get(2)
    cmap = CardMap(eng, db)
    opps = build_gauntlet(db, meta, playable=lambda dk: not cmap.deck_ids(dk)[1])
    ids = [cmap.deck_ids(o.deck)[0] for o in opps]
    rng = random.Random(seed)
    for _ in range(n):
        a, b = rng.sample(ids, 2)
        agents = (SearchAgent(eng, a, b, rng), SearchAgent(eng, b, a, rng))
        obs, _ = eng.game.battle_start(a, b)
        seq = []
        try:
            steps = 0
            while obs["current"]["result"] < 0 and steps < 5000:
                act = agents[obs["current"]["yourIndex"]](obs)
                if obs["current"].get("turn", 0) >= 1 and obs.get("select"):
                    seq.append((obs, act))
                obs = eng.game.battle_select(act)
                steps += 1
            res = obs["current"]["result"]
        finally:
            eng.game.battle_finish()
        yield eng, seq, (res if res in (0, 1) else None)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--kaggle", type=int, default=40)
    ap.add_argument("--selfplay", type=int, default=0)
    args = ap.parse_args()

    g = StateGraph()
    race_wr = defaultdict(list)
    next_wr = defaultdict(list)
    bad_accounting = checked = 0
    from collections import Counter
    feature_counts: Counter = Counter()
    effect_examples: Counter = Counter()
    sources = [("Kaggle top-vs-top", kaggle_games(args.kaggle))]
    if args.selfplay:
        sources.append(("engine self-play", selfplay_games(args.selfplay)))
    for label, games in sources:
        n_games = 0
        for eng, seq, win in games:
            states, moves = [], []
            trackers: dict[int, EffectTracker] = {}
            for ob, act in seq:
                tracker = trackers.setdefault(ob["current"]["yourIndex"], EffectTracker(eng))
                tracker.feed(ob.get("logs"))
                st = encode(eng, ob, tracker)
                for lbl in ("me", "opp"):
                    sd = st["sides"][lbl]
                    feature_counts["status"] += bool(sd["statuses"])
                    feature_counts["effects"] += bool(sd["effects"])
                    for cat, src in sd["effects"]:
                        effect_examples[(cat, src)] += 1
                checked += 1
                if st["accounted"] != (60, 60):
                    bad_accounting += 1
                states.append(st)
                moves.append(move_label(ob, act))
                if win is not None and ob["select"]["type"] == 0:
                    score = 1.0 if win == st["me"] else 0.0
                    race_wr[max(-4, min(4, round(st["race"])))].append(score)
                    next_wr[(min(4, round(st["clock_me"]["next"])), min(4, round(st["clock_opp"]["next"])))].append(score)
            g.add_game(states, moves, win)
            n_games += 1
        print(f"{label}: {n_games} games")

    OUT.parent.mkdir(exist_ok=True)
    g.save(OUT)
    s = g.stats()
    print(f"\nGraph: {s['consolidated_nodes']} consolidated nodes covering {s['exact_states']} distinct exact states; "
          f"{s['edges']} (node, move) edges, {s['transitions']} transitions, mean branching {s['mean_branching']}; "
          f"{s['nodes_seen_10plus']} nodes seen 10+ times. Saved to {OUT.relative_to(ROOT)}")
    print(f"60-card accounting: {checked - bad_accounting}/{checked} states place all 60 cards of both sides")
    print(f"Special Conditions present in {feature_counts['status']} side-states; ongoing effects in {feature_counts['effects']}")
    print("  most common effects in force:", ", ".join(f"{c} ({s}) x{n}" for (c, s), n in effect_examples.most_common(6)))

    print("\nP(player to move wins) by prize race = opponent's turns-to-all-Prizes - ours (main-phase decisions):")
    for k in sorted(race_wr):
        v = race_wr[k]
        print(f"  race {k:+d}: {statistics.mean(v) * 100:5.1f}%  (n={len(v)})")
    print("\nP(win) by turns to OUR next Prize (rows) vs THEIR next Prize (columns), cells with n>=15:")
    print("        " + "".join(f"them {c}  " for c in range(1, 5)))
    for r in range(1, 5):
        row = []
        for c in range(1, 5):
            v = next_wr.get((r, c), [])
            row.append(f"{statistics.mean(v) * 100:5.0f}%  " if len(v) >= 15 else "    -   ")
        print(f"  us {r}  " + "".join(row))

    print("\nMost visited consolidated nodes (win rate for the player to move):")
    for node, n in sorted(g.nodes.items(), key=lambda kv: -kv[1]["visits"])[:6]:
        wr, visits = g.value(node)
        print(f"  {visits:4d} visits, {wr * 100:4.0f}% | {describe_node(node)}")


if __name__ == "__main__":
    main()
