"""
Finite-state view of a Pokemon TCG match: card-position states and a game graph.

STATE  (`encode`): where every one of each side's 60 cards is, as the player to move can see it.
    Zones: deck, hand, discard, prize, stadium, and in-play slots - "A" (Active) and "B1".."B8"
    (Bench) - where a card is either the Pokemon itself or attached to it as energy, tool or
    pre-evolution. Each in-play slot also carries its damage. Hidden cards (deck order, face-down
    Prizes, the opponent's hand) are stored as counts, because the player to move cannot see them.
    Plus: whose move it is, turn number, and the turn's flags (Supporter played, energy attached,
    retreated).

PRIZE CLOCK (`prize_clock`): for each side, the probable number of its turns until it takes its next
    Prize and until it takes all its remaining Prizes, from a greedy KO plan: energy still to
    attach (one per turn), hits needed against current HP, and the chance a missing gust/switch is
    drawn.

GRAPH (`StateGraph`): nodes are states, edges are the moves played between them, like a chess game
    tree built from real games. Two resolutions:
      * exact node  - hash of the full card-position table (identity / transpositions);
      * consolidated node - Prizes left, both prize clocks, KO exposure, board and hand summary.
        Exact positions almost never repeat; consolidated ones do, so each accumulates a
        reliable win rate.
"""
from __future__ import annotations

import gzip
import hashlib
import json
import math
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from cabt_bridge import (
    HIDDEN_HAND_P,
    Engine,
    _can_reach_active,
    _hand_pieces,
    _missing_energy,
    _prize_value,
    _protected_damage,
    ko_classes,
    KO_LIKELY,
)

DECK_SIZE = 60


# ---------------------------------------------------------------------------
# 1. Card positions
# ---------------------------------------------------------------------------

def card_positions(cur: dict[str, Any], side: int, viewer: int, resolving: dict[str, Any] | None = None) -> dict[str, Any]:
    """Every card of `side` and where it is, as `viewer` can see it."""
    p = cur["players"][side]
    cards: list[tuple[str, int, int | None]] = []          # (zone, card id, serial)
    slots = []
    mons = [("A", m) for m in (p.get("active") or []) if m] + [(f"B{i + 1}", m) for i, m in enumerate(p.get("bench") or [])]
    for slot, m in mons:
        cards.append((slot, m["id"], m.get("serial")))
        for kind in ("energyCards", "tools", "preEvolution"):
            for c in m.get(kind) or []:
                cards.append((f"{slot}:{kind[:-5] if kind.endswith('Cards') else kind}", c["id"], c.get("serial")))
        slots.append({"slot": slot, "id": m["id"], "damage": max(0, m.get("maxHp", 0) - m.get("hp", 0)),
                      "energy": sorted(c["id"] for c in m.get("energyCards") or []),
                      "tool": sorted(c["id"] for c in m.get("tools") or []),
                      "under": sorted(c["id"] for c in m.get("preEvolution") or [])})
    for c in p.get("discard") or []:
        cards.append(("discard", c["id"], c.get("serial")))
    face_down_prizes = 0
    for c in p.get("prize") or []:
        if c:
            cards.append(("prize", c["id"], c.get("serial")))
        else:
            face_down_prizes += 1
    hand = p.get("hand") if side == viewer else None
    for c in hand or []:
        cards.append(("hand", c["id"], c.get("serial")))
    for c in cur.get("stadium") or []:
        if c and c.get("playerIndex") == side:
            cards.append(("stadium", c["id"], c.get("serial")))
    # cards mid-action: being looked at (top-of-deck effects) or the Trainer currently resolving
    seen = {sr for _, _, sr in cards if sr is not None}
    for c in cur.get("looking") or []:
        if c and c.get("playerIndex") == side and c.get("serial") not in seen:
            cards.append(("looking", c["id"], c.get("serial")))
            seen.add(c.get("serial"))
    if resolving and resolving.get("playerIndex") == side and resolving.get("serial") not in seen:
        cards.append(("resolving", resolving["id"], resolving.get("serial")))
    hidden = {"deck": p.get("deckCount", 0), "prize": face_down_prizes,
              "hand": 0 if hand is not None else p.get("handCount", 0)}
    return {"cards": cards, "slots": slots, "hidden": hidden,
            "accounted": len(cards) + sum(hidden.values())}


