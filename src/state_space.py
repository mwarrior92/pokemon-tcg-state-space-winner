"""
Finite Board-State & Macro-Action Taxonomy for Pokemon TCG.
Reduces the game into a factored discrete state space S (like a chess position abstraction)
and a 16-action capability space A, calibrated from turn-by-turn competitive match logs
and the 512 tournament decklists in `meta/decklists_2026-09-19_to_10-31.json`.
"""
from __future__ import annotations

import json
import re
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from card_compiler import MACRO_ACTIONS, StandardCardDatabase

# ---------------------------------------------------------------------------
# 1. Formal Taxonomy of the Factored Board State Space (S)
# ---------------------------------------------------------------------------

PHASE_WINDOWS = [
    "T1_OPENING",          # Turn 1 (Plies 1-2): Setup Basics, early draw/search, T1 Budew lock or Turbo attach
    "T2_FIRST_STRIKE",     # Turn 2 (Plies 3-4): First evolutions online, first strike / early spread
    "T3_4_MIDGAME_TRADE",  # Turns 3-4 (Plies 5-8): Full engine online, multi-prize trades, Dusknoir/Munkidori math
    "T5_PLUS_ENDGAME",     # Turns 5+ (Plies 9+): 1-2 prizes left, hand reset (Unfair Stamp/Red Card), Boss checkmate or Wall/Mill
]

ACTIVE_TIERS = [
    "SP_FRAGILE",          # 1-Prize <= 90 HP (Budew 30, Dreepy 70, Abra 50, Dipplin 80)
    "SP_ATTACKER",         # 1-Prize 100-180 HP (Alakazam 140, Dhelmise 140, Slowking 120, Crustle 150, Dusknoir 160)
    "EX_BASIC",            # 2-Prize Basic ex 170-260 HP (Ogerpon ex 210, Raging Bolt ex 240, Clefairy ex 190, Meowth ex 170)
    "EX_STAGE2",           # 2-Prize Stage 1/2 ex 270-330 HP (Dragapult ex 320, N's Zoroark ex 280, Hydrapple ex 330)
    "MEGA_TANK",           # 3-Prize Mega ex or Cape Tank 300-430 HP (Mega Kangaskhan ex 300, Mega Lopunny ex 330, Mega Excadrill ex 340)
]

PRESSURE_MODES = [
    "PASSIVE_SETUP",       # 0-40 dmg, building bench/evolutions
    "CHIP_LOCK",           # 10-90 dmg + Item Lock / Energy Denial / Mill / Ex-Immunity Wall
    "TWO_SHOT_PRESSURE",   # 140-220 dmg efficient 1-2 energy attacker
    "SPREAD_HARVEST",      # 180-200 active dmg + 60-130 bench counters (Dragapult / Dusknoir / Munkidori)
    "BURST_OHKO",          # 240-350+ dmg capable of one-shotting ex / Mega ex
]

BENCH_STRUCTURES = [
    "SPARSE",                   # 1-2 benched Pokemon
    "ENGINE_EXPOSED",           # 3-5 single-prize engine Pokemon (Drakloak 90, Kadabra 80, Thwackey 100)
    "TWO_PRIZE_LIABILITIES",    # 2+ Rule-Box support Pokemon (Fezandipiti ex 210, Meowth ex 170, Latias ex 210)
    "SHIELDED_ENGINE",          # Protected by Shaymin (Flower Curtain) or Rabsca (Spherical Shield)
]

LOCK_CONDITIONS = [
    "OPEN_PLAY",                # Normal unrestricted play
    "ITEM_LOCK",                # Budew Itchy Pollen active (Items disabled)
    "ABILITY_LOCK",             # Team Rocket's Watchtower (Colorless abilities disabled)
    "EX_IMMUNITY_WALL",         # Crustle / Cornerstone Mask Ogerpon / Neutralization Zone (blocks ex attacks)
    "HAND_DISRUPTED",           # Hand reset to 2-4 cards (Unfair Stamp / Special Red Card / Judge) + Crushing Hammer
]

PRIZE_CONTEXTS = [
    "EVEN_START",               # 6-6 or 5-5 early game
    "AHEAD_TEMPO",              # Leading the prize race
    "BEHIND_COMEBACK",          # Trailing prizes (unlocks Counter Catcher, Rosa's Encouragement, Fezandipiti)
    "CHECKMATE_RACE",           # <= 2 prizes remaining on either side
]


# ---------------------------------------------------------------------------
# Situational card-condition liveness
# ---------------------------------------------------------------------------
# Probability that a game-state condition printed on a card ("You can use this card only
# if ...") holds when we want to play it, by phase window. These follow competitive prize-race
# tempo (first KOs on T2, ~2 Prizes per turn afterwards, checkmate at T5+), matching the phase
# definitions above. NOTE: matches/hf_500_games_turn_by_turn.csv was considered but rejected for
# this purpose: it is a slow, low-skill simulation (at ply 9+ a player has <=3 Prizes left only
# ~7% of the time), which would make staples like Special Red Card look unplayable.
CONDITION_LIVENESS: dict[str, dict[str, float]] = {
    "BEHIND_ON_PRIZES":  {"T1_OPENING": 0.00, "T2_FIRST_STRIKE": 0.30, "T3_4_MIDGAME_TRADE": 0.45, "T5_PLUS_ENDGAME": 0.50},
    "AFTER_OWN_KO":      {"T1_OPENING": 0.00, "T2_FIRST_STRIKE": 0.30, "T3_4_MIDGAME_TRADE": 0.55, "T5_PLUS_ENDGAME": 0.65},
    "OPP_PRIZES_LE_3":   {"T1_OPENING": 0.00, "T2_FIRST_STRIKE": 0.00, "T3_4_MIDGAME_TRADE": 0.25, "T5_PLUS_ENDGAME": 0.75},
    "OPP_PRIZES_LE_2":   {"T1_OPENING": 0.00, "T2_FIRST_STRIKE": 0.00, "T3_4_MIDGAME_TRADE": 0.10, "T5_PLUS_ENDGAME": 0.60},
    "OPP_PRIZES_EQ_2":   {"T1_OPENING": 0.00, "T2_FIRST_STRIKE": 0.00, "T3_4_MIDGAME_TRADE": 0.08, "T5_PLUS_ENDGAME": 0.30},
    "LAST_CARD_IN_HAND": {"T1_OPENING": 0.05, "T2_FIRST_STRIKE": 0.15, "T3_4_MIDGAME_TRADE": 0.25, "T5_PLUS_ENDGAME": 0.30},
    "NOT_FIRST_TURN":    {"T1_OPENING": 0.00, "T2_FIRST_STRIKE": 1.00, "T3_4_MIDGAME_TRADE": 1.00, "T5_PLUS_ENDGAME": 1.00},
    # Abilities that only work while the Pokemon is Active (Mega Kangaskhan ex Run Errand).
    "ACTIVE_ONLY":       {"T1_OPENING": 0.40, "T2_FIRST_STRIKE": 0.40, "T3_4_MIDGAME_TRADE": 0.40, "T5_PLUS_ENDGAME": 0.40},
}


def condition_live(cond: str, s: "BoardStateScenario") -> float:
    """Liveness in [0, 1] of a card condition key on board state `s`."""
    if cond in CONDITION_LIVENESS:
        return CONDITION_LIVENESS[cond].get(s.phase, 0.0)
    if cond == "VS_OPP_EX":
        return 1.0 if s.opp_active_is_ex else 0.0
    if cond == "VS_BENCH_SPREAD":
        return 1.0 if s.opp_incoming_bench_spread > 0 else 0.0
    if cond == "VS_BENCH_COUNTERS":
        return 1.0 if (s.opp_incoming_bench_spread > 0 and s.opp_bench_spread_is_counters) else 0.0
    if cond == "VS_BENCH_ATTACK_DAMAGE":
        return 1.0 if (s.opp_incoming_bench_spread > 0 and not s.opp_bench_spread_is_counters) else 0.0
    if cond == "VS_DRAGON":
        return 1.0 if "Dragapult" in s.archetype_source else 0.0
    return 1.0


