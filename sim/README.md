# sim/ — open-source simulator, state generator and turn players

Everything here runs on the **Twinleaf engine** vendored in [`../engine/twinleaf`](../engine/twinleaf)
(MIT, a fork of twinleaf.gg / RyuuPlay; see its `UPSTREAM.md` for the local patches). Nothing here uses
the closed CABT engine or the older Python play heuristics in `../src/`. Those are set aside: the
turn players below start from the rules alone, and everything they know comes from the search and
the training loop.

```
npm install          # once (esbuild, typescript, pako)
npm test             # build + all tests (~15 s)
```

## What is where

| Piece | File | Command |
|---|---|---|
| Engine wrapper: seeded chance, legal moves, copies, macro steps | `src/sim.ts`, `src/prompts.ts`, `src/clone.ts` | `node dist/randomgame.js 20` plays random legal games |
| Decklists → engine cards | `src/cards.ts`, `src/printed.ts` | `npm run decks` |
| Card tests (static vs printed data + in-play smoke) | `src/cardcheck.ts`, `test/index.ts` | `npm test`, `npm run cards`, `npm run cards:all` |
| Random valid board states between two decks | `src/stategen.ts`, `src/invariants.ts` | `node dist/genstates.js 2000` |
| Feature vector (cheap + engine-probe groups) | `src/features.ts` | `node dist/featbench.js` |
| One-turn search (offense teacher) | `src/search.ts` | `node dist/oracle.js 10`, `node --expose-gc dist/searchbench.js 12` (time, positions, memory), `node dist/searchshape.js` (branching of one search) |
| Parallel one-turn search (shared transposition table) | `src/psearch.ts` | `node dist/psearchbench.js 10` (parallel vs serial on the same states) |
| Worker pool (memory-aware size, crash-safe) | `src/pool.ts` | |
| Value models, feature reduction | `src/model.ts`, `src/cli/train.ts` | |
| Fast turn players (offense, defense) | `src/policy.ts` | |
| Training round: label → fit → reduce → evaluate → log → review packet | `src/cli/train.ts` | `node dist/train.js offense`, `node dist/train.js defense` |

## Speed: cores and memory

- **Windows power throttling.** A windowless background process runs in efficiency mode, on the
  efficiency cores only. On the i7-13650HX the 8 E-cores sat at 100% while the 6 P-cores idled, so
  7 and 14 workers ran equally slowly. Every worker pool turns this off for its own process
  (`scripts/fullspeed.ps1`, no admin rights; `SIM_THROTTLE=1` skips it): 42 games went from 797 s to
  165 s on 7 workers. Run it by hand on an older process:
  `powershell -ExecutionPolicy Bypass -File sim/scripts/fullspeed.ps1 -ProcessId <pid>`.
- **Memory per worker.** A game holds about 45 MB of live data, but V8 lets garbage grow to the heap
  cap before collecting. A 320 MB cap (`POOL_HEAP_MB`) plays at full speed with peaks of 380 MB
  (`race` and `plan2`); the old 900 MB cap peaked at 500–600 MB. The worker count is one per logical
  CPU less two, limited by free memory (`POOL_WORKERS_MAX`, `--workers N`). Closing other programs
  is what lets more workers run.

## Card tests

`npm test` checks:
- every card in the meta decklists against an independent copy of the printed card
  (`../pokemon-tcg-data-standard`), covering HP, stage, type, weakness, resistance, retreat, attack
  costs and damage. It also uses each card in play: attacks, abilities and playing it from hand.
  A card fails if the engine throws, if a prompt has no legal answer, if cards appear or vanish,
  or if a plain attack deals damage different from its print;
- every Standard card that is **new or changed** since the last baseline. Each card's fingerprint
  covers its stats and its code, so an upstream sync or a local patch triggers a re-check. Run
  `npm run cards:baseline` after reviewing to record the new state.

Known, accepted differences live in `test/known-card-issues.json` with a reason. Translated names
are recorded automatically; gameplay differences never are. `npm run cards:all` audits every
Standard printing (about 3 minutes) and writes `reports/cardcheck-all.json`.

## State generator

`generateState(deckA, deckB, rng)` returns a settled position at the start of a turn, right after
the draw. It sets up a real game through the engine, then redistributes the same 120 card objects,
so every card stays accounted for. The rules are kept: evolution lines and timing, Rare Candy,
prizes taken matching the Knocked Out Pokémon in the discard, energy bounded by turns taken, at
most one tool per Pokémon, damage below HP, and the deck size limit. It produces about 1,800
states per second.

