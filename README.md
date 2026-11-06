# Pokémon TCG Standard — Finite State-Space & Macro-Action Deck Discovery Engine

A chess-like **finite board-state ($S$) and macro-action ($A$) abstraction** for Pokémon TCG Standard (`G`/`H`/`I`/`J` / 2026 rotation), calibrated from competitive turn-by-turn match telemetry and 512 tournament decklists.

Instead of training a card-playing AI or running slow Monte Carlo game simulations, this engine compiles all **3,108 Standard printings (2,062 canonical cards)** into 16-dimensional mechanical capability vectors and evaluates any 60-card deck against the **52 highest-probability competitive board states** in **~2 ms per deck** using exact hypergeometric reachability, sub-additive role saturation, and prize-trade tempo math.

---

## Quick Start (CLI Commands)

> **Environment Note (Windows):** If `python` is not on your default PATH, invoke Anaconda Python directly (`& C:\Users\marcw\anaconda3\python.exe ...`) or activate your conda environment first.

```powershell
# 1. Discover & optimize a 60-card deck around ANY Pokémon or Trainer card
python discover_deck.py --build "Archeops"
python discover_deck.py --build "Archeops" --save decks/discovered_archeops_ancient_wing.txt
python discover_deck.py --build "Alakazam" --save decks/discovered_alakazam_hand.txt
python discover_deck.py --build "Dawn" --save decks/discovered_dawn_stage2_engine.txt

# 2. Evaluate an existing PTCGL decklist file (includes Going First vs. Going Second split)
python discover_deck.py --evaluate decks/discovered_archeops_ancient_wing.txt
python discover_deck.py --evaluate decks/raging_bolt_fortress.txt

# 3. Inspect the 52 prioritized competitive board states and 6-axis taxonomy
python discover_deck.py --states

# 4. Run the full multi-seed benchmark & re-export meta/competitive_board_states.json
python discover_deck.py --demo

# 5. Re-parse raw turn-by-turn match logs in matches/ into matches/parsed_turn_trajectories.json
python matches/parse_matches.py
```

---

## Repository Directory & File Schema

```text
winner/
├── discover_deck.py                     # Main CLI entry point (--build, --evaluate, --states, --demo)
├── README.md                            # System architecture, data schemas, and AI handover guide
├── src/
│   ├── card_compiler.py                 # Compiles 3,108 raw card JSONs -> CompiledCard + 16-action vectors
│   ├── state_space.py                   # Defines the 6-axis state space (S) & builds the 52 meta states
│   ├── state_evaluator.py               # Hypergeometric + prize-tempo evaluator (First vs. Second split)
│   └── deck_optimizer.py                # Synthesizes 4-5 archetype skeletons & hill-climbs 60-card lists
├── pokemon-tcg-data-standard/
│   ├── sets.json                        # Set metadata and PTCGL set-code mappings
│   └── cards/*.json                     # 22 Standard set JSON files (3,108 card printings)
├── meta/
│   ├── decklists_2026-09-19_to_10-31.json # 512 competitive tournament decklists (archetype weights & card priors)
│   └── competitive_board_states.json    # Exported 52 canonical board states + taxonomy schema
├── matches/
│   ├── parse_matches.py                 # Turn-by-turn replay & log parser
│   ├── parsed_turn_trajectories.json    # Empirical turn cadence, win conditions, first/second splits
│   ├── cabt_*.json                      # Full-state turn-by-turn JSON match replays (CABT format)
│   ├── ptcgl_*.txt                      # Raw PTCGL text match logs
│   └── hf_500_games_turn_by_turn.csv    # 500-game turn-by-turn telemetry dataset
└── decks/
    ├── discovered_archeops_ancient_wing.txt
    ├── discovered_alakazam_hand.txt
    ├── discovered_dawn_stage2_engine.txt
    ├── discovered_dhelmise_anchor.txt
    ├── discovered_hydrapple_vitality.txt
    ├── discovered_mega_lopunny.txt
    └── *.txt                            # User & baseline PTCGL decklists
```

---

## Architecture & Mathematical Schema

### 1. Universal Card Compiler (`src/card_compiler.py`)
Loads every card from `pokemon-tcg-data-standard/cards/*.json`, maps set IDs to official PTCGL set codes, deduplicates alternate-art printings into canonical cards (`StandardCardDatabase.canonical_cards`), builds evolution chains (`evolves_from_map`, `evolves_to_map`), and compiles each card into a `CompiledCard` dataclass.

