"""
Bridge to the CABT rules engine (Kaggle Pokemon TCG AI Battle Challenge engine,
vendored from github.com/Kaggle/kaggle-environments, Apache-2.0, in vendor/cabt/).

The engine owns the RULES: every card effect, legal options, Prizes, Knock Outs.
We own the DECISIONS: `SearchAgent` evaluates each main-phase option by stepping the
engine's forward model (SearchBegin/SearchStep) into the resulting state and scoring
that state, i.e. it compares transitions by where they lead. Hidden information
(deck order, Prizes, the opponent's hand) is filled by sampling from the known
decklists minus every card already visible.

Limits: the engine's card pool is fixed (it is a compiled DLL). Cards it lacks
(e.g. Mew ex, Pokemon Center Lady, all of Delta Reign) make a deck unplayable in the
engine; `CardMap.deck_ids` reports them so callers can fall back to `game_sim`.
"""
from __future__ import annotations

import ctypes
import json
import random
import re
import sys
import unicodedata
from collections import Counter
from pathlib import Path
from typing import Any

from card_compiler import CompiledCard, StandardCardDatabase

ENGINE_DIR = Path(__file__).resolve().parents[1] / "vendor" / "cabt"

# Engine names that differ from printed English names.
NAME_ALIASES = {
    "telepath psychic energy": "telepathic psychic energy",
    "grow grass energy": "growing grass energy",
    "rock fighting energy": "rocky fighting energy",
}
ENERGY_LETTERS = {"g": "grass", "r": "fire", "w": "water", "l": "lightning", "p": "psychic",
                  "f": "fighting", "d": "darkness", "m": "metal", "n": "dragon", "c": "colorless"}

# SelectType / SelectContext / OptionType values from the engine API (matches/cg_api.py)
ST_MAIN = 0
CTX = {"SETUP_ACTIVE": 1, "SETUP_BENCH": 2, "SWITCH": 3, "TO_ACTIVE": 4, "TO_BENCH": 5, "TO_FIELD": 6,
       "TO_HAND": 7, "DISCARD": 8, "TO_DECK": 9, "TO_DECK_BOTTOM": 10, "DAMAGE_COUNTER": 13,
       "DAMAGE_COUNTER_ANY": 14, "DAMAGE": 15, "HEAL": 17, "ATTACH_FROM": 21, "ATTACH_TO": 22,
       "IS_FIRST": 41, "MULLIGAN": 42, "ACTIVATE": 43}
OT_YES, OT_NO, OT_CARD, OT_PLAY, OT_ATTACH, OT_EVOLVE, OT_ABILITY, OT_RETREAT, OT_ATTACK, OT_END = 1, 2, 3, 7, 8, 9, 10, 12, 13, 14
AREA_DECK, AREA_HAND, AREA_DISCARD, AREA_ACTIVE, AREA_BENCH = 1, 2, 3, 4, 5


def norm_name(name: str) -> str:
    name = (name or "").replace("’", "'")
    name = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode().lower()
    m = re.match(r"^basic \{(\w)\} energy$", name)
    if m:
        name = f"{ENERGY_LETTERS.get(m.group(1), m.group(1))} energy"
    name = re.sub(r"\{(\w)\}", lambda mm: ENERGY_LETTERS.get(mm.group(1), mm.group(1)), name)
    name = re.sub(r"[^a-z0-9' ]", "", name)
    name = re.sub(r"\s+", " ", name).strip()
    return NAME_ALIASES.get(name, name)


# ---------------------------------------------------------------------------
# Engine
# ---------------------------------------------------------------------------

class Engine:
    """One loaded engine version. Version 2 = current Kaggle engine; version 1 = the pre-September-2026
    engine the competition's ladder games were played on (vendor/cabt/cg/v1)."""
    _instances: dict[int, "Engine"] = {}

    def __init__(self, version: int = 2) -> None:
        if str(ENGINE_DIR) not in sys.path:
            sys.path.insert(0, str(ENGINE_DIR))
        from cg import game as cg_game  # noqa: E402  (vendored Kaggle wrapper)
        from cg.sim import get_lib  # noqa: E402
        self.version = version
        self.game = cg_game            # battle_* helpers drive the v2 library (cg.sim.Battle.lib)
        lib = get_lib(version)
        self.lib = lib
        lib.AllCard.restype = ctypes.c_char_p
        lib.AllAttack.restype = ctypes.c_char_p
        lib.AgentStart.restype = ctypes.c_void_p
        lib.SearchBegin.restype = ctypes.c_char_p
        lib.SearchBegin.argtypes = [ctypes.c_void_p, ctypes.c_char_p, ctypes.c_int] + [ctypes.POINTER(ctypes.c_int)] * 6 + [ctypes.c_int]
        lib.SearchStep.restype = ctypes.c_char_p
        lib.SearchStep.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.POINTER(ctypes.c_int), ctypes.c_int]
        lib.SearchEnd.argtypes = [ctypes.c_void_p]
        self.agent_ptr = lib.AgentStart()
        self.cards: dict[int, dict[str, Any]] = {c["cardId"]: c for c in json.loads(lib.AllCard().decode())}
        self.attacks: dict[int, dict[str, Any]] = {a["attackId"]: a for a in json.loads(lib.AllAttack().decode())}

    @classmethod
    def get(cls, version: int = 2) -> "Engine":
        if version not in cls._instances:
            cls._instances[version] = Engine(version)
        return cls._instances[version]

    @staticmethod
    def _arr(xs: list[int]):
        return (ctypes.c_int * len(xs))(*xs)

    def search_begin(self, obs: dict[str, Any], your_deck: list[int], your_prize: list[int], opp_deck: list[int],
                     opp_prize: list[int], opp_hand: list[int], opp_active: list[int]) -> dict[str, Any] | None:
        sbi = obs.get("search_begin_input")
        if not sbi:
            return None
        res = json.loads(self.lib.SearchBegin(self.agent_ptr, sbi.encode("ascii"), len(sbi), self._arr(your_deck),
                                              self._arr(your_prize), self._arr(opp_deck), self._arr(opp_prize),
                                              self._arr(opp_hand), self._arr(opp_active), 0).decode())
        return None if res.get("error") else res["state"]

    def search_step(self, search_id: int, select: list[int]) -> dict[str, Any] | None:
        res = json.loads(self.lib.SearchStep(self.agent_ptr, search_id, self._arr(select), len(select)).decode())
        return None if res.get("error") else res["state"]

    def search_end(self) -> None:
        self.lib.SearchEnd(self.agent_ptr)


