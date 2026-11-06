"""
Fast, Generalizable State-Space Deck Evaluator for Pokemon TCG.
Evaluates any 60-card deck against the 52 Prioritized Competitive Board States
using Exact Hypergeometric Reachability, Sub-Additive Role Saturation, and
Prize-Trade Tempo Math — without requiring slow MCTS or AI card-playing simulations.
"""
from __future__ import annotations

import json
import math
import re
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from card_compiler import BASIC_ENERGY_MAP, MACRO_ACTIONS, CompiledCard, StandardCardDatabase, card_matches_filter
from state_space import BoardStateScenario, build_competitive_state_space, conditions_live

# Saturation scale per macro action (raw copy-weighted sum at which capability reaches ~63%).
NORM_SCALES = {
    "SETUP_BASIC": 5.5,
    "EVOLVE_LINE": 3.5,
    "DRAW_REFRESH": 5.5,
    "TUTOR_SEARCH": 5.5,
    "ACCEL_ENERGY": 3.2,
    "STRIKE_LIGHT": 2.5,
    "STRIKE_MID": 2.5,
    "STRIKE_HEAVY": 2.5,
    "SPREAD_BENCH": 2.2,
    "GUST_TARGET": 2.4,
    "DISRUPT_HAND": 2.2,
    "LOCK_STALL": 2.0,
    "WALL_BREAKER": 2.2,
    "MOBILITY_PIVOT": 2.5,
    "RECOVER_CYCLE": 2.0,
    "TANK_SURVIVE": 2.5,
}

# Win-rate calibration. Scores are only meaningful RELATIVE to the real tournament field:
# a deck that scores like the average 512-list tournament deck is a ~50% deck against that
# field. `FIELD_WR_SPREAD` is the win-rate standard deviation assigned to a one-standard-
# deviation score difference among real tournament decks (top archetypes sit at ~43-61%).
FIELD_WR_SPREAD = 0.05
LEGACY_WR_CENTER, LEGACY_WR_SCALE = 62.0, 8.5   # used only when no field decklists are supplied


def hypergeom_prob_at_least(n_total: int, k_success: int, n_draws: int, min_hits: int = 1) -> float:
    """Exact probability P(X >= min_hits) when drawing `n_draws` from `n_total` with `k_success` items."""
    if min_hits <= 0:
        return 1.0
    if k_success < min_hits or n_draws < min_hits:
        return 0.0
    n_draws = min(n_total, max(0, int(round(n_draws))))
    k_success = min(n_total, max(0, int(round(k_success))))
    if n_total - k_success < n_draws - min_hits + 1:
        return 1.0
    total_ways = math.comb(n_total, n_draws)
    if total_ways == 0:
        return 0.0
    fail_ways = 0
    for i in range(min_hits):
        if i <= k_success and (n_draws - i) <= (n_total - k_success):
            fail_ways += math.comb(k_success, i) * math.comb(n_total - k_success, n_draws - i)
    return max(0.0, min(1.0, 1.0 - (fail_ways / total_ways)))


def subadditive_saturate(x: float, scale: float = 1.0) -> float:
    """Models diminishing marginal returns (sub-additivity) of redundant cards in the same role."""
    if x <= 0:
        return 0.0
    return 1.0 - math.exp(-x / max(1e-6, scale))


@dataclass
class DeckEvaluationReport:
    is_legal: bool
    legality_issues: list[str]
    overall_score: float                    # Blended (50% First / 50% Second) state score [0..100]
    expected_win_rate: float                # Blended calibrated meta win rate [0..1]
    going_first_score: float                # State score when Going First (Seat 0) [0..100]
    going_first_win_rate: float             # Calibrated win rate Going First [0..1]
    going_second_score: float               # State score when Going Second (Seat 1) [0..100]
    going_second_win_rate: float            # Calibrated win rate Going Second [0..1]
    preferred_seat: str                     # "GOING_FIRST" or "GOING_SECOND"
    seat_delta_wr: float                    # (going_first_win_rate - going_second_win_rate)
    consistency_score: float                # Blended setup consistency [0..100]
    consistency_first: float                # Turn 1-2 setup consistency Going First (no T1 Supporter, pre-Budew)
    consistency_second: float               # Turn 1-2 setup consistency Going Second (T1 Supporter live, post-opp T1)
    macro_capabilities: dict[str, float]    # Saturated 16-action capability vector [0..1]
    archetype_scores: dict[str, float]      # Blended score vs each meta archetype
    archetype_scores_first: dict[str, float]
    archetype_scores_second: dict[str, float]
    phase_scores: dict[str, float]          # Blended performance across T1, T2, T3-4, T5+
    phase_scores_first: dict[str, float]
    phase_scores_second: dict[str, float]
    state_scores: dict[str, float]          # Blended score on each of the 52 board states
    worst_states: list[tuple[str, str, float, float]]  # (state_id, name, weight, score)
    best_states: list[tuple[str, str, float, float]]
    missing_demands: dict[str, float]       # Bottleneck macro-actions most needed to improve EV
    field_percentile: float | None = None   # Share of real tournament decks scoring below this deck [0..100]
    dead_cards: list[tuple[str, int, str]] = field(default_factory=list)  # (card, copies, reason)