#### Set ID $\leftrightarrow$ PTCGL Code Mapping (`SET_ID_TO_PTCGL`)
| JSON File (`id`) | PTCGL Code | JSON File (`id`) | PTCGL Code | JSON File (`id`) | PTCGL Code |
|---|---|---|---|---|---|
| `me1` | `MEG` | `rsv10pt5` | `WHT` | `sv6pt5` | `SFA` |
| `me2` | `PFL` | `zsv10pt5` | `BLK` | `sv7` | `SCR` |
| `me2pt5` | `ASC` | `sv1` | `SVI` | `sv8` | `SSP` |
| `me3` | `POR` | `sv2` | `PAL` | `sv8pt5` | `PRE` |
| `me4` | `CRI` | `sv3pt5` | `MEW` | `sv9` | `JTG` |
| `me5` | `PBL` | `sv5` | `TEF` | `sv10` | `DRI` |
| `me55` | `30C` | `sv6` | `TWM` | `sve` / `svp` | `MEE` / `PR-SV` |

#### The 16 Canonical Macro-Actions (`MACRO_ACTIONS`)
Every card is projected into a 16-dimensional capability vector $\mathbf{a}(c) \in [0, 1]^{16}$:

| Index | Macro-Action | Mechanical Meaning & Representative Cards |
|---|---|---|
| `0` | `SETUP_BASIC` | Deploy Basic Pokémon to bench/active (`Buddy-Buddy Poffin`, `Ultra Ball`, `Antique Plume Fossil`, Basic Pokémon) |
| `1` | `EVOLVE_LINE` | Evolve Stage 1/2 or skip stages (`Rare Candy`, `Dawn`, `Hilda`, `Forest of Vitality`) |
| `2` | `DRAW_REFRESH` | Hand refresh & draw velocity (`Lillie's Determination`, `Fezandipiti ex`, `Dudunsparce`, `Lunatone`) |
| `3` | `TUTOR_SEARCH` | Targeted deck search (`Poké Pad`, `Ultra Ball`, `Team Rocket's Petrel`, `Ciphermaniac's Codebreaking`) |
| `4` | `ACCEL_ENERGY` | Extra energy attachment beyond 1/turn (`Crispin`, `Teal Mask Ogerpon ex`, `Blaziken ex`, `Metang`) |
| `5` | `STRIKE_LIGHT` | Efficient low-cost attack ($\le 130$ dmg, 1–2 energy: `Solrock`, `Archeops`, `Budew`) |
| `6` | `STRIKE_MID` | Medium 2-shot / single-prize KO attack ($130\text{–}230$ dmg: `Dhelmise`, `Dragapult ex`) |
| `7` | `STRIKE_HEAVY` | Heavy OHKO attack ($240\text{–}350+$ dmg or damage boosts: `Alakazam`, `Raging Bolt ex`, `Premium Power Pro`, `Brave Bangle`) |
| `8` | `SPREAD_BENCH` | Bench snipe & damage counter placement/movement (`Munkidori`, `Dusknoir`, `Dragapult ex`) |
| `9` | `GUST_TARGET` | Force opponent bench to Active (`Boss's Orders`, `Prime Catcher`, `Hariyama`) |
| `10` | `DISRUPT_HAND` | Hand reset / energy denial (`Judge`, `Unfair Stamp`, `Special Red Card`, `Crushing Hammer`) |
| `11` | `LOCK_STALL` | Item lock, Ability lock, Devolution, or Stadium control (`Budew`, `Archeops`, `Team Rocket's Watchtower`, `Battle Cage`) |
| `12` | `WALL_BREAKER` | Bypass immunity walls via Shred or strong non-Rule-Box attacks (`Alakazam`, `Archeops`, `Dhelmise`, `Crustle` counters) |
| `13` | `MOBILITY_PIVOT` | Switch active / reduce retreat cost (`Latias ex`, `Switch`, `Air Balloon`, `Prime Catcher`) |
| `14` | `RECOVER_CYCLE` | Recover Pokémon/Energy from discard or prevent deck-out (`Night Stretcher`, `Sacred Ash`) |
| `15` | `TANK_SURVIVE` | HP buffs, damage reduction, healing, or bench shields (`Hero's Cape`, `Battle Cage`, `Jumbo Ice Cream`, `Shaymin`) |

---

### 2. Factored Board-State Space (`src/state_space.py`)
The full game state is factored into a 6-axis discrete grid $|S| = 4 \times 5 \times 5 \times 4 \times 5 \times 4 = 8,000$ theoretical coordinates, then concentrated onto the **52 highest-probability competitive states** (12 meta archetype families $\times$ 4 game phases + 4 specialized states), weighted by tournament meta share (`meta/decklists_2026-09-19_to_10-31.json`) and empirical phase criticality (`matches/parsed_turn_trajectories.json`):

