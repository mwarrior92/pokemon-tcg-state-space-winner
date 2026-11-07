"""
How does our agent handle one archetype compared with real top-vs-top Kaggle games?

  python src/deck_benchmark.py --card Crustle --fetch          # collect the games that contain the card
  python src/deck_benchmark.py --card Crustle --sim-games 4    # compare

Games come from the top-vs-top ladder episodes already used by the race graph (and the local
benchmark set). Only replays with `--card` in either deck are kept, in matches/kaggle_episodes_deck/<card>/.

Replay positions are read with engine v1 (the format the ladder records); simulated games run on v2.
Reported:
  1. Outcomes: the deck's real win rate in these games vs its simulated win rate with the SAME two
     decklists, played by our search agent on both sides (seats alternated).
  2. Facing the wall: on the opposing player's turns that start with a damage-immune copy of the card
     Active, what they did (attack with a Pokemon ex into it, attack with a non-ex, bring up a
     different target, no attack) and Prizes taken that turn, real vs simulated.
  3. Decision agreement with the real players, separately for the deck's pilot and its opponent.
"""
from __future__ import annotations

import argparse
import json
import random
import re
import statistics
import sys
import time
from collections import Counter, defaultdict
from multiprocessing import Pool
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
from cabt_bridge import OT_ATTACK, OT_RETREAT, ST_MAIN, Engine, SearchAgent, _is_ex, _ntext  # noqa: E402
from decision_benchmark import EP_DIR, decision_points, winner_seat  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
DECK_DIR = ROOT / "matches" / "kaggle_episodes_deck"
SEQ_FILE = ROOT / "matches" / "race_sequences.jsonl"