# ---------------------------------------------------------------------------
# Card mapping
# ---------------------------------------------------------------------------

class CardMap:
    def __init__(self, engine: Engine, db: StandardCardDatabase):
        self.engine = engine
        self.db = db
        self.by_name: dict[str, list[dict[str, Any]]] = {}
        for c in engine.cards.values():
            self.by_name.setdefault(norm_name(c["name"]), []).append(c)
        self._cache: dict[str, int | None] = {}

    def engine_id(self, card: CompiledCard) -> int | None:
        if card.uid in self._cache:
            return self._cache[card.uid]
        cands = self.by_name.get(norm_name(card.name), [])
        cid = None
        if len(cands) == 1:
            cid = cands[0]["cardId"]
        elif cands:
            mine = {norm_name(a.name) for a in card.attacks}

            def score(ec: dict[str, Any]) -> tuple:
                theirs = {norm_name(self.engine.attacks[a]["name"]) for a in ec.get("attacks", []) if a in self.engine.attacks}
                return (len(mine & theirs) - len(mine ^ theirs), ec.get("hp", 0) == card.hp)
            cid = max(cands, key=score)["cardId"]
        self._cache[card.uid] = cid
        return cid

    def deck_ids(self, deck: dict[CompiledCard, int]) -> tuple[list[int], list[str]]:
        ids: list[int] = []
        missing: list[str] = []
        for c, n in deck.items():
            cid = self.engine_id(c)
            if cid is None:
                missing.append(f"{n}x {c.name} ({c.uid})")
            else:
                ids += [cid] * n
        return ids, missing


# ---------------------------------------------------------------------------
# State evaluation (from one player's perspective)
# ---------------------------------------------------------------------------

def _prize_value(engine: Engine, card_id: int) -> int:
    c = engine.cards.get(card_id, {})
    return 3 if c.get("megaEx") else (2 if c.get("ex") else 1)


def _best_attack_damage(engine: Engine, card_id: int) -> int:
    c = engine.cards.get(card_id, {})
    return max((engine.attacks.get(a, {}).get("damage", 0) or 0 for a in c.get("attacks", [])), default=0)


E_COLORLESS, E_RAINBOW, E_ROCKET = 0, 10, 11
E_PSYCHIC, E_DARKNESS = 5, 7


def _missing_energy(cost: list[int], have: list[int]) -> int:
    """How many energy units are missing to pay `cost` (EnergyType ints) from `have`."""
    pool = Counter(have)
    missing = 0
    for t in [c for c in cost if c != E_COLORLESS]:
        if pool[t] > 0:
            pool[t] -= 1
        elif t in (E_PSYCHIC, E_DARKNESS) and pool[E_ROCKET] > 0:
            pool[E_ROCKET] -= 1
        elif pool[E_RAINBOW] > 0:
            pool[E_RAINBOW] -= 1
        else:
            missing += 1
    left = sum(v for v in pool.values() if v > 0)
    return missing + max(0, sum(1 for c in cost if c == E_COLORLESS) - left)


TYPE_LETTER = {"g": 1, "r": 2, "w": 3, "l": 4, "p": 5, "f": 6, "d": 7, "m": 8, "n": 9, "c": 0}


def _ntext(t: str | None) -> str:
    return (t or "").lower().replace("’", "'").replace("{ex}", "ex")


def _is_ex(card: dict[str, Any]) -> bool:
    return bool(card.get("ex") or card.get("megaEx"))   # Mega ex carry megaEx=True, ex=False


def _protected_damage(engine: Engine, attacker_card: dict[str, Any], attack: dict[str, Any],
                      target: dict[str, Any], dmg: float) -> float:
    """
    Damage `attack` would actually do to `target` after the defender's printed protections:
    immunity (Crustle vs Pokemon ex, Ariados vs Basic), flat reductions (Thick Scale, Custom Vest,
    full-HP armor). Attacks that ignore effects on the Active bypass them.
    """
    if "isn't affected by any effects on your opponent's active" in _ntext(attack.get("text")):
        return dmg
    tc = engine.cards.get(target["id"], {})
    texts = [_ntext(s.get("text")) for s in tc.get("skills") or []]
    for tool in target.get("tools") or []:
        texts += [_ntext(s.get("text")) for s in engine.cards.get(tool["id"], {}).get("skills") or []]
    a_type = attacker_card.get("energyType")
    for t in texts:
        if "prevent all damage done to this pokémon by attacks from your opponent's pokémon ex" in t and _is_ex(attacker_card):
            return 0.0
        if "prevent all damage done to this pokémon by attacks from your opponent's basic" in t and attacker_card.get("basic"):
            return 0.0
        m = re.search(r"takes (\d+) less damage from attacks", t)
        if not m:
            continue
        if "full hp" in t and target.get("hp", 0) < target.get("maxHp", 0):
            continue
        if "isn't a mega evolution" in t and _is_ex(tc) and tc.get("megaEx"):
            continue
        if "mega evolution pokémon ex" in t.split("less damage", 1)[1] and not attacker_card.get("megaEx"):
            continue
        types = re.findall(r"\{(\w)\}", t.split("less damage", 1)[1])
        if types and a_type not in {TYPE_LETTER.get(x.lower()) for x in types}:
            continue
        dmg = max(0.0, dmg - int(m.group(1)))
    return dmg


