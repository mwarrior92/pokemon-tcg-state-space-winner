# Pilot fidelity: fidelity-race-mboth

Pilot `race`. 10 meta decks (best-placed complete list of each archetype), every pairing played 12 times with seats alternating: 540 games. Real matchups: matchups_2026-09-19_to_10-31.json (Limitless, all rounds).

## Scores

| score | value | what it means |
|---|---|---|
| correlation, sim vs real matchup win rates | **0.17** | 1 = same order and spacing, 0 = unrelated |
| mean absolute error | **20%** | sampling noise alone would give about 11% |
| lopsidedness (mean distance from 50%) | sim 20%, real 9% | a weak pilot exaggerates matchups; noise adds about 11% to the sim figure |
| rank correlation of deck win rates | **-0.03** | do the decks come out in the real order? |
| deck win rate error (mean absolute, each deck against all the others) | **12%** | the steadiest score: sampling noise alone would give about 4% |

## Decks: average win rate against the others

| deck | sim | real | difference |
|---|---|---|---|
| Alakazam Dudunsparce | 78% | 49% | +29 |
| Basic Box | 58% | 47% | +11 |
| Hydrapple | 56% | 47% | +10 |
| Alakazam Dusknoir | 64% | 54% | +9 |
| Dragapult | 55% | 56% | -1 |
| Dragapult Blaziken | 50% | 51% | -1 |
| Slowking | 44% | 46% | -2 |
| Dragapult Dusknoir | 33% | 50% | -17 |
| Festival Lead | 33% | 51% | -17 |
| N's Zoroark | 29% | 49% | -21 |

Sorted from most overrated by the simulator to most underrated.

## Matchups, largest disagreement first

| deck A | deck B | A wins: sim | A wins: real | sim games | real games |
|---|---|---|---|---|---|
| Alakazam Dudunsparce | Dragapult Dusknoir | 100% | 43% | 12 | 388 |
| Dragapult | Alakazam Dusknoir | 17% | 61% | 12 | 530 |
| Hydrapple | Dragapult Dusknoir | 83% | 39% | 12 | 225 |
| Basic Box | N's Zoroark | 92% | 49% | 12 | 677 |
| Festival Lead | Alakazam Dudunsparce | 17% | 56% | 12 | 233 |
| N's Zoroark | Dragapult Blaziken | 25% | 63% | 12 | 448 |
| N's Zoroark | Alakazam Dudunsparce | 17% | 52% | 12 | 446 |
| Basic Box | Alakazam Dudunsparce | 8% | 44% | 12 | 533 |
| Hydrapple | Festival Lead | 75% | 40% | 12 | 181 |
| Basic Box | Slowking | 83% | 52% | 12 | 624 |
| Dragapult | Alakazam Dudunsparce | 33% | 63% | 12 | 1308 |
| N's Zoroark | Slowking | 25% | 54% | 12 | 576 |
| Slowking | Alakazam Dudunsparce | 0% | 27% | 12 | 453 |
| Festival Lead | Alakazam Dusknoir | 25% | 51% | 12 | 123 |
| Dragapult | Dragapult Dusknoir | 83% | 57% | 12 | 1308 |
| Basic Box | Festival Lead | 75% | 50% | 12 | 333 |
| Hydrapple | Alakazam Dusknoir | 58% | 35% | 12 | 103 |
| Basic Box | Dragapult Blaziken | 75% | 53% | 12 | 473 |
| Alakazam Dudunsparce | Dragapult Blaziken | 58% | 38% | 12 | 344 |
| Basic Box | Dragapult Dusknoir | 75% | 55% | 12 | 500 |
| Basic Box | Hydrapple | 50% | 31% | 12 | 369 |
| N's Zoroark | Alakazam Dusknoir | 33% | 53% | 12 | 170 |
| Alakazam Dudunsparce | Alakazam Dusknoir | 58% | 39% | 12 | 131 |
| Alakazam Dusknoir | Dragapult Blaziken | 58% | 41% | 12 | 134 |
| Slowking | Dragapult Dusknoir | 75% | 59% | 12 | 422 |
| N's Zoroark | Dragapult Dusknoir | 42% | 57% | 12 | 481 |
| Slowking | Festival Lead | 67% | 52% | 12 | 301 |
| Dragapult | N's Zoroark | 58% | 44% | 12 | 1740 |
| Dragapult | Slowking | 58% | 45% | 12 | 1604 |
| Festival Lead | Dragapult Blaziken | 33% | 47% | 12 | 231 |
| Dragapult | Basic Box | 58% | 45% | 12 | 1863 |
| Dragapult | Dragapult Blaziken | 42% | 54% | 12 | 1339 |
| Dragapult | Hydrapple | 75% | 64% | 12 | 957 |
| Basic Box | Alakazam Dusknoir | 25% | 36% | 12 | 208 |
| N's Zoroark | Festival Lead | 33% | 23% | 12 | 328 |
| Dragapult Dusknoir | Dragapult Blaziken | 58% | 49% | 12 | 335 |
| Festival Lead | Dragapult Dusknoir | 42% | 33% | 12 | 258 |
| Slowking | Hydrapple | 33% | 39% | 12 | 284 |
| Hydrapple | Dragapult Blaziken | 42% | 37% | 12 | 251 |
| Dragapult Dusknoir | Alakazam Dusknoir | 42% | 46% | 12 | 117 |
| Hydrapple | Alakazam Dudunsparce | 42% | 37% | 12 | 243 |
| Slowking | Alakazam Dusknoir | 25% | 29% | 12 | 157 |
| Slowking | Dragapult Blaziken | 58% | 56% | 12 | 412 |
| Dragapult | Festival Lead | 67% | 64% | 12 | 905 |
| N's Zoroark | Hydrapple | 33% | 35% | 12 | 318 |

## How games went

- Endings: prizes 477 (88%), no Pokémon in play 43 (8%), deck out 20 (4%).
- Mean length 16.6 turns; 20 s per game in a worker.
- The player who went first won 55% of 540 decided games.

## Reading this

- Real matchups mix pilots of every level and list variants; the sim plays one list per archetype with one pilot on both sides. A perfect pilot would still not match exactly, but its errors should be close to the noise floor and its lopsidedness close to the real figure.
- Decks far above the line (overrated) are ones the pilot plays well relative to their opponents; decks far below are where its play is worst. Audit those games first (`node dist/archive.js audit --kind fidelity --run fidelity-race-mboth`).
