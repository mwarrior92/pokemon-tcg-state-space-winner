# Vendored Twinleaf engine

This folder is a fork of the game server of **twinleaf.gg**, which is itself based on **RyuuPlay**.
Both are MIT-licensed; see [LICENSE](LICENSE) (upstream declares MIT in its README and
`package.json`; the RyuuPlay copyright line comes from RyuuPlay's LICENSE file).

| | |
|---|---|
| Upstream | https://github.com/twinleafgg/twinleafgg (folder `ptcg-server/`) |
| Based on | https://github.com/keeshii/ryuu-play |
| Commit | `837aebeb5f7fbb0f26d1646e958875f16ae55134` (2026-11-07) - also in `.upstream_commit` |
| Copied | `ptcg-server/src/` (engine, card sets, server code), `package.json`, `tsconfig.json` |
| Not copied | web clients, avatars/sleeves/assets, database, Docker files |

Only the game engine (`src/game/store`, `src/game/cards`, `src/sets`, `src/utils`) is used by this
repository's simulator (`sim/`). The server code (`src/backend`, `src/storage`, ...) is kept unmodified
so upstream imports keep resolving and future syncs stay simple.

## Local changes

Every local change is marked in the source with a `[winner patch NNN]` comment.

| Patch | File | Change | Why |
|---|---|---|---|
| 001 | `src/utils/utils.ts` | `deepClone` tracks references in a `Map` and copies take the source's prototype | Upstream was O(n²) and made prototype chains grow on every clone; the Store backs up the whole state with it before every action, which was >50% of simulation time |
| 002 | `src/game/store/store.ts` | `Store.computePlayability` switch (default on) | The web client's "playable cards" list was recomputed after every effect (incl. every HP check); no rules code reads it. The simulator turns it off |
| 003 | `sets/.../set-twilight-masquerade/tatsugiri.ts` | handle a cancelled card choice | crashed on `null` |
| 004 | `src/game/store/store.ts` | `Store.backupOnReduce` switch (default on) | The simulator dispatches only on throw-away copies, so the per-action rollback copy is not needed there |
| 005 | `src/game/store/state/pokemon-card-list.ts` | `PokemonCardList.moveTo` moves each attached energy once | Upstream moved `energies.cards` and then `cards` (which already contain the energy), duplicating every attached energy when a Pokémon went to the hand/deck (Meowth ex Tuck Tail, Scoop Up Cyclone, Abra Teleporter, Dudunsparce Run Away Draw, ...) |
| 006 | `sets/.../set-shrouded-fable/duskull.ts` | Come and Get You checks the discard, "up to 3" | looked in the hand and required at least one |
| 007 | `src/game/store/prefabs/prefabs.ts` | `MOVE_CARDS` from a Pokémon's `energies` list moves from the Pokémon | the cards stayed in the Pokémon's card list too (Mega Skarmory ex Sonic Ripper duplicated its energy into the deck) |
| 008 | `sets/.../set-stellar-crown/slowpoke.ts` | Dangle Tail moves the chosen Pokémon from the discard | moved a copy, leaving the original in the discard; required any card instead of a Pokémon |
| 009 | `sets/.../set-surging-sparks/ceruledge-ex.ts` | Amethyst Rage discards energy with `MOVE_CARDS` | edited `cards` by hand, leaving the energies list pointing at discarded cards |
| 010 | `src/game/store/effect-reducers/check-effect.ts` | every state check drops `energies` entries for energy cards no longer in the stack | safety net for card code that edits a Pokémon's cards directly |
| 011 | `src/game/store/prefabs/attack-effects.ts` | "this attack does X damage to 1 of your opponent's (Benched) Pokémon" target is not cancellable | the prompt allowed cancel and then read `selected[0]` of `null` (≈12 cards crashed) |
| 013 | 3 set `index.ts` files (Stellar Crown, Surging Sparks, Twilight Masquerade) | register Chi-Yu TWM, Charjabug SCR, Altaria SSP (Shinx TWM and Dipplin SCR were also unregistered upstream but their files do not match the printed cards - wrong HP/type/stage - so they stay out) | the card files existed upstream but were never added to their set's list, so the engine never loaded them (Chi-Yu TWM is in 19 meta lists; decks fell back to a different Chi-Yu). `npm test` now fails on any unregistered Standard card file |
| 014 | new: `set-phantasmal-flames/pawmot-pfl.ts`, `set-mega-evolution/buneary-meg.ts`, `set-stellar-crown/payapa-berry.ts` (+ their set indexes) | Pawmot PFL 34, Buneary MEG 107, Payapa Berry SCR 141 written from the printed cards | missing upstream; with these and 013 all 512 meta decklists are fully playable |
| 015 | `src/game/store/store.ts` | `Store.logTimestamps` switch (default on) | every engine log entry formatted the wall-clock time with `toLocaleTimeString`, ~9% of simulation time; the simulator turns it off |
| 016 | `sets/.../set-temporal-forces/salvatore.ts` | the searched card must have no Abilities **and** evolve from one of your Pokémon | upstream blocked only cards failing both conditions, so a Pokémon that evolves from nothing in play could be chosen and the "evolve which Pokémon" prompt had no legal answer |
| 012 | 7 card files (Chikorita M1S, Carvanha M2, Toxtricity M2, Metagross M4, Jirachi ex 30C, Jellicent ex SV11W, Combusken DRI) | HP / resistance / attack cost corrected to the printed card | found by `npm run cards` against `pokemon-tcg-data-standard`; Pawmot and Metagross were confirmed on limitlesstcg.com |

New cards or fixes we write go in this folder as ordinary card files (same layout as upstream) and
get a row here.

## Syncing with upstream

`sim/scripts/sync-upstream.sh` (see `sim/README.md`) re-copies upstream at a given commit, refusing to
overwrite files changed by a local patch. After a sync, run `npm test` in `sim/` - the card smoke
tests cover every card in the meta decklists, including newly added ones.

Card names, text and other Pokémon TCG content are trademarks and copyright of Nintendo,
Creatures Inc., GAME FREAK inc. and The Pokémon Company; this project is not affiliated with them.
