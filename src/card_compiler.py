"""
Universal Card Compiler for Pokemon TCG Standard Rotation (3,101 cards).
Compiles raw JSON card definitions from `pokemon-tcg-data-standard/` into
canonical mechanical profiles (`CompiledCard`) and maps every card into the
16-dimensional Macro-Action Space (A) and State-Transition Capability vectors.
"""
from __future__ import annotations

import glob
import json
import re
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

# The 16 Canonical Macro-Actions in our Chess-like Abstract Action Space (A)
MACRO_ACTIONS = [
    "SETUP_BASIC",       # 0: Deploy Basic Pokemon to bench/active (Balls, Poffin, Artazon, Basics)
    "EVOLVE_LINE",       # 1: Evolve Stage 1/2, skip stage (Rare Candy, Forest of Vitality, Dawn, TM Evo)
    "DRAW_REFRESH",      # 2: Hand refresh & draw velocity (Lillie's, Research, Dudunsparce, Drakloak, Fezandipiti)
    "TUTOR_SEARCH",      # 3: Targeted card search (Poke Pad, Ultra Ball, Arven, Petrel, Ciphermaniac, Thwackey)
    "ACCEL_ENERGY",      # 4: Extra energy attachment beyond 1/turn (Crispin, Janine's, Teal Dance, Metal Maker)
    "STRIKE_LIGHT",      # 5: Fast low-cost attack (1-130 dmg) for early pressure / small basic KOs
    "STRIKE_MID",        # 6: Mid-tier attack (140-230 dmg) for 2-shot / Basic ex KOs
    "STRIKE_HEAVY",      # 7: Heavy OHKO attack (240-350+ dmg) for Stage 2 ex / Mega ex KOs
    "SPREAD_BENCH",      # 8: Bench damage / counter placement / transfer (Dragapult, Dusknoir, Munkidori, Froslass)
    "GUST_TARGET",       # 9: Force opponent bench to Active (Boss's Orders, Prime Catcher, Counter Catcher)
    "DISRUPT_HAND",      # 10: Shrink/shuffle opponent hand or deny energy (Unfair Stamp, Judge, Special Red Card, Hammer)
    "LOCK_STALL",        # 11: Item lock, Ability lock, Retreat lock, Ex-Immunity Wall, or Mill
    "WALL_BREAKER",      # 12: Non-ex high-efficiency attacker or shred attack that bypasses ex-immunity walls
    "MOBILITY_PIVOT",    # 13: Free retreat, Switch, Latias ex Skyliner, Air Balloon, Surfing Beach
    "RECOVER_CYCLE",     # 14: Discard recovery (Night Stretcher, Super Rod, Sacred Ash, Pal Pad, Energy Retrieval)
    "TANK_SURVIVE",      # 15: HP buff, damage reduction, healing, or bench barrier (Hero's Cape, Shaymin, Rabsca)
]

BASIC_ENERGY_MAP = {
    "Grass": ("MEE", "9", "Grass Energy"),
    "Fire": ("MEE", "10", "Fire Energy"),
    "Water": ("MEE", "11", "Water Energy"),
    "Lightning": ("MEE", "12", "Lightning Energy"),
    "Psychic": ("MEE", "13", "Psychic Energy"),
    "Fighting": ("MEE", "14", "Fighting Energy"),
    "Darkness": ("MEE", "15", "Darkness Energy"),
    "Metal": ("MEE", "16", "Metal Energy"),
}

# Card-data errata: upstream JSON misspells the restored-Pokemon fossil name.
# Normalize it so evolution chains (Fossil -> Archen -> Archeops) resolve correctly.
EVOLVES_FROM_ALIASES = {
    "Antiuqe Plume Fossil": "Antique Plume Fossil",
}
FOSSIL_ITEM_NAMES = {"Antique Plume Fossil"}


@dataclass
class AttackProfile:
    name: str
    cost: list[str]
    converted_cost: int
    colored_cost: dict[str, int]
    colorless_cost: int
    printed_damage: int
    expected_damage: float
    max_ceiling_damage: float
    bench_spread_damage: float
    is_damage_counter_effect: bool
    is_shred: bool
    is_item_lock: bool
    is_retreat_lock: bool
    mills_cards: int
    discards_energy: int
    searches_or_draws: bool
    accelerates_energy: bool
    requires_switch_in: bool
    requires_discard_trait: str | None
    scales_with: str | None
    text: str


@dataclass
class CompiledCard:
    uid: str                        # Canonical ID (e.g., "MEG 104" or "TWM 130")
    card_id: str                    # Raw JSON id (e.g., "me1-104")
    name: str
    set_code: str
    set_num: str
    supertype: str                  # "Pokémon", "Trainer", "Energy"
    subtypes: list[str]
    hp: int
    types: list[str]
    evolves_from: str | None
    evolves_to: list[str]
    stage: int                      # 0=Basic, 1=Stage 1, 2=Stage 2, -1=Trainer/Energy
    prize_liability: int            # 1=Single prizer, 2=ex, 3=Mega ex
    is_rule_box: bool
    is_ace_spec: bool
    weakness: str | None
    resistance: str | None
    retreat_cost: int
    attacks: list[AttackProfile] = field(default_factory=list)
    abilities: list[dict[str, str]] = field(default_factory=list)
    rules_text: str = ""
    primary_energy_type: str | None = None
    action_vector: dict[str, float] = field(default_factory=dict)
    tags: set[str] = field(default_factory=set)
    synergy_hooks: set[str] = field(default_factory=set)
    meta_play_rate: float = 0.0     # Empirical play rate in 512 tournament decks
    # ---- Structured effect profile (see `_extract_requirements` / `_extract_play_conditions`) ----
    # Deck-composition prerequisites: the card only does something if the deck contains
    # Pokemon matching `filter` (e.g. Rosa's Encouragement -> {"stage": 2}). Each entry:
    #   {"filter": {...}, "min": <copies for full value>, "acts": [macro actions gated] | None (= all)}
    requirements: list[dict[str, Any]] = field(default_factory=list)
    requirement_mode: str = "all"   # "all" (every req), "any" (one of them), "mean" (partial, e.g. Dawn)
    # Situational gates per macro action, e.g. {"ACCEL_ENERGY": ("BEHIND_ON_PRIZES",)}.
    # Gated actions only count in board states where the condition is live (see CONDITION_LIVENESS).
    action_conditions: dict[str, tuple[str, ...]] = field(default_factory=dict)
    # Attack-damage modifier (Brave Bangle, Black Belt's Training, Premium Power Pro, ...).
    # {"amount": int, "vs_ex": bool, "filter": {...attacker filter...}, "kind": "TOOL"|"ITEM"|"SUPPORTER"}
    damage_bonus: dict[str, Any] | None = None

    def __hash__(self) -> int:
        return hash(self.uid)

    def __eq__(self, other: object) -> bool:
        return isinstance(other, CompiledCard) and self.uid == other.uid


def _parse_int(val: Any, default: int = 0) -> int:
    if val is None:
        return default
    m = re.search(r"\d+", str(val))
    return int(m.group(0)) if m else default


# ---------------------------------------------------------------------------
# Structured effect parsing: requirements, play conditions, damage modifiers
# ---------------------------------------------------------------------------

POKEMON_TYPE_WORDS = {
    "grass", "fire", "water", "lightning", "psychic", "fighting", "darkness", "metal", "dragon", "colorless",
}
_POKEMON_RE = re.compile(r"pok[eé]mon")
_WORD_RE = re.compile(r"[a-z0-9'é-]+")
_REMINDER_RE = re.compile(r"\((?:pok[eé]mon ex|pok[eé]mon v|existing effects|damage is not|damage from attacks|apply weakness|don't apply)[^)]*\)")

