"""
Executable card effects for the turn-by-turn game simulator.

`compile_script(card)` turns a CompiledCard's printed text into a `CardScript`:
small, explicit operations (draw N, search X onto Bench, gust, attach energy from
discard to a Stage 2, put 13 damage counters and Knock Out self, ...) that the
simulator applies as STATE TRANSITIONS.  Anything that can't be parsed is
recorded in `CardScript.unmodeled` so coverage can be reported per deck instead
of silently scoring it.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from card_compiler import POKEMON_TYPE_WORDS, CompiledCard, _parse_pokemon_descriptor

TYPES = {t.capitalize() for t in POKEMON_TYPE_WORDS}
P = r"pok[eé]mon"


def _low(text: str) -> str:
    return (text or "").lower().replace("’", "'")


# ---------------------------------------------------------------------------
# Energy provision
# ---------------------------------------------------------------------------

def energy_units(card: CompiledCard, host: CompiledCard | None) -> list[str]:
    """Energy units an energy card provides while attached to `host`.
    Units are type names, "ANY" (every type, 1 at a time) or "PD" (Psychic or Darkness)."""
    if "BASIC_ENERGY" in card.tags:
        return [card.primary_energy_type or "Colorless"]
    rt = _low(card.rules_text)
    if "provides 2 in any combination of psychic energy and darkness energy" in rt:
        if host is not None and host.name.startswith("Team Rocket's"):
            return ["PD", "PD"]
        return []
    if "stage 2" in rt and "every type of energy but provides only 2" in rt:
        return ["ANY", "ANY"] if host is not None and host.stage == 2 else ["Colorless"]
    if "attached to a basic" in rt and "every type of energy" in rt:
        return ["ANY"] if host is not None and host.stage == 0 else ["Colorless"]
    if "every type of energy" in rt:
        return ["ANY"]
    if "evolution pok" in rt and "colorlesscolorlesscolorless" in rt:
        return ["Colorless"] * (3 if host is not None and host.stage >= 1 else 1)
    m = re.search(r"provides (\w+) energy", rt)
    if m and m.group(1).capitalize() in TYPES:
        return [m.group(1).capitalize()]
    return ["Colorless"]


def can_pay(cost: list[str], units: list[str]) -> bool:
    """Exact-ish payment check: typed requirements first, then wildcards, then Colorless."""
    need: dict[str, int] = {}
    colorless = 0
    for c in cost:
        if c == "Colorless":
            colorless += 1
        elif c != "Free":
            need[c] = need.get(c, 0) + 1
    pool: dict[str, int] = {}
    for u in units:
        pool[u] = pool.get(u, 0) + 1
    for t, n in need.items():
        take = min(n, pool.get(t, 0))
        pool[t] = pool.get(t, 0) - take
        n -= take
        if n and t in ("Psychic", "Darkness"):
            take = min(n, pool.get("PD", 0))
            pool["PD"] = pool.get("PD", 0) - take
            n -= take
        if n:
            take = min(n, pool.get("ANY", 0))
            pool["ANY"] = pool.get("ANY", 0) - take
            n -= take
        if n:
            return False
    return sum(v for v in pool.values() if v > 0) >= colorless


def missing_units(cost: list[str], units: list[str]) -> int:
    """How many more energy attachments (of the right type) are needed to pay `cost`."""
    if can_pay(cost, units):
        return 0
    for k in range(1, len(cost) + 1):
        if can_pay(cost, units + ["ANY"] * k):
            return k
    return len(cost)


# ---------------------------------------------------------------------------
# Search specs ("a Basic Pokemon, a Stage 1 Pokemon, and a Stage 2 Pokemon")
# ---------------------------------------------------------------------------

def _count_word(s: str) -> int:
    m = re.search(r"up to (\d+)|(\d+)", s)
    if m:
        return int(m.group(1) or m.group(2))
    return 1


def parse_card_spec(phrase: str) -> dict[str, Any] | None:
    """One searchable thing: {"kind": pokemon|energy|basic_energy|item|tool|supporter|stadium|trainer|any, "filter": {...}, "n": k}."""
    ph = phrase.strip().strip(".")
    if not ph:
        return None
    n = _count_word(ph)
    m = re.search(P, ph)
    if m and "tool" not in ph[m.end():m.end() + 6]:
        f = _parse_pokemon_descriptor(ph[:m.start()], ph[m.end():]) or {}
        return {"kind": "pokemon", "filter": f, "n": n}
    if "energy" in ph:
        et = None
        for t in TYPES:
            if t.lower() in ph:
                et = t
        return {"kind": "basic_energy" if "basic" in ph else "energy", "etype": et, "n": n}
    for kw, kind in (("item", "item"), ("tool", "tool"), ("supporter", "supporter"), ("stadium", "stadium"), ("trainer", "trainer")):
        if kw in ph:
            return {"kind": kind, "n": n, "team_rocket": "team rocket" in ph}
    if re.search(r"\bcards?\b", ph):
        return {"kind": "any", "n": n}
    return None


def parse_search(text: str) -> dict[str, Any] | None:
    m = re.search(r"search (?:your|their) deck for (.+?)(?:, reveal|, shuffle| and put| put| and attach|\. then|\.$|$)", text)
    if not m:
        return None
    body = m.group(1)
    mode = "and"
    if "in any combination of" in body:
        n = _count_word(body)
        parts = re.split(r",? and |, ", body.split("in any combination of", 1)[1])
        specs = [s for s in (parse_card_spec(p) for p in parts) if s]
        for s in specs:
            s["n"] = n
        mode = "combo"
    elif re.search(r" or (?:a |an |up to |\d)", body):
        specs = [s for s in (parse_card_spec(p) for p in re.split(r" or ", body)) if s]
        mode = "or"
    else:
        specs = [s for s in (parse_card_spec(p) for p in re.split(r",? and |, ", body)) if s]
    if not specs:
        return None
    dest = "bench" if re.search(r"onto (?:your|their) bench", text) else ("top" if "on top of it" in text else "hand")
    return {"op": "search", "specs": specs, "mode": mode, "dest": dest}


# ---------------------------------------------------------------------------
# Scripts
# ---------------------------------------------------------------------------

@dataclass
class AttackScript:
    name: str
    cost: list[str]
    base: int
    kind: str = "damage"                 # "damage" | "counters" | "none"
    mods: list[dict[str, Any]] = field(default_factory=list)   # runtime damage formulas
    effects: list[dict[str, Any]] = field(default_factory=list)  # other state changes
    snipe: dict[str, Any] | None = None  # {"n_targets": k, "amount": d, "bench_only": bool, "ex_only": bool}
    ignores_effects: bool = False        # Shred-style: ignores effects on the opponent's Active
    ignores_wr: bool = False
    fallback_damage: float | None = None  # compiler estimate when the formula is unparsed
    text: str = ""


@dataclass
class CardScript:
    uid: str
    trainer: dict[str, Any] | None = None
    ability: dict[str, Any] | None = None
    passives: set[str] = field(default_factory=set)
    attacks: list[AttackScript] = field(default_factory=list)
    tool: dict[str, Any] = field(default_factory=dict)
    stadium: set[str] = field(default_factory=set)
    unmodeled: list[str] = field(default_factory=list)


def _trainer_ops(card: CompiledCard, t: str, s: CardScript) -> list[dict[str, Any]]:
    ops: list[dict[str, Any]] = []
    # --- hand refresh / disruption ---
    m = re.search(r"shuffle your hand into your deck\. then, draw (\d+) cards", t)
    if m:
        alt = re.search(r"exactly (\d+) prize cards remaining, draw (\d+)", t)
        ops.append({"op": "shuffle_draw", "n": int(m.group(1)), "alt": (int(alt.group(1)), int(alt.group(2))) if alt else None})
    m = re.search(r"each player shuffles their hand into their deck and draws (\d+)", t)
    if m:
        ops.append({"op": "reset_both", "me": int(m.group(1)), "opp": int(m.group(1))})
    m = re.search(r"each player shuffles their hand into their deck\. then, you draw (\d+) cards, and your opponent draws (\d+)", t)
    if m:
        ops.append({"op": "reset_both", "me": int(m.group(1)), "opp": int(m.group(2))})
    m = re.search(r"your opponent shuffles their hand and puts it on the bottom of their deck.*?they draw (\d+)", t)
    if m:
        ops.append({"op": "opp_bottom_draw", "n": int(m.group(1))})
    m = re.search(r"your opponent discards cards from their hand until they have (\d+)", t)
    if m:
        ops.append({"op": "opp_discard_to", "n": int(m.group(1))})
    m = re.search(r"each player discards cards from their hand until they have (\d+)", t)
    if m:
        ops.append({"op": "both_discard_to", "n": int(m.group(1))})
    if "your opponent reveals their hand, and you discard up to 2 item" in t:
        ops.append({"op": "eri", "n": 2})
    m = re.search(r"discard your hand and draw (\d+)", t)
    if m:
        ops.append({"op": "discard_hand_draw", "n": int(m.group(1))})
    if "draw 3 cards for each card you discarded" in t:
        ops.append({"op": "gwynn"})
    m = re.search(r"draw cards until you have (\d+) cards in your hand", t)
    if m:
        ops.append({"op": "draw_to", "n": int(m.group(1))})
    if not ops:
        m = re.search(r"draw (\d+) cards", t)
        if m and "for each" not in t:
            ops.append({"op": "draw", "n": int(m.group(1))})
    # --- look at top N ---
    m = re.search(r"look at the top (\d+) cards of your deck\. you may reveal (?:up to (\d+)|a) (.+?) you find there", t)
    if m:
        spec_txt = m.group(3)
        specs = []
        if "in any combination of" in spec_txt:
            specs = [x for x in (parse_card_spec(p) for p in re.split(r" and ", spec_txt.split("in any combination of", 1)[1])) if x]
        else:
            x = parse_card_spec(spec_txt)
            specs = [x] if x else []
        ops.append({"op": "look_top", "n": int(m.group(1)), "take": int(m.group(2) or 1), "specs": specs, "rest": "shuffle"})
    m = re.search(r"look at the top (\d+) cards of your deck,? and put (?:up to )?(\d+) of them into your hand", t)
    if m:
        ops.append({"op": "look_top", "n": int(m.group(1)), "take": int(m.group(2)), "specs": [{"kind": "any", "n": int(m.group(2))}],
                    "rest": "discard" if "discard the other" in t else "shuffle"})
    # --- search ---
    if "search your deck for" in t and "energy card" in t and "attach" in t:
        if "of different types" in t:
            ops.append({"op": "crispin"})
        elif "darkness pok" in t:
            ops.append({"op": "janine"})
        else:
            s.unmodeled.append("search+attach energy")
    elif "search your deck for 2 cards, shuffle your deck, then put those cards on top" in t:
        ops.append({"op": "search", "specs": [{"kind": "any", "n": 2}], "mode": "and", "dest": "top"})
    elif "search your deck for" in t:
        sr = parse_search(t)
        if sr:
            ops.append(sr)
        else:
            s.unmodeled.append("search: " + t[:80])
    # --- gust / switch ---
    if re.search(r"switch in 1 of your opponent's benched " + P + " to the active spot", t):
        ops.append({"op": "gust"})
        if "switch your active" in t:
            ops.append({"op": "switch"})
    elif re.search(r"switch your active (?:team rocket's )?" + P + " with 1 of your benched", t):
        if "choose 1:" in t:
            ops.append({"op": "modal_switch"})
        else:
            ops.append({"op": "switch"})
            if re.search(r"switch in 1 of your opponent's benched", t):
                ops.append({"op": "gust"})
            m2 = re.search(r"draw cards until you have (\d+)", t)
            if m2 and not any(o["op"] == "draw_to" for o in ops):
                ops.append({"op": "draw_to", "n": int(m2.group(1))})
    # --- energy acceleration ---
    m = re.search(r"attach (?:up to (\d+)|an?) basic (?:(\w+) )?energy cards? from your discard pile to (?:1 of )?(?:your )?(.+?)" + P, t)
    if m and "choose up to 2 of your benched" not in t:
        et = m.group(2).capitalize() if m.group(2) and m.group(2).capitalize() in TYPES else None
        desc = m.group(3)
        f = _parse_pokemon_descriptor("your " + desc, "") or {}
        ops.append({"op": "attach_discard", "n": int(m.group(1) or 1), "etype": et, "filter": f,
                    "bench_only": "benched" in desc, "each": False})
    elif "choose up to 2 of your benched" in t and "attach a basic energy card from your discard pile to each" in t:
        m3 = re.search(r"choose up to 2 of your benched (\w+) pok", t)
        ptype = m3.group(1).capitalize() if m3 else None
        ops.append({"op": "attach_discard", "n": 2, "etype": None, "filter": {"ptype": ptype} if ptype in TYPES else {},
                    "bench_only": True, "each": True})
    if re.search(r"move (?:a|up to \d+) (?:basic )?energy from 1 of your " + P + " to another of your", t):
        ops.append({"op": "energy_switch"})
    m = re.search(r"move up to (\d+) energy from your benched " + P + " to your active", t)
    if m:
        ops.append({"op": "move_bench_to_active", "n": int(m.group(1))})
    # --- recovery ---
    if "from your discard pile into your hand" in t or ("from your discard pile into your deck" in t) or re.search(r"shuffle up to \d+ " + P + " from your discard pile into your deck", t):
        m_n = re.search(r"up to (\d+)", t)
        n = int(m_n.group(1)) if m_n else 1
        kinds = []
        if re.search(P, t):
            kinds.append("pokemon")
        if "energy" in t:
            kinds.append("basic_energy")
        ops.append({"op": "recover", "n": n, "kinds": kinds, "non_rule_box": "rule box" in t,
                    "dest": "deck" if "into your deck" in t else "hand"})
    # --- healing ---
    m = re.search(r"heal (\d+) damage from your active " + P + r"(?: that has (\d+) or more energy)?", t)
    if m:
        ops.append({"op": "heal", "n": int(m.group(1)), "target": "active", "min_energy": int(m.group(2) or 0)})
    m = re.search(r"heal (\d+) damage from 1 of your " + P, t)
    if m:
        ops.append({"op": "heal", "n": int(m.group(1)), "target": "any", "min_energy": 0})
    # --- evolution ---
    if "skipping the stage 1" in t:
        ops.append({"op": "rare_candy"})
    # --- energy denial ---
    if re.search(r"discard an energy from 1 of your opponent's " + P, t):
        ops.append({"op": "hammer", "coin": "flip a coin" in t, "special_only": False})
    elif re.search(r"discard a special energy from 1 of your opponent's", t):
        ops.append({"op": "hammer", "coin": False, "special_only": True})
    if "discard them" in t and "tool" in t:
        ops.append({"op": "tool_scrap"})
    # --- one-turn damage buffs ---
    if card.damage_bonus and "Pokémon Tool" not in card.subtypes:
        ops.append({"op": "dmg_buff", **card.damage_bonus, "modal": "choose 1:" in t})
    return ops


def _stadium_flags(t: str) -> set[str]:
    flags = set()
    table = [
        ("prevent all damage counters from being placed on benched", "battle_cage"),
        ("can evolve into grass", "forest_of_vitality"),
        ("can have up to 8 pok", "area_zero"),
        ("search their deck for a basic pok", "lumiose"),
        ("recovers from all special conditions and can't be affected", "festival"),
        ("place 2 damage counters on that pok", "risky_ruins"),
        ("colorless pokémon in play (both yours and your opponent's) have no abilities", "watchtower"),
        ("pokémon tools attached to each pokémon (both yours and your opponent's) have no effect", "jamming_tower"),
        ("stage 2 pokémon in play (both yours and your opponent's) gets -30 hp", "gravity_mountain"),
        ("discard 2 cards from their hand in order to draw a card", "prism_tower"),
        ("cost colorless more", "nighttime_mine"),
        ("n's pokémon in play (both yours and your opponent's) have no retreat cost", "n_castle"),
        ("put a card from their hand on top of their deck", "academy"),
    ]
    for pat, flag in table:
        if pat in t:
            flags.add(flag)
    return flags


def _ability_script(card: CompiledCard, s: CardScript) -> None:
    for ab in card.abilities:
        name = (ab.get("name") or "").lower()
        t = _low(ab.get("text"))
        a: dict[str, Any] | None = None
        if "prevent all damage done to your benched" in t and "rule box" in t:
            s.passives.add("FLOWER_CURTAIN")
        elif "prevent all damage from and effects of attacks from your opponent's pokémon done to your benched" in t:
            s.passives.add("SPHERICAL_SHIELD")
        elif "prevent all damage done to this pokémon by attacks from your opponent's pokémon ex" in t:
            s.passives.add("EX_IMMUNE")
        elif "your basic pokémon in play have no retreat cost" in t:
            s.passives.add("SKYLINER")
        elif "weakness of each of your opponent's dragon" in t:
            s.passives.add("FAIRY_ZONE")
        elif "festival lead" in name:
            s.passives.add("FESTIVAL_LEAD")
        elif "hide 'n' sneak" in name:
            s.passives.add("HIDE_N_SNEAK")
        elif "lose any ability that requires the pokémon using it to knock out itself" in t:
            s.passives.add("DAMP")
        elif "damage counters on each pokémon" in t and "can't be moved" in t:
            s.passives.add("WATCHFUL_EYE")
        elif "would be knocked out by damage from an attack, flip a coin" in t:
            s.passives.add("DURABLE_BODY")
        elif "each basic grass energy attached to all of your pokémon provides grassgrass" in t:
            s.passives.add("WILD_GROWTH")
        elif "costs colorless less for each prize card your opponent has taken" in t:
            s.passives.add("SEASONED_SKILL")
        elif re.search(r"attacks used by your (\w+) pokémon.*?do (\d+) more damage", t):
            m = re.search(r"attacks used by your (\w+)'?s? pokémon.*?do (\d+) more damage", t)
            s.passives.add("ATTACK_AURA")
            s.tool["aura"] = {"word": m.group(1) if m else "", "amount": int(m.group(2)) if m else 20}
        elif "put" in t and "damage counters on 1 of your opponent's pokémon" in t and "this pokémon is knocked out" in t:
            m = re.search(r"put (\d+) damage counters", t)
            a = {"kind": "bomber", "counters": int(m.group(1)) if m else 5}
        elif "move up to 3 damage counters from 1 of your pokémon to 1 of your opponent's" in t:
            a = {"kind": "adrena", "counters": 3, "needs_energy": "Darkness" if "darkness energy attached" in t else None}
        elif "when you play this pokémon from your hand to evolve" in t and re.search(r"draw (\d+) cards", t):
            a = {"kind": "draw", "n": int(re.search(r"draw (\d+) cards", t).group(1)), "trigger": "evolve"}
        elif "when you play this pokémon from your hand onto your bench" in t:
            if "search your deck for a supporter" in t:
                a = {"kind": "search", "trigger": "bench", "search": {"op": "search", "specs": [{"kind": "supporter", "n": 1}], "mode": "and", "dest": "hand"}}
            elif "discard a stadium" in t:
                a = {"kind": "stadium_discard", "trigger": "bench"}
            elif "switch it with your active" in t:
                a = {"kind": "switch_in", "trigger": "bench", "move_energy": "move any amount of energy" in t}
        elif "look at the top" in t and "put 1 of them into your hand" in t:
            m = re.search(r"look at the top (\d+) cards", t)
            a = {"kind": "look_top", "n": int(m.group(1)) if m else 2, "take": 1, "specs": [{"kind": "any", "n": 1}]}
        elif "look at the top" in t and "supporter card" in t:
            m = re.search(r"look at the top (\d+) cards", t)
            a = {"kind": "look_top", "n": int(m.group(1)) if m else 6, "take": 1, "specs": [{"kind": "supporter", "n": 1}]}
        elif "look at the top" in t and "attach any number of basic" in t:
            m = re.search(r"look at the top (\d+) cards.*?basic (\w+) energy", t)
            a = {"kind": "metal_maker", "n": int(m.group(1)) if m else 4, "etype": (m.group(2).capitalize() if m else "Metal")}
        elif "search your deck for" in t:
            sr = parse_search(t)
            if sr:
                a = {"kind": "search", "search": sr}
        elif re.search(r"attach a basic (\w+ )?energy card from your hand to (this|1 of your) pok", t):
            m = re.search(r"attach a basic (\w+ )?energy card from your hand to (this|1 of your) pok", t)
            a = {"kind": "attach_hand", "etype": (m.group(1) or "").strip().capitalize() or None,
                 "self_only": m.group(2) == "this", "draw": 1 if "draw a card" in t else 0,
                 "heal": int(re.search(r"heal (\d+)", t).group(1)) if re.search(r"heal (\d+)", t) else 0}
        elif re.search(r"attach a basic energy card from your discard pile to 1 of your pok", t):
            a = {"kind": "attach_discard"}
        elif re.search(r"draw (\d+) cards", t):
            a = {"kind": "draw", "n": int(re.search(r"draw (\d+) cards", t).group(1))}
            if "shuffle this pokémon and all attached cards into your deck" in t:
                a["shuffle_self"] = True
            if "you must discard a card from your hand" in t:
                a["discard_cost"] = 1
        elif "switch 1 of your benched" in t and "with your active" in t:
            a = {"kind": "self_switch"}
        else:
            s.unmodeled.append(f"ability {ab.get('name')}")
            continue
        if a is not None:
            a["name"] = ab.get("name")
            a.setdefault("trigger", "once")
            a["active_only"] = "if this pokémon is in the active spot" in t
            a["after_ko"] = "knocked out during your opponent's last turn" in t
            a["needs_festival_active"] = "festival lead ability" in t
            a["festival_grounds"] = "if festival grounds is in play" in t
            s.ability = a


def _attack_script(card: CompiledCard, atk: Any, s: CardScript) -> AttackScript:
    t = _low(atk.text)
    a = AttackScript(name=atk.name, cost=list(atk.cost or []), base=atk.printed_damage, text=t)
    a.ignores_effects = "isn't affected by any effects on your opponent's active" in t or "by any effects on those pok" in t
    a.ignores_wr = "isn't affected by weakness or resistance" in t
    parsed = False
    # damage-counter attacks (Powerful Hand, Furtive Drop, Matcha Spin)
    m = re.search(r"place (\d+) damage counters? on your opponent's active pokémon for each card in your hand", t)
    if m:
        a.kind = "counters"
        a.mods.append({"mod": "per_hand", "per": 10 * int(m.group(1))})
        parsed = True
    m = re.search(r"place (\d+) damage counters? on your opponent's active pokémon\.?$", t)
    if m and not parsed:
        a.kind = "counters"
        a.base = 10 * int(m.group(1))
        parsed = True
    m = re.search(r"place (\d+) damage counters on each of your opponent's pokémon", t)
    if m:
        cond = re.search(r"if you have (\d+) or more pokémon that have the hide 'n' sneak", t)
        a.kind = "counters"
        a.effects.append({"eff": "counters_all", "n": 10 * int(m.group(1)), "need_hns": int(cond.group(1)) if cond else 0})
        parsed = True
    # bench counters / spread
    m = re.search(r"put (\d+) damage counters on your opponent's benched pokémon in any way you like", t)
    if m:
        a.effects.append({"eff": "bench_counters", "n": int(m.group(1)), "split": True})
        parsed = True
    m = re.search(r"place (\d+) damage counters on 1 of your opponent's benched", t)
    if m:
        a.effects.append({"eff": "bench_counters", "n": int(m.group(1)), "split": False})
        parsed = True
    m = re.search(r"does (\d+) damage to (\d+|each) of your opponent's benched", t)
    if m and "also" in t:
        a.effects.append({"eff": "bench_damage", "amount": int(m.group(1)), "targets": 5 if m.group(2) == "each" else int(m.group(2))})
        parsed = True
    m = re.search(r"this attack does (\d+) damage to (\d+) of your opponent's pokémon", t)
    if m:
        a.snipe = {"n_targets": int(m.group(2)), "amount": int(m.group(1)), "bench_only": False, "ex_only": False}
        a.base = 0
        parsed = True
    m = re.search(r"this attack does (\d+) damage to 1 of your opponent's benched pokémon( ex)?", t)
    if m and "also" not in t:
        a.snipe = {"n_targets": 1, "amount": int(m.group(1)), "bench_only": True, "ex_only": bool(m.group(2))}
        parsed = True
    m = re.search(r"also does (\d+) damage to 1 of your opponent's benched", t)
    if m:
        cond = "shuffle 3 energy" in t
        a.effects.append({"eff": "bench_damage", "amount": int(m.group(1)), "targets": 1, "cost_shuffle_energy": 3 if cond else 0})
        parsed = True
    # runtime damage formulas
    formulas = [
        (r"(\d+) (?:more )?damage for each benched pokémon \(both yours and your opponent's\)", "per_bench_both"),
        (r"(\d+) (?:more )?damage for each of your benched pokémon", "per_my_bench"),
        (r"(\d+) (?:more )?damage for each energy attached to both active", "per_energy_both_active"),
        (r"(\d+) (?:more )?damage for each energy attached to your opponent's active", "per_energy_opp_active"),
        (r"(\d+) (?:more )?damage for each grass energy attached to all of your", "per_my_grass_energy"),
        (r"(\d+) (?:more )?damage for each energy attached to this pokémon", "per_energy_self"),
        (r"(\d+) (?:more )?damage for each prize card your opponent has taken", "per_opp_prizes_taken"),
        (r"(\d+) (?:more )?damage for each damage counter on this pokémon", "per_self_counter"),
        (r"(\d+) (?:more )?damage for each of your opponent's pokémon ex in play", "per_opp_ex"),
        (r"(\d+) (?:more )?damage for each of your basic pokémon in play", "per_my_basic"),
        (r"(\d+) more damage for each heads", "coin_until_tails" if "until you get tails" in t else "coins"),
    ]
    for pat, mod in formulas:
        m = re.search(pat, t)
        if m:
            entry = {"mod": mod, "per": int(m.group(1))}
            if " more damage" not in m.group(0) and mod not in ("coins", "coin_until_tails"):
                a.base = 0   # "N damage for each X": the printed N is the per-unit rate, not a base
            if mod == "coins":
                mc = re.search(r"flip (\d+) coins", t)
                entry["n"] = int(mc.group(1)) if mc else 1
            a.mods.append(entry)
            parsed = True
    m = re.search(r"flip (\d+) coins\. this attack does (\d+) damage for each heads", t)
    if m:
        a.base = 0
        a.mods.append({"mod": "coins", "per": int(m.group(2)), "n": int(m.group(1))})
        parsed = True
    m = re.search(r"flip a coin\. if heads, this attack does (\d+) more damage", t)
    if m:
        a.mods.append({"mod": "coins", "per": int(m.group(1)), "n": 1})
        parsed = True
    if "if tails, this attack does nothing" in t:
        a.mods.append({"mod": "tails_nothing"})
        parsed = True
    conditional = [
        (r"moved from your bench to the active spot this turn, this attack does (\d+) more", "if_moved_in"),
        (r"if your opponent's active pokémon is a pokémon ex, this attack does (\d+) more", "if_opp_ex"),
        (r"if a stadium is in play, this attack does (\d+) more", "if_stadium"),
        (r"knocked out by damage from an attack during your opponent's last turn, this attack does (\d+) more", "if_ko_last"),
        (r"(\d+) or more pokémon that have the hide 'n' sneak ability in your discard pile, this attack does (\d+) more", "if_hns"),
        (r"at least 2 extra energy attached.*?this attack does (\d+) more", "if_extra_energy"),
        (r"same type as any of your opponent's pokémon in play, this attack does (\d+) more", "if_same_type"),
        (r"if your opponent's active pokémon is a (\w+) pokémon, this attack does (\d+) more", "if_opp_type"),
    ]
    for pat, mod in conditional:
        m = re.search(pat, t)
        if m:
            g = m.groups()
            entry = {"mod": mod, "per": int(g[-1])}
            if mod == "if_hns":
                entry["need"] = int(g[0])
            if mod == "if_opp_type":
                entry["ptype"] = g[0].capitalize()
            a.mods.append(entry)
            parsed = True
    m = re.search(r"you may discard (\d+) (\w+) energy from this pokémon and have this attack do (\d+) more", t)
    if m:
        a.mods.append({"mod": "optional_discard_boost", "n": int(m.group(1)), "per": int(m.group(3))})
        parsed = True
    m = re.search(r"discard any amount of basic energy from your pokémon\. this attack does (\d+) damage for each", t)
    if m:
        a.base = 0
        a.mods.append({"mod": "discard_any_energy", "per": int(m.group(1))})
        parsed = True
    if "if you don't have lunatone on your bench, this attack does nothing" in t:
        a.mods.append({"mod": "needs_partner", "name": "Lunatone"})
        parsed = True
    # copy attacks
    if "discard the top card of your deck, and if that card is a pokémon" in t:
        a.effects.append({"eff": "copy_topdeck"})
        parsed = True
    if "choose 1 of your benched" in t and "use it as this attack" in t:
        owner = "n's" if "n's pok" in t else None
        a.effects.append({"eff": "copy_bench", "owner": owner})
        parsed = True
    # other effects
    effect_table = [
        (r"they can't play any item cards", {"eff": "item_lock"}),
        (r"the defending pokémon can't retreat", {"eff": "no_retreat"}),
        (r"during your next turn, this pokémon can't (?:attack|use attacks)", {"eff": "self_lock"}),
        (r"during your next turn, this pokémon can't use ", {"eff": "self_lock"}),
        (r"discard all energy from this pokémon", {"eff": "discard_self_energy", "n": 99}),
        (r"put an energy attached to this pokémon into your hand", {"eff": "return_energy", "n": 1}),
        (r"put this pokémon and all attached cards into your hand", {"eff": "tuck_self"}),
        (r"switch out your opponent's active pokémon to the bench", {"eff": "push_out"}),
        (r"both active pokémon are knocked out", {"eff": "double_ko"}),
        (r"take 1 more prize card", {"eff": "extra_prize"}),
        (r"switch this pokémon with 1 of your benched", {"eff": "self_switch"}),
        (r"you may switch this pokémon with 1 of your benched", {"eff": "self_switch"}),
        (r"put up to (\d+) (\w+) from your discard pile onto your bench", {"eff": "revive_to_bench"}),
        (r"put a pokémon from your discard pile into your hand", {"eff": "recover_poke"}),
        (r"search your deck for a card that evolves from this pokémon and put it onto this pokémon", {"eff": "ascension"}),
        (r"discard your hand and draw (\d+) cards", {"eff": "discard_hand_draw"}),
        (r"discard the top (\d+) cards of your opponent's deck", {"eff": "mill"}),
        (r"this pokémon also does (\d+) damage to itself", {"eff": "recoil"}),
        (r"this pokémon is now confused", {"eff": "none"}),
        (r"is now confused", {"eff": "none"}),
    ]
    for pat, eff in effect_table:
        m = re.search(pat, t)
        if m:
            e = dict(eff)
            if m.groups():
                e["n"] = int(m.group(1)) if m.group(1).isdigit() else e.get("n")
                if eff["eff"] == "revive_to_bench":
                    e["name"] = m.group(2)
            if eff["eff"] != "none":
                a.effects.append(e)
            parsed = True
    m = re.search(r"draw (\d+) cards", t)
    if m and not any(e["eff"] == "discard_hand_draw" for e in a.effects):
        a.effects.append({"eff": "draw", "n": int(m.group(1))})
        parsed = True
    if re.search(r"draw a card", t):
        a.effects.append({"eff": "draw", "n": 1})
        parsed = True
    if "search your deck for" in t and not any(e["eff"] == "ascension" for e in a.effects):
        sr = parse_search(t)
        if sr:
            a.effects.append({"eff": "search", "search": sr})
            parsed = True
    m = re.search(r"attach (?:up to (\d+) )?basic (\w+ )?energy cards? from your (discard pile|deck) to", t)
    if m:
        a.effects.append({"eff": "attach_from", "n": int(m.group(1) or 1), "src": "discard" if "discard" in m.group(3) else "deck",
                          "etype": (m.group(2) or "").strip().capitalize() or None})
        parsed = True
    if not t:
        parsed = True
    if not parsed:
        if atk.expected_damage != atk.printed_damage:
            a.fallback_damage = atk.expected_damage
        s.unmodeled.append(f"attack {atk.name}")
    if atk.is_damage_counter_effect:
        a.kind = "counters"
    return a


_CACHE: dict[str, CardScript] = {}


def compile_script(card: CompiledCard) -> CardScript:
    if card.uid in _CACHE:
        return _CACHE[card.uid]
    s = CardScript(uid=card.uid)
    rt = _low(card.rules_text)
    if card.supertype == "Pokémon":
        if "as long as this pokémon is on your bench, prevent all damage done to this pokémon by attacks" in rt:
            s.passives.add("BENCH_SAFE")
        _ability_script(card, s)
        s.attacks = [_attack_script(card, a, s) for a in card.attacks]
    elif card.supertype == "Trainer":
        cost = re.search(r"only if you discard (\d+) other cards? from your hand", rt)
        cost_one = "only if you discard another card from your hand" in rt
        kind = "SUPPORTER" if "Supporter" in card.subtypes else ("TOOL" if "Pokémon Tool" in card.subtypes else ("STADIUM" if "Stadium" in card.subtypes else "ITEM"))
        ops = [] if kind in ("TOOL", "STADIUM") else _trainer_ops(card, rt, s)
        s.trainer = {"kind": kind, "ops": ops, "discard_cost": int(cost.group(1)) if cost else (1 if cost_one else 0),
                     "first_turn_ok": "if you go first, you may use this card during your first turn" in rt}
        if kind == "TOOL":
            m = re.search(r"gets \+(\d+) hp", rt)
            if m:
                s.tool["hp"] = int(m.group(1))
                m2 = re.search(r"the (\w+) pokémon this card is attached to gets", rt)
                if m2:
                    s.tool["hp_type"] = m2.group(1)
            m = re.search(r"retreat cost of the pokémon this card is attached to is (colorless)+ less", rt)
            if m:
                s.tool["retreat_minus"] = rt.count("colorless", m.start(), m.end())
            if card.damage_bonus:
                s.tool["dmg"] = card.damage_bonus
            if "that player takes 1 fewer prize card" in rt:
                s.tool["prize_minus"] = True
            if not s.tool:
                s.unmodeled.append("tool")
        elif kind == "STADIUM":
            s.stadium = _stadium_flags(rt)
            if not s.stadium:
                s.unmodeled.append("stadium")
        elif not ops:
            s.unmodeled.append("trainer")
    elif card.supertype == "Energy" and "Special" in card.subtypes:
        if re.search(r"draw (\d+) cards", rt):
            s.tool["on_attach_draw"] = int(re.search(r"draw (\d+) cards", rt).group(1))
        if "search your deck for up to 2 basic" in rt:
            s.tool["on_attach_search"] = parse_search(rt)
        if "gets +" in rt:
            m = re.search(r"gets \+(\d+) hp", rt)
            if m:
                s.tool["hp"] = int(m.group(1))
        if "takes 1 fewer prize card" in rt:
            s.tool["prize_minus"] = True
        if "discard it at the end of your turn" in rt:
            s.tool["discard_end_of_turn"] = True
    _CACHE[card.uid] = s
    return s
