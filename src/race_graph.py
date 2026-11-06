"""
Race graph: plan toward a position where the NEXT turn can win.

Nodes are RACE STATES at the start of each turn, from the point of view of the player to move:
    (our Prizes left, their Prizes left,
     our turns-to-next-Prize bucket, their turns-to-next-Prize bucket,   # 1 / 2 / 3 / 4+
     we-can-win-next-turn flag, they-can-win-next-turn flag,
     our deck band, their deck band)                                     # <=3 / 4-10 / 11+ cards
A "can win next turn" flag means a whole-turn route (attack + spread + bombers) takes all remaining
Prizes or wipes the other board with its pieces likely available (cabt_bridge.turn_potential), or
the other side will start its turn with an empty deck (deck-out).

Edges are observed turn-to-turn transitions from real games (so they include how strong opponents
actually respond). The value of a node is computed by value iteration over ALL paths:
    A(s) = discounted chance the player to move wins, B(s) = discounted chance they lose,
    A(s) = g * sum P(s'|s) B(s'),  B(s) = g * sum P(s'|s) A(s')      (s' is from the opponent's side)
    value(s) = A(s) - B(s)
so faster wins and slower losses score higher. The single MOST LIKELY path to a "we can win next
turn" node is also available (Dijkstra on -log probability) to explain a plan.

  python src/race_graph.py --fetch 300        # stream more top-vs-top games, then rebuild
  python src/race_graph.py                    # rebuild from what is already saved
"""
from __future__ import annotations

import argparse
import heapq
import json
import math
import sys
import time
import urllib.request
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
from cabt_bridge import Engine, turn_potential  # noqa: E402
from state_graph import prize_clock  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
EP_DIR = ROOT / "matches" / "kaggle_episodes"
SEQ_FILE = ROOT / "matches" / "race_sequences.jsonl"
TABLE_FILE = ROOT / "matches" / "race_values.json"
WIN, LOSS = "WIN", "LOSS"
GAMMA = 0.9
FINE_MIN_VISITS = 5


def _bucket_next(x: float) -> int:
    return 0 if x <= 1 else (1 if x <= 2 else (2 if x <= 3 else 3))


def _bucket_deck(n: int) -> int:
    """Deck size band: 0 = 3 or fewer cards (deck-out is live), 1 = 4-10, 2 = 11+."""
    return 0 if n <= 3 else (1 if n <= 10 else 2)


def race_state(engine: Engine, cur: dict[str, Any], me: int) -> tuple:
    """
    Race state of `cur` from the perspective of player `me` (the player to move):
    (our Prizes, their Prizes, our next-Prize bucket, their next-Prize bucket,
     we-can-win-next-turn, they-can-win-next-turn, our deck band, their deck band).
    Win conditions covered by the flags: taking the last Prizes, wiping the other board, and
    DECK-OUT (a player who must draw from an empty deck at the start of their turn loses).
    """
    players = cur["players"]
    out = []
    for s in (me, 1 - me):
        out.append(len(players[s].get("prize") or []))
    for s in (me, 1 - me):
        out.append(_bucket_next(prize_clock(engine, cur, s)["next"]))
    for s in (me, 1 - me):
        tp = turn_potential(engine, cur, s)
        flag = max(tp["prize_out"], tp["wipe"]) >= 0.5
        # deck-out: the OTHER side starts its next turn unable to draw
        if players[1 - s].get("deckCount", 60) == 0:
            flag = True
        out.append(int(flag))
    for s in (me, 1 - me):
        out.append(_bucket_deck(players[s].get("deckCount", 60)))
    return tuple(out)


def coarse(state: tuple) -> tuple:
    """Back-off level: Prizes left and the two win flags."""
    return (state[0], state[1], state[4], state[5])


# ---------------------------------------------------------------------------
# Data: turn-start race states from replays
# ---------------------------------------------------------------------------

def sequence_from_replay(engine: Engine, replay: dict[str, Any]) -> dict[str, Any] | None:
    """Race state at the first main-phase decision of every turn, plus the winner."""
    r = replay.get("rewards") or []
    if len(r) != 2 or None in r or r[0] == r[1]:
        return None
    winner = 0 if r[0] > r[1] else 1
    steps = replay["steps"]
    seq, last_turn = [], None
    for i in range(1, len(steps) - 1):
        for seat in (0, 1):
            ob = steps[i][seat].get("observation") or {}
            sel, cur = ob.get("select"), ob.get("current") or {}
            if not sel or sel.get("type") != 0 or steps[i][seat].get("status") != "ACTIVE":
                continue
            if cur.get("yourIndex") != seat or cur.get("turn", 0) < 1 or cur["turn"] == last_turn:
                continue
            last_turn = cur["turn"]
            seq.append({"mover": seat, "turn": cur["turn"], "state": list(race_state(engine, cur, seat))})
    return {"winner": winner, "seq": seq} if seq else None


