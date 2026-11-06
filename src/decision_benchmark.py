"""
Decision-quality benchmark: compare our agent's choices with strong players' choices,
position by position, on real top-vs-top Kaggle ladder games (matches/kaggle_episodes/).

Only the WINNER of each game is used as the reference player. For each of the winner's
non-trivial decisions we rebuild the exact position in the engine (from the replay's
`search_begin_input`) and ask our agent what it would do.

Reported:
  * agreement (top-1), overall and by decision type, next to the chance level 1/n;
  * order-insensitive main-phase agreement (our move is one the winner also made that turn);
  * REGRET on genuine disagreements: from the same position, play the game out K times after the
    winner's move and K times after ours, with the same neutral playout policy for both sides.
    Playouts are paired (both moves see the same guess of the hidden cards on each trial) so
    luck cancels out. Regret = winner's win rate - ours. The winner's move is a reference, not
    ground truth: if ours does at least as well, it is not a mistake.

Games are split deterministically into a dev set (for tuning) and a holdout set (for reporting).

  python src/decision_benchmark.py --split holdout --regret 30 --playouts 16 --json out.json
"""
from __future__ import annotations

import argparse
import json
import math
import random
import statistics
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
from cabt_bridge import OT_END, ST_MAIN, Engine, SearchAgent, evaluate_state  # noqa: E402

EP_DIR = Path(__file__).resolve().parents[1] / "matches" / "kaggle_episodes"
OT_NAME = {7: "play card", 8: "attach", 9: "evolve", 10: "ability", 11: "discard", 12: "retreat", 13: "attack", 14: "end turn"}
CTX_NAME = {1: "setup active", 2: "setup bench", 3: "switch", 4: "to active", 5: "to bench", 6: "to field", 7: "to hand",
            8: "discard", 9: "to deck", 13: "damage counter", 14: "damage counters (any)", 15: "damage", 17: "heal",
            21: "attach from", 22: "attach to", 30: "discard energy", 38: "draw count", 41: "go first?", 43: "activate?"}


def episode_files(split: str) -> list[Path]:
    """Deterministic split by episode ID: every 4th game (sorted) is holdout, the rest are dev."""
    files = sorted((f for f in EP_DIR.glob("*.json") if f.name != "index.json"), key=lambda f: int(f.stem))
    if split == "all":
        return files
    hold = [f for k, f in enumerate(files) if k % 4 == 3]
    return hold if split == "holdout" else [f for f in files if f not in hold]


def winner_seat(replay: dict[str, Any]) -> int | None:
    r = replay.get("rewards") or []
    if len(r) != 2 or r[0] == r[1] or None in r:
        return None
    return 0 if r[0] > r[1] else 1


def decision_points(replay: dict[str, Any], only_seat: int | None = None):
    """Yield (step, seat, observation, chosen action, decks) for decisions in a Kaggle replay."""
    steps = replay["steps"]
    decks = [steps[1][0]["action"], steps[1][1]["action"]]
    for i in range(1, len(steps) - 1):
        for seat in (0, 1):
            if only_seat is not None and seat != only_seat:
                continue
            ob = steps[i][seat].get("observation") or {}
            sel = ob.get("select")
            if not sel or steps[i][seat].get("status") != "ACTIVE":
                continue
            if (ob.get("current") or {}).get("yourIndex") != seat:
                continue
            action = steps[i + 1][seat].get("action")
            if isinstance(action, dict):
                action = action.get("action")
            if not isinstance(action, list):
                continue
            yield i, seat, ob, action, decks


def option_signature(ob: dict[str, Any], idx: int) -> tuple:
    """Card-level identity of a main-phase option, stable across the steps of a turn
    (hand indices shift as cards are played; card IDs and targets don't)."""
    o = ob["select"]["option"][idx]
    p = ob["current"]["players"][ob["current"]["yourIndex"]]
    card = target = None
    try:
        if o.get("index") is not None and (o.get("area") == 2 or o["type"] == 7):
            card = p["hand"][o["index"]]["id"]
        elif o.get("area") == 4:
            card = p["active"][0]["id"]
        elif o.get("area") == 5:
            card = p["bench"][o["index"]]["id"]
        if o.get("inPlayArea") == 4:
            target = p["active"][0]["id"]
        elif o.get("inPlayArea") == 5:
            target = p["bench"][o["inPlayIndex"]]["id"]
    except (IndexError, KeyError, TypeError):
        pass
    return (o["type"], card, target, o.get("attackId"))


def kind_of(ob: dict[str, Any]) -> str:
    sel = ob["select"]
    if sel["type"] == ST_MAIN:
        return "main"
    return CTX_NAME.get(sel.get("context"), f"ctx{sel.get('context')}")