def _threat(engine: Engine, attacker: dict[str, Any] | None, target: dict[str, Any] | None) -> tuple[float, int]:
    """(best damage vs target among attacks, energy still missing for it), after Weakness,
    Resistance and the target's protections."""
    if not attacker or not target:
        return 0.0, 99
    ac = engine.cards.get(attacker["id"], {})
    tc = engine.cards.get(target["id"], {})
    best, best_miss = 0.0, 99
    for aid in ac.get("attacks", []):
        a = engine.attacks.get(aid)
        if not a:
            continue
        dmg = float(a.get("damage") or 0)
        if dmg <= 0:
            continue
        if tc.get("weakness") is not None and tc.get("weakness") == ac.get("energyType"):
            dmg *= 2
        if tc.get("resistance") is not None and tc.get("resistance") == ac.get("energyType"):
            dmg = max(0.0, dmg - 30)
        dmg = _protected_damage(engine, ac, a, target, dmg)
        if dmg <= 0:
            continue
        miss = _missing_energy(a.get("energies") or [], attacker.get("energies") or [])
        if (miss, -dmg) < (best_miss, -best):
            best, best_miss = dmg, miss
    return best, best_miss


def _spread_threat(engine: Engine, attacker: dict[str, Any]) -> tuple[float, str, int]:
    """(bench damage amount, "counters"|"damage", energy missing) for the attacker's best bench-hitting attack."""
    ac = engine.cards.get(attacker["id"], {})
    best = (0.0, "", 99)
    for aid in ac.get("attacks", []):
        a = engine.attacks.get(aid)
        if not a:
            continue
        t = _ntext(a.get("text"))
        m = re.search(r"put (\d+) damage counters on your opponent's benched", t) or \
            re.search(r"place (\d+) damage counters on 1 of your opponent's benched", t)
        if m:
            amt, kind = 10.0 * int(m.group(1)), "counters"
        else:
            m = re.search(r"(\d+) damage to (?:1|2|each) of your opponent's benched", t)
            if not m:
                continue
            amt, kind = float(m.group(1)), "damage"
        miss = _missing_energy(a.get("energies") or [], attacker.get("energies") or [])
        if (miss, -amt) < (best[2], -best[0]):
            best = (amt, kind, miss)
    return best


# ---------------------------------------------------------------------------
# KO reachability classes (how exposed each Pokemon is to a Knock Out next turn)
# ---------------------------------------------------------------------------
KO_SURVIVES, KO_POSSIBLE, KO_LIKELY, KO_EASY = 0, 1, 2, 3
KO_CLASS_NAME = {KO_SURVIVES: "survives", KO_POSSIBLE: "KO-able (needs a draw)",
                 KO_LIKELY: "very KO-able (all pieces in hand/play)", KO_EASY: "easy KO (1 action)"}
# Chance an unseen hand holds each piece (used when the attacker's hand is hidden, i.e. the opponent's).
HIDDEN_HAND_P = {"energy": 0.7, "switch": 0.45, "gust": 0.5}


def _hand_pieces(engine: Engine, hand: list[dict[str, Any]] | None) -> dict[str, Any] | None:
    """What the attacking side holds that can complete a KO: energy types, a switch, a gust."""
    if hand is None:
        return None
    energies, switch, gust = [], False, False
    for c in hand:
        cd = engine.cards.get(c["id"], {})
        if cd.get("cardType") in (5, 6):
            energies.append(cd.get("energyType", E_COLORLESS))
        text = " ".join(_ntext(s.get("text")) for s in cd.get("skills") or [])
        if "switch in 1 of your opponent's benched" in text:
            gust = True
        if "switch your active pokémon with 1 of your benched" in text:
            switch = True
    return {"energies": energies, "switch": switch, "gust": gust}


def _can_reach_active(engine: Engine, p: dict[str, Any], pieces: dict[str, Any] | None) -> float:
    """1.0 if a benched attacker can be brought Active (free/payable retreat or a switch card), else
    the chance the hidden hand has a switch, else 0."""
    act = (p.get("active") or [None])[0]
    if act is not None:
        rc = engine.cards.get(act["id"], {}).get("retreatCost", 0)
        if rc <= len(act.get("energies") or []):
            return 1.0
    if pieces is None:
        return HIDDEN_HAND_P["switch"]
    return 1.0 if pieces["switch"] else 0.0


def ko_classes(engine: Engine, cur: dict[str, Any], attacker_side: int) -> list[dict[str, Any]]:
    """
    Classify each of the DEFENDER's Pokemon by how reachable a Knock Out is on the attacker's next turn:
      easy KO      - an attacker that can already pay for the attack takes it out (attack is the only action);
      very KO-able - KO needs more actions (attach the turn's energy, switch the attacker in, gust a
                     benched target) but every piece is already in hand/play;
      KO-able      - KO is in reach but needs a piece that must be drawn;
      survives     - nothing can take it out next turn.
    Each entry carries `weight`, the chance-adjusted strength of the best route (hidden hands use
    HIDDEN_HAND_P for the pieces they might hold).
    """
    a, d = cur["players"][attacker_side], cur["players"][1 - attacker_side]
    pieces = _hand_pieces(engine, a.get("hand"))
    reach_active = _can_reach_active(engine, a, pieces)
    attackers = [(m, True) for m in (a.get("active") or []) if m] + [(m, False) for m in (a.get("bench") or [])]
    defenders = [(m, True) for m in (d.get("active") or []) if m] + [(m, False) for m in (d.get("bench") or [])]
    out = []
    for dm, d_active in defenders:
        dc = engine.cards.get(dm["id"], {})
        hp_left = max(10, dm["hp"])
        best_cls, best_w = KO_SURVIVES, 0.0
        for am, a_active in attackers:
            ac = engine.cards.get(am["id"], {})
            for aid in ac.get("attacks", []):
                atk = engine.attacks.get(aid)
                if not atk or not atk.get("damage"):
                    continue
                text = _ntext(atk.get("text"))
                snipe = "of your opponent's pokémon" in text and "damage to" in text
                dmg = float(atk["damage"])
                if d_active:
                    if dc.get("weakness") is not None and dc.get("weakness") == ac.get("energyType"):
                        dmg *= 2
                    if dc.get("resistance") is not None and dc.get("resistance") == ac.get("energyType"):
                        dmg = max(0.0, dmg - 30)
                elif dc.get("tera"):
                    continue                                  # benched Tera Pokemon take no attack damage
                dmg = _protected_damage(engine, ac, atk, dm, dmg)
                if dmg < hp_left:
                    continue
                # pieces this route needs beyond the attack itself, and whether each is in hand/play
                need_p: list[float] = []
                miss = _missing_energy(atk.get("energies") or [], am.get("energies") or [])
                if miss >= 2:
                    continue
                if miss == 1:
                    if pieces is None:
                        need_p.append(HIDDEN_HAND_P["energy"])
                    else:
                        ok = any(_missing_energy(atk.get("energies") or [], (am.get("energies") or []) + [t]) == 0
                                 for t in pieces["energies"])
                        need_p.append(1.0 if ok else 0.0)
                if not a_active:
                    need_p.append(reach_active)
                if not d_active and not snipe:
                    need_p.append(HIDDEN_HAND_P["gust"] if pieces is None else (1.0 if pieces["gust"] else 0.0))
                if not need_p:
                    cls, w = KO_EASY, 1.0
                else:
                    have = 1.0
                    for q in need_p:
                        have *= q
                    if have >= 1.0:
                        cls, w = KO_LIKELY, 0.8
                    else:
                        cls = KO_LIKELY if have > 0 else KO_POSSIBLE
                        w = 0.8 * have + 0.25 * (1.0 - have)
                if w > best_w:
                    best_cls, best_w = cls, w
        out.append({"mon": dm, "active": d_active, "prizes": _prize_value(engine, dm["id"]), "cls": best_cls, "weight": best_w})
    return out