# Situational play conditions ("You can use this card only if ...") -> condition key.
PLAY_CONDITION_PATTERNS: list[tuple[str, str]] = [
    (r"more prize cards remaining than your opponent", "BEHIND_ON_PRIZES"),
    (r"your opponent has exactly 2 prize cards remaining", "OPP_PRIZES_EQ_2"),
    (r"your opponent has 2 or fewer prize cards remaining", "OPP_PRIZES_LE_2"),
    (r"your opponent has 3 or fewer prize cards remaining", "OPP_PRIZES_LE_3"),
    (r"knocked out during your opponent's last turn", "AFTER_OWN_KO"),
    (r"last card in your hand", "LAST_CARD_IN_HAND"),
    (r"can't use this card during your first turn", "NOT_FIRST_TURN"),
]
# Ability gates ("Once during your turn, if this Pokemon is in the Active Spot, ...").
ABILITY_CONDITION_PATTERNS: list[tuple[str, str]] = [
    (r"if this pok[eé]mon is in the active spot", "ACTIVE_ONLY"),
    (r"knocked out during your opponent's last turn", "AFTER_OWN_KO"),
    (r"more prize cards remaining than your opponent", "BEHIND_ON_PRIZES"),
]


def card_matches_filter(card: "CompiledCard", f: dict[str, Any]) -> bool:
    """True if Pokemon `card` satisfies the structured requirement filter `f`."""
    if card.supertype != "Pokémon":
        return False
    if "stage" in f and card.stage != f["stage"]:
        return False
    if f.get("evolution") and card.stage < 1:
        return False
    if "ptype" in f and f["ptype"] not in card.types:
        return False
    if "owner" in f and not card.name.lower().startswith(f["owner"]):
        return False
    if f.get("rule_box") is False and card.is_rule_box:
        return False
    if f.get("ex") and "ex" not in card.subtypes:
        return False
    if f.get("mega") and "MEGA" not in card.subtypes:
        return False
    for st in ("Tera", "Ancient", "Future"):
        if f.get(st.lower()) and st not in card.subtypes:
            return False
    if "name" in f and card.name.lower() != f["name"]:
        return False
    if "max_hp" in f and card.hp > f["max_hp"]:
        return False
    if f.get("direct_attacker") and not any(
        not a.is_damage_counter_effect and max(a.expected_damage, float(a.printed_damage)) >= 60
        for a in card.attacks
    ):
        return False
    return True


def _parse_pokemon_descriptor(prefix: str, suffix: str) -> dict[str, Any] | None:
    """
    Parse the words immediately before an occurrence of "Pokemon" (and a short suffix)
    into a filter, e.g. "1 of your Benched Psychic" -> {"ptype": "Psychic"}.
    Returns None when the phrase targets the opponent's Pokemon (not a deck requirement).
    """
    words = _WORD_RE.findall(prefix)[-6:]
    f: dict[str, Any] = {}
    i = len(words) - 1
    while i >= 0:
        w = words[i]
        if w in POKEMON_TYPE_WORDS:
            f["ptype"] = w.capitalize()
        elif w in ("1", "2") and i > 0 and words[i - 1] == "stage":
            f["stage"] = int(w)
            i -= 1
        elif w == "basic":
            f["stage"] = 0
        elif w == "evolution":
            if i > 0 and words[i - 1] == "mega":
                f["mega"] = True
                i -= 1
            else:
                f["evolution"] = True
        elif w == "mega":
            f["mega"] = True
        elif w in ("tera", "ancient", "future"):
            f[w] = True
        elif w in ("benched", "active"):
            pass
        elif w == "opponent's":
            return None
        elif w.endswith("'s") and w not in ("player's", "boss's"):
            if w == "rocket's" and i > 0 and words[i - 1] == "team":
                f["owner"] = "team rocket's"
                i -= 1
            else:
                f["owner"] = w
        else:
            break
        i -= 1
    suf = suffix[:70]
    if re.match(r"\s+ex\b", suf):
        f["ex"] = True
    if "doesn't have a rule box" in suf or "don't have a rule box" in suf:
        f["rule_box"] = False
    m_hp = re.match(r"\s+with (\d+) hp or less", suf)
    if m_hp:
        f["max_hp"] = int(m_hp.group(1))
    return f


def _extract_requirements(rules_low: str, subtypes: list[str]) -> tuple[list[dict[str, Any]], str]:
    """
    Extract deck-composition prerequisites from Trainer / Special Energy text.
    Only phrases about *your* Pokemon count; symmetric stadium effects
    ("both yours and your opponent's") and opponent targets are ignored.
    """
    if not rules_low or "both yours and your opponent's" in rules_low:
        return [], "all"
    text = _REMINDER_RE.sub("", rules_low)
    # "Play this card as if it were a 60-HP Basic Colorless Pokemon" (fossils) describes the card itself.
    text = re.sub(r"as if it were an? [^.]*?pok[eé]mon", "", text)
    reqs: list[dict[str, Any]] = []
    seen: set[tuple] = set()

    def _add(f: dict[str, Any], acts: list[str] | None = None, min_copies: int = 3) -> None:
        key = (tuple(sorted(f.items())), tuple(acts or ()))
        if f and key not in seen:
            seen.add(key)
            reqs.append({"filter": f, "min": min_copies, "acts": acts})

    for m in _POKEMON_RE.finditer(text):
        after = text[m.end():]
        if re.match(r"\s+(tool|center|card)", after):
            continue
        f = _parse_pokemon_descriptor(text[:m.start()], after)
        if f:
            _add(f)
    # "If you have a Stage 2 card in your hand" (Rare Candy) / "attached to a Stage 2 Pokemon" (Neo Upper)
    if "stage 2 card" in text:
        _add({"stage": 2})
    # Named attachment targets: "the Pikachu ex this card is attached to" (Light Ball, Core Memory)
    for m in re.finditer(r"the ([a-z0-9' .-]+?) this card is attached to", text):
        target = m.group(1).strip()
        if not _POKEMON_RE.search(target):
            _add({"name": target})

    if "in any combination of" in text or re.search(r"pok[eé]mon or (?:a |an |1 )?(?:basic|evolution|stage)", text) \
            or re.search(r"energy card or a basic", text):
        mode = "any"
    elif "search your deck for" in text and len(reqs) > 1:
        mode = "mean"
    else:
        mode = "all"
    return reqs, mode


def _extract_play_conditions(text_low: str, patterns: list[tuple[str, str]]) -> tuple[str, ...]:
    return tuple(cond for pat, cond in patterns if re.search(pat, text_low))


def _extract_damage_bonus(rules_low: str, subtypes: list[str]) -> dict[str, Any] | None:
    """Parse "+N damage to your opponent's Active Pokemon (ex)" modifiers on Trainers."""
    m = re.search(r"(\d+) more damage to your opponent's active pok[eé]mon( ex)?", rules_low)
    if not m:
        return None
    before = rules_low[:m.start()]
    attacker: dict[str, Any] = {"direct_attacker": True}
    for pm in _POKEMON_RE.finditer(before):
        f = _parse_pokemon_descriptor(before[:pm.start()], before[pm.end():])
        if f:
            attacker.update(f)
    if "doesn't have a rule box" in before or "don't have a rule box" in before:
        attacker["rule_box"] = False
    m_name = re.search(r"the ([a-z0-9' .-]+?) this card is attached to", before)
    if m_name and not _POKEMON_RE.search(m_name.group(1)):
        attacker["name"] = m_name.group(1).strip()
    kind = "TOOL" if "Pokémon Tool" in subtypes else ("SUPPORTER" if "Supporter" in subtypes else "ITEM")
    return {"amount": int(m.group(1)), "vs_ex": bool(m.group(2)), "filter": attacker, "kind": kind}