## Search: fixed chance, position hashes, parallel workers

- **Fixed hidden information.** Every generated state carries a chance seed (`Sim.chanceSeed`,
  set by `determinize`). Each card gets a random rank that depends only on that seed, the turn and
  the card, and every deck shuffle puts the deck in rank order. Within the turn being tested, the
  same cards in a deck therefore always shuffle and draw the same way, whatever order the turn's
  actions came in: a search cannot see different hidden cards on different lines (which both
  inflated its value and multiplied its positions), and orderings of the same plays merge. Taking
  a face-down prize always takes the first prize slots. Coin flips are seeded by the action.
  A new turn gets new ranks, so whole games stay random. `RANDOM_SHUFFLES=1` turns it off.
- **Position identity.** `stateHash` (64 bits) of the canonical `stateKey`: both players' zones
  (deck in order, prizes by content), every Pokémon's cards, damage, energy, tools, conditions
  and markers, and the per-turn flags. Two positions with one hash have the same future.
- **Parallel search.** `ParallelSearch` runs one search over many worker threads. The coordinator
  owns the transposition table; a child whose hash is already known has converged with another
  path and is not expanded again. A work item is the hash plus the replayable steps from the root
  (`Step`: option label + answer indices); a worker rebuilds positions it does not hold by
  replaying them (`replayStep`, checked against the hash) and is preferably given the positions it
  created. Same results as the serial search, 2.7× faster on 10 workers. Training labels many
  states at once instead (one state per worker, which keeps every core busy without replays).
- **Memory.** A search keeps positions only for the sampled nodes it returns (`keepSims`), drops
  expanded positions and the part of the queue the budget cannot reach, and stops at `maxMs`
  (15 s). Round 2 of offense training ran 18 workers that each held up to 0.7 GB and swapped.

## Deck builder and tester

```
node dist/deckbuilder.js --seed "Mega Gardevoir ex"       # build a deck around a card, optimise it, test it
node dist/deckbuilder.js --list my-deck.txt               # test a list (Pokémon TCG Live export format)
node dist/deckbuilder.js --list my-deck.txt --optimize    # improve a list, then test it
node dist/deckbuilder.js --export "Dragapult" --out dragapult.txt   # a meta deck's list to start from
```

Output in `runs/deck-<name>/`:
- `report.md`: the deck list, how it was found (generations, finalists, the winner's family line), win rate against the meta field with a 95%
  range, the matchup table, stuck statistics, how the deck takes prizes, a recommended play style
  and the engine card checks;
- `deck.txt`, `stats.json` and `games.jsonl`.

**How it works:**
- **Games:** full games from turn 1 against the meta decks, by their share of the decklists. Both
  sides are piloted by the same policy (`--pilot`, default v1 `race`; `plan2:<win model>` is
  stronger and slower).
- **Building from a seed** (`deckgen.ts`), all from the 512 meta lists:
  - if the card is played in the meta lists, start from the best-placed list that plays it;
  - otherwise, its evolution line in the usual counts for its stage, basic Energy for its attack
    costs, and the most common staples (Trainers, plus support Basics that stand alone).
- **Searching** (`--seed`, or `--list ... --optimize`): a population of `--population 10` decks:
  the start, other meta lists that play the seed, and bigger variations of the start. Each of
  `--generations 4` generations, every deck plays the same `--screen 10` games; the top half
  survives with its games and the rest are replaced by small changes to the survivors. Ranking uses
  the win rate pulled towards 50% (four imaginary games), minus `--stuck-weight` × share of turns
  stuck. The best `--finalists 3`, plus the starting list, then play the same half of the
  `--games 120` final test; the best of them plays the other half, as does the starting list, for
  a paired before/after. Runners-up are saved as `finalist-2.txt`, `finalist-3.txt`.
- **Which changes are tried** (`synergy.ts`): any legal one- or two-card swap, but the card added is
  weighted by how well it fits the deck and the card cut by how badly it fits the rest of it:
  co-occurrence in the meta lists, whether the deck's Energy pays its attacks (soft; abilities
  count as support), evolution links (line pieces up, orphan evolutions down) and, for basic Energy,
  whether the deck's attacks use the type. Nothing is ruled out, so multi-type decks stay possible.
  `node dist/fitshow.js --list my-deck.txt` (or `--seed "<card>"`) prints the likeliest additions
  and cuts.
