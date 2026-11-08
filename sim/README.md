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