def fetch_and_extract(n_new: int, top_rank: int = 30, teams: int = 10) -> int:
    """Stream top-vs-top replays from Kaggle, keep only race-state sequences (raw replays not stored)."""
    sys.path.insert(0, str(ROOT / "matches"))
    from fetch_kaggle_episodes import COMPETITION_ID, _get, _post
    eng = Engine.get(1)
    done = set()
    if SEQ_FILE.exists():
        for line in SEQ_FILE.read_text(encoding="utf-8").splitlines():
            done.add(json.loads(line)["episode"])
    lb = _post("https://www.kaggle.com/api/i/competitions.LeaderboardService/GetLeaderboard",
               {"competitionId": COMPETITION_ID})["publicLeaderboard"]
    lb.sort(key=lambda x: x["rank"])
    threshold = float(lb[min(top_rank, len(lb)) - 1]["displayScore"])
    cands: dict[int, float] = {}
    for entry in lb[:teams]:
        for e in _post("https://www.kaggle.com/api/i/competitions.EpisodeService/ListEpisodes",
                       {"submissionId": entry["submissionId"]})["episodes"]:
            if e.get("state") == "COMPLETED" and len(e.get("agents", [])) == 2 and \
                    all((a.get("initialScore") or 0) >= threshold for a in e["agents"]):
                cands[e["id"]] = min(a["initialScore"] for a in e["agents"])
        time.sleep(1.0)
    todo = [eid for eid, _ in sorted(cands.items(), key=lambda kv: -kv[1]) if eid not in done][:n_new]
    added = 0
    with SEQ_FILE.open("a", encoding="utf-8") as out:
        for k, eid in enumerate(todo):
            local = EP_DIR / f"{eid}.json"
            try:
                raw = local.read_bytes() if local.exists() else _get(f"https://www.kaggleusercontent.com/episodes/{eid}.json")
                seq = sequence_from_replay(eng, json.loads(raw))
            except Exception as ex:  # one bad replay must not stop the stream
                print(f"  skip {eid}: {ex}")
                continue
            if seq:
                out.write(json.dumps({"episode": eid, **seq}) + "\n")
                added += 1
            if (k + 1) % 25 == 0:
                print(f"  {k + 1}/{len(todo)} replays processed", flush=True)
            if not local.exists():
                time.sleep(1.0)
    return added


# ---------------------------------------------------------------------------
# Graph + value iteration
# ---------------------------------------------------------------------------

class RaceGraph:
    def __init__(self) -> None:
        self.trans: dict[tuple, Counter] = defaultdict(Counter)       # fine state -> Counter(next fine state | WIN | LOSS)
        self.ctrans: dict[tuple, Counter] = defaultdict(Counter)      # coarse level
        self.visits: Counter = Counter()
        self.cvisits: Counter = Counter()
        self.games = 0

    def add(self, game: dict[str, Any]) -> None:
        seq, winner = game["seq"], game["winner"]
        self.games += 1
        for k, step in enumerate(seq):
            s = tuple(step["state"])
            self.visits[s] += 1
            self.cvisits[coarse(s)] += 1
            if k + 1 < len(seq) and seq[k + 1]["mover"] != step["mover"]:
                nxt = tuple(seq[k + 1]["state"])
                self.trans[s][nxt] += 1
                self.ctrans[coarse(s)][coarse(nxt)] += 1
            elif k + 1 == len(seq):
                end = WIN if step["mover"] == winner else LOSS
                self.trans[s][end] += 1
                self.ctrans[coarse(s)][end] += 1

    @staticmethod
    def _iterate(trans: dict[tuple, Counter], fallback=None, iters: int = 200) -> dict[tuple, tuple[float, float]]:
        A = {s: 0.0 for s in trans}
        B = {s: 0.0 for s in trans}
        for _ in range(iters):
            nA, nB = {}, {}
            for s, cnt in trans.items():
                tot = sum(cnt.values())
                a = b = 0.0
                for nxt, c in cnt.items():
                    p = c / tot
                    if nxt == WIN:
                        a += p
                    elif nxt == LOSS:
                        b += p
                    else:
                        if nxt in A:
                            na, nb = A[nxt], B[nxt]
                        elif fallback is not None:
                            na, nb = fallback(nxt)
                        else:
                            na = nb = 0.0
                        a += GAMMA * p * nb          # opponent loses from s' -> we win
                        b += GAMMA * p * na
                nA[s], nB[s] = a, b
            A, B = nA, nB
        return {s: (A[s], B[s]) for s in trans}

    def solve(self) -> None:
        self.cval = self._iterate(self.ctrans)

        def coarse_ab(s: tuple) -> tuple[float, float]:
            return self.cval.get(coarse(s), (0.0, 0.0))
        dense = {s: c for s, c in self.trans.items() if self.visits[s] >= FINE_MIN_VISITS}
        self.fval = self._iterate(dense, fallback=coarse_ab)

    def value(self, s: tuple) -> tuple[float, str]:
        """Discounted win minus loss chance for the player to move at race state `s`."""
        if s in getattr(self, "fval", {}):
            a, b = self.fval[s]
            return a - b, "fine"
        a, b = self.cval.get(coarse(s), (0.0, 0.0))
        return a - b, "coarse" if coarse(s) in self.cval else "none"

    def most_likely_path(self, start: tuple, max_len: int = 12) -> tuple[float, list]:
        """Most probable sequence of turn-start states from `start` to a node where the player who is
        to move at `start` can win next turn (their win flag set on their own turn), or to WIN."""
        best = {(start, 0): 0.0}
        tie = 0                                   # tie-breaker so states/terminal labels are never compared
        heap = [(0.0, tie, 0, start, [start])]
        while heap:
            cost, _, parity, s, path = heapq.heappop(heap)
            if s == WIN and parity == 1 or (s not in (WIN, LOSS) and parity == 0 and len(path) > 1 and s[4] == 1):
                return math.exp(-cost), path
            if s in (WIN, LOSS) or len(path) > max_len:
                continue
            cnt = self.trans.get(s)
            if not cnt:
                continue
            tot = sum(cnt.values())
            for nxt, c in cnt.items():
                np_ = 1 - parity
                nc = cost - math.log(c / tot)
                key = (nxt, np_)
                if nc < best.get(key, 1e18):
                    best[key] = nc
                    tie += 1
                    heapq.heappush(heap, (nc, tie, np_, nxt, path + [nxt]))
        return 0.0, []

    def save(self, path: Path) -> None:
        data = {"games": self.games, "gamma": GAMMA,
                "fine": [[list(s), v[0], v[1], self.visits[s]] for s, v in self.fval.items()],
                "coarse": [[list(s), v[0], v[1], self.cvisits[s]] for s, v in self.cval.items()]}
        path.write_text(json.dumps(data), encoding="utf-8")