def ko_potential(engine: Engine, cur: dict[str, Any], attacker_side: int) -> float:
    """Prizes the attacker can expect from Knock Outs next turn: the best reachable target, plus a
    little credit for a second exposed target (spread / follow-up turns)."""
    vals = sorted((k["prizes"] * k["weight"] for k in ko_classes(engine, cur, attacker_side)), reverse=True)
    if not vals:
        return 0.0
    return vals[0] + 0.25 * (vals[1] if len(vals) > 1 else 0.0)


def _attack_spread(text: str) -> tuple[str, float, int]:
    """Extra damage an attack puts on OTHER Pokemon: ("counters", total, 0) for counters placed as you
    like / on 1 benched Pokemon, ("damage", per_target, n_targets) for bench-damage attacks."""
    m = re.search(r"put (\d+) damage counters on your opponent's benched pokémon in any way you like", text)
    if m:
        return "counters", 10.0 * int(m.group(1)), 0
    m = re.search(r"place (\d+) damage counters on 1 of your opponent's benched", text)
    if m:
        return "counters_one", 10.0 * int(m.group(1)), 1
    m = re.search(r"(\d+) damage to (\d+|each) of your opponent's benched", text)
    if m:
        return "damage", float(m.group(1)), 99 if m.group(2) == "each" else int(m.group(2))
    m = re.search(r"does (\d+) damage to (\d+) of your opponent's pokémon", text)
    if m and int(m.group(2)) > 1:
        return "damage", float(m.group(1)), int(m.group(2)) - 1
    return "", 0.0, 0


def _bombers(engine: Engine, p: dict[str, Any]) -> list[tuple[float, int]]:
    """Self-KO counter abilities in play (Dusknoir/Dusclops Cursed Blast): (damage, Prizes it costs)."""
    out = []
    for m in [m for m in (p.get("active") or []) if m] + list(p.get("bench") or []):
        for s in engine.cards.get(m["id"], {}).get("skills") or []:
            t = _ntext(s.get("text"))
            mm = re.search(r"put (\d+) damage counters on 1 of your opponent's pokémon", t)
            if mm and "knocked out" in t:
                out.append((10.0 * int(mm.group(1)), _prize_value(engine, m["id"])))
    return out