# ---------------------------------------------------------------------------
# 2. Prize clocks
# ---------------------------------------------------------------------------

def prize_clock(engine: Engine, cur: dict[str, Any], side: int, horizon: int = 12) -> dict[str, float]:
    """
    Probable number of `side`'s turns until it takes its next Prize and until it takes all of its
    remaining Prizes. Greedy plan: repeatedly pick the (attacker, target) pair with the most Prizes
    per turn; a pair needs (energy still missing, one attach per turn) + (hits needed - 1) turns,
    plus a fraction of a turn when a gust or switch must still be drawn. Damage carries over between
    hits; Prizes beyond what is on the board cost ~2 turns each (the defender must bench more).
    """
    a, d = cur["players"][side], cur["players"][1 - side]
    prizes_left = len(a.get("prize") or [])
    if prizes_left == 0:
        return {"next": 0.0, "all": 0.0}
    pieces = _hand_pieces(engine, a.get("hand"))
    reach = _can_reach_active(engine, a, pieces)
    gust_p = HIDDEN_HAND_P["gust"] if pieces is None else (1.0 if pieces["gust"] else 0.0)
    attackers = [(m, True) for m in (a.get("active") or []) if m] + [(m, False) for m in (a.get("bench") or [])]
    targets = [{"mon": m, "active": True} for m in (d.get("active") or []) if m] + \
              [{"mon": m, "active": False} for m in (d.get("bench") or [])]
    for t in targets:
        t["hp"] = float(max(10, t["mon"]["hp"]))
        t["pv"] = _prize_value(engine, t["mon"]["id"])
    powered: set[int] = set()            # attackers already given their energy in this plan
    turns, first, need = 0.0, None, prizes_left
    while need > 0 and turns < horizon:
        best = None
        for t in targets:
            tc = engine.cards.get(t["mon"]["id"], {})
            for am, a_active in attackers:
                ac = engine.cards.get(am["id"], {})
                for aid in ac.get("attacks", []):
                    atk = engine.attacks.get(aid)
                    if not atk or not atk.get("damage"):
                        continue
                    dmg = float(atk["damage"])
                    if t["active"]:
                        if tc.get("weakness") is not None and tc.get("weakness") == ac.get("energyType"):
                            dmg *= 2
                        if tc.get("resistance") is not None and tc.get("resistance") == ac.get("energyType"):
                            dmg = max(0.0, dmg - 30)
                    elif tc.get("tera"):
                        continue
                    dmg = _protected_damage(engine, ac, atk, t["mon"], dmg)
                    if dmg <= 0:
                        continue
                    miss = 0 if id(am) in powered else _missing_energy(atk.get("energies") or [], am.get("energies") or [])
                    hits = math.ceil(t["hp"] / dmg)
                    cost = max(1, miss) + hits - 1
                    if not a_active and id(am) not in powered:
                        cost += 0.0 if reach >= 1.0 else 0.5
                    if not t["active"] and "of your opponent's pokémon" not in (atk.get("text") or "").lower():
                        cost += 0.0 if gust_p >= 1.0 else 0.5 * (1.0 - gust_p) + 0.25
                    rate = min(t["pv"], need) / cost
                    if best is None or rate > best[0]:
                        best = (rate, cost, t, am)
        if best is None:
            turns += 2.0 * need            # nothing on the board to take: wait for new targets
            break
        _, cost, t, am = best
        turns += cost
        powered.add(id(am))
        need -= t["pv"]
        targets.remove(t)
        if first is None:
            first = turns
        if not targets and need > 0:
            turns += 2.0 * need
            break
    return {"next": round(min(first if first is not None else turns, horizon), 2), "all": round(min(turns, horizon), 2)}


# ---------------------------------------------------------------------------
# 3. Ongoing effects (tracked from the engine's event log)
# ---------------------------------------------------------------------------