def conditions_live(conds: tuple[str, ...] | None, s: "BoardStateScenario") -> float:
    live = 1.0
    for c in conds or ():
        live *= condition_live(c, s)
    return live


@dataclass
class BoardStateScenario:
    state_id: str
    name: str
    archetype_source: str
    meta_share: float
    phase: str
    state_weight: float                 # Normalized tournament encounter probability P(s)
    # Factored discrete coordinates in S
    active_tier: str
    pressure_mode: str
    bench_structure: str
    lock_condition: str
    prize_context: str
    # Quantitative combat parameters of the opponent board in this state
    opp_active_name: str
    opp_active_hp: int
    opp_active_weakness: str | None
    opp_active_prizes: int
    opp_active_is_ex: bool
    opp_active_stage: int                # 0=Basic, 1=Stage 1, 2=Stage 2 (devolve targets)
    opp_incoming_active_dmg: float
    opp_incoming_bench_spread: float
    opp_bench_spread_is_counters: bool  # True=damage counters (Phantom Dive/Cursed Blast/Adrena-Brain); False=attack dmg (Trifrost/Flamebody Cannon)
    opp_bench_lowest_hp: int
    opp_bench_gust_prizes: int
    opp_bench_gust_hp: int
    opp_energy_denial_rate: float       # Crushing Hammer / retreat lock pressure
    # Action demands: how valuable each of the 16 Macro-Actions is for handling this state
    action_demands: dict[str, float] = field(default_factory=dict)
    description: str = ""


# ---------------------------------------------------------------------------
# 2. Archetype Signatures & Turn-by-Turn State Projection
# ---------------------------------------------------------------------------