1. **`PHASE_WINDOWS` (4)**:
   - `T1_OPENING` (weight `0.22`): Turn 1 (Plies 1–2) — Basic deployment, T1 Going-Second `Budew` item lock or turbo energy attachment.
   - `T2_FIRST_STRIKE` (weight `0.26`): Turn 2 (Plies 3–4) — First evolutions online, first strike / early spread.
   - `T3_4_MIDGAME_TRADE` (weight `0.32`): Turns 3–4 (Plies 5–8) — Full engine online, multi-prize trades, gust KOs, hand disruption.
   - `T5_PLUS_ENDGAME` (weight `0.20`): Turns 5+ (Plies 9+) — Late checkmate race, low-hand disruption (`Judge`/`Unfair Stamp`), recovery, or deck-out.
2. **`ACTIVE_TIERS` (5)**: `SP_FRAGILE` ($\le 90$ HP, 1-Prize), `SP_ATTACKER` ($110\text{–}170$ HP, 1-Prize), `EX_BASIC` ($190\text{–}240$ HP, 2-Prize), `EX_STAGE2` ($260\text{–}340$ HP, 2-Prize), `MEGA_TANK` ($300\text{–}380+$ HP, 3-Prize).
3. **`PRESSURE_MODES` (5)**: `PASSIVE_SETUP`, `CHIP_LOCK`, `TWO_SHOT_PRESSURE`, `BURST_OHKO`, `SPREAD_HARVEST`.
4. **`BENCH_STRUCTURES` (4)**: `SPARSE`, `ENGINE_EXPOSED`, `SHIELDED_ENGINE`, `TWO_PRIZE_LIABILITIES`.
5. **`LOCK_CONDITIONS` (5)**: `OPEN_PLAY`, `ITEM_LOCK`, `ABILITY_LOCK`, `EX_IMMUNITY_WALL`, `HAND_DISRUPTED`.
6. **`PRIZE_CONTEXTS` (4)**: `EVEN_START`, `AHEAD_TEMPO`, `BEHIND_COMEBACK`, `CHECKMATE_RACE`.

Each `BoardStateScenario` in `src/state_space.py` carries quantitative combat parameters:
- `opp_active_hp`, `opp_active_prizes`, `opp_active_is_ex`, `opp_active_stage` (`0`/`1`/`2`), `opp_active_weakness`
- `opp_incoming_active_dmg`, `opp_incoming_bench_spread`, `opp_bench_spread_is_counters` (`True` for damage counters like *Phantom Dive* / *Cursed Blast*; `False` for bench attack damage like *Trifrost* / *Flamebody Cannon*)
- `opp_bench_lowest_hp`, `opp_bench_gust_prizes`, `opp_bench_gust_hp`, `opp_energy_denial_rate`
- `action_demands: dict[str, float]` (target importance weights over `MACRO_ACTIONS`).

---

### 3. State-Space Deck Evaluator (`src/state_evaluator.py`)
Given a 60-card deck $D$, `StateSpaceEvaluator.evaluate_deck(deck)` runs in ~2 ms and computes:

1. **Standard Legality Check (`check_legality`)**:
   - Exactly 60 cards, $\le 4$ copies per card name (except Basic Energy), $\le 1$ `ACE SPEC`, at least 1 Basic Pokémon (including Restored-Pokémon fossils tagged `FOSSIL_BASIC`), and valid pre-evolutions or `Rare Candy` bridges for every Stage 1/2.
2. **Hypergeometric Setup & Seat-Split Reachability (`_analyze_deck_structure`)**:
   - Models the official Pokémon TCG Turn 1 rule asymmetry:
     - **Going First (Player 1)**: Cannot play a Supporter on Turn 1 and cannot attack on Turn 1, but evolves first on Turn 2.
     - **Going Second (Player 2)**: Can play a Supporter on Turn 1 (search/draw) and can use 0–1 energy Basic attacks (`Budew` *Itchy Pollen*, `Solrock`, turbo `Crispin` attackers) on Turn 1.
   - Computes exact hypergeometric probabilities for opening a Basic (`p_open_basic`), deploying 2+ Basics on Turn 1 (`p_two_basics_t1_first` vs `p_two_basics_t1_second`), hitting draw engines by Turn 2, and assembling each attacker's evolution line + energy requirements by phase (`line_prob`, `en_prob`).