def _analyze_attack(atk: dict[str, Any], card_abilities: list[dict[str, str]], card_name: str = "") -> AttackProfile:
    name = atk.get("name", "")
    cost = atk.get("cost") or []
    colored_cost: dict[str, int] = defaultdict(int)
    colorless_cost = 0
    for c in cost:
        if c == "Colorless" or c == "Free":
            if c == "Colorless":
                colorless_cost += 1
        else:
            colored_cost[c] += 1
    conv_cost = len(cost) if cost != ["Free"] else 0

    raw_dmg_str = str(atk.get("damage") or "")
    base_dmg = _parse_int(raw_dmg_str, 0)
    text = atk.get("text") or ""
    text_low = text.lower()

    expected_dmg = float(base_dmg)
    max_dmg = float(base_dmg)
    bench_spread = 0.0
    is_damage_counter_effect = False
    scales_with = None
    requires_switch = False
    requires_discard_trait = None

    # 1. Damage counters placed on Active or Bench (Effect of attack, NOT direct attack damage!)
    if "damage counter" in text_low:
        # e.g., "Place 2 damage counters on your opponent's Active Pokémon for each card in your hand"
        m_hand = re.search(r"(?:place|put) (\d+) damage counters? .*?for each card in your hand", text_low)
        m_opp_hand = re.search(r"(?:place|put) (\d+) damage counters? .*?for each card in your opponent's hand", text_low)
        m_bench_cnt = re.search(r"(?:place|put) (\d+) damage counters? on your opponent's benched", text_low)
        m_fixed_any = re.search(r"(?:place|put) (\d+) damage counters? on your opponent's pok", text_low)
        if m_hand:
            per_card = int(m_hand.group(1)) * 10
            expected_dmg = per_card * 8.5   # Typical midgame hand with Psychic Draw / Dudunsparce
            max_dmg = per_card * 13.0
            scales_with = "HAND_SIZE"
            if base_dmg == 0:
                is_damage_counter_effect = True
        elif m_opp_hand:
            per_card = int(m_opp_hand.group(1)) * 10
            expected_dmg = per_card * 5.5
            max_dmg = per_card * 8.0
            scales_with = "OPP_HAND_SIZE"
            if base_dmg == 0:
                is_damage_counter_effect = True
        elif m_bench_cnt:
            bench_spread = int(m_bench_cnt.group(1)) * 10.0
        elif m_fixed_any:
            total_c = int(m_fixed_any.group(1)) * 10.0
            if base_dmg == 0:
                expected_dmg = total_c * 0.6
                bench_spread = total_c * 0.4
                max_dmg = total_c
                is_damage_counter_effect = True
            else:
                bench_spread = total_c
        elif base_dmg == 0 and ("place" in text_low or "put" in text_low):
            is_damage_counter_effect = True

    # 2. Direct bench damage in text (e.g., "does 30 damage to 1 of your opponent's Benched", "120 damage to 2")
    m_bench_dmg = re.search(r"does (\d+) damage to (\d+|each) of your opponent's benched", text_low)
    if m_bench_dmg:
        bd = int(m_bench_dmg.group(1))
        targets = 3 if m_bench_dmg.group(2) == "each" else int(m_bench_dmg.group(2))
        bench_spread = max(bench_spread, float(bd * targets))
    # Snipe attacks that can hit ANY of the opponent's Pokemon (Fezandipiti ex Cruel Arrow,
    # Iron Crown ex Twin Shotels). This is attack damage (not damage counters), so it
    # can target the Active for a KO or a Benched Pokemon.
    m_snipe = re.search(r"does (\d+) damage to (\d+) of your opponent's pok[eé]mon", text_low)
    if m_snipe and base_dmg == 0:
        sd, n_tg = int(m_snipe.group(1)), int(m_snipe.group(2))
        expected_dmg = max(expected_dmg, float(sd))
        max_dmg = max(max_dmg, float(sd))
        bench_spread = max(bench_spread, float(sd * (n_tg - 1)) if n_tg > 1 else sd * 0.5)

    # 3. Scaling formulas in attack text
    if "benched" in text_low and "for each" in text_low and "damage" in text_low:
        m = re.search(r"(\d+) (?:more )?damage for each (?:of your |of your opponent's )?benched", text_low)
        per_b = int(m.group(1)) if m else 20
        both = "both yours and your opponent" in text_low
        mult_exp = 7.5 if both else 4.5
        mult_max = 10.0 if both else 5.0
        expected_dmg = base_dmg + per_b * mult_exp if "+" in raw_dmg_str else per_b * mult_exp
        max_dmg = base_dmg + per_b * mult_max if "+" in raw_dmg_str else per_b * mult_max
        scales_with = "BENCH_COUNT"

    elif "for each energy" in text_low or "for each basic energy" in text_low or "for each card you discarded" in text_low:
        m = re.search(r"(\d+) (?:more )?damage for each", text_low)
        per_e = int(m.group(1)) if m else 50
        expected_dmg = base_dmg + per_e * 3.5 if "+" in raw_dmg_str else per_e * 4.0
        max_dmg = base_dmg + per_e * 5.5 if "+" in raw_dmg_str else per_e * 6.0
        scales_with = "ENERGY_COUNT"

    elif "prize card your opponent has taken" in text_low:
        m = re.search(r"(\d+) more damage for each prize card", text_low)
        per_p = int(m.group(1)) if m else 30
        expected_dmg = base_dmg + per_p * 3.0
        max_dmg = base_dmg + per_p * 5.0
        scales_with = "OPP_PRIZES_TAKEN"

    elif "moved from your bench to the active spot this turn" in text_low:
        m = re.search(r"does (\d+) more damage", text_low)
        bonus = int(m.group(1)) if m else 120
        expected_dmg = base_dmg + bonus * 0.85
        max_dmg = base_dmg + bonus
        requires_switch = True
        scales_with = "SWITCH_INTO_ACTIVE"

    elif "in your discard pile" in text_low:
        m = re.search(r"does (\d+) (?:more )?damage", text_low)
        val = int(m.group(1)) if m else 100
        if "for each" in text_low:
            expected_dmg = base_dmg + val * 4.0
            max_dmg = base_dmg + val * 6.0
        else:
            expected_dmg = base_dmg + val * 0.85
            max_dmg = base_dmg + val
        scales_with = "DISCARD_PILE"
        if "hide 'n' sneak" in text_low:
            requires_discard_trait = "Hide 'n' Sneak"

    elif "extra energy attached" in text_low:
        m = re.search(r"does (\d+) more damage", text_low)
        bonus = int(m.group(1)) if m else 100
        expected_dmg = base_dmg + bonus * 0.75
        max_dmg = base_dmg + bonus
        scales_with = "EXTRA_ENERGY"

    elif "if you have a stadium in play" in text_low or "if festival grounds is in play" in text_low:
        m = re.search(r"does (\d+) more damage", text_low)
        if m:
            bonus = int(m.group(1))
            expected_dmg = base_dmg + bonus * 0.8
            max_dmg = base_dmg + bonus
            scales_with = "STADIUM_IN_PLAY"

    elif "until you get tails" in text_low:
        m = re.search(r"(\d+) (?:more )?damage for each heads", text_low)
        per_h = int(m.group(1)) if m else 50
        expected_dmg = base_dmg + per_h * 1.0  # E[Geom(0.5) heads before tails] = 1
        max_dmg = base_dmg + per_h * 3.0
        scales_with = "COIN_FLIP"

    elif "flip" in text_low and "coin" in text_low:
        m_n = re.search(r"flip (\d+) coins.*(\d+) (?:more )?damage for each heads", text_low)
        m_1 = re.search(r"flip a coin\. if heads, this attack does (\d+) more damage", text_low)
        if m_n:
            ncoins, per_h = int(m_n.group(1)), int(m_n.group(2))
            expected_dmg = base_dmg + 0.5 * ncoins * per_h
            max_dmg = base_dmg + ncoins * per_h
        elif m_1:
            bonus = int(m_1.group(1))
            expected_dmg = base_dmg + 0.5 * bonus
            max_dmg = base_dmg + bonus
        elif "if tails, this attack does nothing" in text_low:
            expected_dmg = base_dmg * 0.5

    # Special copy-attack mechanics (Slowking Seek Inspiration, N's Zoroark Night Joker, Mew ex Genome Hacking)
    if "discard the top card of your deck, and if that card is a pok" in text_low:
        expected_dmg = 220.0
        max_dmg = 330.0
        bench_spread = 90.0
        scales_with = "TOPDECK_ATTACK_COPY"
    elif "choose 1 of your benched" in text_low and "use it as this attack" in text_low:
        expected_dmg = 210.0
        max_dmg = 280.0
        bench_spread = 60.0
        scales_with = "BENCH_ATTACK_COPY"
    elif "choose 1 of your opponent's active pok" in text_low and "use it as this attack" in text_low:
        expected_dmg = 190.0
        max_dmg = 280.0
        scales_with = "OPP_ATTACK_COPY"

    # Shared attack-text compiler (src/attack_text.py + card_patches.json): patches with typical values win;
    # otherwise it fills in attacks the heuristics above found nothing special in (Knock-Out-both, optional
    # or conditional bonuses, freely placed counters, ...), so deck scoring and the engine bridge agree.
    try:
        from attack_text import parse_attack, typical_damage
        _sp = parse_attack(text, atk.get("damage"), cost, name, card_name)
        _exp, _mx = typical_damage(_sp)
        if _sp.get("patched") and _sp.get("typical"):
            expected_dmg, max_dmg = float(_exp), float(_mx)
        elif abs(expected_dmg - base_dmg) < 1e-6 and abs(_exp - base_dmg) > 1e-6:
            expected_dmg, max_dmg = float(_exp), max(float(_mx), max_dmg)
    except Exception:  # the compiler must never fail on odd card text
        pass

    # Check if Pokemon has Seasoned Skill (Bloodmoon Ursaluna ex cost reduction)
    if any("seasoned skill" in (ab.get("name") or "").lower() for ab in card_abilities) and conv_cost >= 4:
        conv_cost = 1
        colorless_cost = 1

    # Check if Pokemon has Festival Lead ability (attacks twice when Stadium is in play!)
    has_festival_lead = any("festival lead" in (ab.get("name") or "").lower() for ab in card_abilities)
    if has_festival_lead and expected_dmg > 0:
        expected_dmg *= 1.85
        max_dmg *= 2.0

    is_shred = "isn't affected by any effects on your opponent's active" in text_low or "isn't affected by weakness or resistance, or by any effects" in text_low
    is_item_lock = "can't play any item cards" in text_low
    is_retreat_lock = "can't retreat" in text_low
    m_mill = re.search(r"discard the top (\d+) cards? of your opponent's deck", text_low)
    mills_cards = int(m_mill.group(1)) if m_mill else (1 if "discard the top card of your opponent's deck" in text_low else 0)
    m_disc_en = re.search(r"discard (\d+|all) .*?energ.*?from this pok", text_low)
    discards_en = 3 if (m_disc_en and m_disc_en.group(1) == "all") else (int(m_disc_en.group(1)) if m_disc_en else 0)
    searches_or_draws = ("search your deck" in text_low or "draw " in text_low) and expected_dmg <= 90
    accelerates_en = "attach" in text_low and "energy" in text_low and ("from your deck" in text_low or "from your discard" in text_low)

    return AttackProfile(
        name=name,
        cost=cost,
        converted_cost=conv_cost,
        colored_cost=dict(colored_cost),
        colorless_cost=colorless_cost,
        printed_damage=base_dmg,
        expected_damage=round(expected_dmg, 1),
        max_ceiling_damage=round(max_dmg, 1),
        bench_spread_damage=round(bench_spread, 1),
        is_damage_counter_effect=is_damage_counter_effect,
        is_shred=is_shred,
        is_item_lock=is_item_lock,
        is_retreat_lock=is_retreat_lock,
        mills_cards=mills_cards,
        discards_energy=discards_en,
        searches_or_draws=searches_or_draws,
        accelerates_energy=accelerates_en,
        requires_switch_in=requires_switch,
        requires_discard_trait=requires_discard_trait,
        scales_with=scales_with,
        text=text,
    )