class StateSpaceEvaluator:
    def __init__(
        self,
        db: StandardCardDatabase,
        scenarios: list[BoardStateScenario],
        field_decklists: Path | list[dict[str, Any]] | None = None,
    ):
        """
        `field_decklists` (the tournament decklist JSON, or its parsed list) calibrates win
        rates against the real field: without it, win rates use legacy constants and are
        NOT comparable to real-world win rates.
        """
        self.db = db
        self.scenarios = scenarios
        w_tot = sum(s.state_weight for s in scenarios) or 1.0
        self._cond_avg_cache: dict[tuple[str, ...], float] = {}
        self._w_tot = w_tot
        self._field_source = field_decklists
        self._field_scores: list[float] | None = None
        self._wr_center, self._wr_scale = LEGACY_WR_CENTER, LEGACY_WR_SCALE

    # ------------------------------------------------------------------
    # Field calibration
    # ------------------------------------------------------------------
    def _ensure_calibrated(self) -> None:
        if self._field_source is None or self._field_scores is not None:
            return
        src = self._field_source
        self._field_scores = []  # set first: evaluate_deck below must not recurse into calibration
        if isinstance(src, (str, Path)):
            with open(src, encoding="utf-8") as f:
                src = json.load(f)
        scores = []
        for d in src:
            deck: dict[CompiledCard, int] = defaultdict(int)
            for c in d.get("cards", []):
                cc = self.db.resolve_card(c["name"], c.get("set"), str(c.get("num", "")))
                if cc:
                    deck[cc] += int(c["count"])
            if sum(deck.values()) == 60:
                scores.append(self._raw_scores(dict(deck))[0])
        if len(scores) >= 20:
            mu = sum(scores) / len(scores)
            sd = math.sqrt(sum((x - mu) ** 2 for x in scores) / (len(scores) - 1)) or 1.0
            self._wr_center = mu
            # logistic((score - mu) / T) == 0.5 + FIELD_WR_SPREAD at one standard deviation
            self._wr_scale = sd / math.log((0.5 + FIELD_WR_SPREAD) / (0.5 - FIELD_WR_SPREAD))
            self._field_scores = sorted(scores)

    def _win_rate(self, score: float) -> float:
        return 1.0 / (1.0 + math.exp(-(score - self._wr_center) / self._wr_scale))

    def _field_percentile(self, score: float) -> float | None:
        if not self._field_scores:
            return None
        below = sum(1 for x in self._field_scores if x < score)
        return round(100.0 * below / len(self._field_scores), 1)

    # ------------------------------------------------------------------
    # Generic card-effect checks (requirements & situational conditions)
    # ------------------------------------------------------------------
    def avg_condition_live(self, conds: tuple[str, ...] | None) -> float:
        """State-weighted average liveness of a condition tuple across the meta state space."""
        if not conds:
            return 1.0
        if conds not in self._cond_avg_cache:
            self._cond_avg_cache[conds] = sum(
                s.state_weight * conditions_live(conds, s) for s in self.scenarios
            ) / self._w_tot
        return self._cond_avg_cache[conds]

    @staticmethod
    def requirement_satisfaction(card: CompiledCard, deck: dict[CompiledCard, int]) -> dict[str | None, float]:
        """
        Per-macro-action satisfaction [0..1] of `card`'s deck-composition requirements.
        Key None holds the satisfaction for actions not explicitly listed.
        E.g. Rosa's Encouragement needs Stage 2 Pokemon: 0 Stage 2 copies -> 0.0 (dead card).
        """
        if not card.requirements:
            return {None: 1.0}
        per_req: list[tuple[float, list[str] | None]] = []
        for r in card.requirements:
            matching = sum(cnt for c, cnt in deck.items() if cnt > 0 and card_matches_filter(c, r["filter"]))
            per_req.append((min(1.0, matching / max(1, r.get("min", 3))), r.get("acts")))

        def _combine(vals: list[float]) -> float:
            if not vals:
                return 1.0
            if card.requirement_mode == "any":
                return max(vals)
            if card.requirement_mode == "mean":
                return sum(vals) / len(vals)
            return min(vals)

        out: dict[str | None, float] = {None: _combine([v for v, acts in per_req if acts is None])}
        for act in card.action_vector:
            out[act] = _combine([v for v, acts in per_req if acts is None or act in acts])
        return out

    def card_action_weight(self, card: CompiledCard, act: str, sat: dict[str | None, float]) -> float:
        """Expected usefulness [0..1] of `card` for `act`: requirement satisfaction x condition liveness."""
        return sat.get(act, sat[None]) * self.avg_condition_live(card.action_conditions.get(act))

    def check_legality(self, deck: dict[CompiledCard, int]) -> tuple[bool, list[str]]:
        issues = []
        total_cards = sum(deck.values())
        if total_cards != 60:
            issues.append(f"Deck has {total_cards} cards (must be exactly 60).")

        by_name: dict[str, int] = defaultdict(int)
        ace_specs = 0
        basics = 0
        pokemon_names = set()

        for card, cnt in deck.items():
            if cnt < 0:
                issues.append(f"Negative count for {card.name}.")
            if "BASIC_ENERGY" not in card.tags:
                by_name[card.name] += cnt
            if card.is_ace_spec:
                ace_specs += cnt
            if card.supertype == "Pokémon":
                pokemon_names.add(card.name)
                if card.stage == 0:
                    basics += cnt
            elif "FOSSIL_BASIC" in card.tags:
                # Fossil Items (e.g. Antique Plume Fossil) are played as 60-HP Basic Pokemon.
                basics += cnt

        for nm, cnt in by_name.items():
            if cnt > 4:
                issues.append(f"Exceeds 4-copy limit for '{nm}' ({cnt} copies).")

        if ace_specs > 1:
            issues.append(f"Contains {ace_specs} ACE SPEC cards (maximum 1 allowed).")

        if basics == 0:
            issues.append("Deck must contain at least 1 Basic Pokémon.")

        return (len(issues) == 0), issues

    def _analyze_deck_structure(self, deck: dict[CompiledCard, int]) -> dict[str, Any]:
        """Extract structural, hypergeometric, and combat parameters of a 60-card deck."""
        total_basics = 0
        poffin_basics = 0
        draw_supporters = 0
        search_supporters = 0
        gust_cards = 0
        disrupt_cards = 0
        ball_tutors = 0
        rare_candies = 0
        forest_of_vitality = 0
        stadiums = 0
        switch_pivots = 0
        recovery_cards = 0
        draw_engine_pokemon = 0
        colorless_ability_pokemon = 0
        energy_accel_cards = 0
        bench_barrier = 0
        bench_damage_barrier = 0
        bench_counter_barrier = 0
        has_clefairy_ex = False
        hide_n_sneak_count = 0
        festival_grounds_count = 0
        academy_at_night_count = 0
        fossil_basics = 0
        fossil_tutors = 0
        devolution_control = 0

        energy_counts: dict[str, int] = defaultdict(int)
        total_energy = 0
        raw_macro = {act: 0.0 for act in MACRO_ACTIONS}
        name_counts: dict[str, int] = defaultdict(int)

        # First pass: count names, energies, and structural traits
        has_grass_poke = False
        has_stage2_poke = False
        has_dark_poke = False
        has_direct_damage_attacker = False
        has_non_rule_box_direct_attacker = False
        has_fighting_direct_attacker = False
        has_damage_counter_primary = False
        has_poison_source = False
        team_rocket_poke_count = 0

        for card, cnt in deck.items():
            if cnt <= 0:
                continue
            name_counts[card.name] += cnt
            card_text = " ".join(
                [card.rules_text]
                + [a.text for a in card.attacks]
                + [ab.get("text", "") for ab in card.abilities]
            ).lower()
            if "poison" in card_text and card.name != "Binding Mochi":
                has_poison_source = True
            if card.supertype == "Pokémon":
                if "Grass" in card.types:
                    has_grass_poke = True
                if "Darkness" in card.types:
                    has_dark_poke = True
                if card.stage == 2:
                    has_stage2_poke = True
                if card.name.startswith("Team Rocket's"):
                    team_rocket_poke_count += cnt
                if cnt >= 3 and card.attacks and all(a.is_damage_counter_effect for a in card.attacks if a.expected_damage > 0):
                    has_damage_counter_primary = True
                elif cnt >= 3 and any(not a.is_damage_counter_effect and a.expected_damage >= 80 for a in card.attacks):
                    has_direct_damage_attacker = True
                    if not card.is_rule_box:
                        has_non_rule_box_direct_attacker = True
                    if "Fighting" in card.types:
                        has_fighting_direct_attacker = True
            elif card.supertype == "Energy":
                total_energy += cnt
                if card.primary_energy_type:
                    energy_counts[card.primary_energy_type] += cnt
                elif "Luminous" in card.name or "Legacy" in card.name or "Neo Upper" in card.name or "provides every type of energy" in card.rules_text.lower():
                    for et in BASIC_ENERGY_MAP:
                        energy_counts[et] += cnt
                else:
                    energy_counts["Colorless"] += cnt

        if has_damage_counter_primary:
            has_direct_damage_attacker = False
        # Primary attacker scales with OUR hand size (Alakazam Powerful Hand): symmetric hand
        # resets (Judge, Unfair Stamp) shrink our own hand too, so they are mostly anti-synergy.
        hand_size_primary = any(
            cnt >= 3 and "SCALES_HAND_SIZE" in c.synergy_hooks for c, cnt in deck.items() if c.supertype == "Pokémon"
        )

        distinct_basic_energy_types = sum(1 for et in BASIC_ENERGY_MAP if energy_counts.get(et, 0) > 0)

        # Second pass: accumulate conditional Trainer/Energy/Ability capabilities.
        # Every card is checked GENERICALLY against its compiled requirements (e.g. Rosa's
        # Encouragement -> needs Stage 2 Pokemon) and situational conditions (e.g. Rosa only
        # when behind on Prizes); gated contributions go to `cond_macro` and are only credited
        # in board states where the condition is live (see `_state_capabilities`).
        OFFENSIVE_ACTIONS = {"STRIKE_LIGHT", "STRIKE_MID", "STRIKE_HEAVY", "WALL_BREAKER"}
        dead_card_count = 0
        dead_cards: list[tuple[str, int, str]] = []
        cond_macro: dict[tuple[str, ...], dict[str, float]] = defaultdict(lambda: defaultdict(float))
        damage_bonuses: list[dict[str, Any]] = []

        def _mark_dead(card: CompiledCard, n: int, reason: str) -> None:
            nonlocal dead_card_count
            dead_card_count += n
            dead_cards.append((card.name, n, reason))

        for card, cnt in deck.items():
            if cnt <= 0:
                continue
            copy_eff = cnt ** 0.82
            sat = self.requirement_satisfaction(card, deck)
            if hand_size_primary and "SYMMETRIC_HAND_RESET" in card.tags:
                sat = {k: v * 0.35 for k, v in sat.items()}

            def w(act: str) -> float:
                return self.card_action_weight(card, act, sat)

            # Generic requirement check: a Trainer (or attach-restricted Special Energy) whose
            # every capability needs Pokemon the deck doesn't run is a dead card.
            if card.requirements and (card.supertype == "Trainer" or "can only be attached to" in card.rules_text.lower()):
                acts = list(card.action_vector) or [None]
                if all(sat.get(a, sat[None]) <= 0.0 for a in acts):
                    needs = " / ".join(
                        ",".join(f"{k}={v}" for k, v in r["filter"].items()) for r in card.requirements
                    )
                    _mark_dead(card, cnt, f"requires Pokemon matching [{needs}] (none in deck)")
                    continue

            # Card-specific checks the generic parser can't express
            if card.supertype == "Trainer":
                if card.name in ("Janine's Secret Art", "Dark Bell") and (not has_dark_poke or energy_counts.get("Darkness", 0) < 3):
                    _mark_dead(card, cnt, "needs Darkness Pokemon + 3+ Basic Darkness Energy")
                    continue
                if card.name == "Crispin" and distinct_basic_energy_types < 2:
                    _mark_dead(card, cnt, "needs 2+ Basic Energy types")
                    continue
                if "poisoned" in card.rules_text.lower() and not has_poison_source:
                    _mark_dead(card, cnt, "needs a Poison source")
                    continue
                if card.name == "Risky Ruins" and not has_dark_poke and not (name_counts.get("Munkidori", 0) > 0 and energy_counts.get("Darkness", 0) >= 2):
                    _mark_dead(card, cnt, "needs Darkness Pokemon (or Munkidori + Darkness Energy)")
                    continue
                if card.damage_bonus:
                    damage_bonuses.append({
                        **card.damage_bonus,
                        "card": card.name,
                        "copies": cnt,
                        "conds": card.action_conditions.get("STRIKE_HEAVY") or card.action_conditions.get("STRIKE_MID"),
                    })

            for act, val in card.action_vector.items():
                if card.supertype == "Pokémon" and act in OFFENSIVE_ACTIONS:
                    # Pokemon offensive actions are added ONLY in the attacker pass below if their energy & lineage are met!
                    continue
                if card.damage_bonus and act in OFFENSIVE_ACTIONS:
                    # Damage modifiers have no offense of their own: their value flows ONLY through
                    # the attackers they actually boost (see `_damage_bonus` / attacker pass).
                    continue
                if card.supertype == "Pokémon" and act == "SPREAD_BENCH" and not (
                    "SELF_KO_BOMBER" in card.tags or "DAMAGE_MOVER" in card.tags or "PASSIVE_SPREAD" in card.tags
                ):
                    # Attack-based spread is also added in the attacker pass below if energy & lineage are met
                    continue
                if card.supertype == "Pokémon" and "DAMAGE_MOVER" in card.tags and energy_counts.get("Darkness", 0) == 0:
                    continue
                eff = copy_eff
                if (
                    card.supertype == "Pokémon"
                    and act == "TANK_SURVIVE"
                    and "BENCH_DAMAGE_BARRIER" in card.tags
                    and "BENCH_COUNTER_BARRIER" not in card.tags
                ):
                    # Flower Curtain (Shaymin) does not stack; 87/87 tournament decks play 1 copy.
                    eff = 1.0
                contrib = val * eff * sat.get(act, sat[None])
                if contrib <= 0:
                    continue
                conds = card.action_conditions.get(act)
                if conds:
                    cond_macro[conds][act] += contrib
                else:
                    raw_macro[act] += contrib

            if card.supertype == "Pokémon":
                if card.stage == 0:
                    total_basics += cnt
                    if card.hp <= 70:
                        poffin_basics += cnt
                if "DRAW_ENGINE_POKEMON" in card.tags:
                    draw_engine_pokemon += cnt * w("DRAW_REFRESH")
                    if "Colorless" in card.types:
                        colorless_ability_pokemon += cnt
                if "ENERGY_ACCEL_POKEMON" in card.tags or "ENERGY_DOUBLER" in card.tags:
                    energy_accel_cards += cnt
                if "BENCH_BARRIER" in card.tags:
                    bench_barrier += cnt
                if "BENCH_DAMAGE_BARRIER" in card.tags:
                    bench_damage_barrier += cnt
                    if (
                        "BENCH_COUNTER_BARRIER" not in card.tags
                        and card.stage == 0
                        and cnt > 1
                    ):
                        # Extra copies of a pure attack-damage bench barrier (Shaymin) do not stack
                        # and clog opening hands / bench slots.
                        _mark_dead(card, cnt - 1, "extra copies of a non-stacking bench barrier")
                if "BENCH_COUNTER_BARRIER" in card.tags:
                    bench_counter_barrier += cnt
                if "DRAGON_SLAYER" in card.tags or card.name == "Lillie's Clefairy ex":
                    has_clefairy_ex = True
                if "HIDE_N_SNEAK" in card.synergy_hooks:
                    hide_n_sneak_count += cnt
                if "FREE_RETREAT_AURA" in card.tags:
                    switch_pivots += cnt * 2
                if "DEVOLUTION_CONTROL" in card.tags:
                    devolution_control += cnt
            elif card.supertype == "Trainer":
                if "BENCH_COUNTER_BARRIER" in card.tags:
                    bench_counter_barrier += cnt
                    bench_barrier += cnt
                if "FOSSIL_BASIC" in card.tags:
                    total_basics += cnt
                    fossil_basics += cnt
                if card.name in ("Team Rocket's Petrel", "Ciphermaniac's Codebreaking", "Secret Box"):
                    fossil_tutors += cnt
                if "SUPPORTER" in card.tags:
                    if card.action_vector.get("DRAW_REFRESH", 0) >= 0.5:
                        draw_supporters += cnt * w("DRAW_REFRESH")
                    if card.action_vector.get("TUTOR_SEARCH", 0) >= 0.5:
                        search_supporters += cnt * w("TUTOR_SEARCH")
                if "ITEM" in card.tags and (card.action_vector.get("SETUP_BASIC", 0) >= 0.5 or card.action_vector.get("TUTOR_SEARCH", 0) >= 0.5):
                    ball_tutors += cnt * max(w("SETUP_BASIC"), w("TUTOR_SEARCH"))
                if card.name == "Rare Candy" and has_stage2_poke:
                    rare_candies += cnt
                if card.name == "Forest of Vitality" and has_grass_poke:
                    forest_of_vitality += cnt
                if card.name == "Festival Grounds":
                    festival_grounds_count += cnt
                if card.name == "Academy at Night":
                    academy_at_night_count += cnt
                if "STADIUM" in card.tags:
                    stadiums += cnt
                if card.action_vector.get("GUST_TARGET", 0) >= 0.5:
                    gust_cards += cnt * w("GUST_TARGET")
                if card.action_vector.get("DISRUPT_HAND", 0) >= 0.5:
                    disrupt_cards += cnt * w("DISRUPT_HAND")
                if card.action_vector.get("MOBILITY_PIVOT", 0) >= 0.5:
                    switch_pivots += cnt * w("MOBILITY_PIVOT")
                if card.action_vector.get("RECOVER_CYCLE", 0) >= 0.5:
                    recovery_cards += cnt * w("RECOVER_CYCLE")
                if card.action_vector.get("ACCEL_ENERGY", 0) >= 0.5:
                    energy_accel_cards += cnt * w("ACCEL_ENERGY")
            elif card.supertype == "Energy":
                if card.action_vector.get("SETUP_BASIC", 0) >= 0.5:
                    ball_tutors += cnt * w("SETUP_BASIC")
                if card.action_vector.get("ACCEL_ENERGY", 0) >= 0.5:
                    energy_accel_cards += cnt * w("ACCEL_ENERGY")
                if card.action_vector.get("MOBILITY_PIVOT", 0) >= 0.5:
                    switch_pivots += cnt * w("MOBILITY_PIVOT")

        # Opening hand probabilities (distinguishing Going First vs Going Second rules!)
        p_open_basic = hypergeom_prob_at_least(60, total_basics, 7, 1)
        # Going First (Seat 0): Cannot play Supporters on Turn 1! Only Basics + Ball/Poffin Items + Stadiums + Telepathic Energy work on T1.
        p_two_basics_t1_first = hypergeom_prob_at_least(60, total_basics + ball_tutors, 8, 2)
        p_draw_t1_t2_first = hypergeom_prob_at_least(60, draw_supporters + search_supporters + draw_engine_pokemon + ball_tutors // 2, 9, 1)
        # Going Second (Seat 1): CAN play Supporters (Dawn, Lillie's, Crispin, Gwynn) on Turn 1!
        p_two_basics_t1_second = hypergeom_prob_at_least(60, total_basics + ball_tutors + search_supporters, 8, 2)
        p_draw_t1_t2_second = hypergeom_prob_at_least(60, draw_supporters + search_supporters + draw_engine_pokemon, 8, 1)
        p_two_basics_t1 = 0.5 * (p_two_basics_t1_first + p_two_basics_t1_second)
        p_draw_t1_t2 = 0.5 * (p_draw_t1_t2_first + p_draw_t1_t2_second)

        # Evaluate candidate attackers in the deck
        # Count passive/ability spread support (e.g. Dusknoir Cursed Blast, Munkidori Adrena-Brain, Froslass)
        ability_spread_support = 0.0
        bomber_burst, bomber_avail = 0.0, 0.0
        for c2, cnt2 in deck.items():
            if cnt2 <= 0:
                continue
            if "SELF_KO_BOMBER" in c2.tags:
                # Check the bomber's evolution line is actually present (e.g. Duskull for Dusknoir)
                root = self.db.get_evolution_chain(c2.name, walk_up=False)[0]
                if name_counts.get(root, 0) > 0:
                    ability_spread_support += 45.0 * min(1.0, cnt2 / 2.0)
                    # Cursed Blast can also target the ACTIVE Pokemon to finish a KO
                    # (Mega Lopunny ex 230 + Dusknoir 130 = 360 one-shots any Mega ex).
                    m_dc = re.search(r"put (\d+) damage counters", " ".join(ab.get("text", "") for ab in c2.abilities).lower())
                    burst = 10.0 * int(m_dc.group(1)) if m_dc else 50.0
                    avail = min(0.9, 0.35 * cnt2)
                    if burst * avail > bomber_burst * bomber_avail:
                        bomber_burst, bomber_avail = burst, avail
            elif "DAMAGE_MOVER" in c2.tags:
                if energy_counts.get("Darkness", 0) > 0:
                    ability_spread_support += 25.0 * min(1.0, cnt2 / 2.0)
                else:
                    _mark_dead(c2, cnt2, "Adrena-Brain needs Darkness Energy")
            elif "PASSIVE_SPREAD" in c2.tags:
                ability_spread_support += 20.0 * min(1.0, cnt2 / 2.0)

        attackers = []
        for card, cnt in deck.items():
            if cnt <= 0 or card.supertype != "Pokémon" or not card.attacks:
                continue
            # Check lineage reachability using hypergeometric tutor density
            line_prob = 1.0
            tutor_boost = min(12, ball_tutors + search_supporters * 2)
            if card.stage == 0:
                # A Basic attacker still has to be found: a 1-of is not "always available".
                line_prob = hypergeom_prob_at_least(60, cnt + tutor_boost, 11, 1)
            elif card.stage == 1 and card.evolves_from:
                b_cnt = name_counts.get(card.evolves_from, 0)
                b_is_fossil = "Fossil" in card.evolves_from
                if b_cnt == 0 and not b_is_fossil:
                    continue
                # Fossils are Items, so Pokemon-only ball tutors cannot find them;
                # only generic Trainer/any-card search (Petrel, Ciphermaniac, Secret Box) can.
                b_search = fossil_tutors if b_is_fossil else tutor_boost
                b_window = 10 if b_is_fossil else 11
                p_b = hypergeom_prob_at_least(60, max(1, b_cnt) + b_search, b_window, 1)
                p_s1 = hypergeom_prob_at_least(60, cnt + tutor_boost, 13, 1)
                line_prob = p_b * p_s1
            elif card.stage == 2 and card.evolves_from:
                s1_name = card.evolves_from
                b_name = self.db.evolves_from_map.get(s1_name, "")
                b_cnt = name_counts.get(b_name, 0)
                s1_cnt = name_counts.get(s1_name, 0)
                bridge_cnt = s1_cnt + rare_candies + (forest_of_vitality if "Grass" in card.types else 0)
                if b_cnt == 0 or bridge_cnt == 0:
                    continue
                b_is_fossil = "Fossil" in b_name
                b_search = fossil_tutors if b_is_fossil else tutor_boost
                b_window = 10 if b_is_fossil else 11
                p_b = hypergeom_prob_at_least(60, b_cnt + b_search, b_window, 1)
                p_br = hypergeom_prob_at_least(60, bridge_cnt + search_supporters * 2, 14, 1)
                p_s2 = hypergeom_prob_at_least(60, cnt + tutor_boost, 14, 1)
                line_prob = p_b * p_br * p_s2

            for atk in card.attacks:
                if atk.expected_damage <= 0 and atk.bench_spread_damage <= 0 and not atk.is_item_lock and not atk.is_retreat_lock and atk.mills_cards == 0:
                    continue
                # Check energy availability in deck
                en_ok = True
                en_prob = 1.0
                en_search = search_supporters + energy_accel_cards * 2
                if atk.converted_cost > 0:
                    # Require sufficient total energy & acceleration for 3+ cost attacks
                    if atk.converted_cost >= 3 and (total_energy + energy_accel_cards * 2) < 12:
                        en_prob *= max(0.15, (total_energy + energy_accel_cards * 2) / 14.0)
                    for et, req_c in atk.colored_cost.items():
                        avail_c = energy_counts.get(et, 0)
                        if avail_c < req_c:
                            en_ok = False
                            break
                        en_prob = min(en_prob, hypergeom_prob_at_least(60, avail_c + en_search, 14, req_c))
                    if total_energy < atk.converted_cost:
                        en_ok = False
                    else:
                        en_prob = min(en_prob, hypergeom_prob_at_least(60, total_energy + en_search, 14, atk.converted_cost))
                if not en_ok:
                    continue

                # Synergy adjustment for conditional attacks.
                # `eff_dmg` excludes Trainer damage modifiers: those depend on the target
                # (most only hit Pokemon ex) and are applied per board state in
                # `_damage_bonus`. They NEVER apply to damage-counter placement effects.
                applicable_tool_bonus = 0.0
                bonus_mult = 1.0
                eff_dmg = atk.expected_damage
                eff_spread = atk.bench_spread_damage + ability_spread_support
                if atk.requires_discard_trait == "Hide 'n' Sneak":
                    # Requires >= 4 Hide 'n' Sneak Pokemon in discard
                    if hide_n_sneak_count < 4:
                        eff_dmg = float(atk.printed_damage)
                    else:
                        synergy_mult = min(1.0, (hide_n_sneak_count / 6.0) * (0.5 + 0.5 * min(1.0, (draw_supporters + ball_tutors) / 8.0)))
                        eff_dmg = atk.printed_damage + (atk.max_ceiling_damage - atk.printed_damage) * synergy_mult + applicable_tool_bonus
                elif atk.requires_switch_in:
                    pivot_mult = min(1.0, switch_pivots / 4.0)
                    eff_dmg = atk.printed_damage + (atk.max_ceiling_damage - atk.printed_damage) * pivot_mult + applicable_tool_bonus
                elif atk.scales_with == "HAND_SIZE":
                    hand_mult = min(1.20, 0.65 + 0.05 * (draw_supporters + draw_engine_pokemon + search_supporters))
                    eff_dmg = atk.expected_damage * hand_mult + applicable_tool_bonus
                elif atk.scales_with == "BENCH_COUNT":
                    bench_mult = min(1.0, (total_basics + ball_tutors) / 12.0)
                    eff_dmg = atk.expected_damage * bench_mult
                    if any("festival lead" in (ab.get("name") or "").lower() for ab in card.abilities):
                        stad_mult = min(1.0, festival_grounds_count / 3.0)
                        base_single = atk.expected_damage / 1.85
                        eff_dmg = (base_single + applicable_tool_bonus) * (1.0 + 0.90 * stad_mult)
                        bonus_mult = 1.0 + 0.90 * stad_mult
                        # Double attack can also overflow KO onto a second Pokemon (effectively bench/secondary spread!)
                        eff_spread = max(eff_spread, 45.0 * stad_mult)
                elif atk.scales_with == "TOPDECK_ATTACK_COPY":
                    # Slowking needs Academy at Night + high-damage targets in deck
                    big_targets = sum(
                        cnt2 for c2, cnt2 in deck.items()
                        if c2.supertype == "Pokémon" and c2.name != card.name and any(a2.expected_damage >= 180 or a2.bench_spread_damage >= 90 for a2 in c2.attacks)
                    )
                    copy_mult = min(1.0, (academy_at_night_count / 3.0) * (big_targets / 3.0))
                    eff_dmg = 240.0 * copy_mult
                    eff_spread = 110.0 * copy_mult + ability_spread_support
                elif atk.scales_with == "BENCH_ATTACK_COPY":
                    # N's Zoroark ex copies N's Pokemon attacks
                    ns_targets = sum(
                        cnt2 for c2, cnt2 in deck.items()
                        if c2.supertype == "Pokémon" and c2.name != card.name and c2.name.startswith("N's ") and any(a2.expected_damage >= 120 or a2.bench_spread_damage >= 60 for a2 in c2.attacks)
                    )
                    copy_mult = min(1.0, 0.35 + 0.65 * (ns_targets / 2.0))
                    eff_dmg *= copy_mult
                    eff_spread = eff_spread * copy_mult + ability_spread_support
                elif atk.scales_with == "ENERGY_COUNT":
                    en_mult = min(1.15, (total_energy + energy_accel_cards * 1.5) / 14.0)
                    eff_dmg = atk.expected_damage * en_mult

                bonus_terms = [b for b in damage_bonuses if not atk.is_damage_counter_effect and card_matches_filter(card, b["filter"])]
                avg_bonus = self._damage_bonus(card, atk, bonus_terms) * bonus_mult
                attackers.append({
                    "bonus_terms": bonus_terms,
                    "card": card,
                    "copies": cnt,
                    "attack": atk,
                    "eff_dmg_base": eff_dmg,       # before Trainer damage modifiers
                    "bonus_mult": bonus_mult,
                    "eff_dmg": eff_dmg + avg_bonus,  # state-averaged, for capability classification
                    "eff_spread": eff_spread,
                    "line_prob": line_prob,
                    "en_prob": en_prob,
                    "combined_ready": line_prob * en_prob,
                })

        # Add verified, reachable attacker capabilities into raw_macro
        playable_attacker_cards = {a["card"].uid for a in attackers}
        for card, cnt in deck.items():
            if cnt <= 0 or card.supertype != "Pokémon":
                continue
            if card.uid in playable_attacker_cards:
                best_att = max((a for a in attackers if a["card"].uid == card.uid), key=lambda x: x["eff_dmg"] + x["eff_spread"])
                ready_w = (cnt ** 0.82) * best_att["combined_ready"]
                if 0 < best_att["eff_dmg"] <= 135 or card.action_vector.get("STRIKE_LIGHT", 0) > 0:
                    raw_macro["STRIKE_LIGHT"] += max(card.action_vector.get("STRIKE_LIGHT", 0), min(1.0, best_att["eff_dmg"] / 120.0)) * ready_w
                if 130 < best_att["eff_dmg"] <= 235:
                    raw_macro["STRIKE_MID"] += min(1.0, best_att["eff_dmg"] / 190.0) * ready_w
                if best_att["eff_dmg"] >= 210:
                    raw_macro["STRIKE_HEAVY"] += min(1.0, best_att["eff_dmg"] / 260.0) * ready_w
                if best_att["eff_spread"] > 0:
                    raw_macro["SPREAD_BENCH"] += min(1.0, best_att["eff_spread"] / 60.0) * ready_w
                if best_att["attack"].is_shred or (not card.is_rule_box and best_att["eff_dmg"] >= 110):
                    raw_macro["WALL_BREAKER"] += min(1.0, best_att["eff_dmg"] / 150.0) * ready_w
            else:
                # Non-attacker Pokemon: check if it's a valid evolution pre-stage, draw/tutor/accel/wall/spread support, or Slowking/Zoroark copy target
                is_pre_evo = any(c2.evolves_from == card.name for c2 in deck)
                # Any Ability is a role (Chien-Pao stadium removal, Genesect ACE SPEC lock, ...),
                # even if the compiler can't quantify it.
                is_support = bool(card.abilities) or bool(card.tags & {"DRAW_ENGINE_POKEMON", "TUTOR_POKEMON", "ENERGY_ACCEL_POKEMON", "ENERGY_DOUBLER", "SELF_KO_BOMBER", "DAMAGE_MOVER", "PASSIVE_SPREAD", "BENCH_BARRIER", "IMMUNITY_WALL", "FREE_RETREAT_AURA", "DRAGON_SLAYER"}) or ("HIDE_N_SNEAK" in card.synergy_hooks)
                is_copy_target = (academy_at_night_count >= 2 and not card.is_rule_box) or (card.name.startswith("N's ") and any(c2.name == "N's Zoroark ex" for c2 in deck))
                if not (is_pre_evo or is_support or is_copy_target):
                    _mark_dead(card, cnt, "Pokemon with no reachable attack or support role")

        # Expected (state-averaged) saturated capability vector, for reporting & bottlenecks.
        # Per-state capabilities (with situational cards switched on/off) come from `_state_capabilities`.
        cond_macro_plain = {k: dict(v) for k, v in cond_macro.items()}
        expected_raw = dict(raw_macro)
        for conds, acts in cond_macro_plain.items():
            live = self.avg_condition_live(conds)
            for act, v in acts.items():
                expected_raw[act] += live * v
        macro_cap = {
            act: round(subadditive_saturate(expected_raw[act], NORM_SCALES[act]), 4)
            for act in MACRO_ACTIONS
        }

        # Compute Opening Active Liability & Retreat Trap risk across all Basics
        basic_prize_weighted = 0.0
        basic_retreat_trap = 0.0
        distinct_attacker_lines = set()
        for card, cnt in deck.items():
            if cnt > 0 and card.supertype == "Pokémon" and card.stage == 0:
                basic_prize_weighted += cnt * card.prize_liability
                if card.retreat_cost >= 2 and "FREE_RETREAT_AURA" not in card.tags:
                    basic_retreat_trap += cnt * (card.retreat_cost - 1)
            elif cnt > 0 and "FOSSIL_BASIC" in card.tags:
                # A fossil in play is a 1-Prize 60-HP Basic (cannot retreat, but can discard itself).
                basic_prize_weighted += cnt * 1.0
        avg_opening_liability = basic_prize_weighted / max(1, total_basics)
        avg_retreat_trap = max(0.0, (basic_retreat_trap / max(1, total_basics)) - 0.12 * switch_pivots)

        for a in attackers:
            if a["eff_dmg"] >= 110 or a["eff_spread"] >= 60:
                chain_root = self.db.get_evolution_chain(a["card"].name)[0]
                distinct_attacker_lines.add(chain_root)

        # Check if deck has a Turn 1 Going Second attack capability (0-1 energy Basic attacker or Turbo Basic + Crispin/Accel)
        has_t1_going_second_attack = False
        t1_going_second_power = 0.0
        for a in attackers:
            c_att = a["card"]
            atk = a["attack"]
            if c_att.stage == 0:
                if atk.converted_cost == 0 and (atk.is_item_lock or a["eff_dmg"] > 0):
                    has_t1_going_second_attack = True
                    t1_going_second_power = max(t1_going_second_power, 0.75 if atk.is_item_lock else 0.45)
                elif atk.converted_cost == 1:
                    has_t1_going_second_attack = True
                    t1_going_second_power = max(t1_going_second_power, min(0.95, a["eff_dmg"] / 170.0) * a["combined_ready"])
                elif atk.converted_cost >= 2 and energy_accel_cards >= 5 and switch_pivots >= 3:
                    has_t1_going_second_attack = True
                    t1_going_second_power = max(t1_going_second_power, min(0.90, a["eff_dmg"] / 240.0) * a["combined_ready"] * 0.8)

        return {
            "total_basics": total_basics,
            "poffin_basics": poffin_basics,
            "draw_supporters": draw_supporters,
            "search_supporters": search_supporters,
            "ball_tutors": ball_tutors,
            "rare_candies": rare_candies,
            "forest_of_vitality": forest_of_vitality,
            "stadiums": stadiums,
            "gust_cards": gust_cards,
            "disrupt_cards": disrupt_cards,
            "switch_pivots": switch_pivots,
            "recovery_cards": recovery_cards,
            "draw_engine_pokemon": draw_engine_pokemon,
            "colorless_ability_pokemon": colorless_ability_pokemon,
            "energy_accel_cards": energy_accel_cards,
            "bench_barrier": bench_barrier,
            "bench_damage_barrier": bench_damage_barrier,
            "bench_counter_barrier": bench_counter_barrier,
            "has_clefairy_ex": has_clefairy_ex,
            "fossil_basics": fossil_basics,
            "fossil_tutors": fossil_tutors,
            "devolution_control": devolution_control,
            "damage_bonuses": damage_bonuses,
            "bomber_burst": bomber_burst,
            "bomber_avail": bomber_avail,
            "raw_macro": dict(raw_macro),
            "cond_macro": cond_macro_plain,
            "dead_cards": dead_cards,
            "total_energy": total_energy,
            "energy_counts": dict(energy_counts),
            "macro_cap": macro_cap,
            "p_open_basic": p_open_basic,
            "p_two_basics_t1": p_two_basics_t1,
            "p_two_basics_t1_first": p_two_basics_t1_first,
            "p_two_basics_t1_second": p_two_basics_t1_second,
            "p_draw_t1_t2": p_draw_t1_t2,
            "p_draw_t1_t2_first": p_draw_t1_t2_first,
            "p_draw_t1_t2_second": p_draw_t1_t2_second,
            "has_t1_going_second_attack": has_t1_going_second_attack,
            "t1_going_second_power": t1_going_second_power,
            "dead_card_count": dead_card_count,
            "avg_opening_liability": avg_opening_liability,
            "avg_retreat_trap": avg_retreat_trap,
            "num_attacker_lines": len(distinct_attacker_lines),
            "attackers": attackers,
        }

    def _damage_bonus(
        self,
        card: CompiledCard,
        atk: Any,
        bonuses: list[dict[str, Any]],
        s: BoardStateScenario | None = None,
    ) -> float:
        """
        Attack-damage bonus from Trainer modifiers for `card`'s attack `atk` on state `s`
        (or averaged over the state space when `s` is None).
        - Only direct attack damage is boosted, never damage-counter effects (Alakazam).
        - Attacker filters apply (Brave Bangle: no Rule Box; Premium Power Pro: Fighting).
        - Most modifiers only hit an Active Pokemon ex (Maximum Belt, Black Belt's Training, Kieran).
        - Only 1 Tool per Pokemon and 1 Supporter per turn; Item boosts can stack.
        """
        if atk.is_damage_counter_effect or not bonuses:
            return 0.0
        best_tool = best_supp = items = 0.0
        for b in bonuses:
            if not card_matches_filter(card, b["filter"]):
                continue
            live = self.avg_condition_live(b["conds"]) if s is None else conditions_live(b["conds"], s)
            if live <= 0:
                continue
            n = b["copies"]
            if b["kind"] == "TOOL":
                best_tool = max(best_tool, b["amount"] * min(1.0, n / 2.0) * live)
            elif b["kind"] == "SUPPORTER":
                best_supp = max(best_supp, b["amount"] * min(1.0, n / 3.0) * live)
            else:
                items += b["amount"] * min(1.5, n / 2.0) * live
        return best_tool + best_supp + items

    def _state_capabilities(self, ds: dict[str, Any], s: BoardStateScenario) -> dict[str, float]:
        """Saturated capability vector on state `s`: situational cards count only where live."""
        raw = dict(ds["raw_macro"])
        for conds, acts in ds["cond_macro"].items():
            live = conditions_live(conds, s)
            if live <= 0:
                continue
            for act, v in acts.items():
                raw[act] += live * v
        return {act: subadditive_saturate(raw[act], NORM_SCALES[act]) for act in MACRO_ACTIONS}

    def evaluate_deck_on_state(self, ds: dict[str, Any], s: BoardStateScenario, seat: str = "first") -> float:
        """
        Compute expected performance score [0..1] of deck structure `ds` on board state `s`
        when playing from `seat` ("first" or "second").
        Models official Pokemon TCG turn-order asymmetries:
          - Going First (seat="first"):
              * Turn 1 happens BEFORE opponent's Turn 1 Budew Item Lock (Items 100% live on T1!),
              * Cannot play a Supporter or Attack on Turn 1,
              * Evolves FIRST on Turn 2 (Ply 3) before opponent reaches Stage 1/2!
          - Going Second (seat="second"):
              * CAN play a Supporter (Lillie's, Dawn, Gwynn, Crispin) on Turn 1,
              * CAN Attack on Turn 1 (Budew Itchy Pollen, Dhelmise 1-energy 170 dmg, Basic Box Turbo),
              * Suffers opponent's Turn 1 setup / stadium / evolution-first tempo on Turn 2+.
        """
        cap = self._state_capabilities(ds, s)
        is_first = (seat == "first")

        # 1. Adjust capabilities for opponent's active Lock Condition & Seat Order in state `s`
        if s.lock_condition == "ITEM_LOCK":
            if is_first and s.phase == "T1_OPENING":
                # Going First, our Turn 1 happens BEFORE opponent's Budew can attack with Itchy Pollen!
                pass
            else:
                # Going Second on T1 (if opponent somehow locked) or on T2+ under Budew Item Lock:
                non_item_setup = min(1.0, (ds["total_basics"] + ds["search_supporters"] * 2) / 14.0)
                item_lock_severity = 0.45 if is_first else 0.30  # Worse Going Second because our T1/T2 items get caught after opponent evolves/locks
                cap["SETUP_BASIC"] = item_lock_severity * cap["SETUP_BASIC"] + (1.0 - item_lock_severity) * non_item_setup
                if ds["rare_candies"] > 0 and ds["forest_of_vitality"] == 0:
                    cap["EVOLVE_LINE"] *= (0.72 if is_first else 0.55)
        elif s.lock_condition == "ABILITY_LOCK":
            if ds["colorless_ability_pokemon"] > 0:
                stadium_bump = min(1.0, ds["stadiums"] / 3.0)
                penalty = 0.70 + 0.30 * stadium_bump
                cap["DRAW_REFRESH"] *= penalty
        elif s.lock_condition == "HAND_DISRUPTED":
            board_draw_bonus = min(0.25, ds["draw_engine_pokemon"] * 0.05)
            cap["DRAW_REFRESH"] = min(1.0, cap["DRAW_REFRESH"] * 0.80 + board_draw_bonus)

        # Turn 1 Supporter rule asymmetry
        if s.phase == "T1_OPENING":
            if is_first:
                # Going First cannot play Supporters on Turn 1: rely on Items (Balls/Poffin) and Basic Pokemon Abilities
                item_engine_t1 = min(1.0, (ds["ball_tutors"] + ds["poffin_basics"]) / 11.0)
                cap["DRAW_REFRESH"] = 0.45 * cap["DRAW_REFRESH"] + 0.55 * item_engine_t1
            else:
                # Going Second CAN play Supporters on Turn 1 (Dawn, Lillie's, Gwynn, Crispin)
                supp_engine_t1 = min(1.0, (ds["draw_supporters"] + ds["search_supporters"]) / 8.0)
                cap["DRAW_REFRESH"] = min(1.0, cap["DRAW_REFRESH"] * 1.08 + 0.10 * supp_engine_t1)
                cap["SETUP_BASIC"] = min(1.0, cap["SETUP_BASIC"] + 0.12 * supp_engine_t1)

        # Energy denial resistance (Crushing Hammer)
        if s.opp_energy_denial_rate > 0:
            en_resilience = min(1.0, (ds["total_energy"] + ds["energy_accel_cards"] * 2 + ds["recovery_cards"]) / 14.0)
        else:
            en_resilience = 1.0

        # 2. Macro-Action Demand satisfaction
        demand_sum = sum(s.action_demands.values()) or 1.0
        demand_hit = 0.0
        for act, weight in s.action_demands.items():
            demand_hit += weight * cap.get(act, 0.0)
        macro_alignment = demand_hit / demand_sum

        # 3. Combat & Prize-Trade Tempo Evaluation (Seat-Sensitive!)
        best_combat_score = 0.12
        # Going First gets +0.35 turn lead on Evolution timing; Going Second gets +0.40 turn lead on Basic/Supporter/Accel timing
        phase_turn_budget = {
            "T1_OPENING": 1.0 if is_first else 1.5,
            "T2_FIRST_STRIKE": 2.45 if is_first else 2.05,
            "T3_4_MIDGAME_TRADE": 3.65 if is_first else 3.45,
            "T5_PLUS_ENDGAME": 5.0,
        }[s.phase]

        accel_speedup = 1.0 + min(1.5, ds["energy_accel_cards"] * (0.22 if is_first else 0.28))

        for att in ds["attackers"]:
            card: CompiledCard = att["card"]
            atk = att["attack"]

            stage_turn_needed = 1.0 if card.stage == 0 else (2.0 if (card.stage == 1 or ds["rare_candies"] >= 3 or ds["forest_of_vitality"] >= 2) else 2.5)
            # Going First evolves on Ply 3 (before opponent's T2); Going Second evolves on Ply 4 (after opponent's T2 attack!)
            if card.stage >= 1 and not is_first:
                stage_turn_needed += 0.30
            energy_turn_needed = max(1.0, atk.converted_cost / accel_speedup)
            turns_to_arm = max(stage_turn_needed, energy_turn_needed)

            if s.phase == "T1_OPENING":
                if is_first:
                    # Cannot attack on Turn 1 Going First! Score reflects setting up the attacker safely for Turn 2
                    phase_reach = att["combined_ready"] * (0.88 if card.stage >= 1 else 0.72)
                else:
                    # Going Second CAN attack on Turn 1 if Basic & low/accelerated cost!
                    if card.stage == 0 and (atk.converted_cost <= 1 or (atk.converted_cost >= 2 and ds["energy_accel_cards"] >= 4)):
                        phase_reach = att["combined_ready"] * 1.12
                    else:
                        phase_reach = att["combined_ready"] * 0.65
            elif turns_to_arm <= phase_turn_budget:
                phase_reach = att["combined_ready"] * (1.06 if (is_first and card.stage >= 1) else (1.05 if (not is_first and card.stage == 0) else 1.0))
            else:
                phase_reach = att["combined_ready"] * max(0.25, phase_turn_budget / turns_to_arm)

            # Calculate effective damage against opponent active in state `s`
            # (Trainer damage modifiers depend on the target: most only boost vs Pokemon ex).
            dmg = att["eff_dmg_base"] + (
                att["bonus_mult"] * self._damage_bonus(card, atk, att["bonus_terms"], s) if att["bonus_terms"] else 0.0
            )
            spread = att["eff_spread"]

            # Check Crustle / Ex-Immunity Wall! (Prevents DAMAGE from Pokemon ex; does not prevent damage-counter effects unless Mist Energy)
            if s.lock_condition == "EX_IMMUNITY_WALL" and card.is_rule_box and not atk.is_shred and not atk.is_damage_counter_effect:
                dmg = 0.0

            # Check Weakness (x2) — Weakness ONLY applies to direct attack damage, NEVER to damage counter placement!
            hits_weakness = False
            if not atk.is_damage_counter_effect:
                if s.opp_active_weakness and s.opp_active_weakness in card.types:
                    hits_weakness = True
                elif ds["has_clefairy_ex"] and "Dragapult" in s.archetype_source and "Psychic" in card.types:
                    hits_weakness = True
            if hits_weakness:
                dmg *= 2.0

            total_offense = dmg + 0.65 * spread
            if total_offense <= 0 and not atk.is_item_lock and atk.mills_cards == 0:
                continue

            # Ancient Wing (Archeops): devolve the opponent's Active BEFORE attacking.
            # A 320-HP Dragapult ex becomes a ~90-HP Drakloak (1 Prize) that Rock Throw KOs.
            devolve_active = bool(
                "DEVOLUTION_CONTROL" in card.tags
                and s.opp_active_stage >= 1
                and dmg > 0
            )
            if devolve_active:
                target_hp = min(float(s.opp_active_hp), max(70.0, s.opp_active_hp * 0.38))
                target_prizes = 1
            else:
                target_hp = float(s.opp_active_hp)
                target_prizes = s.opp_active_prizes

            # Turns for us to KO opponent active
            def _turns_to_ko(hp_left: float) -> float:
                t = max(1.0, math.ceil(hp_left / max(20.0, dmg))) if dmg > 0 else 5.0
                if spread >= s.opp_bench_lowest_hp:
                    t = max(1.0, t - 0.45)
                # Seat tempo modifier on Prize Race:
                # Going First gets first evolution attack on T2 (-0.18 turns to KO for Stage 1/2 decks);
                # Going Second gets T1 attack/item-lock initiative (-0.22 turns to KO for Basic/1-energy decks).
                if is_first and card.stage >= 1:
                    t = max(0.85, t - 0.16)
                elif not is_first and card.stage == 0 and ds["has_t1_going_second_attack"]:
                    t = max(0.85, t - 0.20 * ds["t1_going_second_power"])
                return t

            turns_to_ko_opp = _turns_to_ko(target_hp)

            # Turns for opponent to KO our active
            opp_dmg = max(20.0, s.opp_incoming_active_dmg)
            if card.weakness and card.weakness in s.archetype_source:
                opp_dmg *= 1.5
            effective_my_hp = card.hp + (35 if cap["TANK_SURVIVE"] >= 0.5 else 0)
            if "IMMUNITY_WALL" in card.tags and s.opp_active_is_ex:
                turns_opp_kos_us = 4.5
            else:
                turns_opp_kos_us = max(1.0, math.ceil(effective_my_hp / opp_dmg))

            if devolve_active:
                # The devolved attacker must be re-evolved before it can threaten again.
                turns_opp_kos_us += 0.35
                # Devolve + Judge/Unfair Stamp shuffles the returned evolution card away.
                if ds["disrupt_cards"] >= 3:
                    turns_opp_kos_us += 0.15

            # Bench vulnerability penalty if opponent has heavy spread
            bench_survival_mod = 1.0
            if s.opp_incoming_bench_spread >= 60 and (ds["poffin_basics"] + ds["fossil_basics"]) >= 4:
                # Shaymin (Flower Curtain) ONLY stops bench attack damage (Trifrost / Flamebody Cannon),
                # NOT damage counters placed by effects of attacks (Dragapult Phantom Dive) or Abilities
                # (Dusknoir Cursed Blast / Munkidori Adrena-Brain). Only Battle Cage / Rabsca block those!
                if s.opp_bench_spread_is_counters:
                    # A Stadium barrier (Battle Cage) can be prized or bumped if played as a 1-of;
                    # 2+ copies reliably hold the Stadium war.
                    barrier_cov = min(1.0, ds["bench_counter_barrier"] / 2.0)
                else:
                    # Shaymin (Basic Pokemon) is searchable by Poke Pad / Ultra Ball / Dawn, so 1 copy suffices.
                    barrier_cov = 1.0 if ds["bench_damage_barrier"] > 0 else 0.0
                base_pen = 0.12 if is_first else 0.16  # Worse Going Second since opponent reaches Phantom Dive / Cursed Blast first
                bench_survival_mod = 1.0 - base_pen * (1.0 - barrier_cov)

            # Prize Trade Ratio: (opp_prizes / turns_to_ko_opp) vs (my_prizes / turns_opp_kos_us)
            effective_my_liability = 0.75 * max(1, card.prize_liability) + 0.25 * ds.get("avg_opening_liability", 1.0)
            my_prize_rate = target_prizes / turns_to_ko_opp
            opp_prize_rate = effective_my_liability / turns_opp_kos_us
            trade_ratio = my_prize_rate / max(0.25, opp_prize_rate)
            # Self-KO bomber finish (Dusknoir Cursed Blast on the Active): worth it only when it
            # saves a whole attack, and it hands the opponent 1 Prize per use.
            if ds["bomber_burst"] > 0 and dmg > 0 and not devolve_active:
                t_burst = _turns_to_ko(max(0.0, target_hp - ds["bomber_burst"]))
                if t_burst < turns_to_ko_opp:
                    tr_burst = (target_prizes / t_burst) / max(0.25, opp_prize_rate + 1.0 / t_burst)
                    if tr_burst > trade_ratio:
                        trade_ratio = ds["bomber_avail"] * tr_burst + (1.0 - ds["bomber_avail"]) * trade_ratio
            copy_weight = min(1.0, 0.55 + 0.15 * att["copies"])
            combat_val = min(1.0, (trade_ratio / 1.75) * phase_reach * en_resilience * bench_survival_mod * copy_weight)

            if combat_val > best_combat_score:
                best_combat_score = combat_val

        # 4. Combine Seat-Specific Consistency, Macro-Action Alignment, and Combat Prize-Trade Tempo
        clutter_penalty = 1.0 - 0.04 * max(0, ds.get("num_attacker_lines", 1) - 3)
        trap_penalty = max(0.80, 1.0 - (0.045 if is_first else 0.06) * ds.get("avg_retreat_trap", 0.0))
        # A dead card is roughly a blank slot: ~2% per card, applied once (it used to be applied
        # twice at 4%, so a single false "dead" flag cost a real deck ~3 points).
        dead_penalty = max(0.60, 1.0 - 0.02 * ds.get("dead_card_count", 0)) * clutter_penalty * trap_penalty

        if is_first:
            c_t1 = 0.45 * ds["p_open_basic"] + 0.30 * ds["p_two_basics_t1_first"] + 0.25 * ds["p_draw_t1_t2_first"]
        else:
            c_t1 = 0.45 * ds["p_open_basic"] + 0.30 * ds["p_two_basics_t1_second"] + 0.25 * ds["p_draw_t1_t2_second"]

        consistency_factor = c_t1
        raw_state_score = (
            0.25 * consistency_factor
            + 0.35 * macro_alignment
            + 0.40 * best_combat_score
        ) * dead_penalty
        return round(max(0.0, min(1.0, raw_state_score)), 4)

    def _raw_scores(self, deck: dict[CompiledCard, int]) -> tuple[float]:
        return (self.evaluate_deck(deck).overall_score,)

    def evaluate_deck(self, deck: dict[CompiledCard, int]) -> DeckEvaluationReport:
        self._ensure_calibrated()
        is_legal, issues = self.check_legality(deck)
        ds = self._analyze_deck_structure(deck)

        consistency_first = round(
            100.0 * (0.45 * ds["p_open_basic"] + 0.30 * ds["p_two_basics_t1_first"] + 0.25 * ds["p_draw_t1_t2_first"]),
            2,
        )
        consistency_second = round(
            100.0 * (0.45 * ds["p_open_basic"] + 0.30 * ds["p_two_basics_t1_second"] + 0.25 * ds["p_draw_t1_t2_second"]),
            2,
        )
        consistency_score = round(0.5 * (consistency_first + consistency_second), 2)

        state_scores: dict[str, float] = {}
        arch_sum_1st: dict[str, float] = defaultdict(float)
        arch_sum_2nd: dict[str, float] = defaultdict(float)
        arch_weight_tot: dict[str, float] = defaultdict(float)
        phase_sum_1st: dict[str, float] = defaultdict(float)
        phase_sum_2nd: dict[str, float] = defaultdict(float)
        phase_weight_tot: dict[str, float] = defaultdict(float)

        missing_demands: dict[str, float] = defaultdict(float)
        weighted_first = 0.0
        weighted_second = 0.0

        for s in self.scenarios:
            sc_1st = self.evaluate_deck_on_state(ds, s, seat="first")
            sc_2nd = self.evaluate_deck_on_state(ds, s, seat="second")
            sc_blend = round(0.5 * (sc_1st + sc_2nd), 4)
            state_scores[s.state_id] = sc_blend

            weighted_first += s.state_weight * sc_1st
            weighted_second += s.state_weight * sc_2nd

            arch_sum_1st[s.archetype_source] += s.state_weight * sc_1st
            arch_sum_2nd[s.archetype_source] += s.state_weight * sc_2nd
            arch_weight_tot[s.archetype_source] += s.state_weight

            phase_sum_1st[s.phase] += s.state_weight * sc_1st
            phase_sum_2nd[s.phase] += s.state_weight * sc_2nd
            phase_weight_tot[s.phase] += s.state_weight

            deficit = max(0.0, 0.85 - sc_blend)
            for act, d_val in s.action_demands.items():
                gap = max(0.0, d_val - ds["macro_cap"].get(act, 0.0))
                missing_demands[act] += s.state_weight * deficit * gap

        legality_mult = 1.0 if is_legal else max(0.2, 1.0 - 0.15 * len(issues))
        going_first_score = round(100.0 * weighted_first * legality_mult, 2)
        going_second_score = round(100.0 * weighted_second * legality_mult, 2)
        overall_score = round(0.5 * (going_first_score + going_second_score), 2)

        going_first_wr = self._win_rate(going_first_score)
        going_second_wr = self._win_rate(going_second_score)
        calibrated_wr = 0.5 * (going_first_wr + going_second_wr)

        preferred_seat = "GOING_FIRST" if going_first_score >= going_second_score else "GOING_SECOND"
        seat_delta_wr = round(going_first_wr - going_second_wr, 4)

        arch_scores_first = {
            arch: round(100.0 * (arch_sum_1st[arch] / max(1e-9, arch_weight_tot[arch])), 2)
            for arch in arch_weight_tot
        }
        arch_scores_second = {
            arch: round(100.0 * (arch_sum_2nd[arch] / max(1e-9, arch_weight_tot[arch])), 2)
            for arch in arch_weight_tot
        }
        arch_scores = {
            arch: round(0.5 * (arch_scores_first[arch] + arch_scores_second[arch]), 2)
            for arch in arch_weight_tot
        }

        phase_scores_first = {
            ph: round(100.0 * (phase_sum_1st[ph] / max(1e-9, phase_weight_tot[ph])), 2)
            for ph in phase_weight_tot
        }
        phase_scores_second = {
            ph: round(100.0 * (phase_sum_2nd[ph] / max(1e-9, phase_weight_tot[ph])), 2)
            for ph in phase_weight_tot
        }
        phase_scores = {
            ph: round(0.5 * (phase_scores_first[ph] + phase_scores_second[ph]), 2)
            for ph in phase_weight_tot
        }

        ranked_states = [
            (s.state_id, s.name, s.state_weight, state_scores[s.state_id])
            for s in self.scenarios
        ]
        worst_states = sorted(ranked_states, key=lambda x: x[2] * (1.0 - x[3]), reverse=True)[:8]
        best_states = sorted(ranked_states, key=lambda x: x[3], reverse=True)[:8]

        top_missing = {
            k: round(v, 4)
            for k, v in sorted(missing_demands.items(), key=lambda x: -x[1])
            if v > 0
        }

        return DeckEvaluationReport(
            is_legal=is_legal,
            legality_issues=issues,
            overall_score=overall_score,
            expected_win_rate=round(calibrated_wr, 4),
            going_first_score=going_first_score,
            going_first_win_rate=round(going_first_wr, 4),
            going_second_score=going_second_score,
            going_second_win_rate=round(going_second_wr, 4),
            preferred_seat=preferred_seat,
            seat_delta_wr=seat_delta_wr,
            consistency_score=consistency_score,
            consistency_first=consistency_first,
            consistency_second=consistency_second,
            macro_capabilities=ds["macro_cap"],
            archetype_scores=arch_scores,
            archetype_scores_first=arch_scores_first,
            archetype_scores_second=arch_scores_second,
            phase_scores=phase_scores,
            phase_scores_first=phase_scores_first,
            phase_scores_second=phase_scores_second,
            state_scores=state_scores,
            worst_states=worst_states,
            best_states=best_states,
            missing_demands=top_missing,
            field_percentile=self._field_percentile(overall_score),
            dead_cards=ds["dead_cards"],
        )


def parse_ptcgl_decklist(text: str, db: StandardCardDatabase) -> dict[CompiledCard, int]:
    """Parse a standard PTCGL text decklist into {CompiledCard: count}."""
    deck: dict[CompiledCard, int] = defaultdict(int)
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or line.startswith("Pokémon:") or line.startswith("Trainer:") or line.startswith("Energy:") or line.startswith("Total Cards:"):
            continue
        # Match: <count> <Card Name> <SET> <NUM>
        m = re.match(r"^(\d+)\s+(.+?)\s+([A-Z0-9-]+)\s+(\d+[a-zA-Z]?)$", line)
        if m:
            cnt = int(m.group(1))
            name, sc, sn = m.group(2).strip(), m.group(3).strip(), m.group(4).strip()
            card = db.resolve_card(name, sc, sn)
            if card:
                deck[card] += cnt
        else:
            m2 = re.match(r"^(\d+)\s+(.+)$", line)
            if m2:
                cnt = int(m2.group(1))
                name = m2.group(2).strip()
                card = db.resolve_card(name)
                if card:
                    deck[card] += cnt
    return dict(deck)


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
    evaluator = StateSpaceEvaluator(db, scenarios)

    print("=== Evaluating Existing User Decks in `decks/` & Top Meta Decks ===")
    for dfile in sorted((root / "decks").glob("*.txt")):
        dmap = parse_ptcgl_decklist(dfile.read_text(encoding="utf-8"), db)
        rep = evaluator.evaluate_deck(dmap)
        print(f"  Deck {dfile.name:28s}: Score={rep.overall_score:5.2f}/100 | EstWinRate={rep.expected_win_rate*100:5.1f}% | Consistency={rep.consistency_score:5.1f}% | Legal={rep.is_legal}")
        if not rep.is_legal:
            print(f"    Issues: {rep.legality_issues}")