class RaceValues:
    """Lightweight lookup of a solved race graph (used by the playing agent)."""

    def __init__(self, path: Path = TABLE_FILE):
        data = json.loads(path.read_text(encoding="utf-8"))
        self.fine = {tuple(s): a - b for s, a, b, _ in data["fine"]}
        self.coarse = {tuple(s): a - b for s, a, b, _ in data["coarse"]}

    def value(self, s: tuple) -> float:
        if s in self.fine:
            return self.fine[s]
        return self.coarse.get(coarse(s), 0.0)


def load_games() -> list[dict[str, Any]]:
    games = []
    if SEQ_FILE.exists():
        for line in SEQ_FILE.read_text(encoding="utf-8").splitlines():
            games.append(json.loads(line))
    return games


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--fetch", type=int, default=0, help="stream this many more top-vs-top replays first")
    args = ap.parse_args()
    if args.fetch or not SEQ_FILE.exists():
        print(f"extracting race sequences (cached replays first, then {args.fetch} streamed)...")
        added = fetch_and_extract(max(args.fetch, 40))
        print(f"  added {added} games")
    games = load_games()
    g = RaceGraph()
    for game in games:
        g.add(game)
    g.solve()
    g.save(TABLE_FILE)
    dense = sum(1 for s in g.visits if g.visits[s] >= FINE_MIN_VISITS)
    print(f"\n{g.games} games, {sum(g.visits.values())} turn states, {len(g.visits)} distinct race states "
          f"({dense} seen {FINE_MIN_VISITS}+ times), {len(g.cvisits)} coarse states. Saved {TABLE_FILE.relative_to(ROOT)}")

    print("\nValue for the player to move (discounted win - loss chance), by Prizes left [ours rows x theirs cols], no win flags:")
    print("        " + "".join(f"  opp {c}" for c in range(6, 0, -1)))
    for r in range(6, 0, -1):
        row = []
        for c in range(6, 0, -1):
            v = g.cval.get((r, c, 0, 0))
            row.append(f"  {v[0] - v[1]:+.2f}" if v and g.cvisits[(r, c, 0, 0)] >= 5 else "     - ")
        print(f"  us {r} " + "".join(row))
    print("\nEffect of the 'can win next turn' flags (coarse, averaged over Prize counts):")
    for flags, label in (((1, 0), "we can win next turn, they can't"), ((0, 1), "they can win next turn, we can't"),
                         ((1, 1), "both can"), ((0, 0), "neither")):
        vals = [(a - b, g.cvisits[s]) for s, (a, b) in g.cval.items() if (s[2], s[3]) == flags and g.cvisits[s] >= 5]
        if vals:
            wavg = sum(v * n for v, n in vals) / sum(n for _, n in vals)
            print(f"  {label:34s} {wavg:+.2f}  ({sum(n for _, n in vals)} turn states)")
    start = max((s for s in g.visits if s[0] == 6 and s[1] == 6), key=lambda s: g.visits[s], default=None)
    if start:
        p, path = g.most_likely_path(start)
        print(f"\nMost likely path from the commonest opening state {start} to 'we can win next turn' (p={p:.3f}):")
        for k, s in enumerate(path):
            if s in (WIN, LOSS):
                print(f"   -> {'we win' if (s == WIN) == (k % 2 == 1) else 'we lose'}")
                continue
            who = "us" if k % 2 == 0 else "them"
            print(f"   {who:4s} to move: {s}")


if __name__ == "__main__":
    main()