3. **Prize-Trade Combat & Special Mechanics (`_score_single_state`)**:
   - Evaluates expected turns-to-KO (`turns_to_ko_opp`) vs. opponent turns-to-KO-us (`turns_opp_kos_us`), accounting for Weakness, single-prize vs. multi-prize liability, gust KOs, and bench spread survival.
   - **Critical Mechanical Rules Enforced**:
     - **Damage Modifiers vs. Damage Counters**: Tools/Items that boost attack *damage* (`Maximum Belt`, `Brave Bangle`, `Premium Power Pro`, `Vitality Band`) **only** apply to direct-damage attacks (`not atk.is_damage_counter_effect`); they give zero boost to effect/counter attackers like `Alakazam` (*Powerful Hand*) and are flagged as dead cards if the deck lacks a qualifying attacker.
     - **Bench Attack Damage vs. Bench Damage Counters**:
       - `Shaymin (DRI 10, Flower Curtain)` (`BENCH_DAMAGE_BARRIER`) only blocks *attack damage* to Benched non-Rule-Box Pokémon (`opp_bench_spread_is_counters == False`: Slowking *Trifrost*, N's Zoroark *Flamebody Cannon*). It does **not** stack (copies $>1$ are penalized as dead cards) and does **not** block damage counters.
       - `Battle Cage (PFL 85)` and `Rabsca (TEF 24)` (`BENCH_COUNTER_BARRIER`) block *damage counters* placed on Benched Pokémon (`opp_bench_spread_is_counters == True`: Dragapult ex *Phantom Dive*, Dusknoir *Cursed Blast*, Munkidori *Adrena-Brain*).
     - **Restored-Pokémon Fossils (`Antique Plume Fossil -> Archen -> Archeops`)**:
       - Upstream data typo `"Antiuqe Plume Fossil"` on `Archen (WHT 50)` is normalized via `EVOLVES_FROM_ALIASES` in `src/card_compiler.py`.
       - Fossils are Trainer Items in deck (`FOSSIL_BASIC`), so Pokémon-only ball tutors (`Poké Pad`, `Ultra Ball`, `Buddy-Buddy Poffin`, `Fighting Gong`) **cannot** search them; only Trainer/any-card tutors (`Team Rocket's Petrel`, `Ciphermaniac's Codebreaking`, `Secret Box`) contribute to fossil reachability (`fossil_tutors`).
     - **Devolution Control (`Archeops WHT 51, Ancient Wing`)**:
       - Tagged `DEVOLUTION_CONTROL`. Against evolved Active targets (`s.opp_active_stage >= 1`), `Ancient Wing` strips the highest Stage before attacking, reducing the target to its pre-evolution HP/1-Prize body and adding tempo delay (`+0.35` to `+0.50` turns when paired with `Judge`/`Unfair Stamp` hand disruption).

---

### 4. Bottleneck-Guided Deck Optimizer (`src/deck_optimizer.py`)
When `discover_deck.py --build "<Card Name>"` is run:
1. Resolves the seed card (Pokémon or Trainer) and constructs **4–5 archetype skeletons**:
   - Style 0: *High-Velocity Consistency Engine*
   - Style 1: *Spread & Counter Harvest (Dusknoir / Munkidori)*
   - Style 2: *Turbo Tempo & Aggressive Pivot*
   - Style 3: *Disruption & Anti-Meta Control*
   - Style 4 (when seed has `DEVOLUTION_CONTROL`): *Fossil Devolution Lock (Ancient Wing + Judge)*
2. Runs **bottleneck-directed hill-climbing**:
   - Identifies the worst-performing high-weight board states in `rep.worst_states` and the highest-deficit macro-actions in `rep.bottleneck_actions`.
   - Proposes legal 1-for-1 card swaps from `self.candidate_pool` while protecting core evolution lines and staple floors (`Lillie's Determination`, `Rare Candy`, `Poké Pad`, `Boss's Orders`).
   - Evaluates thousands of candidate 60-card decks across all 52 states in a few seconds and returns the highest-scoring legal list.

---

## Guide for Future AI Agents / Developers

If you are an AI agent stepping into this repository to build a new deck, tune the evaluator, or add new cards:

1. **Using Python Programmatically**:
   ```python
   import sys
   from pathlib import Path
   sys.path.insert(0, "src")

   from card_compiler import StandardCardDatabase
   from state_space import build_competitive_state_space
   from state_evaluator import StateSpaceEvaluator, parse_ptcgl_decklist
   from deck_optimizer import StateGuidedDeckOptimizer, format_ptcgl_decklist

   root = Path(".")
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

   # Evaluate any PTCGL text decklist:
   deck = parse_ptcgl_decklist((root / "decks/discovered_archeops_ancient_wing.txt").read_text("utf-8"), db)
   report = evaluator.evaluate_deck(deck)
   print(report.overall_score, report.going_first_score, report.going_second_score, report.is_legal)
   ```
2. **Adding New Mechanics or Fixing Card Interactions**:
   - **Step 1**: Check how the card compiles via `db.resolve_card("Card Name")` — inspect `.tags`, `.synergy_hooks`, `.action_vector`, and `.attacks`.
   - **Step 2**: Add or refine mechanical tags in `compile_card()` in `src/card_compiler.py`.
   - **Step 3**: Enforce conditional synergy / dead-card rules in `_analyze_deck_structure()` and combat math in `_score_single_state()` in `src/state_evaluator.py`.
   - **Step 4**: Always verify your changes by running `python discover_deck.py --evaluate <deck_file>` and checking that `_analyze_deck_structure(deck)["dead_card_count"] == 0` for intended builds.