def _greedy_playout(eng: Engine, agent: SearchAgent, state: dict[str, Any], seat: int, max_steps: int = 1500) -> float | None:
    """Neutral playout policy for BOTH sides: one-step greedy on main decisions, static otherwise.
    Returns 1.0 if `seat` wins, 0.0 if it loses, 0.5 draw, None if unfinished."""
    for _ in range(max_steps):
        ob = state["observation"]
        cur = ob["current"]
        if cur["result"] >= 0:
            return 1.0 if cur["result"] == seat else (0.0 if cur["result"] in (0, 1) else 0.5)
        sel = ob["select"]
        if sel is None:
            return None
        who = cur["yourIndex"]
        if sel["type"] == ST_MAIN and len(sel["option"]) > 1:
            best, best_v = 0, -1e18
            for i, o in enumerate(sel["option"]):
                ch = eng.search_step(state["searchId"], [i])
                if ch is None:
                    continue
                v = evaluate_state(eng, ch["observation"]["current"], who) - (0.5 if o["type"] == OT_END else 0.0)
                if v > best_v:
                    best, best_v = i, v
            choice = [best]
        else:
            choice = agent.static_choice(ob)
        nxt = eng.search_step(state["searchId"], choice)
        if nxt is None:
            return None
        state = nxt
    return None


