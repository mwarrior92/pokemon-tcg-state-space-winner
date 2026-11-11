# Pilot fidelity: fidelity-race-guard

Pilot `race`. 10 meta decks (best-placed complete list of each archetype), every pairing played 12 times with seats alternating: 540 games. Real matchups: matchups_2026-09-19_to_10-31.json (Limitless, all rounds).

## Scores

| score | value | what it means |
|---|---|---|
| correlation, sim vs real matchup win rates | **0.17** | 1 = same order and spacing, 0 = unrelated |
| mean absolute error | **18%** | sampling noise alone would give about 12% |
| lopsidedness (mean distance from 50%) | sim 17%, real 9% | a weak pilot exaggerates matchups; noise adds about 12% to the sim figure |
| rank correlation of deck win rates | **0.04** | do the decks come out in the real order? |
| deck win rate error (mean absolute, each deck against all the others) | **10%** | the steadiest score: sampling noise alone would give about 4% |

## Decks: average win rate against the others

| deck | sim | real | difference |
|---|---|---|---|
| Alakazam Dudunsparce | 68% | 49% | +19 |
| Dragapult Blaziken | 60% | 51% | +9 |
| Alakazam Dusknoir | 63% | 54% | +9 |
| Basic Box | 56% | 47% | +8 |
| Hydrapple | 52% | 47% | +6 |
| Slowking | 42% | 46% | -3 |
| Dragapult | 52% | 56% | -4 |
| N's Zoroark | 40% | 49% | -9 |
| Dragapult Dusknoir | 35% | 50% | -16 |
| Festival Lead | 32% | 51% | -19 |

Sorted from most overrated by the simulator to most underrated.

## Matchups, largest disagreement first

| deck A | deck B | A wins: sim | A wins: real | sim games | real games |
|---|---|---|---|---|---|
| N's Zoroark | Dragapult Blaziken | 17% | 63% | 12 | 448 |
| Basic Box | N's Zoroark | 92% | 49% | 12 | 677 |
| Dragapult | Alakazam Dudunsparce | 25% | 63% | 12 | 1308 |
| Dragapult | Alakazam Dusknoir | 25% | 61% | 12 | 530 |
| N's Zoroark | Alakazam Dudunsparce | 17% | 52% | 12 | 446 |
| Dragapult Dusknoir | Dragapult Blaziken | 17% | 49% | 12 | 335 |
| Festival Lead | Alakazam Dudunsparce | 25% | 56% | 12 | 233 |
| Alakazam Dudunsparce | Dragapult Blaziken | 67% | 38% | 12 | 344 |
| N's Zoroark | Alakazam Dusknoir | 25% | 53% | 12 | 170 |
| N's Zoroark | Festival Lead | 50% | 23% | 12 | 328 |
| Hydrapple | Festival Lead | 67% | 40% | 12 | 181 |
| Festival Lead | Alakazam Dusknoir | 25% | 51% | 12 | 123 |
| N's Zoroark | Dragapult Dusknoir | 83% | 57% | 12 | 481 |
| Basic Box | Festival Lead | 75% | 50% | 12 | 333 |
| Slowking | Dragapult Blaziken | 33% | 56% | 12 | 412 |
| Hydrapple | Alakazam Dudunsparce | 58% | 37% | 12 | 243 |
| Alakazam Dudunsparce | Alakazam Dusknoir | 58% | 39% | 12 | 131 |
| Dragapult | Festival Lead | 83% | 64% | 12 | 905 |
| Alakazam Dusknoir | Dragapult Blaziken | 58% | 41% | 12 | 134 |
| Alakazam Dudunsparce | Dragapult Dusknoir | 58% | 43% | 12 | 388 |
| Basic Box | Slowking | 67% | 52% | 12 | 624 |
| Dragapult | Slowking | 58% | 45% | 12 | 1604 |
| Festival Lead | Dragapult Blaziken | 33% | 47% | 12 | 231 |
| Slowking | Dragapult Dusknoir | 73% | 59% | 11 | 422 |
| Dragapult | Basic Box | 58% | 45% | 12 | 1863 |
| Dragapult Dusknoir | Alakazam Dusknoir | 33% | 46% | 12 | 117 |
| Slowking | Alakazam Dusknoir | 42% | 29% | 12 | 157 |
| Hydrapple | Dragapult Blaziken | 25% | 37% | 12 | 251 |
| Basic Box | Dragapult Dusknoir | 67% | 55% | 12 | 500 |
| Hydrapple | Dragapult Dusknoir | 50% | 39% | 12 | 225 |
| Dragapult | N's Zoroark | 33% | 44% | 12 | 1740 |
| Slowking | Alakazam Dudunsparce | 17% | 27% | 12 | 453 |
| Basic Box | Alakazam Dudunsparce | 33% | 44% | 12 | 533 |
| N's Zoroark | Slowking | 64% | 54% | 11 | 576 |
| Dragapult | Dragapult Dusknoir | 67% | 57% | 12 | 1308 |
| Festival Lead | Dragapult Dusknoir | 42% | 33% | 12 | 258 |
| Slowking | Festival Lead | 60% | 52% | 10 | 301 |
| Slowking | Hydrapple | 45% | 39% | 11 | 284 |
| Hydrapple | Alakazam Dusknoir | 42% | 35% | 12 | 103 |
| Basic Box | Alakazam Dusknoir | 42% | 36% | 12 | 208 |
| Basic Box | Hydrapple | 25% | 31% | 12 | 369 |
| Basic Box | Dragapult Blaziken | 58% | 53% | 12 | 473 |
| Dragapult | Dragapult Blaziken | 50% | 54% | 12 | 1339 |
| Dragapult | Hydrapple | 67% | 64% | 12 | 957 |
| N's Zoroark | Hydrapple | 33% | 35% | 12 | 318 |

## How games went

- Endings: prizes 442 (82%), no Pokémon in play 63 (12%), deck out 30 (6%), turn limit 5 (1%).
- Mean length 20.3 turns; 16 s per game in a worker.
- The player who went first won 57% of 535 decided games.

## Reading this

- Real matchups mix pilots of every level and list variants; the sim plays one list per archetype with one pilot on both sides. A perfect pilot would still not match exactly, but its errors should be close to the noise floor and its lopsidedness close to the real figure.
- Decks far above the line (overrated) are ones the pilot plays well relative to their opponents; decks far below are where its play is worst. Audit those games first (`node dist/archive.js audit --kind fidelity --run fidelity-race-guard`).
