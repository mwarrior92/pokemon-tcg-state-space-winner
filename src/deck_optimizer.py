"""
State-Guided Deck Discovery & Optimization Engine for Pokemon TCG Standard.
Given any Pokemon or Trainer card to build around, synthesizes diverse archetype
skeletons and optimizes the 60-card list directly against the 52 Prioritized
Competitive Board States using bottleneck-directed swaps.
"""
from __future__ import annotations

import copy
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from card_compiler import BASIC_ENERGY_MAP, MACRO_ACTIONS, CompiledCard, StandardCardDatabase
from state_evaluator import DeckEvaluationReport, StateSpaceEvaluator
from state_space import BoardStateScenario, build_competitive_state_space


@dataclass
class OptimizationResult:
    seed_card: CompiledCard
    archetype_style: str
    deck: dict[CompiledCard, int]
    report: DeckEvaluationReport
    iterations_evaluated: int
    score_history: list[float]


class StateGuidedDeckOptimizer:
    def __init__(self, db: StandardCardDatabase, evaluator: StateSpaceEvaluator):
        self.db = db
        self.evaluator = evaluator
        self.candidate_pool = self._build_candidate_pool()

    def _build_candidate_pool(self) -> dict[str, list[CompiledCard]]:
        """Index high-utility Standard tech & staple cards by Macro-Action for bottleneck-guided mutations."""
        pool: dict[str, list[CompiledCard]] = defaultdict(list)
        SUPPORT_POKEMON_TAGS = {
            "DRAW_ENGINE_POKEMON", "TUTOR_POKEMON", "ENERGY_ACCEL_POKEMON",
            "DAMAGE_MOVER", "BENCH_BARRIER", "FREE_RETREAT_AURA", "DRAGON_SLAYER",
        }
        for card in self.db.canonical_cards:
            if card.supertype == "Pokémon":
                if card.stage >= 1:
                    continue
                # For single-slot tech mutations, only consider proven universal utility Basics (meta rate >= 5%)
                if card.meta_play_rate < 0.05 or not (card.tags & SUPPORT_POKEMON_TAGS or card.name == "Budew"):
                    continue
            elif card.supertype == "Trainer":
                if card.name.startswith("Team Rocket's") and card.name not in ("Team Rocket's Petrel", "Team Rocket's Watchtower"):
                    continue
                if card.meta_play_rate < 0.008 and not card.is_ace_spec:
                    continue
            for act, val in card.action_vector.items():
                if val >= 0.45:
                    pool[act].append(card)

        for act in pool:
            pool[act].sort(
                key=lambda c: (c.meta_play_rate * 0.65 + c.action_vector.get(act, 0.0) * 0.35),
                reverse=True,
            )
        return dict(pool)

    def _add_card(
        self,
        deck: dict[CompiledCard, int],
        card: CompiledCard | None,
        count: int,
        protected_names: set[str] | None = None,
    ) -> int:
        """Safely add up to `count` copies of `card` respecting 60-card cap, 4-per-name, and 1 ACE SPEC."""
        if card is None or count <= 0:
            return 0
        current_total = sum(deck.values())
        if current_total >= 60:
            return 0

        if card.is_ace_spec:
            has_ace = sum(cnt for c, cnt in deck.items() if c.is_ace_spec and cnt > 0)
            if has_ace >= 1:
                return 0
            count = 1

        if "BASIC_ENERGY" not in card.tags:
            same_name_cnt = sum(cnt for c, cnt in deck.items() if c.name == card.name)
            avail_name = max(0, 4 - same_name_cnt)
            count = min(count, avail_name)

        to_add = min(count, 60 - current_total)
        if to_add > 0:
            deck[card] = deck.get(card, 0) + to_add
        return to_add

    def _add_evolution_line(
        self,
        deck: dict[CompiledCard, int],
        target_name: str,
        counts: tuple[int, ...] = (4, 3, 3),
        prefer_rare_candy: bool = False,
    ) -> list[CompiledCard]:
        """Add an entire evolution chain [Basic, (Stage 1), (Stage 2)] to `deck`."""
        chain = self.db.get_evolution_chain(target_name)
        added_cards = []
        for idx, nm in enumerate(chain):
            cc = self.db.resolve_card(nm)
            if not cc:
                continue
            c_num = counts[idx] if idx < len(counts) else 2
            self._add_card(deck, cc, c_num)
            added_cards.append(cc)
        if len(chain) == 3 and prefer_rare_candy:
            rc = self.db.resolve_card("Rare Candy")
            self._add_card(deck, rc, 3)
        return added_cards

    def _select_partner_for_trainer(self, trainer: CompiledCard) -> CompiledCard:
        """If the user seeds with a Trainer/Energy card, pick the most synergistic Pokemon attacker to pair with it."""
        rt = trainer.rules_text.lower()
        tname = trainer.name.lower()
        if "hide 'n' sneak" in rt or "gwynn" in tname:
            return self.db.resolve_card("Dhelmise", "PBL", "39") or self.db.resolve_card("Alakazam", "MEG", "56")
        if "grass" in rt or "vitality" in tname or "bug catching" in tname:
            return self.db.resolve_card("Hydrapple ex") or self.db.resolve_card("Dipplin", "TWM", "18")
        if "festival" in tname:
            return self.db.resolve_card("Dipplin", "TWM", "18")
        if "academy at night" in tname or "ciphermaniac" in tname:
            return self.db.resolve_card("Slowking", "SCR", "58")
        if "darkness" in rt or "janine" in tname or "dark bell" in tname:
            return self.db.resolve_card("Mega Darkrai ex") or self.db.resolve_card("N's Zoroark ex")
        if "stage 2" in rt or "dawn" in tname or "rare candy" in tname or "rosa" in tname:
            return self.db.resolve_card("Alakazam", "MEG", "56") or self.db.resolve_card("Dragapult ex")
        if "area zero" in tname or "crispin" in tname or "energy switch" in tname:
            return self.db.resolve_card("Mega Kangaskhan ex") or self.db.resolve_card("Raging Bolt ex")
        if "jumbo ice cream" in tname or "neutralization" in tname:
            return self.db.resolve_card("Crustle", "DRI", "12")
        return self.db.resolve_card("Dragapult ex") or self.db.resolve_card("Mega Kangaskhan ex")

    def _generate_initial_skeletons(self, seed_card: CompiledCard) -> list[tuple[str, dict[CompiledCard, int], set[str]]]:
        """
        Build 4 distinct, legal 60-card archetype skeletons around `seed_card`:
          1. High-Velocity Engine (Drakloak / Dudunsparce / Poffin / Poke Pad)
          2. Dusknoir / Munkidori Spread & Multi-Prize Control
          3. Turbo Tempo & Mobility (Teal Mask Ogerpon / Latias ex / Crispin / Switch)
          4. Disruption & Anti-Meta Tech (Budew / Shaymin / Watchtower / Hand Reset)
        """
        styles = [
            "High-Velocity Consistency Engine",
            "Spread & Counter Harvest (Dusknoir / Munkidori)",
            "Turbo Tempo & Aggressive Pivot",
            "Disruption & Anti-Meta Control",
        ]
        if seed_card.supertype == "Pokémon" and "DEVOLUTION_CONTROL" in seed_card.tags:
            styles.append("Fossil Devolution Lock (Ancient Wing + Judge)")
        skeletons: list[tuple[str, dict[CompiledCard, int], set[str]]] = []

        for style_idx, style_name in enumerate(styles):
            deck: dict[CompiledCard, int] = {}
            protected: set[str] = {seed_card.name}

            if seed_card.supertype == "Pokémon":
                primary_poke = seed_card
            else:
                # Add 4 copies of the seed Trainer/Energy (or 1 if ACE SPEC)
                self._add_card(deck, seed_card, 1 if seed_card.is_ace_spec else 4)
                primary_poke = self._select_partner_for_trainer(seed_card)
                protected.add(primary_poke.name)

            # 1. Add primary Pokemon evolution line
            chain = self.db.get_evolution_chain(primary_poke.name)
            for nm in chain:
                protected.add(nm)
            if len(chain) == 1:
                self._add_card(deck, primary_poke, 4)
            elif len(chain) == 2:
                b_card = self.db.resolve_card(chain[0])
                s1_card = primary_poke if primary_poke.stage == 1 else self.db.resolve_card(chain[1])
                self._add_card(deck, b_card, 4)
                self._add_card(deck, s1_card, 4 if not s1_card.is_rule_box else 3)
            else:
                b_card = self.db.resolve_card(chain[0])
                s1_card = self.db.resolve_card(chain[1])
                s2_card = primary_poke if primary_poke.stage == 2 else self.db.resolve_card(chain[2])
                self._add_card(deck, b_card, 4)
                # Check if Stage 1 has a strong draw ability (Drakloak, Kadabra)
                s1_draws = s1_card and "DRAW_ENGINE_POKEMON" in s1_card.tags
                self._add_card(deck, s1_card, 4 if s1_draws else (2 if style_idx == 2 else 3))
                self._add_card(deck, s2_card, 3)
                if not s1_draws or style_idx in (1, 2):
                    self._add_card(deck, self.db.resolve_card("Rare Candy"), 3 if s1_draws else 4)

            # 2. Add mandatory mechanical synergy packages for the primary attacker
            p_energy = primary_poke.primary_energy_type or (primary_poke.types[0] if primary_poke.types else "Colorless")
            needs_energy_count = 8
            if "DEVOLUTION_CONTROL" in primary_poke.tags:
                needs_energy_count = 10

            if "NEEDS_HIDE_N_SNEAK" in primary_poke.synergy_hooks:
                polt = self.db.resolve_card("Poltchageist", "PBL", "5")
                ban = self.db.resolve_card("Banette", "PBL", "34")
                gwynn = self.db.resolve_card("Gwynn", "PBL", "78")
                self._add_card(deck, polt, 4)
                self._add_card(deck, ban, 4)
                self._add_card(deck, gwynn, 4)
                if polt:
                    protected.add(polt.name)
                if ban:
                    protected.add(ban.name)
                if gwynn:
                    protected.add(gwynn.name)
                needs_energy_count = 7

            if "NEEDS_SWITCH_PIVOT" in primary_poke.synergy_hooks:
                self._add_card(deck, self.db.resolve_card("Switch"), 4)
                self._add_card(deck, self.db.resolve_card("Latias ex"), 2)
                self._add_card(deck, self.db.resolve_card("Air Balloon"), 2)
                self._add_card(deck, self.db.resolve_card("Jet Energy"), 3)
                needs_energy_count = 6

            if any("festival lead" in (ab.get("name") or "").lower() for ab in primary_poke.abilities):
                self._add_evolution_line(deck, "Thwackey", (4, 4))
                self._add_card(deck, self.db.resolve_card("Festival Grounds"), 4)
                self._add_card(deck, self.db.resolve_card("Bug Catching Set"), 4)
                self._add_card(deck, self.db.resolve_card("Brave Bangle") or self.db.resolve_card("Vitality Band"), 2)
                protected.update({"Grookey", "Thwackey", "Festival Grounds"})
                needs_energy_count = 6

            if "SCALES_HAND_SIZE" in primary_poke.synergy_hooks:
                self._add_evolution_line(deck, "Dudunsparce", (3, 3))
                self._add_card(deck, self.db.resolve_card("Dawn"), 4)
                self._add_card(deck, self.db.resolve_card("Hilda"), 3)
                self._add_card(deck, self.db.resolve_card("Telepathic Psychic Energy"), 4)
                needs_energy_count = 8

            if "SCALES_TOPDECK_ATTACK_COPY" in primary_poke.synergy_hooks:
                self._add_card(deck, self.db.resolve_card("Academy at Night"), 4)
                self._add_card(deck, self.db.resolve_card("Ciphermaniac's Codebreaking"), 4)
                self._add_card(deck, self.db.resolve_card("Kyurem", "SFA", "47"), 2)
                self._add_card(deck, self.db.resolve_card("Regigigas", "PRE", "86") or self.db.resolve_card("Conkeldurr", "TWM", "105"), 2)
                self._add_card(deck, self.db.resolve_card("Annihilape", "SSP", "100") or self.db.resolve_card("Metagross", "TEF", "115"), 2)
                self._add_card(deck, self.db.resolve_card("Telepathic Psychic Energy"), 4)
                protected.add("Academy at Night")
                needs_energy_count = 6

            if "SCALES_BENCH_ATTACK_COPY" in primary_poke.synergy_hooks or primary_poke.name.startswith("N's "):
                self._add_evolution_line(deck, "N's Darmanitan", (2, 2))
                self._add_card(deck, self.db.resolve_card("N's Reshiram"), 2)
                self._add_card(deck, self.db.resolve_card("N's PP Up"), 4)
                needs_energy_count = 8

            if "IMMUNITY_WALL" in primary_poke.tags:
                self._add_card(deck, self.db.resolve_card("Mega Kangaskhan ex"), 3)
                self._add_card(deck, self.db.resolve_card("Jumbo Ice Cream"), 4)
                self._add_card(deck, self.db.resolve_card("Hero's Cape"), 1)
                self._add_card(deck, self.db.resolve_card("Mist Energy"), 3)
                self._add_card(deck, self.db.resolve_card("Spiky Energy"), 3)
                if "Grass" in primary_poke.types:
                    self._add_card(deck, self.db.resolve_card("Growing Grass Energy"), 4)
                needs_energy_count = 6

            if "Grass" in primary_poke.types and primary_poke.stage >= 1 and "Festival Grounds" not in protected:
                self._add_card(deck, self.db.resolve_card("Teal Mask Ogerpon ex"), 3)
                self._add_card(deck, self.db.resolve_card("Bug Catching Set"), 4)
                self._add_card(deck, self.db.resolve_card("Forest of Vitality"), 3)
                protected.update({"Teal Mask Ogerpon ex", "Bug Catching Set", "Forest of Vitality"})
                if primary_poke.stage == 2:
                    self._add_evolution_line(deck, "Meganium", (2, 1, 2))
                    protected.update({"Chikorita", "Bayleef", "Meganium"})
                needs_energy_count = 11

            if "Metal" in primary_poke.types and max((a.converted_cost for a in primary_poke.attacks), default=0) >= 3:
                self._add_evolution_line(deck, "Metang", (3, 3))
                needs_energy_count = 13

            if "Darkness" in primary_poke.types and max((a.converted_cost for a in primary_poke.attacks), default=0) >= 2 and not primary_poke.name.startswith("N's "):
                self._add_card(deck, self.db.resolve_card("Janine's Secret Art"), 4)
                self._add_card(deck, self.db.resolve_card("Pecharunt ex"), 2)
                needs_energy_count = 10

            if "SCALES_ENERGY_COUNT" in primary_poke.synergy_hooks and "Grass" not in primary_poke.types:
                self._add_card(deck, self.db.resolve_card("Teal Mask Ogerpon ex"), 3)
                self._add_card(deck, self.db.resolve_card("Crispin"), 4)
                self._add_card(deck, self.db.resolve_card("Energy Switch"), 4)
                needs_energy_count = 11

            # 3. Reserve and add Required Energy Cards BEFORE secondary engines/staples so energy count is guaranteed!
            if p_energy == "Psychic" and "Telepathic Psychic Energy" not in {c.name for c in deck}:
                self._add_card(deck, self.db.resolve_card("Telepathic Psychic Energy"), 3)
            current_energy = sum(cnt for c, cnt in deck.items() if c.supertype == "Energy")
            if current_energy < needs_energy_count:
                et_fill = p_energy if p_energy in BASIC_ENERGY_MAP else "Grass"
                sc, sn, ename = BASIC_ENERGY_MAP[et_fill]
                ecard = self.db.resolve_card(ename, sc, sn)
                self._add_card(deck, ecard, needs_energy_count - current_energy)

            # 4. Add Style-Specific Secondary Engine
            if style_idx == 0:
                # Style 0: High-Velocity Consistency Engine
                if "DEVOLUTION_CONTROL" in primary_poke.tags:
                    # Solrock / Lunatone: 1-Prize Fighting backup + discard-energy draw engine.
                    self._add_card(deck, self.db.resolve_card("Solrock"), 2)
                    self._add_card(deck, self.db.resolve_card("Lunatone"), 1)
                elif sum(c.stage >= 1 for c in deck) == 0 and primary_poke.is_rule_box:
                    # Basic Box style
                    self._add_card(deck, self.db.resolve_card("Mega Kangaskhan ex"), 2)
                    self._add_card(deck, self.db.resolve_card("Teal Mask Ogerpon ex"), 2)
                    self._add_card(deck, self.db.resolve_card("Latias ex"), 2)
                    self._add_card(deck, self.db.resolve_card("Area Zero Underdepths"), 3)
                    self._add_card(deck, self.db.resolve_card("Crispin"), 3)
                elif "Dudunsparce" not in {c.name for c in deck} and "Drakloak" not in {c.name for c in deck} and "Thwackey" not in {c.name for c in deck}:
                    self._add_evolution_line(deck, "Dudunsparce", (2, 2))
            elif style_idx == 1:
                # Style 1: Dusknoir / Munkidori Spread & Wall-Break
                if "Dusknoir" not in {c.name for c in deck}:
                    self._add_evolution_line(deck, "Dusknoir", (2, 1, 2), prefer_rare_candy=True)
                self._add_card(deck, self.db.resolve_card("Munkidori"), 2)
                sc_d, sn_d, ename_d = BASIC_ENERGY_MAP["Darkness"]
                self._add_card(deck, self.db.resolve_card(ename_d, sc_d, sn_d), 2)
            elif style_idx == 2:
                # Style 2: Turbo Tempo & Mobility
                self._add_card(deck, self.db.resolve_card("Latias ex"), 1)
                self._add_card(deck, self.db.resolve_card("Meowth ex"), 2)
                self._add_card(deck, self.db.resolve_card("Prime Catcher") or self.db.resolve_card("Secret Box"), 1)
                self._add_card(deck, self.db.resolve_card("Switch"), 2)
                if p_energy in ("Fire", "Psychic", "Lightning", "Fighting", "Water", "Grass"):
                    self._add_card(deck, self.db.resolve_card("Crispin"), 2)
            elif style_idx == 3:
                # Style 3: Disruption & Anti-Meta Control
                self._add_card(deck, self.db.resolve_card("Budew"), 2)
                self._add_card(deck, self.db.resolve_card("Shaymin", "DRI", "10"), 1)
                self._add_card(deck, self.db.resolve_card("Battle Cage"), 2)
                self._add_card(deck, self.db.resolve_card("Munkidori"), 2)
                sc_d, sn_d, ename_d = BASIC_ENERGY_MAP["Darkness"]
                self._add_card(deck, self.db.resolve_card(ename_d, sc_d, sn_d), 2)
                self._add_card(deck, self.db.resolve_card("Unfair Stamp"), 1)
                self._add_card(deck, self.db.resolve_card("Judge"), 2)
                self._add_card(deck, self.db.resolve_card("Special Red Card"), 1)
            elif style_idx == 4:
                # Style 4: Fossil Devolution Lock (Archeops Ancient Wing + hand shuffle)
                self._add_card(deck, self.db.resolve_card("Premium Power Pro"), 3)
                self._add_card(deck, self.db.resolve_card("Brave Bangle"), 2)
                self._add_card(deck, self.db.resolve_card("Fighting Gong"), 2)
                self._add_card(deck, self.db.resolve_card("Team Rocket's Petrel"), 2)
                self._add_card(deck, self.db.resolve_card("Ciphermaniac's Codebreaking"), 2)
                self._add_card(deck, self.db.resolve_card("Judge"), 3)
                self._add_card(deck, self.db.resolve_card("Solrock"), 1)
                self._add_card(deck, self.db.resolve_card("Lunatone"), 1)
                self._add_card(deck, self.db.resolve_card("Shaymin", "DRI", "10"), 1)
                self._add_card(deck, self.db.resolve_card("Battle Cage"), 2)
                self._add_card(deck, self.db.resolve_card("Hero's Cape"), 1)
                protected.update({
                    "Antique Plume Fossil", "Archen", "Archeops", "Rare Candy",
                    "Team Rocket's Petrel", "Ciphermaniac's Codebreaking",
                    "Premium Power Pro", "Brave Bangle", "Judge", "Battle Cage",
                })

            # 5. Add Universal Competitive Staples (Balls, Draw Supporters, Gust, Recovery, ACE SPEC)
            self._add_card(deck, self.db.resolve_card("Lillie's Determination"), 4)
            self._add_card(deck, self.db.resolve_card("Boss's Orders"), 3)
            self._add_card(deck, self.db.resolve_card("Ultra Ball"), 4)
            has_non_rule_box = any(not c.is_rule_box and c.supertype == "Pokémon" for c in deck)
            if has_non_rule_box:
                self._add_card(deck, self.db.resolve_card("Poké Pad"), 4)
            has_poffin_targets = sum(cnt for c, cnt in deck.items() if c.supertype == "Pokémon" and c.stage == 0 and c.hp <= 70) >= 3
            if has_poffin_targets:
                self._add_card(deck, self.db.resolve_card("Buddy-Buddy Poffin"), 4)

            self._add_card(deck, self.db.resolve_card("Night Stretcher"), 2)
            self._add_card(deck, self.db.resolve_card("Fezandipiti ex"), 1)
            self._add_card(deck, self.db.resolve_card("Meowth ex"), 1)

            # Ensure a non-ex Wall Breaker is present to beat Crustle states!
            has_wall_breaker = any("WALL_BREAKER_ATTACKER" in c.tags for c in deck)
            if not has_wall_breaker and sum(cnt for c, cnt in deck.items() if c.primary_energy_type == "Darkness") >= 2:
                wb = self.db.resolve_card("Munkidori")
                self._add_card(deck, wb, 2)

            # Add ACE SPEC if none present yet
            if not any(c.is_ace_spec for c in deck):
                ace = self.db.resolve_card("Unfair Stamp") or self.db.resolve_card("Prime Catcher") or self.db.resolve_card("Secret Box")
                self._add_card(deck, ace, 1)

            # 6. Pad remaining slots to exactly 60 with high-utility trainers
            fillers = [
                "Dawn", "Judge", "Special Red Card", "Switch", "Air Balloon",
                "Ciphermaniac's Codebreaking", "Night Stretcher", "Pokégear 3.0",
                "Team Rocket's Watchtower", "Risky Ruins", "Lillie's Clefairy ex",
                "Battle Cage", "Budew", "Boss's Orders", "Ultra Ball", "Poké Pad",
            ]
            for fnm in fillers:
                if sum(deck.values()) >= 60:
                    break
                fc = self.db.resolve_card(fnm)
                self._add_card(deck, fc, 1)

            # Final fallback pad with primary basic energy if still < 60
            if sum(deck.values()) < 60:
                et_fill = p_energy if p_energy in BASIC_ENERGY_MAP else "Psychic"
                sc, sn, ename = BASIC_ENERGY_MAP[et_fill]
                ecard = self.db.resolve_card(ename, sc, sn)
                self._add_card(deck, ecard, 60 - sum(deck.values()))

            skeletons.append((style_name, deck, protected))

        return skeletons

    def optimize_deck(self, seed_query: str, max_iterations: int = 80) -> OptimizationResult:
        """
        Discover and optimize the best 60-card deck built around `seed_query`
        by testing against the 52 Prioritized Competitive Board States.
        """
        seed_card = self.db.resolve_card(seed_query)
        if not seed_card:
            raise ValueError(f"Could not find card matching '{seed_query}' in Standard rotation database.")

        skeletons = self._generate_initial_skeletons(seed_card)

        best_style = ""
        best_deck: dict[CompiledCard, int] = {}
        best_report: DeckEvaluationReport | None = None
        best_protected: set[str] = set()
        eval_count = 0

        # Evaluate all initial skeletons and refine the top ones
        refined_candidates: list[OptimizationResult] = []

        for style_name, init_deck, protected in skeletons:
            curr_deck = dict(init_deck)
            curr_rep = self.evaluator.evaluate_deck(curr_deck)
            eval_count += 1
            history = [curr_rep.overall_score]

            # Bottleneck-guided iterative hill climbing
            for _ in range(max_iterations // len(skeletons)):
                if not curr_rep.missing_demands:
                    break
                # Identify top 3 bottleneck macro-actions
                top_actions = list(curr_rep.missing_demands.keys())[:3]

                # Find removable non-protected cards with lowest marginal contribution
                staple_floors = {
                    "Lillie's Determination": 3,
                    "Ultra Ball": 3,
                    "Boss's Orders": 2,
                    "Poké Pad": 2,
                    "Buddy-Buddy Poffin": 2,
                    # Stage 2 decks (especially fossil lines) must keep enough Rare Candy
                    # to bridge Basic -> Stage 2 without relying on the fragile Stage 1.
                    "Rare Candy": 3,
                }
                removable = [
                    c for c, cnt in curr_deck.items()
                    if cnt > staple_floors.get(c.name, 0)
                    and c.name not in protected
                    and not (c.supertype == "Pokémon" and c.stage >= 1)
                    and not (c.supertype == "Pokémon" and any(c2.evolves_from == c.name for c2 in curr_deck))
                ]
                if not removable:
                    break

                deck_energies = {
                    c.primary_energy_type for c, cnt in curr_deck.items()
                    if cnt > 0 and c.supertype == "Energy" and c.primary_energy_type
                }

                improved = False
                for act in top_actions:
                    cands_in = self.candidate_pool.get(act, [])[:12]
                    for card_in in cands_in:
                        # Filter out cards whose colored energy or attack-damage requirements don't match the deck
                        if card_in.supertype == "Pokémon":
                            if "DAMAGE_MOVER" in card_in.tags and "Darkness" not in deck_energies:
                                continue
                            if card_in.attacks:
                                reqs = set()
                                for a in card_in.attacks:
                                    reqs.update(a.colored_cost.keys())
                                if reqs and not reqs.issubset(deck_energies) and "ENERGY_ACCEL_POKEMON" not in card_in.tags:
                                    continue
                        # Check 4-copy and ACE SPEC constraints before trying swap
                        if card_in.is_ace_spec and any(c.is_ace_spec and cnt > 0 for c, cnt in curr_deck.items()):
                            continue
                        if "BASIC_ENERGY" not in card_in.tags:
                            curr_name_cnt = sum(cnt for c, cnt in curr_deck.items() if c.name == card_in.name)
                            max_allowed = 4
                            if card_in.supertype == "Pokémon" and card_in.name not in protected:
                                max_allowed = 1 if card_in.is_rule_box else 2
                            if curr_name_cnt >= max_allowed:
                                continue

                        for card_out in removable:
                            if card_out.uid == card_in.uid:
                                continue
                            # Don't drop below minimum energy count or required typed energy
                            if card_out.supertype == "Energy":
                                if sum(cnt for c, cnt in curr_deck.items() if c.supertype == "Energy") <= 7:
                                    continue
                                if card_out.primary_energy_type == "Darkness" and any(c.name == "Munkidori" for c in curr_deck):
                                    if sum(cnt for c, cnt in curr_deck.items() if c.primary_energy_type == "Darkness") <= 2:
                                        continue
                                if "BASIC_ENERGY" in card_out.tags and sum(cnt for c, cnt in curr_deck.items() if "BASIC_ENERGY" in c.tags) <= 3:
                                    continue

                            trial = dict(curr_deck)
                            trial[card_out] -= 1
                            if trial[card_out] <= 0:
                                del trial[card_out]
                            trial[card_in] = trial.get(card_in, 0) + 1

                            t_rep = self.evaluator.evaluate_deck(trial)
                            eval_count += 1
                            if t_rep.is_legal and t_rep.overall_score > curr_rep.overall_score + 0.02:
                                curr_deck = trial
                                curr_rep = t_rep
                                history.append(curr_rep.overall_score)
                                improved = True
                                break
                        if improved:
                            break
                    if improved:
                        break
                if not improved:
                    break

            refined_candidates.append(
                OptimizationResult(
                    seed_card=seed_card,
                    archetype_style=style_name,
                    deck=curr_deck,
                    report=curr_rep,
                    iterations_evaluated=eval_count,
                    score_history=history,
                )
            )

        refined_candidates.sort(key=lambda r: r.report.overall_score, reverse=True)
        winner = refined_candidates[0]
        winner.iterations_evaluated = eval_count
        return winner


def format_ptcgl_decklist(deck: dict[CompiledCard, int], header_comment: str | None = None) -> str:
    """Format a {CompiledCard: count} dictionary into standard PTCGL export format."""
    pokes = sorted([(c, cnt) for c, cnt in deck.items() if cnt > 0 and c.supertype == "Pokémon"], key=lambda x: (-x[1], x[0].stage, x[0].name))
    trainers = sorted([(c, cnt) for c, cnt in deck.items() if cnt > 0 and c.supertype == "Trainer"], key=lambda x: (-x[1], x[0].name))
    energies = sorted([(c, cnt) for c, cnt in deck.items() if cnt > 0 and c.supertype == "Energy"], key=lambda x: (-x[1], x[0].name))

    lines = []
    if header_comment:
        for hl in header_comment.splitlines():
            lines.append(f"# {hl}")
        lines.append("")

    lines.append(f"Pokémon: {sum(cnt for _, cnt in pokes)}")
    for c, cnt in pokes:
        lines.append(f"{cnt} {c.name} {c.set_code} {c.set_num}")
    lines.append("")

    lines.append(f"Trainer: {sum(cnt for _, cnt in trainers)}")
    for c, cnt in trainers:
        lines.append(f"{cnt} {c.name} {c.set_code} {c.set_num}")
    lines.append("")

    lines.append(f"Energy: {sum(cnt for _, cnt in energies)}")
    for c, cnt in energies:
        lines.append(f"{cnt} {c.name} {c.set_code} {c.set_num}")
    lines.append("")
    lines.append(f"Total Cards: {sum(deck.values())}")
    return "\n".join(lines)


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
    optimizer = StateGuidedDeckOptimizer(db, evaluator)

    for seed in ["Dhelmise", "Alakazam", "Mega Lopunny ex", "Dawn"]:
        res = optimizer.optimize_deck(seed)
        print(f"\n=== Discovered Deck for Seed: {res.seed_card.name} ({res.seed_card.uid}) ===")
        print(f"Style: {res.archetype_style} | Score: {res.report.overall_score}/100 | Est Meta Win Rate: {res.report.expected_win_rate*100:.1f}% | Evals: {res.iterations_evaluated}")
        print(f"Score progression: {res.score_history[0]} -> {res.score_history[-1]}")