def turn_potential(engine: Engine, cur: dict[str, Any], attacker_side: int) -> dict[str, float]:
    """
    The attacker's best WHOLE-TURN route next turn: one attack on its target (Active, gusted bench
    target, or snipe) plus whatever the attack's spread and the side's self-KO bombers can finish off.
    Returns expected Prizes (route Prizes x chance its pieces are available), the route's raw Prizes,
    Knock Outs, and the chance it wipes the defender's board or takes the attacker's last Prizes.
    """
    a, d = cur["players"][attacker_side], cur["players"][1 - attacker_side]
    pieces = _hand_pieces(engine, a.get("hand"))
    reach_active = _can_reach_active(engine, a, pieces)
    bombers = _bombers(engine, a)
    defenders = [(m, True) for m in (d.get("active") or []) if m] + [(m, False) for m in (d.get("bench") or [])]
    attackers = [(m, True) for m in (a.get("active") or []) if m] + [(m, False) for m in (a.get("bench") or [])]
    prizes_left = len(a.get("prize") or [])
    best = {"expected": 0.0, "prizes": 0.0, "kos": 0.0, "wipe": 0.0, "prize_out": 0.0}
    if not defenders:
        return best
    for am, a_active in attackers:
        ac = engine.cards.get(am["id"], {})
        for aid in ac.get("attacks", []):
            atk = engine.attacks.get(aid)
            if not atk:
                continue
            miss = _missing_energy(atk.get("energies") or [], am.get("energies") or [])
            if miss >= 2:
                continue
            text = _ntext(atk.get("text"))
            snipe = "of your opponent's pokémon" in text and "damage to" in text
            avail = 1.0
            if miss == 1:
                if pieces is None:
                    avail *= HIDDEN_HAND_P["energy"]
                else:
                    avail *= 1.0 if any(_missing_energy(atk.get("energies") or [], (am.get("energies") or []) + [t]) == 0
                                        for t in pieces["energies"]) else 0.25
            if not a_active:
                avail *= reach_active if reach_active > 0 else 0.25
            spread_kind, spread_amt, spread_n = _attack_spread(text)
            for dm, d_active in defenders:
                route_avail = avail
                if not d_active and not snipe:
                    route_avail *= HIDDEN_HAND_P["gust"] if pieces is None else (1.0 if pieces["gust"] else 0.25)
                dc = engine.cards.get(dm["id"], {})
                dmg = float(atk.get("damage") or 0)
                if d_active:
                    if dc.get("weakness") is not None and dc.get("weakness") == ac.get("energyType"):
                        dmg *= 2
                    if dc.get("resistance") is not None and dc.get("resistance") == ac.get("energyType"):
                        dmg = max(0.0, dmg - 30)
                elif dc.get("tera"):
                    dmg = 0.0
                dmg = _protected_damage(engine, ac, atk, dm, dmg)
                # remaining HP after the attack's main damage; then spread + bombers finish what they can
                left = {id(m): max(0.0, float(m["hp"])) for m, _ in defenders}
                left[id(dm)] -= dmg
                pool = spread_amt if spread_kind == "counters" else 0.0
                bomb_cost = 0
                for bd, cost in bombers:
                    pool += bd
                    bomb_cost += cost
                if spread_kind == "damage":
                    others = sorted([m for m, act in defenders if not act and m is not dm and not engine.cards.get(m["id"], {}).get("tera")],
                                    key=lambda m: left[id(m)])
                    for m in others[:spread_n]:
                        left[id(m)] -= spread_amt
                if spread_kind == "counters_one":
                    pool += spread_amt
                # spend counters greedily: finish the target first, then the cheapest Prizes per counter
                order = sorted(defenders, key=lambda x: (x[0] is not dm, left[id(x[0])] / max(1, _prize_value(engine, x[0]["id"]))))
                used_bombs = 0.0
                for m, _ in order:
                    need = left[id(m)]
                    if 0 < need <= pool:
                        pool -= need
                        used_bombs += need
                        left[id(m)] = 0.0
                kos = [m for m, _ in defenders if left[id(m)] <= 0]
                if not kos:
                    continue
                prizes = sum(_prize_value(engine, m["id"]) for m in kos)
                # bombers only "cost" their Prizes if their counters were actually needed
                net = prizes - (bomb_cost if bombers and used_bombs > spread_amt else 0)
                exp = route_avail * max(0.0, net)
                if exp > best["expected"]:
                    best = {"expected": exp, "prizes": float(prizes), "kos": float(len(kos)),
                            "wipe": route_avail if len(kos) >= len(defenders) else 0.0,
                            "prize_out": route_avail if prizes >= prizes_left > 0 else 0.0}
    return best


def evaluate_state(engine: Engine, cur: dict[str, Any], me: int, ko_model: bool = False) -> float:
    """
    Heuristic value of a board for player `me` (used to compare transitions):
    Prizes taken, damage on each side weighted by Prize value, development, and THREAT.
    With `ko_model`, threat = KO reachability classes (easy / very KO-able / KO-able / survives)
    for both sides: the Prizes we can expect to take next turn minus the Prizes we are exposing.
    """
    if cur is None:
        return 0.0
    if cur.get("result", -1) >= 0:
        return 1000.0 if cur["result"] == me else (-1000.0 if cur["result"] == 1 - me else 0.0)
    v = 0.0
    if ko_model:
        # Offense: the Prizes our best whole-turn route can expect; defense: the opponent's.
        # Board wipes and prize-outs end the game, so they dominate when a route can reach them.
        ours = turn_potential(engine, cur, me)
        theirs = turn_potential(engine, cur, 1 - me)
        v += 4.0 * ours["expected"] + 120.0 * max(ours["wipe"], ours["prize_out"])
        v -= 4.0 * theirs["expected"] + 300.0 * max(theirs["wipe"], theirs["prize_out"])
    for side, sign in ((me, 1.0), (1 - me, -1.0)):
        p, o = cur["players"][side], cur["players"][1 - side]
        tgt = (o.get("active") or [None])[0]
        if tgt:
            tgt_left = max(10, tgt["hp"])
            pv = _prize_value(engine, tgt["id"])
            opp_bench = list(o.get("bench") or [])
            for i, m in enumerate([m for m in (p.get("active") or []) if m] + list(p.get("bench") or [])):
                reach = 1.0 if i == 0 else 0.45          # benched attackers must be switched in
                persp = 1.0 if side == me else 0.8
                if not ko_model:      # (the KO classes replace this Active-only threat term)
                    dmg, miss = _threat(engine, m, tgt)
                    if dmg > 0 and miss <= 1:
                        ready = 1.0 if miss == 0 else 0.4
                        v += sign * 4.0 * pv * min(1.0, dmg / tgt_left) * reach * ready * persp
                # bench spread (Phantom Dive counters, bench-damage attacks): threatens benched Prizes
                amt, kind, smiss = _spread_threat(engine, m)
                if amt > 0 and smiss <= 1 and opp_bench:
                    best = 0.0
                    for b in opp_bench:
                        if kind == "damage" and engine.cards.get(b["id"], {}).get("tera"):
                            continue                     # benched Tera Pokemon take no attack damage
                        best = max(best, _prize_value(engine, b["id"]) * min(1.0, amt / max(10, b["hp"])))
                    v += sign * 2.5 * best * reach * (1.0 if smiss == 0 else 0.4) * persp
    for side, sign in ((me, 1.0), (1 - me, -1.0)):
        p = cur["players"][side]
        taken = 6 - len(p["prize"])            # Prizes this side has taken
        v += sign * 10.0 * taken
        mons = [m for m in (p.get("active") or []) if m] + list(p.get("bench") or [])
        for i, m in enumerate(mons):
            hp, mx = m.get("hp", 0), max(1, m.get("maxHp", 1))
            pv = _prize_value(engine, m["id"])
            # damage on a Pokemon = progress toward the opponent taking its Prizes
            v -= sign * 3.0 * pv * (1.0 - hp / mx)
            # development: attached energy, evolution stage, threatening attackers
            v += sign * (0.8 * len(m.get("energies") or []) + 1.0 * len(m.get("preEvolution") or []))
            v += sign * 0.004 * min(250, _best_attack_damage(engine, m["id"])) * min(1.0, len(m.get("energies") or []) / 2.0)
            v += sign * 0.6
        if not mons:
            v -= sign * 50.0
        v += sign * 0.15 * min(8, p.get("handCount", 0))
        if p.get("deckCount", 60) < 6:
            v -= sign * (6 - p["deckCount"]) * 1.5
    return v