def compile_card_from_json(raw: dict[str, Any], set_code: str, meta_rate: float = 0.0) -> CompiledCard:
    name = raw["name"]
    num = str(raw.get("number", ""))
    uid = f"{set_code} {num}"
    supertype = raw.get("supertype", "")
    subtypes = raw.get("subtypes") or []
    hp = _parse_int(raw.get("hp"), 0)
    types = raw.get("types") or []
    evolves_from = raw.get("evolvesFrom")
    if evolves_from:
        evolves_from = EVOLVES_FROM_ALIASES.get(evolves_from, evolves_from)
    evolves_to = raw.get("evolvesTo") or []

    if supertype == "Pokémon":
        if "Basic" in subtypes:
            stage = 0
        elif "Stage 1" in subtypes:
            stage = 1
        elif "Stage 2" in subtypes:
            stage = 2
        else:
            stage = 0
    else:
        stage = -1

    is_mega = "MEGA" in subtypes
    is_ex = "ex" in subtypes
    is_ace_spec = "ACE SPEC" in subtypes
    prize_liability = 3 if is_mega else (2 if is_ex else (1 if supertype == "Pokémon" else 0))
    is_rule_box = prize_liability >= 2

    weaknesses = raw.get("weaknesses") or []
    weakness = weaknesses[0].get("type") if weaknesses else None
    resistances = raw.get("resistances") or []
    resistance = resistances[0].get("type") if resistances else None
    retreat_cost = int(raw.get("convertedRetreatCost") or 0)

    abilities = raw.get("abilities") or []
    attacks = [_analyze_attack(a, abilities, raw.get("name", "")) for a in (raw.get("attacks") or [])]

    rules_list = [
        r for r in (raw.get("rules") or [])
        if not r.startswith("You may play")
        and not r.startswith("When your")
        and not r.startswith("Pokémon ex rule")
        and not r.startswith("Mega Evolution ex Rule")
        and not r.startswith("Attach a Pokémon Tool")
        and not r.startswith("You can't have more than 1 ACE SPEC")
    ]
    rules_text = " ".join(rules_list)

    # Determine primary energy type for Pokemon or Energy
    primary_energy = None
    if supertype == "Pokémon":
        for a in attacks:
            if a.colored_cost:
                primary_energy = max(a.colored_cost.items(), key=lambda x: x[1])[0]
                break
        if not primary_energy and types:
            primary_energy = types[0]
    elif supertype == "Energy":
        for et in BASIC_ENERGY_MAP:
            if et.lower() in name.lower() or f"provides {et.lower()} energy" in rules_text.lower():
                primary_energy = et
                break

    vec = {act: 0.0 for act in MACRO_ACTIONS}
    tags: set[str] = set()
    hooks: set[str] = set()
    action_conditions: dict[str, tuple[str, ...]] = {}
    requirements: list[dict[str, Any]] = []
    requirement_mode = "all"
    damage_bonus: dict[str, Any] | None = None

    if is_ace_spec:
        tags.add("ACE_SPEC")
    if is_rule_box:
        tags.add("RULE_BOX")
    else:
        tags.add("NON_RULE_BOX")

    if supertype == "Pokémon":
        if stage == 0:
            vec["SETUP_BASIC"] += 0.35
            if hp <= 70:
                tags.add("POFFIN_TARGET")
        else:
            vec["EVOLVE_LINE"] += 0.25

        # Abilities analysis
        cond_parts: dict[str, dict[tuple[str, ...], float]] = defaultdict(dict)
        for ab in abilities:
            ab_name = (ab.get("name") or "").lower()
            ab_text = (ab.get("text") or "").lower()
            vec_before = dict(vec)
            ab_conds = _extract_play_conditions(ab_text, ABILITY_CONDITION_PATTERNS)
            if "hide 'n' sneak" in ab_name:
                hooks.add("HIDE_N_SNEAK")
                vec["TANK_SURVIVE"] += 0.25
            if "draw" in ab_text or ("look at the top" in ab_text and "put" in ab_text and "into your hand" in ab_text):
                m_dr = re.search(r"draw (\d+) cards?", ab_text)
                n_dr = int(m_dr.group(1)) if m_dr else 2
                vec["DRAW_REFRESH"] += min(1.0, 0.30 * n_dr)
                tags.add("DRAW_ENGINE_POKEMON")
                if "shuffle this pok" in ab_text:
                    vec["MOBILITY_PIVOT"] += 0.35
            if "search your deck" in ab_text and "put" in ab_text and "into your hand" in ab_text:
                vec["TUTOR_SEARCH"] += 0.85
                vec["DRAW_REFRESH"] += 0.45
                tags.add("TUTOR_POKEMON")
                tags.add("DRAW_ENGINE_POKEMON")
                if "festival lead" in ab_text:
                    hooks.add("SUPPORTS_FESTIVAL_LEAD")
            if re.search(r"\battach\b", ab_text) and "energy" in ab_text and "to" in ab_text:
                if "if you have" not in ab_text or "in play" not in ab_text:
                    vec["ACCEL_ENERGY"] += 0.85
                    tags.add("ENERGY_ACCEL_POKEMON")
                    for et in BASIC_ENERGY_MAP:
                        if et.lower() in ab_text:
                            hooks.add(f"ACCEL_{et.upper()}")
            if "provides" in ab_text and "energy" in ab_text and "each basic" in ab_text:
                vec["ACCEL_ENERGY"] += 0.95
                tags.add("ENERGY_DOUBLER")
                hooks.add("ACCEL_GRASS")
            if "damage counter" in ab_text and ("opponent" in ab_text or "each pok" in ab_text):
                if "knocked out" in ab_text:
                    m_dc = re.search(r"put (\d+) damage counters", ab_text)
                    dc = int(m_dc.group(1)) if m_dc else 5
                    vec["SPREAD_BENCH"] += min(1.0, dc / 10.0)
                    tags.add("SELF_KO_BOMBER")
                    hooks.add("DUSKNOIR_LINE")
                elif "can't be moved" in ab_text:
                    vec["TANK_SURVIVE"] += 0.55
                elif "move" in ab_text:
                    vec["SPREAD_BENCH"] += 0.65
                    vec["TANK_SURVIVE"] += 0.35
                    tags.add("DAMAGE_MOVER")
                else:
                    vec["SPREAD_BENCH"] += 0.55
                    tags.add("PASSIVE_SPREAD")
            if "prevent all damage" in ab_text and "benched" in ab_text:
                tags.add("BENCH_BARRIER")
                tags.add("BENCH_DAMAGE_BARRIER")
                if "effects of attacks" in ab_text:
                    # Rabsca (Spherical Shield): blocks BOTH bench attack damage AND attack effects
                    # (such as Dragapult ex's Phantom Dive damage counters).
                    vec["TANK_SURVIVE"] += 0.65
                    tags.add("BENCH_COUNTER_BARRIER")
                    ab_conds = ab_conds + ("VS_BENCH_SPREAD",)
                else:
                    # Shaymin (Flower Curtain): blocks ONLY attack damage to benched non-Rule-Box
                    # Pokemon (e.g. Trifrost / Flamebody Cannon). Does NOT stop damage counters
                    # placed by effects of attacks (Phantom Dive) or Abilities (Cursed Blast / Adrena-Brain).
                    # Its survival value therefore only exists against bench ATTACK DAMAGE.
                    vec["TANK_SURVIVE"] += 0.35
                    ab_conds = ab_conds + ("VS_BENCH_ATTACK_DAMAGE",)
            # IMMUNITY_WALL is SELf-protection (Crustle, Sylveon, Farigiraf), not bench
            # protection. Shaymin's Flower Curtain also mentions "(Pokemon ex ...)" in its
            # reminder text, which used to mis-tag it as an unkillable attacker.
            if (
                "prevent all damage" in ab_text
                and "benched" not in ab_text
                and "on your bench" not in ab_text
                and ("to this pok" in ab_text or "to your active pok" in ab_text)
            ):
                vec["LOCK_STALL"] += 0.95
                vec["TANK_SURVIVE"] += 0.70
                tags.add("IMMUNITY_WALL")
            if "have no retreat cost" in ab_text or ("retreat cost" in ab_text and "less" in ab_text):
                vec["MOBILITY_PIVOT"] += 0.85
                tags.add("FREE_RETREAT_AURA")
            elif "retreat cost" in ab_text and "more" in ab_text:
                vec["LOCK_STALL"] += 0.55
            if "switched" in ab_text and "active" in ab_text and "opponent" in ab_text:
                vec["GUST_TARGET"] += 0.60
            if "devolve" in ab_text and "opponent" in ab_text and "evolution" in ab_text:
                # Ancient Wing (Archeops): repeatedly strips the opponent's highest Stage
                # while Archeops is Active, forcing them to rebuild their evolution line.
                vec["LOCK_STALL"] += 0.55
                vec["WALL_BREAKER"] += 0.45
                tags.add("DEVOLUTION_CONTROL")
            if "weakness of each of your opponent's dragon" in ab_text:
                vec["STRIKE_HEAVY"] += 0.65
                tags.add("DRAGON_SLAYER")
                ab_conds = ab_conds + ("VS_DRAGON",)
            if ab_conds:
                for act, v in vec.items():
                    delta = v - vec_before.get(act, 0.0)
                    if delta > 0:
                        cond_parts[act][ab_conds] = cond_parts[act].get(ab_conds, 0.0) + delta

        # Attacks analysis
        for atk in attacks:
            eff_cost = max(1.0, atk.converted_cost - 0.3 * atk.colorless_cost)
            dmg_eff = atk.expected_damage / eff_cost
            if 0 < atk.expected_damage <= 130:
                vec["STRIKE_LIGHT"] = max(vec["STRIKE_LIGHT"], min(1.0, (atk.expected_damage / 110.0) * (1.2 / max(1, atk.converted_cost))))
            if 130 < atk.expected_damage <= 230 or (atk.max_ceiling_damage >= 160 and atk.expected_damage >= 110):
                vec["STRIKE_MID"] = max(vec["STRIKE_MID"], min(1.0, atk.expected_damage / 200.0))
            if atk.expected_damage >= 210 or atk.max_ceiling_damage >= 260:
                vec["STRIKE_HEAVY"] = max(vec["STRIKE_HEAVY"], min(1.0, max(atk.expected_damage, atk.max_ceiling_damage * 0.85) / 280.0))
            if atk.bench_spread_damage > 0:
                vec["SPREAD_BENCH"] = max(vec["SPREAD_BENCH"], min(1.0, atk.bench_spread_damage / 60.0))
            if atk.is_shred or (not is_rule_box and atk.expected_damage >= 110):
                vec["WALL_BREAKER"] = max(vec["WALL_BREAKER"], min(1.0, max(atk.expected_damage, 120.0) / 170.0))
                tags.add("WALL_BREAKER_ATTACKER")
            if atk.is_item_lock or atk.is_retreat_lock or atk.mills_cards >= 2:
                vec["LOCK_STALL"] = max(vec["LOCK_STALL"], 0.85 if atk.is_item_lock else 0.65)
            if atk.accelerates_energy:
                vec["ACCEL_ENERGY"] = max(vec["ACCEL_ENERGY"], 0.55)
            if atk.searches_or_draws:
                vec["SETUP_BASIC"] = max(vec["SETUP_BASIC"], 0.40)
            if atk.requires_switch_in:
                hooks.add("NEEDS_SWITCH_PIVOT")
            if atk.requires_discard_trait == "Hide 'n' Sneak":
                hooks.add("NEEDS_HIDE_N_SNEAK")
            if atk.scales_with:
                hooks.add(f"SCALES_{atk.scales_with}")

        if retreat_cost == 0:
            vec["MOBILITY_PIVOT"] = max(vec["MOBILITY_PIVOT"], 0.45)
            tags.add("FREE_RETREATER")
        if hp >= 300:
            vec["TANK_SURVIVE"] = max(vec["TANK_SURVIVE"], min(1.0, (hp - 220) / 140.0))

        # Gate an action on its ability's condition only when ALL of that action's value
        # came from conditional abilities (e.g. Mega Kangaskhan ex draws only while Active,
        # Fezandipiti ex draws only after a KO); unconditional sources keep it live.
        for act, parts in cond_parts.items():
            cond_total = sum(parts.values())
            if cond_total > 0 and cond_total >= vec[act] - 1e-6:
                action_conditions[act] = max(parts.items(), key=lambda kv: kv[1])[0]

    elif supertype == "Trainer":
        rt = rules_text.lower()
        is_supp = "Supporter" in subtypes
        is_item = "Item" in subtypes
        is_tool = "Pokémon Tool" in subtypes
        is_stad = "Stadium" in subtypes

        if is_supp:
            tags.add("SUPPORTER")
        elif is_item:
            tags.add("ITEM")
        elif is_tool:
            tags.add("TOOL")
        elif is_stad:
            tags.add("STADIUM")

        # Setup Basic
        if "search your deck for" in rt and re.search(r"basic (?:[\w']+ ){0,2}pok[eé]mon", rt) and ("onto your bench" in rt or "into your hand" in rt):
            vec["SETUP_BASIC"] += 0.90 if is_item or is_stad else 0.70
            vec["TUTOR_SEARCH"] += 0.45
        if is_stad and re.search(r"search their deck for an? basic pok[eé]mon and put it onto their bench", rt):
            vec["SETUP_BASIC"] += 0.80
            vec["TUTOR_SEARCH"] += 0.35
        # Restored-Pokemon fossils are Items that enter play as 60-HP Basic Pokemon.
        if name in FOSSIL_ITEM_NAMES or ("as if it were" in rt and "basic" in rt and "hp" in rt):
            tags.add("FOSSIL_BASIC")
            vec["SETUP_BASIC"] += 0.85
            vec["TANK_SURVIVE"] += 0.20
        # Evolve / Stage skip
        if "stage 2" in rt and "put it onto" in rt and "skipping" in rt or "evolve" in rt and ("stage 1" in rt or "stage 2" in rt or "during the turn they play" in rt):
            vec["EVOLVE_LINE"] += 0.95
        if "basic" in rt and "stage 1" in rt and "stage 2" in rt and "search your deck" in rt:
            vec["EVOLVE_LINE"] += 0.85
            vec["TUTOR_SEARCH"] += 0.80
            vec["SETUP_BASIC"] += 0.60
        if "evolution pok" in rt and "energy card" in rt and "search your deck" in rt:
            vec["EVOLVE_LINE"] += 0.75
            vec["TUTOR_SEARCH"] += 0.75
        # Draw / Refresh
        if "draw" in rt and "cards" in rt:
            m_d = re.search(r"draw (\d+) cards", rt)
            nd = int(m_d.group(1)) if m_d else 3
            if "if you have" in rt and "8 cards instead" in rt:
                nd = 7
            if "discard up to 2 pok" in rt and "draw 3 cards for each" in rt:
                nd = 6
                hooks.add("DISCARDS_NON_RULE_BOX_POKEMON")
            vec["DRAW_REFRESH"] += min(1.0, nd / 7.0)
        # Tutor / Search
        energy_only_search = bool(re.search(r"search your deck for [^.]*?energy card", rt)) and not re.search(r"search your deck for [^.]*?(?:pok[eé]mon|trainer|item|supporter)", rt)
        if "search your deck for" in rt and vec["TUTOR_SEARCH"] < 0.5:
            vec["TUTOR_SEARCH"] += 0.40 if energy_only_search else (0.85 if ("pokémon" in rt or "trainer" in rt or "any" in rt or "item" in rt) else 0.55)
        m_look = re.search(r"look at the top (\d+) cards of your deck,? and put (?:up to )?(\d+) of them into your hand", rt)
        if m_look:
            vec["TUTOR_SEARCH"] += min(0.75, 0.10 * int(m_look.group(1)))
            vec["DRAW_REFRESH"] += min(0.60, 0.20 * int(m_look.group(2)))
        if "look at the top" in rt and ("supporter" in rt or "put them back on top" in rt or "grass pok" in rt):
            vec["TUTOR_SEARCH"] += 0.75
            vec["DRAW_REFRESH"] += 0.40
            if "grass pok" in rt:
                vec["SETUP_BASIC"] += 0.70
                vec["EVOLVE_LINE"] += 0.55
                vec["ACCEL_ENERGY"] += 0.45
        # Energy Acceleration / Switch
        if ("attach" in rt or "move" in rt) and "energy" in rt and ("from your deck" in rt or "from your discard" in rt or "from your hand" in rt or "to another" in rt or "from your benched" in rt):
            vec["ACCEL_ENERGY"] += 0.85
        elif "search your deck for up to 2" in rt and "energy" in rt and "attach" in rt:
            vec["ACCEL_ENERGY"] += 0.95
            vec["TUTOR_SEARCH"] = min(vec["TUTOR_SEARCH"] + 0.20, 0.60)
        elif re.search(r"search your deck for an? basic \w+ energy card and attach it", rt):
            # Janine's Secret Art: deck -> board energy acceleration, not a hand tutor.
            vec["ACCEL_ENERGY"] += 0.90
            vec["TUTOR_SEARCH"] = min(vec["TUTOR_SEARCH"], 0.30)
        # Gust
        if "switch in 1 of your opponent's benched" in rt or "switch 1 of your opponent's benched" in rt:
            vec["GUST_TARGET"] += 0.95
            if "also switch your active" in rt:
                vec["MOBILITY_PIVOT"] += 0.65
        # Hand Disruption / Energy Denial
        if (
            "your opponent shuffles their hand" in rt
            or "each player shuffles their hand" in rt
            or re.search(r"discards? cards (?:from their hand )?until they have", rt)
            or "choose 3 cards from their hand" in rt
        ):
            if "both players" in rt or "each player" in rt:
                vec["DRAW_REFRESH"] = max(vec["DRAW_REFRESH"], 0.55)
            vec["DISRUPT_HAND"] += 0.90
            if "each player shuffles their hand" in rt:
                # Judge / Unfair Stamp also throw away OUR hand: anti-synergy with hand-size attackers.
                tags.add("SYMMETRIC_HAND_RESET")
        if "your opponent reveals their hand" in rt and "discard" in rt:
            vec["DISRUPT_HAND"] += 0.60
        if re.search(r"discard (?:an|a special|a pok[eé]mon tool and a special) energy from 1 of your opponent", rt) or "put an energy attached to 1 of your opponent" in rt:
            vec["DISRUPT_HAND"] += 0.70
            vec["LOCK_STALL"] += 0.40
        # Lock / Stadium Control
        if "have no abilities" in rt or "prevent all damage done to your" in rt and "by attacks from your opponent's pokémon ex" in rt:
            vec["LOCK_STALL"] += 0.80
        if "prevent all damage counters from being placed on benched" in rt:
            # Battle Cage (PFL 85): prevents damage counters from being placed on Benched Pokemon
            # by effects of attacks (Dragapult Phantom Dive) AND Abilities (Dusknoir / Munkidori).
            vec["TANK_SURVIVE"] += 0.65
            vec["LOCK_STALL"] += 0.35
            tags.add("BENCH_BARRIER")
            tags.add("BENCH_COUNTER_BARRIER")
            # ...but it does nothing against bench ATTACK DAMAGE or decks without bench counters.
            action_conditions["TANK_SURVIVE"] = ("VS_BENCH_COUNTERS",)
            action_conditions["LOCK_STALL"] = ("VS_BENCH_COUNTERS",)
        if "bench" in rt and "8 pok" in rt:
            vec["SETUP_BASIC"] += 0.55
            hooks.add("EXPANDS_BENCH_8")
        if "place 2 damage counters on that pok" in rt:
            vec["SPREAD_BENCH"] += 0.60
        if "festival grounds" in name.lower():
            hooks.add("FESTIVAL_STADIUM")
            vec["MOBILITY_PIVOT"] += 0.35
        if "academy at night" in name.lower():
            hooks.add("TOPDECK_STACKER")
            vec["TUTOR_SEARCH"] += 0.55
        # Mobility / Pivot
        if "switch your active" in rt or "retreat cost" in rt and "less" in rt:
            vec["MOBILITY_PIVOT"] += 0.80
        # Recovery
        if ("from your discard pile" in rt) and ("into your hand" in rt or "into your deck" in rt):
            vec["RECOVER_CYCLE"] += 0.85
        # Tank / Buff
        if "gets +" in rt and "hp" in rt or "takes" in rt and "less damage" in rt or "heal" in rt:
            vec["TANK_SURVIVE"] += 0.75
        if re.search(r"(attacks used by|attacks of|attacks it uses|this pok[eé]mon's attacks).{0,90}more damage", rt):
            vec["STRIKE_HEAVY"] += 0.45
            vec["STRIKE_MID"] += 0.45
            if is_tool:
                tags.add("DAMAGE_MOD_TOOL")
            else:
                tags.add("DAMAGE_MOD_ITEM")
            if "fighting pok" in rt:
                tags.add("FIGHTING_DAMAGE_BOOST")

        # ---- Structured effect profile ----
        requirements, requirement_mode = _extract_requirements(rt, subtypes)
        damage_bonus = _extract_damage_bonus(rt, subtypes)
        if damage_bonus:
            strike_acts = ["STRIKE_MID", "STRIKE_HEAVY"]
            # The bonus is only worth anything with a qualifying DIRECT-damage attacker
            # (never damage-counter attacks such as Alakazam's Powerful Hand).
            requirements = [
                r for r in requirements
                if not set(r["filter"].items()) <= set(damage_bonus["filter"].items())
            ]
            requirements.append({"filter": damage_bonus["filter"], "min": 3, "acts": strike_acts})
            if damage_bonus["vs_ex"]:
                for act in strike_acts:
                    action_conditions[act] = ("VS_OPP_EX",)
            if "Choose 1:" in rules_text or "choose 1:" in rt:
                # Modal cards (Kieran): other modes don't depend on the attacker requirement.
                for r in requirements:
                    r["acts"] = r["acts"] or strike_acts
        play_conds = _extract_play_conditions(rt, PLAY_CONDITION_PATTERNS)
        if play_conds:
            for act in list(vec):
                if vec[act] > 0:
                    action_conditions[act] = tuple(dict.fromkeys(action_conditions.get(act, ()) + play_conds))

    elif supertype == "Energy":
        rt = rules_text.lower()
        requirements, requirement_mode = _extract_requirements(rt, subtypes)
        if "Special" in subtypes:
            tags.add("SPECIAL_ENERGY")
            if "search your deck for up to 2 basic" in rt:
                vec["SETUP_BASIC"] += 0.85
            if "provides 2" in rt:
                vec["ACCEL_ENERGY"] += 0.80
            if "switch" in rt and "active" in rt:
                vec["MOBILITY_PIVOT"] += 0.75
            if "prevent all effects of attacks" in rt or "gets +" in rt and "hp" in rt:
                vec["TANK_SURVIVE"] += 0.55
            if "damage counters" in rt:
                vec["SPREAD_BENCH"] += 0.40
            if "1 fewer prize card" in rt:
                vec["TANK_SURVIVE"] += 0.85
            m_edraw = re.search(r"draw (\d+) cards", rt)
            if m_edraw:
                vec["DRAW_REFRESH"] += min(1.0, int(m_edraw.group(1)) / 7.0)
        else:
            tags.add("BASIC_ENERGY")

    return CompiledCard(
        uid=uid,
        card_id=raw.get("id", uid),
        name=name,
        set_code=set_code,
        set_num=num,
        supertype=supertype,
        subtypes=subtypes,
        hp=hp,
        types=types,
        evolves_from=evolves_from,
        evolves_to=evolves_to,
        stage=stage,
        prize_liability=prize_liability,
        is_rule_box=is_rule_box,
        is_ace_spec=is_ace_spec,
        weakness=weakness,
        resistance=resistance,
        retreat_cost=retreat_cost,
        attacks=attacks,
        abilities=abilities,
        rules_text=rules_text,
        primary_energy_type=primary_energy,
        action_vector={k: round(v, 3) for k, v in vec.items() if v > 0},
        tags=tags,
        synergy_hooks=hooks,
        meta_play_rate=round(meta_rate, 4),
        requirements=requirements,
        requirement_mode=requirement_mode,
        action_conditions={k: v for k, v in action_conditions.items() if vec.get(k, 0) > 0},
        damage_bonus=damage_bonus,
    )