LOG_TURN_START, LOG_PLAY, LOG_ATTACK = 2, 10, 15
EFFECT_CATEGORIES = [
    ("item lock", r"can't play any item"),
    ("evolution lock", r"can't play any pokémon from their hand to evolve"),
    ("can't retreat", r"can't retreat"),
    ("can't attack", r"can't (?:attack|use attacks|use [a-z' -]+)"),
    ("damage prevention", r"prevent all damage"),
    ("damage reduction", r"takes \d+ less damage"),
    ("damage boost", r"\d+ more damage"),
]
LOCKS = {"item lock", "evolution lock", "can't retreat", "can't attack"}
SHIELDS = {"damage prevention", "damage reduction"}


class EffectTracker:
    """
    Follows one player's stream of engine logs and keeps the effects currently in force:
      "during your opponent's next turn, ..." -> applies to the OTHER side for its next turn;
      "during your next turn, ..."            -> applies to the attacker's side for its next turn;
      "during this turn, ..."                 -> applies until the current turn ends.
    Each effect expires when the right number of turns have started.
    """

    def __init__(self, engine: Engine):
        self.engine = engine
        self.turns_started = 0
        self.effects: list[dict[str, Any]] = []

    @staticmethod
    def _clauses(text: str) -> list[tuple[str, str]]:
        t = (text or "").lower().replace("’", "'")
        out = []
        for m in re.finditer(r"during (your opponent's next turn|your next turn|this turn),?\s*([^.]*)", t):
            out.append((m.group(1), m.group(2)))
        return out

    def _add(self, who: int, source: str, text: str) -> None:
        for when, clause in self._clauses(text):
            for cat, pat in EFFECT_CATEGORIES:
                if re.search(pat, clause):
                    if when == "your opponent's next turn":
                        target, expires = 1 - who, self.turns_started + 2
                    elif when == "your next turn":
                        target, expires = who, self.turns_started + 3
                    else:
                        target, expires = who, self.turns_started + 1
                    self.effects.append({"side": target, "category": cat, "source": source, "expires": expires})
                    break

    def feed(self, logs: list[dict[str, Any]] | None) -> None:
        for lg in logs or []:
            t = lg.get("type")
            if t == LOG_TURN_START:
                self.turns_started += 1
                self.effects = [e for e in self.effects if e["expires"] > self.turns_started]
            elif t == LOG_ATTACK:
                a = self.engine.attacks.get(lg.get("attackId"), {})
                self._add(lg.get("playerIndex", 0), a.get("name", "attack"), a.get("text", ""))
            elif t == LOG_PLAY:
                c = self.engine.cards.get(lg.get("cardId"), {})
                text = " ".join(sk.get("text", "") for sk in c.get("skills") or [])
                self._add(lg.get("playerIndex", 0), c.get("name", "card"), text)

    def active_for(self, side: int) -> list[tuple[str, str]]:
        return sorted((e["category"], e["source"]) for e in self.effects if e["side"] == side)


# ---------------------------------------------------------------------------
# 4. Encoding: exact key + consolidated key
# ---------------------------------------------------------------------------

STATUS_KEYS = ("poisoned", "burned", "asleep", "paralyzed", "confused")


def _bucket(x: float, edges: list[float]) -> int:
    for i, e in enumerate(edges):
        if x <= e:
            return i
    return len(edges)


def _status_code(p: dict[str, Any]) -> int:
    """Special Condition on the Active: 0 none, 1 damage over time (Poisoned/Burned),
    2 can't act (Asleep/Paralyzed), 3 Confused."""
    if p.get("asleep") or p.get("paralyzed"):
        return 2
    if p.get("confused"):
        return 3
    if p.get("poisoned") or p.get("burned"):
        return 1
    return 0