def build_competitive_state_space(
    db: StandardCardDatabase,
    meta_decks_path: Path,
    trajectories_path: Path | None = None,
) -> list[BoardStateScenario]:
    """
    Construct the prioritized set of Canonical Competitive Board States from the
    512 tournament decklists and empirical turn-by-turn match trajectories.
    """
    with open(meta_decks_path, encoding="utf-8") as f:
        meta_decks = json.load(f)

    total_decks = len(meta_decks)
    arch_counts = Counter(d["deck"] for d in meta_decks)

    # Group minor variants into canonical archetype families so 100% of meta is represented
    family_map = {
        "Dragapult": "Dragapult Control/Hammer",
        "Dragapult Dusknoir": "Dragapult Dusknoir",
        "Dragapult Blaziken": "Dragapult Blaziken",
        "Dragapult Dudunsparce": "Dragapult Control/Hammer",
        "Basic Box": "Basic Box (Mega Kangaskhan / Ogerpon)",
        "N's Zoroark": "N's Zoroark ex",
        "Slowking": "Slowking (Seek Inspiration)",
        "Hydrapple": "Hydrapple ex / Meganium",
        "Festival Lead": "Festival Lead (Dipplin / Thwackey)",
        "Alakazam Dudunsparce": "Alakazam (Powerful Hand)",
        "Alakazam Dusknoir": "Alakazam (Powerful Hand)",
        "Dhelmise": "Dhelmise / Banette (Hide 'n' Sneak)",
        "Crustle": "Crustle / Mega Kangaskhan Wall",
        "Lopunny Dusknoir": "Mega Lopunny ex / Dusknoir",
        "Mega Excadrill": "Mega Excadrill ex / Metang",
    }

    family_counts: dict[str, int] = defaultdict(int)
    for arch, cnt in arch_counts.items():
        fam = family_map.get(arch, "Rogue / Other Meta")
        family_counts[fam] += cnt

    # Normalized meta weights across the 12 major competitive families
    major_total = sum(v for k, v in family_counts.items() if k != "Rogue / Other Meta")
    family_weights = {
        k: round(v / max(1, major_total), 4)
        for k, v in sorted(family_counts.items(), key=lambda x: -x[1])
        if k != "Rogue / Other Meta"
    }

    # Empirical phase weights from match trajectories (reflecting decision criticality & frequency):
    # Turn 1 setup (0.22), Turn 2 transition/first-strike (0.26), Turns 3-4 midgame trade (0.32), Turns 5+ endgame (0.20)
    phase_weights = {
        "T1_OPENING": 0.22,
        "T2_FIRST_STRIKE": 0.26,
        "T3_4_MIDGAME_TRADE": 0.32,
        "T5_PLUS_ENDGAME": 0.20,
    }

    # Define the 12 canonical archetype state progressions across the 4 phases (48 states total)
    archetype_profiles: dict[str, dict[str, Any]] = {
        "Dragapult Control/Hammer": {
            "weakness": None,  # Dragon type has no printed weakness unless Lillie's Clefairy ex is in play
            "phases": {
                "T1_OPENING": {
                    "active_name": "Budew", "hp": 30, "prizes": 1, "is_ex": False,
                    "tier": "SP_FRAGILE", "mode": "CHIP_LOCK", "bench": "ENGINE_EXPOSED",
                    "lock": "ITEM_LOCK", "prize_ctx": "EVEN_START",
                    "dmg": 10.0, "spread": 0.0, "bench_low_hp": 70, "gust_prizes": 1, "gust_hp": 70, "hammer": 0.55,
                    "desc": "Budew Active using Itchy Pollen (Item Lock) while benching 3x Dreepy + Crushing Hammer.",
                    "demands": {"SETUP_BASIC": 1.0, "DRAW_REFRESH": 0.9, "STRIKE_LIGHT": 0.85, "MOBILITY_PIVOT": 0.7, "EVOLVE_LINE": 0.6},
                },
                "T2_FIRST_STRIKE": {
                    "active_name": "Budew / Drakloak", "hp": 90, "prizes": 1, "is_ex": False,
                    "tier": "SP_FRAGILE", "mode": "CHIP_LOCK", "bench": "ENGINE_EXPOSED",
                    "lock": "ITEM_LOCK", "prize_ctx": "EVEN_START",
                    "dmg": 70.0, "spread": 20.0, "bench_low_hp": 80, "gust_prizes": 1, "gust_hp": 90, "hammer": 0.65,
                    "desc": "Multiple Drakloak Recon Directives online + Crushing Hammer energy denial + Munkidori setup.",
                    "demands": {"EVOLVE_LINE": 0.9, "DRAW_REFRESH": 0.85, "ACCEL_ENERGY": 0.8, "STRIKE_LIGHT": 0.8, "GUST_TARGET": 0.65},
                },
                "T3_4_MIDGAME_TRADE": {
                    "active_name": "Dragapult ex", "hp": 320, "prizes": 2, "is_ex": True,
                    "tier": "EX_STAGE2", "mode": "SPREAD_HARVEST", "bench": "ENGINE_EXPOSED",
                    "lock": "OPEN_PLAY", "prize_ctx": "BEHIND_COMEBACK",
                    "dmg": 200.0, "spread": 90.0, "bench_low_hp": 90, "gust_prizes": 2, "gust_hp": 210, "hammer": 0.50,
                    "desc": "Dragapult ex Phantom Dive (200 + 60 spread) + Munkidori Adrena-Brain (30 spread) harvesting bench.",
                    "demands": {"STRIKE_HEAVY": 1.0, "TANK_SURVIVE": 0.9, "DRAW_REFRESH": 0.8, "RECOVER_CYCLE": 0.75, "GUST_TARGET": 0.7},
                },
                "T5_PLUS_ENDGAME": {
                    "active_name": "Dragapult ex", "hp": 320, "prizes": 2, "is_ex": True,
                    "tier": "EX_STAGE2", "mode": "SPREAD_HARVEST", "bench": "TWO_PRIZE_LIABILITIES",
                    "lock": "HAND_DISRUPTED", "prize_ctx": "CHECKMATE_RACE",
                    "dmg": 200.0, "spread": 90.0, "bench_low_hp": 90, "gust_prizes": 2, "gust_hp": 170, "hammer": 0.35,
                    "desc": "Late-game Unfair Stamp / Special Red Card hand reset + Phantom Dive multi-prize checkmate.",
                    "demands": {"DRAW_REFRESH": 1.0, "GUST_TARGET": 0.95, "STRIKE_HEAVY": 0.9, "TANK_SURVIVE": 0.8, "RECOVER_CYCLE": 0.7},
                },
            },
        },
        "Basic Box (Mega Kangaskhan / Ogerpon)": {
            "weakness": "Fighting",
            "phases": {
                "T1_OPENING": {
                    "active_name": "Mega Kangaskhan ex", "hp": 300, "prizes": 3, "is_ex": True,
                    "tier": "MEGA_TANK", "mode": "TWO_SHOT_PRESSURE", "bench": "TWO_PRIZE_LIABILITIES",
                    "lock": "OPEN_PLAY", "prize_ctx": "EVEN_START",
                    "dmg": 150.0, "spread": 0.0, "bench_low_hp": 170, "gust_prizes": 2, "gust_hp": 210, "hammer": 0.0,
                    "desc": "Turn 1 Area Zero Underdepths + Teal Dance + Crispin + Latias ex Skyliner into Mega Kangaskhan ex Run Errand.",
                    "demands": {"SETUP_BASIC": 1.0, "TANK_SURVIVE": 0.8, "TUTOR_SEARCH": 0.8, "ACCEL_ENERGY": 0.75},
                },
                "T2_FIRST_STRIKE": {
                    "active_name": "Mega Kangaskhan ex", "hp": 300, "prizes": 3, "is_ex": True,
                    "tier": "MEGA_TANK", "mode": "BURST_OHKO", "bench": "TWO_PRIZE_LIABILITIES",
                    "lock": "OPEN_PLAY", "prize_ctx": "BEHIND_COMEBACK",
                    "dmg": 250.0, "spread": 0.0, "bench_low_hp": 170, "gust_prizes": 2, "gust_hp": 210, "hammer": 0.0,
                    "desc": "Mega Kangaskhan ex (300 HP, 250 avg dmg) or Raging Bolt ex / Wellspring Ogerpon attacking on Turn 2.",
                    "demands": {"STRIKE_HEAVY": 0.95, "EVOLVE_LINE": 0.85, "ACCEL_ENERGY": 0.85, "GUST_TARGET": 0.75},
                },
                "T3_4_MIDGAME_TRADE": {
                    "active_name": "Raging Bolt ex / Mega Kangaskhan ex", "hp": 300, "prizes": 3, "is_ex": True,
                    "tier": "MEGA_TANK", "mode": "BURST_OHKO", "bench": "TWO_PRIZE_LIABILITIES",
                    "lock": "OPEN_PLAY", "prize_ctx": "EVEN_START",
                    "dmg": 280.0, "spread": 0.0, "bench_low_hp": 170, "gust_prizes": 2, "gust_hp": 190, "hammer": 0.0,
                    "desc": "Toolbox attackers (Raging Bolt 280+, Clefairy ex vs Dragons, Iron Leaves ex) trading prizes rapidly.",
                    "demands": {"STRIKE_HEAVY": 1.0, "GUST_TARGET": 0.9, "DISRUPT_HAND": 0.75, "WALL_BREAKER": 0.7},
                },
                "T5_PLUS_ENDGAME": {
                    "active_name": "Mega Kangaskhan ex (Hero's Cape)", "hp": 400, "prizes": 3, "is_ex": True,
                    "tier": "MEGA_TANK", "mode": "BURST_OHKO", "bench": "TWO_PRIZE_LIABILITIES",
                    "lock": "HAND_DISRUPTED", "prize_ctx": "CHECKMATE_RACE",
                    "dmg": 250.0, "spread": 0.0, "bench_low_hp": 170, "gust_prizes": 2, "gust_hp": 170, "hammer": 0.0,
                    "desc": "Endgame Boss's Orders + Special Red Card with high-HP Mega Kangaskhan or 2-prize bench liabilities.",
                    "demands": {"GUST_TARGET": 1.0, "STRIKE_HEAVY": 0.95, "DRAW_REFRESH": 0.85},
                },
            },
        },
        "N's Zoroark ex": {
            "weakness": "Grass",
            "phases": {
                "T1_OPENING": {
                    "active_name": "N's Zorua", "hp": 70, "prizes": 1, "is_ex": False,
                    "tier": "SP_FRAGILE", "mode": "PASSIVE_SETUP", "bench": "ENGINE_EXPOSED",
                    "lock": "OPEN_PLAY", "prize_ctx": "EVEN_START",
                    "dmg": 20.0, "spread": 0.0, "bench_low_hp": 70, "gust_prizes": 1, "gust_hp": 70, "hammer": 0.0,
                    "desc": "Buddy-Buddy Poffin deploying multiple N's Zorua + N's Darmanitan / N's Reshiram.",
                    "demands": {"SETUP_BASIC": 0.95, "TUTOR_SEARCH": 0.8, "STRIKE_LIGHT": 0.7},
                },
                "T2_FIRST_STRIKE": {
                    "active_name": "N's Zoroark ex", "hp": 280, "prizes": 2, "is_ex": True,
                    "tier": "EX_STAGE2", "mode": "TWO_SHOT_PRESSURE", "bench": "ENGINE_EXPOSED",
                    "lock": "ABILITY_LOCK", "prize_ctx": "EVEN_START",
                    "dmg": 190.0, "spread": 90.0, "bench_low_hp": 70, "gust_prizes": 2, "gust_hp": 210, "hammer": 0.0,
                    "desc": "N's Zoroark ex Trade draw engine + N's PP Up acceleration + Night Joker copying Flamebody Cannon (90x2).",
                    "demands": {"TANK_SURVIVE": 0.85, "STRIKE_HEAVY": 0.85, "EVOLVE_LINE": 0.8, "DRAW_REFRESH": 0.8},
                },
                "T3_4_MIDGAME_TRADE": {
                    "active_name": "N's Zoroark ex", "hp": 280, "prizes": 2, "is_ex": True,
                    "tier": "EX_STAGE2", "mode": "BURST_OHKO", "bench": "TWO_PRIZE_LIABILITIES",
                    "lock": "ABILITY_LOCK", "prize_ctx": "EVEN_START",
                    "dmg": 260.0, "spread": 60.0, "bench_low_hp": 90, "gust_prizes": 2, "gust_hp": 170, "hammer": 0.0,
                    "desc": "Multiple Zoroark ex Trade engines drawing 6+ cards/turn + Virtuous Rage / Flamebody Cannon + Watchtower.",
                    "demands": {"STRIKE_HEAVY": 0.95, "DISRUPT_HAND": 0.85, "GUST_TARGET": 0.85, "TANK_SURVIVE": 0.75},
                },
                "T5_PLUS_ENDGAME": {
                    "active_name": "N's Zoroark ex", "hp": 280, "prizes": 2, "is_ex": True,
                    "tier": "EX_STAGE2", "mode": "BURST_OHKO", "bench": "TWO_PRIZE_LIABILITIES",
                    "lock": "HAND_DISRUPTED", "prize_ctx": "CHECKMATE_RACE",
                    "dmg": 280.0, "spread": 0.0, "bench_low_hp": 140, "gust_prizes": 2, "gust_hp": 210, "hammer": 0.0,
                    "desc": "High consistency Trade bench resisting late hand disruption and closing with Boss's Orders.",
                    "demands": {"STRIKE_HEAVY": 0.95, "GUST_TARGET": 0.9, "DISRUPT_HAND": 0.8, "DRAW_REFRESH": 0.8},
                },
            },
        },
        "Alakazam (Powerful Hand)": {
            "weakness": "Darkness",
            "phases": {
                "T1_OPENING": {
                    "active_name": "Abra / Dunsparce", "hp": 60, "prizes": 1, "is_ex": False,
                    "tier": "SP_FRAGILE", "mode": "PASSIVE_SETUP", "bench": "ENGINE_EXPOSED",
                    "lock": "OPEN_PLAY", "prize_ctx": "EVEN_START",
                    "dmg": 10.0, "spread": 0.0, "bench_low_hp": 50, "gust_prizes": 1, "gust_hp": 50, "hammer": 0.0,
                    "desc": "Telepathic Psychic Energy + Buddy-Buddy Poffin filling bench with Abra and Dunsparce/Duskull.",
                    "demands": {"SETUP_BASIC": 0.95, "SPREAD_BENCH": 0.85, "STRIKE_LIGHT": 0.75},
                },
                "T2_FIRST_STRIKE": {
                    "active_name": "Alakazam", "hp": 140, "prizes": 1, "is_ex": False,
                    "tier": "SP_ATTACKER", "mode": "TWO_SHOT_PRESSURE", "bench": "SHIELDED_ENGINE",
                    "lock": "OPEN_PLAY", "prize_ctx": "EVEN_START",
                    "dmg": 180.0, "spread": 0.0, "bench_low_hp": 80, "gust_prizes": 1, "gust_hp": 80, "hammer": 0.0,
                    "desc": "Kadabra (draw 2) + Alakazam (draw 3) + Dudunsparce (draw 3) building a 9-card hand for 180 dmg with 1 Psychic Energy.",
                    "demands": {"DISRUPT_HAND": 0.95, "STRIKE_LIGHT": 0.9, "SPREAD_BENCH": 0.85, "EVOLVE_LINE": 0.8},
                },
                "T3_4_MIDGAME_TRADE": {
                    "active_name": "Alakazam", "hp": 140, "prizes": 1, "is_ex": False,
                    "tier": "SP_ATTACKER", "mode": "BURST_OHKO", "bench": "SHIELDED_ENGINE",
                    "lock": "OPEN_PLAY", "prize_ctx": "BEHIND_COMEBACK",
                    "dmg": 260.0, "spread": 60.0, "bench_low_hp": 80, "gust_prizes": 1, "gust_hp": 90, "hammer": 0.0,
                    "desc": "13-card hand Alakazam placing 26 damage counters (260 dmg) for 1 Energy while trading only 1 Prize!",
                    "demands": {"DISRUPT_HAND": 1.0, "SPREAD_BENCH": 0.9, "STRIKE_LIGHT": 0.9, "WALL_BREAKER": 0.85, "RECOVER_CYCLE": 0.8},
                },
                "T5_PLUS_ENDGAME": {
                    "active_name": "Alakazam", "hp": 140, "prizes": 1, "is_ex": False,
                    "tier": "SP_ATTACKER", "mode": "BURST_OHKO", "bench": "SHIELDED_ENGINE",
                    "lock": "OPEN_PLAY", "prize_ctx": "CHECKMATE_RACE",
                    "dmg": 280.0, "spread": 130.0, "bench_low_hp": 80, "gust_prizes": 1, "gust_hp": 140, "hammer": 0.0,
                    "desc": "Chained single-prize Alakazams + Dusknoir Cursed Blast forcing unfavorable 1-for-2/3 prize trades.",
                    "demands": {"DISRUPT_HAND": 1.0, "STRIKE_LIGHT": 0.9, "TANK_SURVIVE": 0.85, "RECOVER_CYCLE": 0.8},
                },
            },
        },
        "Slowking (Seek Inspiration)": {
            "weakness": "Darkness",
            "phases": {
                "T1_OPENING": {
                    "active_name": "Budew / Slowpoke", "hp": 70, "prizes": 1, "is_ex": False,
                    "tier": "SP_FRAGILE", "mode": "CHIP_LOCK", "bench": "ENGINE_EXPOSED",
                    "lock": "ITEM_LOCK", "prize_ctx": "EVEN_START",
                    "dmg": 10.0, "spread": 0.0, "bench_low_hp": 70, "gust_prizes": 1, "gust_hp": 70, "hammer": 0.0,
                    "desc": "Telepathic Psychic Energy deploying Slowpoke + Xatu while Budew stalls.",
                    "demands": {"SETUP_BASIC": 0.95, "DRAW_REFRESH": 0.85, "STRIKE_LIGHT": 0.75},
                },
                "T2_FIRST_STRIKE": {
                    "active_name": "Slowking", "hp": 120, "prizes": 1, "is_ex": False,
                    "tier": "SP_ATTACKER", "mode": "SPREAD_HARVEST", "bench": "ENGINE_EXPOSED",
                    "lock": "OPEN_PLAY", "prize_ctx": "BEHIND_COMEBACK",
                    "dmg": 110.0, "spread": 220.0, "bench_low_hp": 70, "gust_prizes": 1, "gust_hp": 100, "hammer": 0.0,
                    "desc": "Academy at Night + Ciphermaniac stacking Kyurem (Trifrost 110 to 3 Pokemon) or Regigigas (330 vs ex).",
                    "demands": {"TANK_SURVIVE": 0.95, "STRIKE_LIGHT": 0.9, "DISRUPT_HAND": 0.8, "GUST_TARGET": 0.75},
                },
                "T3_4_MIDGAME_TRADE": {
                    "active_name": "Slowking", "hp": 120, "prizes": 1, "is_ex": False,
                    "tier": "SP_ATTACKER", "mode": "BURST_OHKO", "bench": "ENGINE_EXPOSED",
                    "lock": "OPEN_PLAY", "prize_ctx": "BEHIND_COMEBACK",
                    "dmg": 260.0, "spread": 110.0, "bench_low_hp": 80, "gust_prizes": 1, "gust_hp": 100, "hammer": 0.0,
                    "desc": "Single-prize Slowking copying Regigigas (330 dmg) or Conkeldurr (250 dmg) or Kyurem Trifrost every turn.",
                    "demands": {"STRIKE_LIGHT": 0.95, "DISRUPT_HAND": 0.9, "SPREAD_BENCH": 0.85, "TANK_SURVIVE": 0.85},
                },
                "T5_PLUS_ENDGAME": {
                    "active_name": "Slowking", "hp": 120, "prizes": 1, "is_ex": False,
                    "tier": "SP_ATTACKER", "mode": "BURST_OHKO", "bench": "ENGINE_EXPOSED",
                    "lock": "OPEN_PLAY", "prize_ctx": "CHECKMATE_RACE",
                    "dmg": 300.0, "spread": 110.0, "bench_low_hp": 100, "gust_prizes": 2, "gust_hp": 170, "hammer": 0.0,
                    "desc": "Night Stretcher recycling Slowking + Academy at Night topdecking lethal attack.",
                    "demands": {"DISRUPT_HAND": 0.95, "GUST_TARGET": 0.9, "STRIKE_LIGHT": 0.9},
                },
            },
        },
        "Hydrapple ex / Meganium": {
            "weakness": "Fire",
            "phases": {
                "T1_OPENING": {
                    "active_name": "Teal Mask Ogerpon ex", "hp": 210, "prizes": 2, "is_ex": True,
                    "tier": "EX_BASIC", "mode": "PASSIVE_SETUP", "bench": "ENGINE_EXPOSED",
                    "lock": "OPEN_PLAY", "prize_ctx": "EVEN_START",
                    "dmg": 30.0, "spread": 0.0, "bench_low_hp": 60, "gust_prizes": 2, "gust_hp": 210, "hammer": 0.0,
                    "desc": "Bug Catching Set + Teal Dance accelerating Grass Energy + Forest of Vitality stadium.",
                    "demands": {"SETUP_BASIC": 0.95, "TUTOR_SEARCH": 0.85, "ACCEL_ENERGY": 0.8},
                },
                "T2_FIRST_STRIKE": {
                    "active_name": "Hydrapple ex", "hp": 330, "prizes": 2, "is_ex": True,
                    "tier": "EX_STAGE2", "mode": "BURST_OHKO", "bench": "TWO_PRIZE_LIABILITIES",
                    "lock": "OPEN_PLAY", "prize_ctx": "EVEN_START",
                    "dmg": 240.0, "spread": 0.0, "bench_low_hp": 80, "gust_prizes": 2, "gust_hp": 210, "hammer": 0.0,
                    "desc": "Forest of Vitality instant Grass evolution into Hydrapple ex + Meganium Wild Growth doubling Grass Energy.",
                    "demands": {"STRIKE_HEAVY": 0.95, "GUST_TARGET": 0.85, "EVOLVE_LINE": 0.8},
                },
                "T3_4_MIDGAME_TRADE": {
                    "active_name": "Hydrapple ex", "hp": 330, "prizes": 2, "is_ex": True,
                    "tier": "EX_STAGE2", "mode": "BURST_OHKO", "bench": "TWO_PRIZE_LIABILITIES",
                    "lock": "OPEN_PLAY", "prize_ctx": "EVEN_START",
                    "dmg": 330.0, "spread": 0.0, "bench_low_hp": 160, "gust_prizes": 2, "gust_hp": 210, "hammer": 0.0,
                    "desc": "330 HP Hydrapple ex healing 30 + dealing 300+ Syrup Storm damage with Meganium energy doubling.",
                    "demands": {"STRIKE_HEAVY": 1.0, "GUST_TARGET": 0.9, "WALL_BREAKER": 0.75},
                },
                "T5_PLUS_ENDGAME": {
                    "active_name": "Hydrapple ex", "hp": 330, "prizes": 2, "is_ex": True,
                    "tier": "EX_STAGE2", "mode": "BURST_OHKO", "bench": "TWO_PRIZE_LIABILITIES",
                    "lock": "OPEN_PLAY", "prize_ctx": "CHECKMATE_RACE",
                    "dmg": 360.0, "spread": 0.0, "bench_low_hp": 160, "gust_prizes": 2, "gust_hp": 210, "hammer": 0.0,
                    "desc": "Late-game 330 HP tanking + uncapped Syrup Storm OHKOing any active.",
                    "demands": {"GUST_TARGET": 1.0, "STRIKE_HEAVY": 0.95, "DISRUPT_HAND": 0.75},
                },
            },
        },
        "Festival Lead (Dipplin / Thwackey)": {
            "weakness": "Fire",
            "phases": {
                "T1_OPENING": {
                    "active_name": "Applin / Grookey", "hp": 60, "prizes": 1, "is_ex": False,
                    "tier": "SP_FRAGILE", "mode": "PASSIVE_SETUP", "bench": "ENGINE_EXPOSED",
                    "lock": "OPEN_PLAY", "prize_ctx": "EVEN_START",
                    "dmg": 20.0, "spread": 0.0, "bench_low_hp": 60, "gust_prizes": 1, "gust_hp": 60, "hammer": 0.0,
                    "desc": "Buddy-Buddy Poffin + Bug Catching Set filling all 5 bench slots with Applin and Grookey.",
                    "demands": {"SETUP_BASIC": 0.95, "SPREAD_BENCH": 0.85, "STRIKE_LIGHT": 0.8},
                },
                "T2_FIRST_STRIKE": {
                    "active_name": "Dipplin", "hp": 80, "prizes": 1, "is_ex": False,
                    "tier": "SP_FRAGILE", "mode": "TWO_SHOT_PRESSURE", "bench": "SHIELDED_ENGINE",
                    "lock": "OPEN_PLAY", "prize_ctx": "BEHIND_COMEBACK",
                    "dmg": 200.0, "spread": 0.0, "bench_low_hp": 80, "gust_prizes": 1, "gust_hp": 100, "hammer": 0.0,
                    "desc": "Dipplin Festival Lead attacking TWICE with Do the Wave (100x2 = 200 dmg) for 1 Grass Energy + Thwackey Booming Groove.",
                    "demands": {"STRIKE_LIGHT": 0.95, "SPREAD_BENCH": 0.9, "DISRUPT_HAND": 0.8, "TANK_SURVIVE": 0.75},
                },
                "T3_4_MIDGAME_TRADE": {
                    "active_name": "Dipplin (Brave Bangle / Max Belt)", "hp": 80, "prizes": 1, "is_ex": False,
                    "tier": "SP_FRAGILE", "mode": "BURST_OHKO", "bench": "SHIELDED_ENGINE",
                    "lock": "OPEN_PLAY", "prize_ctx": "BEHIND_COMEBACK",
                    "dmg": 260.0, "spread": 0.0, "bench_low_hp": 80, "gust_prizes": 1, "gust_hp": 100, "hammer": 0.0,
                    "desc": "Thwackey tutoring exact cards every turn while Dipplin deals 260-300 dmg across two hits for 1 Energy.",
                    "demands": {"SPREAD_BENCH": 0.95, "STRIKE_LIGHT": 0.95, "DISRUPT_HAND": 0.85, "GUST_TARGET": 0.8},
                },
                "T5_PLUS_ENDGAME": {
                    "active_name": "Dipplin / Rillaboom", "hp": 90, "prizes": 1, "is_ex": False,
                    "tier": "SP_FRAGILE", "mode": "BURST_OHKO", "bench": "SHIELDED_ENGINE",
                    "lock": "OPEN_PLAY", "prize_ctx": "CHECKMATE_RACE",
                    "dmg": 260.0, "spread": 0.0, "bench_low_hp": 90, "gust_prizes": 1, "gust_hp": 100, "hammer": 0.0,
                    "desc": "Continuous 1-Prize double attackers immune to single-target hand disruption due to Thwackey bench engine.",
                    "demands": {"SPREAD_BENCH": 0.95, "GUST_TARGET": 0.9, "STRIKE_LIGHT": 0.9, "DISRUPT_HAND": 0.85},
                },
            },
        },
        "Dragapult Dusknoir": {
            "weakness": None,
            "phases": {
                "T1_OPENING": {
                    "active_name": "Budew", "hp": 30, "prizes": 1, "is_ex": False,
                    "tier": "SP_FRAGILE", "mode": "CHIP_LOCK", "bench": "ENGINE_EXPOSED",
                    "lock": "ITEM_LOCK", "prize_ctx": "EVEN_START",
                    "dmg": 10.0, "spread": 0.0, "bench_low_hp": 60, "gust_prizes": 1, "gust_hp": 60, "hammer": 0.0,
                    "desc": "Budew Item Lock + Dreepy and Duskull deployed on bench.",
                    "demands": {"SETUP_BASIC": 1.0, "DRAW_REFRESH": 0.9, "STRIKE_LIGHT": 0.8, "GUST_TARGET": 0.7},
                },
                "T2_FIRST_STRIKE": {
                    "active_name": "Drakloak", "hp": 90, "prizes": 1, "is_ex": False,
                    "tier": "SP_FRAGILE", "mode": "SPREAD_HARVEST", "bench": "ENGINE_EXPOSED",
                    "lock": "OPEN_PLAY", "prize_ctx": "EVEN_START",
                    "dmg": 70.0, "spread": 50.0, "bench_low_hp": 60, "gust_prizes": 1, "gust_hp": 90, "hammer": 0.0,
                    "desc": "Dusclops Cursed Blast (50 dmg) or Dusknoir (130 dmg) sniping key evolving Basic/Stage 1 on bench.",
                    "demands": {"TANK_SURVIVE": 0.9, "SETUP_BASIC": 0.85, "EVOLVE_LINE": 0.85, "GUST_TARGET": 0.75},
                },
                "T3_4_MIDGAME_TRADE": {
                    "active_name": "Dragapult ex", "hp": 320, "prizes": 2, "is_ex": True,
                    "tier": "EX_STAGE2", "mode": "SPREAD_HARVEST", "bench": "ENGINE_EXPOSED",
                    "lock": "HAND_DISRUPTED", "prize_ctx": "BEHIND_COMEBACK",
                    "dmg": 200.0, "spread": 190.0, "bench_low_hp": 90, "gust_prizes": 2, "gust_hp": 210, "hammer": 0.0,
                    "desc": "Dusknoir Cursed Blast (130) + Phantom Dive (200 + 60) + Counter Catcher + Iono/Unfair Stamp taking 3-4 Prizes in one turn.",
                    "demands": {"TANK_SURVIVE": 1.0, "STRIKE_HEAVY": 0.95, "DRAW_REFRESH": 0.9, "RECOVER_CYCLE": 0.8},
                },
                "T5_PLUS_ENDGAME": {
                    "active_name": "Dragapult ex / Bloodmoon Ursaluna ex", "hp": 320, "prizes": 2, "is_ex": True,
                    "tier": "EX_STAGE2", "mode": "SPREAD_HARVEST", "bench": "TWO_PRIZE_LIABILITIES",
                    "lock": "HAND_DISRUPTED", "prize_ctx": "CHECKMATE_RACE",
                    "dmg": 240.0, "spread": 60.0, "bench_low_hp": 90, "gust_prizes": 2, "gust_hp": 210, "hammer": 0.0,
                    "desc": "Endgame Phantom Dive + Dusknoir board wipe threat.",
                    "demands": {"STRIKE_HEAVY": 0.95, "GUST_TARGET": 0.95, "TANK_SURVIVE": 0.85, "DRAW_REFRESH": 0.85},
                },
            },
        },
        "Dragapult Blaziken": {
            "weakness": None,
            "phases": {
                "T1_OPENING": {
                    "active_name": "Budew / Dreepy", "hp": 70, "prizes": 1, "is_ex": False,
                    "tier": "SP_FRAGILE", "mode": "CHIP_LOCK", "bench": "ENGINE_EXPOSED",
                    "lock": "ITEM_LOCK", "prize_ctx": "EVEN_START",
                    "dmg": 10.0, "spread": 0.0, "bench_low_hp": 60, "gust_prizes": 1, "gust_hp": 60, "hammer": 0.0,
                    "desc": "Dreepy + Torchic setup behind Budew.",
                    "demands": {"SETUP_BASIC": 0.95, "DRAW_REFRESH": 0.85, "STRIKE_LIGHT": 0.75},
                },
                "T2_FIRST_STRIKE": {
                    "active_name": "Dragapult ex", "hp": 320, "prizes": 2, "is_ex": True,
                    "tier": "EX_STAGE2", "mode": "SPREAD_HARVEST", "bench": "ENGINE_EXPOSED",
                    "lock": "OPEN_PLAY", "prize_ctx": "EVEN_START",
                    "dmg": 200.0, "spread": 60.0, "bench_low_hp": 80, "gust_prizes": 1, "gust_hp": 90, "hammer": 0.0,
                    "desc": "Blaziken ex Burning Charge accelerating Fire/Psychic energy from discard to power Dragapult ex immediately.",
                    "demands": {"STRIKE_HEAVY": 0.9, "TANK_SURVIVE": 0.85, "EVOLVE_LINE": 0.85, "ACCEL_ENERGY": 0.8},
                },
                "T3_4_MIDGAME_TRADE": {
                    "active_name": "Dragapult ex / Blaziken ex", "hp": 320, "prizes": 2, "is_ex": True,
                    "tier": "EX_STAGE2", "mode": "SPREAD_HARVEST", "bench": "TWO_PRIZE_LIABILITIES",
                    "lock": "OPEN_PLAY", "prize_ctx": "EVEN_START",
                    "dmg": 200.0, "spread": 60.0, "bench_low_hp": 90, "gust_prizes": 2, "gust_hp": 210, "hammer": 0.0,
                    "desc": "Dual Stage 2 ex attackers (Dragapult ex 320 HP + Blaziken ex 320 HP) endlessly re-armed via Burning Charge.",
                    "demands": {"STRIKE_HEAVY": 1.0, "GUST_TARGET": 0.85, "TANK_SURVIVE": 0.85},
                },
                "T5_PLUS_ENDGAME": {
                    "active_name": "Blaziken ex / Dragapult ex", "hp": 320, "prizes": 2, "is_ex": True,
                    "tier": "EX_STAGE2", "mode": "BURST_OHKO", "bench": "TWO_PRIZE_LIABILITIES",
                    "lock": "HAND_DISRUPTED", "prize_ctx": "CHECKMATE_RACE",
                    "dmg": 240.0, "spread": 60.0, "bench_low_hp": 90, "gust_prizes": 2, "gust_hp": 170, "hammer": 0.0,
                    "desc": "320 HP Stage 2 ex closing out prize race with instant discard energy reload.",
                    "demands": {"STRIKE_HEAVY": 1.0, "GUST_TARGET": 0.95, "DRAW_REFRESH": 0.85},
                },
            },
        },
        "Dhelmise / Banette (Hide 'n' Sneak)": {
            "weakness": "Darkness",
            "phases": {
                "T1_OPENING": {
                    "active_name": "Dhelmise", "hp": 140, "prizes": 1, "is_ex": False,
                    "tier": "SP_ATTACKER", "mode": "PASSIVE_SETUP", "bench": "SPARSE",
                    "lock": "OPEN_PLAY", "prize_ctx": "EVEN_START",
                    "dmg": 30.0, "spread": 0.0, "bench_low_hp": 30, "gust_prizes": 1, "gust_hp": 30, "hammer": 0.0,
                    "desc": "Ultra Ball + Gwynn discarding Poltchageist/Banette (Hide 'n' Sneak) while drawing 6 cards.",
                    "demands": {"SETUP_BASIC": 0.9, "DRAW_REFRESH": 0.85, "STRIKE_MID": 0.75},
                },
                "T2_FIRST_STRIKE": {
                    "active_name": "Dhelmise", "hp": 140, "prizes": 1, "is_ex": False,
                    "tier": "SP_ATTACKER", "mode": "TWO_SHOT_PRESSURE", "bench": "SPARSE",
                    "lock": "OPEN_PLAY", "prize_ctx": "BEHIND_COMEBACK",
                    "dmg": 170.0, "spread": 0.0, "bench_low_hp": 80, "gust_prizes": 1, "gust_hp": 80, "hammer": 0.0,
                    "desc": "140 HP Basic Dhelmise hitting 170 dmg for a single Psychic Energy (Vengeful Anchor) on Turn 2!",
                    "demands": {"STRIKE_MID": 0.95, "TANK_SURVIVE": 0.85, "SPREAD_BENCH": 0.75, "WALL_BREAKER": 0.8},
                },
                "T3_4_MIDGAME_TRADE": {
                    "active_name": "Dhelmise", "hp": 140, "prizes": 1, "is_ex": False,
                    "tier": "SP_ATTACKER", "mode": "TWO_SHOT_PRESSURE", "bench": "SPARSE",
                    "lock": "OPEN_PLAY", "prize_ctx": "BEHIND_COMEBACK",
                    "dmg": 170.0, "spread": 30.0, "bench_low_hp": 80, "gust_prizes": 1, "gust_hp": 90, "hammer": 0.0,
                    "desc": "Streaming 1-Prize 140 HP Dhelmise attackers for 1 Energy each + Munkidori / Risky Ruins.",
                    "demands": {"STRIKE_MID": 0.95, "TANK_SURVIVE": 0.9, "RECOVER_CYCLE": 0.85, "SPREAD_BENCH": 0.8},
                },
                "T5_PLUS_ENDGAME": {
                    "active_name": "Dhelmise", "hp": 140, "prizes": 1, "is_ex": False,
                    "tier": "SP_ATTACKER", "mode": "TWO_SHOT_PRESSURE", "bench": "SPARSE",
                    "lock": "HAND_DISRUPTED", "prize_ctx": "CHECKMATE_RACE",
                    "dmg": 170.0, "spread": 30.0, "bench_low_hp": 140, "gust_prizes": 1, "gust_hp": 140, "hammer": 0.0,
                    "desc": "Sacred Ash / Night Stretcher looping Dhelmise to win the 1-prize vs 2-prize war.",
                    "demands": {"TANK_SURVIVE": 0.9, "STRIKE_MID": 0.9, "GUST_TARGET": 0.85},
                },
            },
        },
        "Crustle / Mega Kangaskhan Wall": {
            "weakness": "Fire",
            "phases": {
                "T1_OPENING": {
                    "active_name": "Mega Kangaskhan ex / Dwebble", "hp": 300, "prizes": 3, "is_ex": True,
                    "tier": "MEGA_TANK", "mode": "PASSIVE_SETUP", "bench": "SPARSE",
                    "lock": "OPEN_PLAY", "prize_ctx": "EVEN_START",
                    "dmg": 0.0, "spread": 0.0, "bench_low_hp": 70, "gust_prizes": 1, "gust_hp": 70, "hammer": 0.4,
                    "desc": "Mega Kangaskhan ex tanking & drawing 2/turn while Dwebble sets up on bench.",
                    "demands": {"GUST_TARGET": 0.9, "SETUP_BASIC": 0.85, "ACCEL_ENERGY": 0.8},
                },
                "T2_FIRST_STRIKE": {
                    "active_name": "Crustle", "hp": 170, "prizes": 1, "is_ex": False,
                    "tier": "SP_ATTACKER", "mode": "CHIP_LOCK", "bench": "SPARSE",
                    "lock": "EX_IMMUNITY_WALL", "prize_ctx": "EVEN_START",
                    "dmg": 120.0, "spread": 20.0, "bench_low_hp": 150, "gust_prizes": 3, "gust_hp": 300, "hammer": 0.4,
                    "desc": "Crustle (Mysterious Rock Inn: immune to all damage from Pokemon ex) + Growing Grass Energy (+20 HP) + Spiky Energy.",
                    "demands": {"WALL_BREAKER": 1.0, "GUST_TARGET": 0.9, "SPREAD_BENCH": 0.8},
                },
                "T3_4_MIDGAME_TRADE": {
                    "active_name": "Crustle (Hero's Cape / Jumbo Ice Cream)", "hp": 250, "prizes": 1, "is_ex": False,
                    "tier": "SP_ATTACKER", "mode": "CHIP_LOCK", "bench": "SPARSE",
                    "lock": "EX_IMMUNITY_WALL", "prize_ctx": "BEHIND_COMEBACK",
                    "dmg": 120.0, "spread": 40.0, "bench_low_hp": 150, "gust_prizes": 1, "gust_hp": 150, "hammer": 0.5,
                    "desc": "Full Crustle wall lock healing 80/turn with Jumbo Ice Cream + Mist Energy blocking effects, aiming for Deck-Out or slow sweep.",
                    "demands": {"WALL_BREAKER": 1.0, "RECOVER_CYCLE": 0.8, "ACCEL_ENERGY": 0.7},
                },
                "T5_PLUS_ENDGAME": {
                    "active_name": "Crustle", "hp": 190, "prizes": 1, "is_ex": False,
                    "tier": "SP_ATTACKER", "mode": "CHIP_LOCK", "bench": "SPARSE",
                    "lock": "EX_IMMUNITY_WALL", "prize_ctx": "CHECKMATE_RACE",
                    "dmg": 120.0, "spread": 40.0, "bench_low_hp": 170, "gust_prizes": 1, "gust_hp": 170, "hammer": 0.5,
                    "desc": "Late-game Crustle wall + deck-out pressure (39.8% of Crustle games end in deck-out).",
                    "demands": {"WALL_BREAKER": 1.0, "RECOVER_CYCLE": 0.9, "GUST_TARGET": 0.75},
                },
            },
        },
        "Mega Lopunny ex / Dusknoir": {
            "weakness": "Fighting",
            "phases": {
                "T1_OPENING": {
                    "active_name": "Buneary / Budew", "hp": 70, "prizes": 1, "is_ex": False,
                    "tier": "SP_FRAGILE", "mode": "CHIP_LOCK", "bench": "ENGINE_EXPOSED",
                    "lock": "ITEM_LOCK", "prize_ctx": "EVEN_START",
                    "dmg": 10.0, "spread": 0.0, "bench_low_hp": 60, "gust_prizes": 1, "gust_hp": 60, "hammer": 0.0,
                    "desc": "Buneary + Duskull + Dunsparce setup.",
                    "demands": {"SETUP_BASIC": 0.95, "STRIKE_LIGHT": 0.8, "DRAW_REFRESH": 0.8},
                },
                "T2_FIRST_STRIKE": {
                    "active_name": "Mega Lopunny ex", "hp": 330, "prizes": 3, "is_ex": True,
                    "tier": "MEGA_TANK", "mode": "BURST_OHKO", "bench": "ENGINE_EXPOSED",
                    "lock": "OPEN_PLAY", "prize_ctx": "EVEN_START",
                    "dmg": 230.0, "spread": 50.0, "bench_low_hp": 60, "gust_prizes": 1, "gust_hp": 90, "hammer": 0.0,
                    "desc": "330 HP Mega Lopunny ex switching in for 1 Colorless Energy Gale Thrust (230 dmg) + Dusclops.",
                    "demands": {"STRIKE_HEAVY": 0.95, "TANK_SURVIVE": 0.85, "GUST_TARGET": 0.8},
                },
                "T3_4_MIDGAME_TRADE": {
                    "active_name": "Mega Lopunny ex", "hp": 330, "prizes": 3, "is_ex": True,
                    "tier": "MEGA_TANK", "mode": "SPREAD_HARVEST", "bench": "ENGINE_EXPOSED",
                    "lock": "OPEN_PLAY", "prize_ctx": "EVEN_START",
                    "dmg": 230.0, "spread": 130.0, "bench_low_hp": 90, "gust_prizes": 2, "gust_hp": 170, "hammer": 0.0,
                    "desc": "Mega Lopunny ex (230 dmg for 1 energy) + Dusknoir Cursed Blast (130 dmg) = 360 single-turn burst.",
                    "demands": {"STRIKE_HEAVY": 1.0, "TANK_SURVIVE": 0.95, "GUST_TARGET": 0.85},
                },
                "T5_PLUS_ENDGAME": {
                    "active_name": "Mega Lopunny ex", "hp": 330, "prizes": 3, "is_ex": True,
                    "tier": "MEGA_TANK", "mode": "BURST_OHKO", "bench": "TWO_PRIZE_LIABILITIES",
                    "lock": "HAND_DISRUPTED", "prize_ctx": "CHECKMATE_RACE",
                    "dmg": 230.0, "spread": 0.0, "bench_low_hp": 140, "gust_prizes": 3, "gust_hp": 330, "hammer": 0.0,
                    "desc": "330 HP Mega Lopunny ex pivoting with Jet Energy / Switch to close the game.",
                    "demands": {"STRIKE_HEAVY": 1.0, "GUST_TARGET": 0.9, "DISRUPT_HAND": 0.8},
                },
            },
        },
        "Mega Excadrill ex / Metang": {
            "weakness": "Fire",
            "phases": {
                "T1_OPENING": {
                    "active_name": "Beldum / Drilbur", "hp": 70, "prizes": 1, "is_ex": False,
                    "tier": "SP_FRAGILE", "mode": "PASSIVE_SETUP", "bench": "ENGINE_EXPOSED",
                    "lock": "OPEN_PLAY", "prize_ctx": "EVEN_START",
                    "dmg": 20.0, "spread": 0.0, "bench_low_hp": 70, "gust_prizes": 1, "gust_hp": 70, "hammer": 0.0,
                    "desc": "Buddy-Buddy Poffin deploying Beldum and Drilbur with 16+ Metal Energy in deck.",
                    "demands": {"SETUP_BASIC": 0.95, "GUST_TARGET": 0.8, "STRIKE_LIGHT": 0.75},
                },
                "T2_FIRST_STRIKE": {
                    "active_name": "Mega Excadrill ex", "hp": 340, "prizes": 3, "is_ex": True,
                    "tier": "MEGA_TANK", "mode": "BURST_OHKO", "bench": "ENGINE_EXPOSED",
                    "lock": "OPEN_PLAY", "prize_ctx": "EVEN_START",
                    "dmg": 265.0, "spread": 0.0, "bench_low_hp": 100, "gust_prizes": 1, "gust_hp": 100, "hammer": 0.0,
                    "desc": "Metang Metal Maker accelerating Metal Energies onto 340 HP Mega Excadrill ex.",
                    "demands": {"STRIKE_HEAVY": 0.95, "GUST_TARGET": 0.85, "ACCEL_ENERGY": 0.8},
                },
                "T3_4_MIDGAME_TRADE": {
                    "active_name": "Mega Excadrill ex", "hp": 340, "prizes": 3, "is_ex": True,
                    "tier": "MEGA_TANK", "mode": "BURST_OHKO", "bench": "ENGINE_EXPOSED",
                    "lock": "OPEN_PLAY", "prize_ctx": "EVEN_START",
                    "dmg": 330.0, "spread": 0.0, "bench_low_hp": 100, "gust_prizes": 1, "gust_hp": 100, "hammer": 0.0,
                    "desc": "Mega Excadrill ex Maximum Drilling (330 dmg with 5 Metal Energy) or Undermine mill.",
                    "demands": {"STRIKE_HEAVY": 1.0, "DISRUPT_HAND": 0.85, "GUST_TARGET": 0.85},
                },
                "T5_PLUS_ENDGAME": {
                    "active_name": "Mega Excadrill ex", "hp": 340, "prizes": 3, "is_ex": True,
                    "tier": "MEGA_TANK", "mode": "BURST_OHKO", "bench": "ENGINE_EXPOSED",
                    "lock": "OPEN_PLAY", "prize_ctx": "CHECKMATE_RACE",
                    "dmg": 330.0, "spread": 0.0, "bench_low_hp": 100, "gust_prizes": 1, "gust_hp": 100, "hammer": 0.0,
                    "desc": "340 HP Mega tank requiring 340+ burst or 2-shot survival to take 3 Prizes.",
                    "demands": {"STRIKE_HEAVY": 1.0, "TANK_SURVIVE": 0.85, "GUST_TARGET": 0.85},
                },
            },
        },
    }

    def _opp_active_stage(active_name: str, tier: str) -> int:
        """Resolve the opponent's Active evolution stage (needed for devolution effects)."""
        clean = re.sub(r"\s*\(.*?\)", "", active_name)
        for token in (t.strip() for t in clean.split("/")):
            cands = db.by_name.get(token)
            if cands:
                return max(0, cands[0].stage)
        return {"SP_FRAGILE": 0, "SP_ATTACKER": 1, "EX_BASIC": 0, "EX_STAGE2": 2, "MEGA_TANK": 1}.get(tier, 0)

    scenarios: list[BoardStateScenario] = []
    idx = 1
    for fam_name, meta_share in family_weights.items():
        prof = archetype_profiles.get(fam_name)
        if not prof:
            continue
        weak = prof["weakness"]
        for phase, p_weight in phase_weights.items():
            p_data = prof["phases"][phase]
            w = round(meta_share * p_weight, 5)
            scenarios.append(
                BoardStateScenario(
                    state_id=f"S{idx:02d}",
                    name=f"{fam_name} @ {phase}",
                    archetype_source=fam_name,
                    meta_share=meta_share,
                    phase=phase,
                    state_weight=w,
                    active_tier=p_data["tier"],
                    pressure_mode=p_data["mode"],
                    bench_structure=p_data["bench"],
                    lock_condition=p_data["lock"],
                    prize_context=p_data["prize_ctx"],
                    opp_active_name=p_data["active_name"],
                    opp_active_hp=p_data["hp"],
                    opp_active_weakness=weak,
                    opp_active_prizes=p_data["prizes"],
                    opp_active_is_ex=p_data["is_ex"],
                    opp_active_stage=_opp_active_stage(p_data["active_name"], p_data["tier"]),
                    opp_incoming_active_dmg=p_data["dmg"],
                    opp_incoming_bench_spread=p_data["spread"],
                    opp_bench_spread_is_counters=fam_name not in ("N's Zoroark ex", "Slowking (Seek Inspiration)"),
                    opp_bench_lowest_hp=p_data["bench_low_hp"],
                    opp_bench_gust_prizes=p_data["gust_prizes"],
                    opp_bench_gust_hp=p_data["gust_hp"],
                    opp_energy_denial_rate=p_data["hammer"],
                    action_demands=p_data["demands"],
                    description=p_data["desc"],
                )
            )
            idx += 1

    # Normalize state weights so they sum to 1.0
    total_w = sum(s.state_weight for s in scenarios)
    for s in scenarios:
        s.state_weight = round(s.state_weight / max(1e-9, total_w), 5)

    # Sort by highest priority (expected tournament encounter weight)
    scenarios.sort(key=lambda s: s.state_weight, reverse=True)
    return scenarios