class StandardCardDatabase:
    """Loads, compiles, and indexes all Standard-legal cards and evolution lineages."""

    def __init__(self, data_dir: Path, meta_path: Path | None = None):
        self.data_dir = data_dir
        self.meta_path = meta_path
        self.by_uid: dict[str, CompiledCard] = {}
        self.by_name: dict[str, list[CompiledCard]] = defaultdict(list)
        self.canonical_cards: list[CompiledCard] = []
        self.evolves_from_map: dict[str, str] = {}
        self.evolves_to_map: dict[str, list[str]] = defaultdict(list)
        self._load()

    def _load(self) -> None:
        sets_file = self.data_dir / "sets.json"
        with open(sets_file, encoding="utf-8") as f:
            sets_info = json.load(f)

        # Calculate empirical meta play rates per card name and per (set, num)
        meta_name_counts: dict[str, int] = defaultdict(int)
        meta_uid_decks: dict[tuple[str, str], int] = defaultdict(int)
        meta_preferred_uid: dict[str, tuple[str, str, int]] = {}
        total_meta_decks = 1
        if self.meta_path and self.meta_path.exists():
            with open(self.meta_path, encoding="utf-8") as f:
                meta_decks = json.load(f)
            total_meta_decks = max(1, len(meta_decks))
            uid_freq: dict[tuple[str, str, str], int] = defaultdict(int)
            for d in meta_decks:
                seen_names = set()
                seen_uids = set()
                for c in d["cards"]:
                    seen_names.add(c["name"])
                    seen_uids.add((c["set"], str(c["num"])))
                    uid_freq[(c["name"], c["set"], str(c["num"]))] += c["count"]
                for nm in seen_names:
                    meta_name_counts[nm] += 1
                for u in seen_uids:
                    meta_uid_decks[u] += 1
            for (nm, sc, sn), cnt in uid_freq.items():
                if nm not in meta_preferred_uid or cnt > meta_preferred_uid[nm][2]:
                    meta_preferred_uid[nm] = (sc, sn, cnt)

        # Load all set card files
        mech_signatures: dict[tuple, CompiledCard] = {}

        for s in sets_info:
            sid = s["id"]
            pcode = s.get("ptcgoCode") or sid.upper()
            cfile = self.data_dir / "cards" / f"{sid}.json"
            if not cfile.exists():
                continue
            with open(cfile, encoding="utf-8") as f:
                raw_cards = json.load(f)
            for raw in raw_cards:
                nm = raw["name"]
                num_str = str(raw.get("number", ""))
                exact_decks = meta_uid_decks.get((pcode, num_str), 0)
                # If this exact printing is used in meta decks, use its exact rate; otherwise fallback to a fraction of name rate if it shares the preferred signature
                rate = (exact_decks / total_meta_decks) if exact_decks > 0 else (meta_name_counts.get(nm, 0) / total_meta_decks * 0.1)
                cc = compile_card_from_json(raw, pcode, rate)
                self.by_uid[cc.uid] = cc

                if cc.evolves_from:
                    self.evolves_from_map[cc.name] = cc.evolves_from
                    if cc.name not in self.evolves_to_map[cc.evolves_from]:
                        self.evolves_to_map[cc.evolves_from].append(cc.name)

                # Deduplicate purely cosmetic reprints using mechanical signature
                sig = (
                    cc.name,
                    cc.supertype,
                    tuple(cc.subtypes),
                    cc.hp,
                    tuple(cc.types),
                    tuple((a.name, a.printed_damage, a.text) for a in cc.attacks),
                    tuple((ab.get("name"), ab.get("text")) for ab in cc.abilities),
                    cc.rules_text[:120],
                )
                if sig not in mech_signatures:
                    mech_signatures[sig] = cc
                else:
                    # Prefer the printing most used in competitive meta decklists
                    if cc.meta_play_rate > mech_signatures[sig].meta_play_rate:
                        mech_signatures[sig] = cc
                    else:
                        pref = meta_preferred_uid.get(cc.name)
                        if pref and (cc.set_code, cc.set_num) == (pref[0], pref[1]):
                            cc.meta_play_rate = max(cc.meta_play_rate, meta_name_counts.get(cc.name, 0) / total_meta_decks)
                            mech_signatures[sig] = cc

        # Add canonical MEE Basic Energies so decklists use standard MEE codes
        for et, (sc, sn, ename) in BASIC_ENERGY_MAP.items():
            raw_e = {
                "id": f"mee-{sn}",
                "name": ename,
                "number": sn,
                "supertype": "Energy",
                "subtypes": ["Basic"],
                "rules": [f"Provides {et} Energy."],
            }
            cc = compile_card_from_json(raw_e, sc, meta_name_counts.get(ename, 0) / total_meta_decks)
            cc.primary_energy_type = et
            self.by_uid[cc.uid] = cc
            sig = (cc.name, "Energy", ("Basic",), et)
            mech_signatures[sig] = cc

        self.canonical_cards = list(mech_signatures.values())
        for cc in self.canonical_cards:
            self.by_name[cc.name].append(cc)

    def resolve_card(self, query: str, set_code: str | None = None, set_num: str | None = None) -> CompiledCard | None:
        if set_code and set_num:
            uid = f"{set_code} {set_num}"
            if uid in self.by_uid:
                return self.by_uid[uid]
        # Try exact UID match (e.g., "MEG 104" or "PBL 39")
        q_clean = query.strip()
        if q_clean in self.by_uid:
            return self.by_uid[q_clean]
        # Try exact name match (return highest meta-rate / best printing)
        if q_clean in self.by_name:
            cands = self.by_name[q_clean]
            return sorted(cands, key=lambda c: (c.meta_play_rate, sum(c.action_vector.values())), reverse=True)[0]
        # Try case-insensitive / substring match
        q_low = q_clean.lower()
        for nm, cands in self.by_name.items():
            if nm.lower() == q_low:
                return sorted(cands, key=lambda c: (c.meta_play_rate, sum(c.action_vector.values())), reverse=True)[0]
        matches = []
        for cc in self.canonical_cards:
            if q_low in cc.name.lower() or q_low == cc.card_id.lower():
                matches.append(cc)
        if matches:
            return sorted(matches, key=lambda c: (c.name.lower() == q_low, c.meta_play_rate, sum(c.action_vector.values())), reverse=True)[0]
        return None

    def get_evolution_chain(self, card_name: str, walk_up: bool = True) -> list[str]:
        """Return ordered evolution chain [Basic, Stage 1, (Stage 2)] containing `card_name`."""
        # Walk down to Basic
        curr = card_name
        visited = {curr}
        chain_down = [curr]
        while curr in self.evolves_from_map:
            prev = self.evolves_from_map[curr]
            if prev in visited:
                break
            visited.add(prev)
            chain_down.append(prev)
            curr = prev
        chain = list(reversed(chain_down))
        if not walk_up:
            return chain
        # Walk up to highest evolution ONLY if card_name is a Basic or non-attacker Stage 1
        seed_cards = self.by_name.get(card_name, [])
        is_self_sufficient_stage1 = any(
            c.stage == 1 and (
                c.is_rule_box
                or "IMMUNITY_WALL" in c.tags
                or "TUTOR_POKEMON" in c.tags
                or "DRAW_ENGINE_POKEMON" in c.tags
                or "ENERGY_ACCEL_POKEMON" in c.tags
                or any("festival lead" in (ab.get("name") or "").lower() for ab in c.abilities)
                or max((a.expected_damage for a in c.attacks), default=0) >= 140
            )
            for c in seed_cards
        )
        if is_self_sufficient_stage1:
            return chain
        curr_top = chain[-1]
        while curr_top in self.evolves_to_map and self.evolves_to_map[curr_top]:
            next_evos = self.evolves_to_map[curr_top]
            best_evo = max(
                next_evos,
                key=lambda nm: max((c.meta_play_rate + 0.01 * sum(c.action_vector.values()) for c in self.by_name.get(nm, [])), default=0.0),
            )
            if best_evo in visited:
                break
            visited.add(best_evo)
            chain.append(best_evo)
            curr_top = best_evo
        return chain


if __name__ == "__main__":
    root = Path(__file__).resolve().parents[1]
    db = StandardCardDatabase(
        root / "pokemon-tcg-data-standard",
        root / "meta" / "decklists_2026-09-19_to_10-31.json",
    )
    print(f"Loaded {len(db.by_uid)} total card printings -> {len(db.canonical_cards)} canonical mechanical cards.")
    for sample in ["Dragapult ex", "Mega Kangaskhan ex", "Alakazam", "Dhelmise", "Mega Lopunny ex", "Lillie's Determination", "Poké Pad"]:
        c = db.resolve_card(sample)
        if c:
            print(f"  {c.name} ({c.uid}): stage={c.stage}, HP={c.hp}, prizes={c.prize_liability}, energy={c.primary_energy_type}, actions={c.action_vector}, hooks={c.synergy_hooks}")