- **Every card must be usable** (`usability.ts`): a rules check from costs and texts. Each text is
  read into conditions on kinds of cards ("Tera Pokémon", "Basic Pokémon with 70 HP or less",
  "Benched N's Pokémon", "Pokémon Tools"). Each condition records whose cards it is about (yours, the
  opponent's, or both) and what it does with them: it can enable, copy attacks, search, target or
  harm. The check runs both ways:
  - **Helpful cards** need cards in the list that meet their conditions. Area Zero Underdepths needs
    a Tera Pokémon, Rosa's Encouragement needs Basic Energy and a Stage 2. Sentences and clauses must
    all be met; "or" and lists of search targets are alternatives.
  - **Harmful cards** should hurt none of your own cards (Nighttime Mine with your Tera Pokémon,
    Path to the Peak with your Rule Box Pokémon). If what they hurt is a third of your Pokémon or
    more, the card is unusable. A smaller hit is noted in the report as a side effect, and the
    builder adds such cards less often: 70 meta lists run Team Rocket's Watchtower with a Meowth ex.
  - **Reverse:** a Pokémon is usable if another card uses it. Examples are N's Zoroark ex copying
    Benched N's Pokémon, Slowking copying deck-top Pokémon (no evolution line needed), and Area Zero
    needing a Tera Pokémon in play. Being searched for or targeted is not a use.
  - **Pokémon** also count as usable with an attack the deck's Energy can pay (if it does no damage,
    its text must work), an ability whose conditions are met, or a place in a line. An evolution
    needs its pre-evolution, its Fossil, or Rare Candy and its Basic.

  A change may not add an unusable card or strand a usable one, and seed builds skip unusable
  staples. It flags no card in any of the 512 meta lists (`node dist/usablecheck.js --meta`).
  `--list my-deck.txt` checks one list, and `--conds` prints how every Trainer text is read. The
  report's **Card usage** table adds how often each card was really used in the final test games.
- A default run plays about 760 games, roughly 30 minutes on 8 workers.

**Limits:** the result measures how well the simulator pilots the deck. Decks whose plan needs
long ability chains are likely under-played (see Pilot fidelity below for how far the simulator's
matchups are from real ones). Compare a new deck with meta decks tested the same way.

## Pilot fidelity

```
node dist/fidelity.js --pilot race --name fidelity-race                  # 10 meta decks round-robin, 12 games a pairing
node dist/fidelity.js --pilot race --name fidelity-race-b --seeds 1      # the same on other games
node dist/fidelity.js --compare fidelity-race+fidelity-race-b,fidelity-plan2   # scores side by side ("+" pools runs)
node dist/fidelity.js --pilot race --name fidelity-race --replay "Dragapult|Festival Lead|2"  # one game, board every turn
```

The top 10 meta archetypes play every other one, both sides piloted by `--pilot`, and the win
rates are compared with real matchups (Limitless, `meta/matchups_*.json`). `runs/<name>/report.md`
gives the matchup correlation and error (with the error sampling noise alone would give), the
lopsidedness (a weak pilot exaggerates matchups), each deck's win rate against the field, the
worst-matching matchups and how games end. A replay shows the board before each turn, the moves
and the planner's finalists with their scores. A run of `race` takes about 25 minutes.

**Noise:** with 12 games a pairing a deck's win rate moves about 5 points between runs on different
games, and the scores move with it. A pilot change is only measured by pooling runs of several
`--seeds`.