def encode(engine: Engine, obs: dict[str, Any], tracker: EffectTracker | None = None) -> dict[str, Any]:
    """
    State of `obs` from the perspective of the player to move (`me`): every card's position,
    damage on every in-play slot, Special Conditions, the Stadium, effects in force (from
    `tracker`, if given), turn flags, and both prize clocks.
    """
    cur = obs["current"]
    me = cur["yourIndex"]
    resolving = (obs.get("select") or {}).get("effect")
    stadium = (cur.get("stadium") or [None])[0]
    sides = {}
    for label, s in (("me", me), ("opp", 1 - me)):
        pos = card_positions(cur, s, me, resolving)
        clock = prize_clock(engine, cur, s)
        exposure = ko_classes(engine, cur, 1 - s)          # how the OTHER side could KO this side's Pokemon
        exposed = max((k["prizes"] for k in exposure if k["cls"] >= KO_LIKELY), default=0)
        p = cur["players"][s]
        act = (p.get("active") or [None])[0]
        effects = tracker.active_for(s) if tracker else []
        sides[label] = {"pos": pos, "clock": clock, "exposed": exposed, "prizes": len(p.get("prize") or []),
                        "hand": p.get("handCount", 0), "deck": p.get("deckCount", 0),
                        "in_play": len(pos["slots"]),
                        "active_hp": (act["hp"] / max(1, act["maxHp"])) if act else 0.0,
                        "damage_total": sum(sl["damage"] for sl in pos["slots"]),
                        "status": _status_code(p),
                        "statuses": [k for k in STATUS_KEYS if p.get(k)],
                        "effects": effects,
                        "locked": int(any(c in LOCKS for c, _ in effects)),
                        "shielded": int(any(c in SHIELDS for c, _ in effects))}
    flags = (cur.get("supporterPlayed"), cur.get("energyAttached"), cur.get("retreated"))
    stadium_owner = None if not stadium else ("me" if stadium.get("playerIndex") == me else "opp")
    exact = {"turn": cur["turn"], "flags": flags, "stadium": [stadium["id"], stadium_owner] if stadium else None}
    for label in ("me", "opp"):
        sd = sides[label]
        exact[label] = sorted((z, c) for z, c, _ in sd["pos"]["cards"])
        exact[label + "_hidden"] = sd["pos"]["hidden"]
        exact[label + "_damage"] = [(sl["slot"], sl["damage"]) for sl in sd["pos"]["slots"]]
        exact[label + "_status"] = sd["statuses"]
        exact[label + "_effects"] = sd["effects"]
    exact_key = hashlib.sha1(json.dumps(exact, sort_keys=True, default=str).encode()).hexdigest()[:16]

    def summary(sd: dict[str, Any]) -> tuple:
        return (sd["prizes"],
                _bucket(sd["clock"]["next"], [1, 2, 3]),          # turns to next Prize: 1 / 2 / 3 / 4+
                _bucket(sd["clock"]["all"], [2, 4, 6]),           # turns to take all Prizes: <=2 / <=4 / <=6 / 7+
                min(sd["exposed"], 3),                            # Prizes this side exposes to a likely KO
                _bucket(sd["in_play"], [1, 3, 5]),                # 1 / 2-3 / 4-5 / 6+ Pokemon in play
                _bucket(sd["hand"], [2, 5]),                      # hand 0-2 / 3-5 / 6+
                _bucket(sd["active_hp"], [0.34, 0.67]),           # Active HP left: <=1/3 / <=2/3 / more
                sd["status"],                                     # Special Condition on the Active
                sd["locked"],                                     # under an item/evolution/retreat/attack lock
                sd["shielded"])                                   # protected by damage prevention/reduction
    consolidated = ("me",) + summary(sides["me"]) + ("opp",) + summary(sides["opp"]) + \
                   ("stadium", {"me": 1, "opp": 2}.get(stadium_owner or "", 0))
    race = sides["opp"]["clock"]["all"] - sides["me"]["clock"]["all"]   # >0: we finish first
    return {"me": me, "turn": cur["turn"], "exact_key": exact_key, "node": consolidated, "race": race,
            "clock_me": sides["me"]["clock"], "clock_opp": sides["opp"]["clock"],
            "accounted": (sides["me"]["pos"]["accounted"], sides["opp"]["pos"]["accounted"]), "sides": sides}


NODE_FIELDS = ["prizes left", "turns to next Prize", "turns to all Prizes", "Prizes exposed", "Pokémon in play",
               "hand size", "Active HP left", "Special Condition", "locked", "shielded"]


def describe_node(node: tuple) -> str:
    me, opp = node[1:11], node[12:22]
    nxt, allp = ["1", "2", "3", "4+"], ["<=2", "<=4", "<=6", "7+"]
    play, hand, hp = ["1", "2-3", "4-5", "6+"], ["0-2", "3-5", "6+"], ["<=1/3", "<=2/3", ">2/3"]
    cond = ["", ", Poisoned/Burned", ", Asleep/Paralyzed", ", Confused"]

    def one(s: tuple) -> str:
        return (f"{s[0]} Prizes left, next Prize in {nxt[s[1]]} turns, all in {allp[s[2]]}, exposes {s[3]}, "
                f"{play[s[4]]} in play, hand {hand[s[5]]}, Active HP {hp[s[6]]}{cond[s[7]]}"
                f"{', locked' if s[8] else ''}{', shielded' if s[9] else ''}")
    stad = {0: "no Stadium", 1: "Stadium: player to move's", 2: "Stadium: opponent's"}.get(node[-1], "")
    return f"to move: {one(me)} | opponent: {one(opp)} | {stad}"