def paired_regret(eng: Engine, agent: SearchAgent, ob: dict[str, Any], seat: int, expert: list[int], ours: list[int],
                  k: int) -> dict[str, float] | None:
    """Paired playouts: on each trial both moves see the SAME hidden-card guess. Returns win rates,
    mean difference (expert - ours) and its standard error."""
    diffs, we, wo = [], [], []
    for _ in range(k):
        guesses = agent._guesses(ob)
        pair = []
        for move in (expert, ours):
            root = eng.search_begin(ob, *guesses)
            if root is None:
                return None
            ch = eng.search_step(root["searchId"], move)
            w = _greedy_playout(eng, agent, ch, seat) if ch is not None else None
            eng.search_end()
            pair.append(w)
        if None in pair:
            continue
        we.append(pair[0])
        wo.append(pair[1])
        diffs.append(pair[0] - pair[1])
    if len(diffs) < max(3, k // 2):
        return None
    sd = statistics.stdev(diffs) if len(diffs) > 1 else 0.0
    return {"expert": statistics.mean(we), "ours": statistics.mean(wo), "diff": statistics.mean(diffs),
            "se": sd / math.sqrt(len(diffs)), "n": len(diffs)}


def run(split: str = "holdout", episodes: int = 0, regret_n: int = 30, playouts: int = 16, engine_version: int = 1,
        seed: int = 0, agent_kwargs: dict[str, Any] | None = None, verbose: bool = True) -> dict[str, Any]:
    eng = Engine.get(engine_version)
    rng = random.Random(seed)
    files = episode_files(split)
    if episodes:
        files = files[:episodes]
    agent_kwargs = agent_kwargs or {}

    stats: dict[str, Counter] = defaultdict(Counter)
    chance: dict[str, list[float]] = defaultdict(list)
    by_opt: dict[str, Counter] = defaultdict(Counter)
    turnset = Counter()
    disagreements = []
    errors = games = 0
    for f in files:
        replay = json.loads(f.read_text(encoding="utf-8"))
        win = winner_seat(replay)
        if win is None:
            continue
        games += 1
        expert_turn_actions: dict[int, set] = defaultdict(set)
        points = list(decision_points(replay, only_seat=win))
        for i, seat, ob, expert, decks in points:
            if ob["select"]["type"] == ST_MAIN and expert:
                expert_turn_actions[ob["current"]["turn"]].add(option_signature(ob, expert[0]))
        for i, seat, ob, expert, decks in points:
            sel = ob["select"]
            n = len(sel["option"])
            if n <= 1 or sel["maxCount"] == 0:
                continue
            kind = kind_of(ob)
            agent = SearchAgent(eng, decks[seat], decks[1 - seat], rng, **agent_kwargs)
            try:
                ours = agent(ob)
            except Exception:  # an engine error on one position must not stop the benchmark
                errors += 1
                continue
            same = sorted(ours) == sorted(expert)
            stats[kind]["n"] += 1
            stats[kind]["agree"] += same
            chance[kind].append(1.0 / n if sel["maxCount"] == 1 else 1.0 / max(1, math.comb(n, max(1, len(expert)))))
            reorder = False
            if kind == "main" and expert:
                t = OT_NAME.get(sel["option"][expert[0]]["type"], "?")
                by_opt[t]["n"] += 1
                by_opt[t]["agree"] += same
                if ours:
                    turnset["n"] += 1
                    reorder = option_signature(ob, ours[0]) in expert_turn_actions[ob["current"]["turn"]]
                    turnset["in"] += reorder
            if not same and not reorder:
                disagreements.append((f.name, i, seat, ob, expert, ours, decks, kind))

    out: dict[str, Any] = {"split": split, "games": games, "engine_version": engine_version, "errors": errors,
                           "agent": agent_kwargs, "by_kind": {}, "main_by_expert_action": {}}
    tot = sum(s["n"] for s in stats.values())
    agr = sum(s["agree"] for s in stats.values())
    out["agreement_all"] = agr / max(1, tot)
    out["decisions"] = tot
    for kind, s in stats.items():
        out["by_kind"][kind] = {"n": s["n"], "agree": s["agree"] / s["n"], "chance": statistics.mean(chance[kind])}
    out["main_order_insensitive"] = turnset["in"] / max(1, turnset["n"])
    for t, c in by_opt.items():
        out["main_by_expert_action"][t] = {"n": c["n"], "agree": c["agree"] / c["n"]}

    if verbose:
        print(f"Engine v{engine_version}, {split} split, {games} games, winner's decisions only, agent={agent_kwargs}, {errors} positions skipped")
        print(f"{'decision type':22s} {'n':>6s} {'agree':>7s} {'chance':>7s}")
        for kind in sorted(stats, key=lambda k: -stats[k]["n"]):
            if stats[kind]["n"] < 10:
                continue
            d = out["by_kind"][kind]
            print(f"{kind:22s} {d['n']:6d} {d['agree'] * 100:6.1f}% {d['chance'] * 100:6.1f}%")
        print(f"{'ALL':22s} {tot:6d} {out['agreement_all'] * 100:6.1f}%")
        print(f"Main phase, order-insensitive (our move is one the winner also made that turn): {out['main_order_insensitive'] * 100:.1f}%")
        print("Main-phase agreement by the winner's chosen action:")
        for t, c in sorted(out["main_by_expert_action"].items(), key=lambda x: -x[1]["n"]):
            print(f"  {t:10s} n={c['n']:5d}  agree {c['agree'] * 100:5.1f}%")

    if regret_n and disagreements:
        sample = random.Random(seed + 1).sample(disagreements, min(regret_n, len(disagreements)))
        rows = []
        for name, i, seat, ob, expert, ours, decks, kind in sample:
            agent = SearchAgent(eng, decks[seat], decks[1 - seat], rng, **agent_kwargs)
            r = paired_regret(eng, agent, ob, seat, expert, ours, playouts)
            if r is None:
                continue
            rows.append({**r, "kind": kind, "episode": name, "step": i})
        if rows:
            diffs = [r["diff"] for r in rows]
            worse = [r for r in rows if r["diff"] - 2 * r["se"] > 0]
            better = [r for r in rows if r["diff"] + 2 * r["se"] < 0]
            out["regret"] = {"positions": len(rows), "playouts": playouts, "mean": statistics.mean(diffs),
                             "se": statistics.stdev(diffs) / math.sqrt(len(diffs)) if len(diffs) > 1 else 0.0,
                             "significantly_worse": len(worse), "significantly_better": len(better), "rows": rows}
            if verbose:
                rg = out["regret"]
                print(f"\nRegret on {len(rows)} genuine disagreements ({playouts} paired playouts each):")
                print(f"  mean regret (winner's win rate - ours): {rg['mean'] * 100:+.1f} pts  (+/- {2 * rg['se'] * 100:.1f})")
                print(f"  ours significantly worse: {len(worse)}   significantly better: {len(better)}   "
                      f"not distinguishable: {len(rows) - len(worse) - len(better)}")
                for r in sorted(rows, key=lambda r: -r["diff"])[:8]:
                    print(f"    {r['diff'] * 100:+5.0f} pts +/-{2 * r['se'] * 100:3.0f}  {r['kind']:20s} winner {r['expert'] * 100:3.0f}% "
                          f"vs ours {r['ours'] * 100:3.0f}%  [{r['episode']} step {r['step']}]")
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--split", default="holdout", choices=["dev", "holdout", "all"])
    ap.add_argument("--episodes", type=int, default=0, help="limit number of games (0 = whole split)")
    ap.add_argument("--regret", type=int, default=30, help="genuine disagreements to score by paired playouts")
    ap.add_argument("--playouts", type=int, default=16)
    ap.add_argument("--engine-version", type=int, default=1, help="1 = engine the Aug-2026 ladder ran on")
    ap.add_argument("--horizon", default="turn", choices=["turn", "step"])
    ap.add_argument("--no-sub-search", action="store_true", help="use fixed rules for card/target choices")
    ap.add_argument("--ko-model", action="store_true", help="use KO reachability classes in the state value")
    ap.add_argument("--race-values", action="store_true", help="score moves with the solved race graph (matches/race_values.json)")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--json", type=str, help="write results to this JSON file")
    args = ap.parse_args()
    res = run(args.split, args.episodes, args.regret, args.playouts, args.engine_version, args.seed,
              {"horizon": args.horizon, "sub_search": not args.no_sub_search, "ko_model": args.ko_model,
               **({"race_values": __import__("race_graph").RaceValues()} if args.race_values else {})})
    if args.json:
        Path(args.json).write_text(json.dumps(res, indent=1, default=str), encoding="utf-8")


if __name__ == "__main__":
    main()