def slug(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


def seats_with(eng: Engine, replay: dict[str, Any], card: str) -> list[int]:
    decks = [replay["steps"][1][s]["action"] for s in (0, 1)]
    return [s for s in (0, 1) if any(eng.cards.get(i, {}).get("name") == card for i in decks[s])]


def fetch(card: str) -> Path:
    sys.path.insert(0, str(ROOT / "matches"))
    from fetch_kaggle_episodes import _get
    eng = Engine.get(1)
    out = DECK_DIR / slug(card)
    out.mkdir(parents=True, exist_ok=True)
    ids = [json.loads(line)["episode"] for line in SEQ_FILE.read_text(encoding="utf-8").splitlines()] if SEQ_FILE.exists() else []
    ids += [int(f.stem) for f in EP_DIR.glob("*.json") if f.stem.isdigit()]
    ids = sorted(set(ids))
    kept = 0
    for k, eid in enumerate(ids, 1):
        dst = out / f"{eid}.json"
        if dst.exists():
            kept += 1
            continue
        local = EP_DIR / f"{eid}.json"
        try:
            raw = local.read_bytes() if local.exists() else _get(f"https://www.kaggleusercontent.com/episodes/{eid}.json")
            if seats_with(eng, json.loads(raw), card):
                dst.write_bytes(raw)
                kept += 1
        except Exception as ex:  # one bad replay must not stop the scan
            print(f"  skip {eid}: {ex}")
        if not local.exists():
            time.sleep(1.0)
        if k % 25 == 0:
            print(f"  {k}/{len(ids)} scanned, {kept} with {card}", flush=True)
    print(f"{kept} games with {card} in {out.relative_to(ROOT)}")
    return out


# ---------------------------------------------------------------------------
# Behaviour facing the wall
# ---------------------------------------------------------------------------

def wall_ids(eng: Engine, card: str) -> set[int]:
    """Versions of `card` that prevent damage from attacks (the ones a player has to play around)."""
    return {i for i, c in eng.cards.items() if c.get("name") == card and
            any("prevent all damage" in _ntext(s.get("text")) for s in c.get("skills") or [])}


def _active_id(cur: dict[str, Any], side: int) -> int | None:
    a = (cur["players"][side].get("active") or [None])[0]
    return a.get("id") if a else None


def turn_behaviour(eng: Engine, decisions: list[tuple[dict, list[int]]], walls: set[int]) -> list[dict[str, Any]]:
    """`decisions`: one player's (observation, chosen action) in order. One row per turn that starts
    with a wall Active on the other side."""
    turns: dict[int, list] = defaultdict(list)
    for ob, act in decisions:
        if ob.get("select") and ob["select"]["type"] == ST_MAIN:
            turns[ob["current"]["turn"]].append((ob, act))
    order = sorted(turns)
    rows = []
    for k, t in enumerate(order):
        ob0 = turns[t][0][0]
        me = ob0["current"]["yourIndex"]
        if _active_id(ob0["current"], 1 - me) not in walls:
            continue
        prizes0 = len(ob0["current"]["players"][me].get("prize") or [])
        nxt = turns[order[k + 1]][0][0] if k + 1 < len(order) else None
        taken = (prizes0 - len(nxt["current"]["players"][me].get("prize") or [])) if nxt else None
        what = "no attack"
        retreated = False
        for ob, act in turns[t]:
            o = ob["select"]["option"][act[0]] if act else None
            if not o:
                continue
            if o["type"] == OT_RETREAT:
                retreated = True
            if o["type"] == OT_ATTACK:
                cur = ob["current"]
                defender = _active_id(cur, 1 - me)
                attacker = eng.cards.get(_active_id(cur, me) or -1, {})
                if defender not in walls:
                    what = "attacked another target"
                else:
                    what = "attacked wall with ex" if _is_ex(attacker) else "attacked wall with non-ex"
                break
        rows.append({"what": what, "taken": taken, "retreated": retreated})
    return rows


def summarize(rows: list[dict[str, Any]]) -> dict[str, Any]:
    c = Counter(r["what"] for r in rows)
    taken = [r["taken"] for r in rows if r["taken"] is not None]
    return {"turns": len(rows), "share": {k: v / max(1, len(rows)) for k, v in c.items()},
            "prizes_per_turn": statistics.mean(taken) if taken else 0.0,
            "retreat_share": sum(r["retreated"] for r in rows) / max(1, len(rows))}


# ---------------------------------------------------------------------------
# Simulated games with the real decklists
# ---------------------------------------------------------------------------

_W: dict = {}


def _init() -> None:
    # Simulated games run on v2: card IDs are identical in both engines (v2 only adds cards), and v1's
    # search is only reliable on positions recorded by the Kaggle ladder, not on live local games.
    _W["eng"] = Engine.get(2)


def _sim_job(args: tuple) -> list[dict[str, Any]]:
    deck_seat, decks, games, seed, kw, card = args
    eng = _W["eng"]
    walls = wall_ids(eng, card)
    rng = random.Random(seed)
    out = []
    for g in range(games):
        order = (0, 1) if g % 2 == 0 else (1, 0)                 # engine seat 0 always goes first
        d0, d1 = decks[order[0]], decks[order[1]]
        agents = (SearchAgent(eng, d0, d1, rng, **kw), SearchAgent(eng, d1, d0, rng, **kw))
        obs, _ = eng.game.battle_start(d0, d1)
        log = {0: [], 1: []}
        try:
            steps = 0
            while obs["current"]["result"] < 0 and steps < 5000:
                who = obs["current"]["yourIndex"]
                act = agents[who](obs)
                log[who].append((obs, act))
                obs = eng.game.battle_select(act)
                steps += 1
            res = obs["current"]["result"]
        except OSError:                                          # rare engine crash: drop this game
            continue
        finally:
            eng.game.battle_finish()
        deck_engine_seat = order.index(deck_seat)
        opp_engine_seat = 1 - deck_engine_seat
        out.append({"deck_won": 0.5 if res not in (0, 1) else float(res == deck_engine_seat),
                    "deck_first": deck_engine_seat == 0,
                    "behaviour": turn_behaviour(eng, log[opp_engine_seat], walls)})
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--card", default="Crustle")
    ap.add_argument("--fetch", action="store_true", help="scan known top-vs-top episodes for games with --card")
    ap.add_argument("--sim-games", type=int, default=4, help="simulated games per real game (same decklists)")
    ap.add_argument("--regret", type=int, default=12)
    ap.add_argument("--playouts", type=int, default=12)
    ap.add_argument("--workers", type=int, default=10)
    ap.add_argument("--no-agreement", action="store_true")
    args = ap.parse_args()
    if args.fetch:
        fetch(args.card)
    eng = Engine.get(1)
    walls = wall_ids(eng, args.card)
    files = sorted((DECK_DIR / slug(args.card)).glob("*.json"), key=lambda f: int(f.stem))
    if not files:
        sys.exit(f"no games with {args.card}; run with --fetch")

    real_out, real_beh, pairs = [], [], []
    for f in files:
        rep = json.loads(f.read_text(encoding="utf-8"))
        seats = seats_with(eng, rep, args.card)
        if len(seats) != 1:                                      # skip mirrors
            continue
        s = seats[0]
        win = winner_seat(rep)
        if win is not None:
            real_out.append(float(win == s))
        opp_dec = [(ob, act) for _, _, ob, act, _ in decision_points(rep, only_seat=1 - s)]
        real_beh += turn_behaviour(eng, opp_dec, walls)
        pairs.append((s, [rep["steps"][1][0]["action"], rep["steps"][1][1]["action"]]))
    print(f"{len(files)} games with {args.card}, {len(pairs)} non-mirror; damage-immune versions: {sorted(walls)}")

    kw = {}
    jobs = [(s, decks, args.sim_games, 7919 * k, kw, args.card) for k, (s, decks) in enumerate(pairs)]
    sim = []
    t0 = time.perf_counter()
    with Pool(args.workers, initializer=_init) as p:
        for k, res in enumerate(p.imap_unordered(_sim_job, jobs), 1):
            sim += res
            if k % 5 == 0 or k == len(jobs):
                print(f"  simulated {k}/{len(jobs)} deck pairs ({time.perf_counter() - t0:.0f}s)", flush=True)
    sim_beh = [r for g in sim for r in g["behaviour"]]

    print(f"\n1. Outcomes with the same decklists ({args.card} seat):")
    print(f"   real top-vs-top games: {args.card} won {statistics.mean(real_out) * 100:.0f}% of {len(real_out)}")
    print(f"   our agents:            {args.card} won {statistics.mean(g['deck_won'] for g in sim) * 100:.0f}% of {len(sim)}")

    rs, ss = summarize(real_beh), summarize(sim_beh)
    print(f"\n2. Opponent's turns that start with a damage-immune {args.card} Active:")
    print(f"   {'':30s} {'real':>8s} {'ours':>8s}")
    print(f"   {'turns observed':30s} {rs['turns']:8d} {ss['turns']:8d}")
    for k in ("attacked wall with ex", "attacked wall with non-ex", "attacked another target", "no attack"):
        print(f"   {k:30s} {rs['share'].get(k, 0) * 100:7.0f}% {ss['share'].get(k, 0) * 100:7.0f}%")
    print(f"   {'retreated during the turn':30s} {rs['retreat_share'] * 100:7.0f}% {ss['retreat_share'] * 100:7.0f}%")
    print(f"   {'Prizes taken per such turn':30s} {rs['prizes_per_turn']:8.2f} {ss['prizes_per_turn']:8.2f}")

    result = {"card": args.card, "games": len(files), "real_win": real_out, "sim_win": [g["deck_won"] for g in sim],
              "real_behaviour": rs, "sim_behaviour": ss}
    if not args.no_agreement:
        from decision_benchmark import run
        for role, pick in (("pilot", lambda rep: seats_with(eng, rep, args.card)[:1]),
                           ("opponent", lambda rep: [1 - seats_with(eng, rep, args.card)[0]])):
            print(f"\n3{'ab'[role == 'opponent']}. Decision agreement with the real {role} of {args.card}:")
            result[role] = run("all", 0, args.regret, args.playouts, 1, 0, kw, True,
                               files=[f for f in files if len(seats_with(eng, json.loads(f.read_text(encoding='utf-8')), args.card)) == 1],
                               seats=pick)
    out = ROOT / "matches" / "regression_results" / f"deck_{slug(args.card)}_{time.strftime('%Y%m%d-%H%M%S')}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=1, default=str), encoding="utf-8")
    print(f"\nsaved {out.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