**Pilot rules that came out of the replays** (all pilots):
- **Bench-out guard** (`benchGuard` in `planner.ts`): ending a turn with an empty Bench loses the
  game to one Knock Out. Such an ending is valued toward a loss by the chance the Active is Knocked
  Out next turn (the defense model's expected prizes over what the Active is worth, at least 35%),
  also after `plan2`'s sampled replies, which often miss the Knock Out. When the turn search runs
  out of budget, a position with an empty Bench also tries benching each Basic in hand.
  `SIM_NO_GUARD=1` turns the guard off.
- **Set-up** (`setupChooser` in `playgame.ts`): every Basic down, the Active chosen by a rule of
  thumb (few prizes, cheap retreat, high HP, an attack for one Energy). `SIM_RANDOM_SETUP=1` restores
  random set-up.
- **Material** (`race` only, `material` in `planner.ts`): Energy attached, Pokémon in play (more
  when evolved) and cards in hand count for a little (a full board is about one prize), so resources
  are no longer thrown away when the next two turns' prizes do not change. `SIM_MATERIAL=both`
  counts the mover's material minus the opponent's; `off` turns it off.

These removed clear blunders (games lost with no Pokémon in play fell from 31% to 8%; the pilots no
longer discard the Basic they just searched for or stall for 20 turns), but the fidelity scores
stayed within noise: the remaining gap is in long plans (Festival Lead's Thwackey engine, Dragapult
ex's Phantom Dive set-up), not single blunders.

## Alignment with real play (states from tournament games)

```
node dist/align.js --check                                  # replay the match logs: does every action apply?
node dist/align.js --pilot race --name align-race           # the pilot's choice at every real state
node dist/align.js --pilot plan2:runs/value-v2/value-model.json --name align-plan2
```

**Match logs** (`sim/data/matches/*.json`, local like the transcripts they come from) record real
games from the commentated finals and top cut videos (`scripts/fetch_transcripts.py`): the two
decklists (meta list ids; finalists are rank 1 and 2 of the event), who went first, the opening
Pokémon, prize cards the commentators saw, and each turn as a list of actions - `bench`, `evolve`,
`attach`, `tool`, `play`, `ability`, `retreat`, `attack`, `end`, plus `promote` after a Knock Out and
`concede`. An action names its card and target, the answers to its prompts in order (`choices`, by
card names, `"*"` when not known), the other hand cards it spends (`uses`: Ultra Ball's discards, the
Energy Teal Dance attaches), and whether it was stated by the commentators or only implied by what
came after (`inferred`). The format is in `src/matchlog.ts`; logs are written by reading a
transcript (an AI does it; the captions misspell card names, so names are checked against the lists).

**States** (`replayLog`): the log is replayed in the engine from set-up, giving a state before every
real action. Hidden information is filled in so that the real play is possible: the opening Pokémon
go in the opening hand, known prizes in the prizes, and before each action every card the player
plays from hand up to the next action that draws or searches is swapped into the hand (cards played
after a draw may have come from it). The rest of both hands, the prizes and the deck order are
random. The opponent's promotions come from the log.

**Scores** (`runs/<name>/report.md`, every state in `steps.jsonl`, boards in `replay-<game>.md`): at
each state the pilot plans from there and its first action is compared with the real one:
- the same action (card and target), and also with the same prompt answers;
- the same or interchangeable: a later real action of that turn also counts when it does not depend
  on the ones before it - played first, then those, it reaches the same board (checked in the
  engine; only up to the next draw or search);
- in the pilot's planned turn: the real action is anywhere in the line it planned (order aside).

Implied actions are replayed but not scored. The hand filler is random, so the pilot sometimes holds
cards the real player did not; scores are for comparing pilots on the same logs.

## Game archive, refits and play audits

Every game the deck builder and the playout runner play is appended to a local archive,
`sim/data/archive/games-<date>.jsonl.gz`. The folder is gitignored and is never committed. Each
record holds:
- the game, with the mover's cheap feature vector at every turn, the category, the prizes and the
  moves;
- the spec to replay it;
- the git commit, and a fingerprint of every card in both decks, so games played with a card that
  was fixed later are left out.

It takes about 4–5 KB per game compressed, about 3.5 MB per deck builder run. `NO_ARCHIVE=1` turns
it off.

```
node dist/archive.js stats                                  # games, positions, kinds, pilots, commits
node dist/fitvalue.js playout-win2-vs-v2 --archive --out value-v3   # refit the win model with archived games
node dist/archive.js audit --pilot plan:runs/value-v3 --n 6  # replay games that pilot won, boards on
```

**Refit procedure** (win model, category rates, or any learned weight the pilot or generator uses):
1. Refit from the archive. Use only games played with today's card rules; `fitvalue --archive` does
   this.
2. Play the new model against the current one, both seats, same games. Adopt it only if it wins.
3. **Audit before adopting.** Run `archive.js audit` on games the new model won, especially
   comebacks. Have them reviewed (an AI review is fine) for sensible play: sequencing, targets,
   resource use, not leaving itself open, and wins that only came from the opponent's mistakes.
   Save the review in `sim/reviews/` and fix what it finds before adopting.

## Training rounds and review

`node dist/train.js offense --states 1000 --eval 100 --run name` writes `runs/<run>/` containing
`labels.jsonl` (every labelled state, appended as it finishes), `data.json` (all labelled positions),
`model.json` (the chosen reduced model), `battles.jsonl` (every evaluated turn, appended as it
finishes: board, search line, policy line with the alternatives it considered), `log.txt` and
`review-packet.md`. Rerunning the same command resumes: finished states are skipped (the seed
defaults to one derived from the run name). Progress lines show the time per window and the
largest worker heap, so a slowdown is visible. `--workers auto` (the default) uses as many workers
as cores and free memory allow.
After each round the AI review step reads the packet and records its reasoning and changes in
`reviews/`; see [REVIEW.md](REVIEW.md).