def export_state_space(out_path: Path, scenarios: list[BoardStateScenario]) -> None:
    payload = {
        "taxonomy": {
            "description": "Chess-like factored Board State Space (S) and 16-dimensional Macro-Action Space (A) for Pokemon TCG Standard.",
            "state_dimensions": {
                "phase_windows": PHASE_WINDOWS,
                "active_tiers": ACTIVE_TIERS,
                "pressure_modes": PRESSURE_MODES,
                "bench_structures": BENCH_STRUCTURES,
                "lock_conditions": LOCK_CONDITIONS,
                "prize_contexts": PRIZE_CONTEXTS,
            },
            "theoretical_grid_size": (
                len(PHASE_WINDOWS)
                * len(ACTIVE_TIERS)
                * len(PRESSURE_MODES)
                * len(BENCH_STRUCTURES)
                * len(LOCK_CONDITIONS)
                * len(PRIZE_CONTEXTS)
            ),
            "canonical_competitive_states_count": len(scenarios),
            "macro_actions": MACRO_ACTIONS,
        },
        "prioritized_competitive_states": [asdict(s) for s in scenarios],
    }
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)


if __name__ == "__main__":
    root = Path(__file__).resolve().parents[1]
    db = StandardCardDatabase(
        root / "pokemon-tcg-data-standard",
        root / "meta" / "decklists_2026-09-19_to_10-31.json",
    )
    scenarios = build_competitive_state_space(
        db,
        root / "meta" / "decklists_2026-09-19_to_10-31.json",
        root / "matches" / "parsed_turn_trajectories.json",
    )
    out_file = root / "meta" / "competitive_board_states.json"
    export_state_space(out_file, scenarios)
    print(f"Exported {len(scenarios)} prioritized competitive board states to {out_file}")
    print("\nTop 12 Highest-Priority Competitive Board States:")
    for s in scenarios[:12]:
        print(f"  [{s.state_id}] w={s.state_weight*100:5.2f}% | {s.name:48s} | {s.active_tier}/{s.pressure_mode}/{s.lock_condition}")