# ---------------------------------------------------------------------------
# 5. The game graph
# ---------------------------------------------------------------------------

class StateGraph:
    """Consolidated states as nodes, moves as edges, with win statistics backed up from real games."""

    def __init__(self) -> None:
        self.nodes: dict[tuple, dict[str, Any]] = {}
        self.edges: dict[tuple, Counter] = defaultdict(Counter)    # (from node, move) -> Counter(to node)
        self.exact_per_node: dict[tuple, set] = defaultdict(set)
        self.games = 0

    def add_game(self, states: list[dict[str, Any]], moves: list[str], winner: int | None) -> None:
        """`states[i]` = encode() at decision i, `moves[i]` = move played there."""
        self.games += 1
        prev = None
        for st, mv in zip(states, moves):
            n = self.nodes.setdefault(st["node"], {"visits": 0, "wins": 0.0, "race": []})
            n["visits"] += 1
            n["wins"] += 0.5 if winner is None else (1.0 if winner == st["me"] else 0.0)
            if len(n["race"]) < 200:
                n["race"].append(st["race"])
            self.exact_per_node[st["node"]].add(st["exact_key"])
            if prev is not None:
                self.edges[(prev[0], prev[1])][st["node"]] += 1
            prev = (st["node"], mv)

    def value(self, node: tuple, prior: float = 0.5, strength: float = 4.0) -> tuple[float, int]:
        """Win rate for the player to move at `node`, shrunk toward `prior` when visits are few."""
        n = self.nodes.get(node)
        if not n:
            return prior, 0
        return (n["wins"] + prior * strength) / (n["visits"] + strength), n["visits"]

    def stats(self) -> dict[str, Any]:
        visits = [n["visits"] for n in self.nodes.values()]
        exact = sum(len(v) for v in self.exact_per_node.values())
        return {"games": self.games, "consolidated_nodes": len(self.nodes), "exact_states": exact,
                "edges": len(self.edges), "transitions": sum(sum(c.values()) for c in self.edges.values()),
                "nodes_seen_10plus": sum(1 for v in visits if v >= 10),
                "mean_branching": round(sum(len(c) for c in self.edges.values()) / max(1, len(self.edges)), 2)}

    def save(self, path: Path) -> None:
        data = {"games": self.games,
                "nodes": [[list(k), v["visits"], v["wins"], len(self.exact_per_node[k])] for k, v in self.nodes.items()],
                "edges": [[list(k[0]), k[1], [[list(t), c] for t, c in cnt.items()]] for k, cnt in self.edges.items()]}
        with gzip.open(path, "wt", encoding="utf-8") as f:
            json.dump(data, f)

    @classmethod
    def load(cls, path: Path) -> "StateGraph":
        g = cls()
        with gzip.open(path, "rt", encoding="utf-8") as f:
            data = json.load(f)
        g.games = data["games"]
        for k, visits, wins, n_exact in data["nodes"]:
            g.nodes[tuple(k)] = {"visits": visits, "wins": wins, "race": []}
            g.exact_per_node[tuple(k)] = set(range(n_exact))
        for frm, mv, tos in data["edges"]:
            for t, c in tos:
                g.edges[(tuple(frm), mv)][tuple(t)] = c
        return g


def move_label(obs: dict[str, Any], action: list[int]) -> str:
    """Short move name for graph edges: main-phase option type (or the sub-choice context)."""
    sel = obs["select"]
    names = {7: "play", 8: "attach", 9: "evolve", 10: "ability", 11: "discard", 12: "retreat", 13: "attack", 14: "end"}
    if sel["type"] == 0 and action:
        return names.get(sel["option"][action[0]]["type"], "other")
    return f"choice:{sel.get('context')}"