# ---------------------------------------------------------------------------
# Agents
# ---------------------------------------------------------------------------

class RandomAgent:
    def __init__(self, rng: random.Random):
        self.rng = rng

    def __call__(self, obs: dict[str, Any]) -> list[int]:
        sel = obs["select"]
        return self.rng.sample(range(len(sel["option"])), sel["maxCount"])


class SearchAgent:
    """
    Main-phase decisions: try every legal option in the engine's forward model, finish
    the resulting sub-choices with the static policy, and pick the option whose
    resulting state scores best (one transition of lookahead). Other decisions use
    a static policy (promote the readiest Pokemon, discard the least useful card, ...).
    """

    def __init__(self, engine: Engine, my_deck: list[int], opp_deck: list[int], rng: random.Random,
                 max_rollout_steps: int = 12, reply: bool = False, max_reply_steps: int = 80,
                 horizon: str = "turn", sub_search: bool = True, ko_model: bool = False,
                 race_values: Any = None):
        self.engine = engine
        self.my_deck = Counter(my_deck)
        self.opp_deck = Counter(opp_deck)
        self.rng = rng
        self.max_rollout_steps = max_rollout_steps
        # Simulating the opponent's reply turn is OFF by default: the engine's forward model is
        # stochastic (coin flips / shuffles), so a single sampled reply is noise of the same size as
        # the differences between moves, and it made play measurably worse. The deterministic
        # threat term in evaluate_state stands in for the opponent's next turn instead.
        self.reply = reply
        self.horizon = horizon                  # "turn": score every option after finishing our turn; "step": immediate
        self.sub_search = sub_search            # search card/target choices too (else fixed rules)
        self.ko_model = ko_model                # KO reachability classes in the state value
        # Solved race graph (race_graph.RaceValues): score a move by the discounted chance of winning
        # from the race state it leads to, i.e. by progress toward a position whose next turn can win.
        self.race_values = race_values
        self.max_reply_steps = max_reply_steps
        self.max_turn_actions = 12             # cap on greedy actions when completing a turn
        self.searches = 0

    # ---- hidden information ----
    @staticmethod
    def _visible(p: dict[str, Any]) -> Counter:
        seen: Counter = Counter()
        for m in [m for m in (p.get("active") or []) if m] + list(p.get("bench") or []):
            seen[m["id"]] += 1
            for k in ("energyCards", "tools", "preEvolution"):
                for c in m.get(k) or []:
                    seen[c["id"]] += 1
        for c in p.get("discard") or []:
            seen[c["id"]] += 1
        for c in p.get("prize") or []:
            if c:
                seen[c["id"]] += 1
        for c in p.get("hand") or []:
            if c:
                seen[c["id"]] += 1
        return seen

    def _sample(self, pool: Counter, n: int, filler: int) -> list[int]:
        bag = list(pool.elements())
        self.rng.shuffle(bag)
        out = bag[:n]
        while len(out) < n:
            out.append(filler)
        for x in out:
            if pool[x] > 0:
                pool[x] -= 1
        return out

    def _guesses(self, obs: dict[str, Any]) -> tuple[list[int], ...]:
        cur = obs["current"]
        me = cur["yourIndex"]
        p, o = cur["players"][me], cur["players"][1 - me]
        filler_me = next(iter(self.my_deck)) if self.my_deck else 1
        filler_op = next(iter(self.opp_deck)) if self.opp_deck else 1
        my_pool = self.my_deck - self._visible(p)
        your_deck = [] if (obs["select"] or {}).get("deck") else self._sample(my_pool, p["deckCount"], filler_me)
        your_prize = self._sample(my_pool, sum(1 for c in p["prize"] if c is None), filler_me)
        op_pool = self.opp_deck - self._visible(o)
        opp_active: list[int] = []
        if o.get("active") and o["active"][0] is None:
            basics = [cid for cid in op_pool.elements() if self.engine.cards.get(cid, {}).get("basic")]
            opp_active = [basics[0] if basics else filler_op]
            if basics:
                op_pool[basics[0]] -= 1
        opp_hand = self._sample(op_pool, o["handCount"], filler_op)
        opp_prize = self._sample(op_pool, sum(1 for c in o["prize"] if c is None), filler_op)
        opp_deck = self._sample(op_pool, o["deckCount"], filler_op)
        return your_deck, your_prize, opp_deck, opp_prize, opp_hand, opp_active

    # ---- static policy for sub-decisions ----
    def _card_value(self, cid: int) -> float:
        c = self.engine.cards.get(cid, {})
        if not c:
            return 0.0
        if c.get("cardType") == 0:   # Pokemon
            return 1.0 + _best_attack_damage(self.engine, cid) / 100.0 + 0.5 * bool(c.get("skills")) + 0.3 * (c.get("stage1") or c.get("stage2"))
        if c.get("cardType") in (5, 6):  # energy
            return 0.9
        return 1.2

    def _option_card_id(self, obs: dict[str, Any], opt: dict[str, Any]) -> int | None:
        cur = obs["current"]
        if opt.get("cardId"):
            return opt["cardId"]
        area, idx, pi = opt.get("area"), opt.get("index"), opt.get("playerIndex", cur["yourIndex"])
        try:
            if area == AREA_DECK and (obs["select"] or {}).get("deck"):
                return obs["select"]["deck"][idx]["id"]
            p = cur["players"][pi]
            if area == AREA_HAND:
                return p["hand"][idx]["id"]
            if area == AREA_DISCARD:
                return p["discard"][idx]["id"]
            if area == AREA_ACTIVE:
                return p["active"][0]["id"] if p["active"] and p["active"][0] else None
            if area == AREA_BENCH:
                return p["bench"][idx]["id"]
            looking = cur.get("looking") or []
            if looking and idx is not None and idx < len(looking) and looking[idx]:
                return looking[idx]["id"]
        except (IndexError, KeyError, TypeError):
            return None
        return None

    def _pokemon_at(self, obs: dict[str, Any], opt: dict[str, Any]) -> dict[str, Any] | None:
        cur = obs["current"]
        pi = opt.get("playerIndex", cur["yourIndex"])
        p = cur["players"][pi]
        try:
            if opt.get("area") == AREA_ACTIVE:
                return p["active"][0]
            if opt.get("area") == AREA_BENCH:
                return p["bench"][opt["index"]]
        except (IndexError, KeyError, TypeError):
            return None
        return None

    def static_choice(self, obs: dict[str, Any]) -> list[int]:
        sel = obs["select"]
        opts = sel["option"]
        n_min, n_max = sel["minCount"], sel["maxCount"]
        ctx = sel.get("context")
        me = obs["current"]["yourIndex"]
        if n_max == 0:
            return []
        types = {o["type"] for o in opts}
        if types <= {OT_YES, OT_NO}:
            want = OT_YES
            return [next((i for i, o in enumerate(opts) if o["type"] == want), 0)]

        def score(i: int) -> float:
            o = opts[i]
            t = o["type"]
            if t == OT_END:
                return -5.0
            if t == OT_ATTACK:
                return 5.0 + (self.engine.attacks.get(o.get("attackId"), {}).get("damage", 0) or 0) / 50.0
            mon = self._pokemon_at(obs, o) if t == OT_CARD else None
            if mon is not None:
                mine = o.get("playerIndex", me) == me
                frac = mon["hp"] / max(1, mon["maxHp"])
                if ctx in (CTX["SWITCH"], CTX["TO_ACTIVE"]):   # promote / switch in: readiest, healthiest
                    return len(mon.get("energies") or []) + 2 * frac + _best_attack_damage(self.engine, mon["id"]) / 100.0
                if ctx in (CTX["DAMAGE_COUNTER"], CTX["DAMAGE_COUNTER_ANY"], CTX["DAMAGE"]):
                    return (-1.0 if mine else 1.0) * (2.0 - frac + _prize_value(self.engine, mon["id"]))
                if ctx == CTX["HEAL"]:
                    return (1.0 if mine else -1.0) * (1.0 - frac)
                return (1.0 if mine else -1.0) * (len(mon.get("energies") or []) + _best_attack_damage(self.engine, mon["id"]) / 100.0)
            cid = self._option_card_id(obs, o)
            v = self._card_value(cid) if cid else 0.0
            if ctx in (CTX["DISCARD"], CTX["TO_DECK"], CTX["TO_DECK_BOTTOM"]):
                return -v
            if ctx == CTX["SETUP_ACTIVE"]:
                c = self.engine.cards.get(cid or 0, {})
                return -0.8 * c.get("retreatCost", 1) - 1.5 * (_prize_value(self.engine, cid or 0) - 1) + 0.5
            return v

        ranked = sorted(range(len(opts)), key=score, reverse=True)
        if ctx in (CTX["SETUP_BENCH"], CTX["TO_BENCH"], CTX["TO_HAND"], CTX["TO_FIELD"]):
            k = n_max
        elif ctx in (CTX["DISCARD"], CTX["TO_DECK"], CTX["TO_DECK_BOTTOM"]):
            k = max(n_min, 0)
        else:
            k = max(1, n_min)
        k = max(n_min, min(n_max, k))
        self._last_ranked = ranked
        return ranked[:k]

    def _candidate_selections(self, obs: dict[str, Any], cap: int = 10) -> list[list[int]]:
        """Candidate answers for a card/target choice: every option for a pick-one choice; for a
        pick-several choice, the fixed-rule pick plus single swaps and the min/max-size variants."""
        sel = obs["select"]
        n, n_min, n_max = len(sel["option"]), sel["minCount"], sel["maxCount"]
        base = self.static_choice(obs)
        ranked = getattr(self, "_last_ranked", list(range(n)))
        types = {o["type"] for o in sel["option"]}
        if n_max == 1 or types <= {OT_YES, OT_NO}:
            order = [base[0]] + [i for i in ranked if i != base[0]] if base else ranked
            return [[i] for i in order[:cap]] + ([[]] if n_min == 0 and [] != base else [])
        cands: list[list[int]] = [list(base)]
        rest = [i for i in ranked if i not in base]
        for out_i in base[:3]:
            for in_i in rest[:3]:
                cands.append(sorted([x for x in base if x != out_i] + [in_i]))
        for size in {n_min, n_max}:
            if size != len(base) and 0 <= size <= n:
                cands.append(ranked[:size])
        uniq: list[list[int]] = []
        for c in cands:
            if sorted(c) not in [sorted(u) for u in uniq] and n_min <= len(c) <= n_max:
                uniq.append(c)
        return uniq[:cap]

    # ---- lookahead ----
    def _advance_static(self, state: dict[str, Any], me: int, turn: int) -> tuple[dict[str, Any] | None, bool]:
        """Resolve sub-choices with the static policy until our next main-phase decision or the
        end of our turn. Returns (state, turn_ended)."""
        steps = 0
        while state is not None and steps < self.max_rollout_steps:
            ob = state["observation"]
            cur = ob["current"]
            if cur["result"] >= 0 or ob["select"] is None:
                return state, True
            if cur["yourIndex"] == me and ob["select"]["type"] == ST_MAIN:
                return state, cur["turn"] != turn
            if cur["turn"] != turn and cur["yourIndex"] != me:
                return state, True
            nxt = self.engine.search_step(state["searchId"], self.static_choice(ob))
            if nxt is None:
                return state, False
            state = nxt
            steps += 1
        return state, False

    def _complete_turn(self, state: dict[str, Any], me: int, turn: int) -> tuple[dict[str, Any] | None, bool]:
        """Play out the rest of our turn: at each main-phase decision take the option whose
        immediate result scores best (no reply), until the turn ends."""
        for _ in range(self.max_turn_actions):
            state, ended = self._advance_static(state, me, turn)
            if state is None or ended:
                return state, ended
            sel = state["observation"]["select"]
            best, best_v = None, -1e18
            for i, o in enumerate(sel["option"]):
                ch = self.engine.search_step(state["searchId"], [i])
                if ch is None:
                    continue
                ch2, _ = self._advance_static(ch, me, turn)
                if ch2 is None:
                    continue
                v = evaluate_state(self.engine, ch2["observation"]["current"], me, self.ko_model) - (0.5 if o["type"] == OT_END else 0.0)
                if v > best_v:
                    best, best_v = ch, v
            if best is None:
                return state, False
            state = best
        return state, False

    def _option_value(self, child: dict[str, Any], me: int, turn: int) -> float:
        """Value of a candidate move at a CONSISTENT horizon for every option: finish our turn
        greedily, let the opponent play their reply turn, then score."""
        if self.horizon == "step":
            state, ended = self._advance_static(child, me, turn)
        else:
            state, ended = self._complete_turn(child, me, turn)
        if state is None:
            return -1e9
        if ended and self.reply:
            state = self._play_opponent_turn(state, me)
            if state is None:
                return -1e9
        cur = state["observation"]["current"]
        heuristic = evaluate_state(self.engine, cur, me, self.ko_model)
        if self.race_values is None:
            return heuristic
        if cur.get("result", -1) >= 0:
            return 10.0 if cur["result"] == me else (-10.0 if cur["result"] == 1 - me else 0.0)
        from race_graph import race_state   # local import: race_graph imports this module
        mover = cur.get("yourIndex", me)
        v = self.race_values.value(race_state(self.engine, cur, mover))
        v = v if mover == me else -v          # value is for the player to move
        return v + heuristic / 2000.0          # heuristic only breaks ties within a race state

    def _play_opponent_turn(self, state: dict[str, Any], me: int) -> dict[str, Any] | None:
        """
        Play out the opponent's whole reply turn in the forward model. Their main-phase choices
        are greedy one-step lookahead scored from THEIR perspective; everything else uses the
        static policy. Stops when our next turn begins (or the game ends).
        """
        steps = 0
        while state is not None and steps < self.max_reply_steps:
            ob = state["observation"]
            cur = ob["current"]
            sel = ob["select"]
            if cur["result"] >= 0 or sel is None:
                break
            who = cur["yourIndex"]
            if who == me and sel["type"] == ST_MAIN:
                break                    # our next turn has started
            if who != me and sel["type"] == ST_MAIN and len(sel["option"]) > 1:
                best_i, best_v = 0, -1e18
                for i, o in enumerate(sel["option"]):
                    ch = self.engine.search_step(state["searchId"], [i])
                    if ch is None:
                        continue
                    v = evaluate_state(self.engine, ch["observation"]["current"], who, self.ko_model)
                    if o["type"] == OT_END:
                        v -= 0.5
                    if v > best_v:
                        best_i, best_v = i, v
                choice = [best_i]
            else:
                choice = self.static_choice(ob)
            nxt = self.engine.search_step(state["searchId"], choice)
            if nxt is None:
                return state
            state = nxt
            steps += 1
        return state

    def __call__(self, obs: dict[str, Any]) -> list[int]:
        sel = obs["select"]
        if sel is None:
            return list(self.my_deck.elements())
        cur = obs["current"]
        if len(sel["option"]) <= 1 or sel["maxCount"] == 0:
            return self.static_choice(obs)
        if sel["type"] == ST_MAIN:
            candidates = [[i] for i in range(len(sel["option"]))]
        elif self.sub_search and cur.get("turn", 0) >= 1:
            # card / target choices (search targets, discards, damage counters, promotions...)
            candidates = self._candidate_selections(obs)
            if len(candidates) <= 1:
                return candidates[0] if candidates else self.static_choice(obs)
        else:
            return self.static_choice(obs)
        me = cur["yourIndex"]
        root = self.engine.search_begin(obs, *self._guesses(obs))
        if root is None:
            return self.static_choice(obs)
        self.searches += 1
        best, best_v = candidates[0], -1e18
        for cand in candidates:
            child = self.engine.search_step(root["searchId"], cand)
            if child is None:
                continue
            v = self._option_value(child, me, cur["turn"])
            if v > best_v:
                best, best_v = cand, v
        self.engine.search_end()
        return best


# ---------------------------------------------------------------------------
# Games
# ---------------------------------------------------------------------------

def play_engine_game(deck0: list[int], deck1: list[int], agents: tuple[Any, Any], max_steps: int = 5000) -> dict[str, Any]:
    """Play one engine game. Returns winner (0/1/None), turns, and a per-turn state trace."""
    eng = Engine.get()
    obs, sd = eng.game.battle_start(deck0, deck1)
    if obs is None:
        raise ValueError(f"engine rejected decks (errorPlayer={sd.errorPlayer}, errorType={sd.errorType})")
    trace: list[dict[str, Any]] = []
    last_turn = -1
    steps = 0
    try:
        while obs["current"]["result"] < 0 and steps < max_steps:
            cur = obs["current"]
            if cur["turn"] != last_turn and cur["turn"] >= 1:
                last_turn = cur["turn"]
                trace.append({
                    "turn": cur["turn"], "first": cur["firstPlayer"],
                    "prizes": tuple(len(p["prize"]) for p in cur["players"]),
                    "in_play": tuple(len([m for m in (p.get("active") or []) if m]) + len(p.get("bench") or []) for p in cur["players"]),
                    "hand": tuple(p["handCount"] for p in cur["players"]),
                })
            who = cur["yourIndex"]
            obs = eng.game.battle_select(agents[who](obs))
            steps += 1
        result = obs["current"]["result"]
        first = obs["current"]["firstPlayer"]
    finally:
        eng.game.battle_finish()
    return {"winner": result if result in (0, 1) else None, "first": first, "turns": last_turn, "trace": trace, "steps": steps}
