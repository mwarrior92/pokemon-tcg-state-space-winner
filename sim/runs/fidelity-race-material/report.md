# Pilot fidelity: fidelity-race-material

Pilot `race`. 10 meta decks (best-placed complete list of each archetype), every pairing played 12 times with seats alternating: 540 games. Real matchups: matchups_2026-09-19_to_10-31.json (Limitless, all rounds).

## Scores

| score | value | what it means |
|---|---|---|
| correlation, sim vs real matchup win rates | **0.04** | 1 = same order and spacing, 0 = unrelated |
| mean absolute error | **22%** | sampling noise alone would give about 11% |
| lopsidedness (mean distance from 50%) | sim 20%, real 9% | a weak pilot exaggerates matchups; noise adds about 11% to the sim figure |
| rank correlation of deck win rates | **-0.08** | do the decks come out in the real order? |
| deck win rate error (mean absolute, each deck against all the others) | **14%** | the steadiest score: sampling noise alone would give about 4% |

## Decks: average win rate against the others

| deck | sim | real | difference |
|---|---|---|---|
| Alakazam Dudunsparce | 81% | 49% | +32 |
| Hydrapple | 65% | 47% | +18 |
| Alakazam Dusknoir | 66% | 54% | +11 |
| Basic Box | 55% | 47% | +8 |
| Dragapult | 52% | 56% | -4 |
| Dragapult Blaziken | 46% | 51% | -5 |
| Slowking | 38% | 46% | -8 |
| N's Zoroark | 34% | 49% | -15 |
| Dragapult Dusknoir | 33% | 50% | -17 |
| Festival Lead | 31% | 51% | -20 |

Sorted from most overrated by the simulator to most underrated.

## Matchups, largest disagreement first

| deck A | deck B | A wins: sim | A wins: real | sim games | real games |
|---|---|---|---|---|---|
| Alakazam Dudunsparce | Dragapult Blaziken | 92% | 38% | 12 | 344 |
| Alakazam Dudunsparce | Dragapult Dusknoir | 92% | 43% | 12 | 388 |
| Festival Lead | Alakazam Dudunsparce | 8% | 56% | 12 | 233 |
| Dragapult | Alakazam Dudunsparce | 17% | 63% | 12 | 1308 |
| Dragapult | Alakazam Dusknoir | 17% | 61% | 12 | 530 |
| Hydrapple | Dragapult Dusknoir | 83% | 39% | 12 | 225 |
| Hydrapple | Festival Lead | 83% | 40% | 12 | 181 |
| Basic Box | N's Zoroark | 83% | 49% | 12 | 677 |
| Dragapult | Dragapult Dusknoir | 92% | 57% | 12 | 1308 |
| Basic Box | Slowking | 83% | 52% | 12 | 624 |
| Dragapult | Slowking | 75% | 45% | 12 | 1604 |
| Basic Box | Dragapult Dusknoir | 83% | 55% | 12 | 500 |
| N's Zoroark | Alakazam Dusknoir | 25% | 53% | 12 | 170 |
| Alakazam Dudunsparce | Alakazam Dusknoir | 67% | 39% | 12 | 131 |
| Slowking | Alakazam Dudunsparce | 0% | 27% | 12 | 453 |
| Basic Box | Alakazam Dudunsparce | 17% | 44% | 12 | 533 |
| N's Zoroark | Festival Lead | 50% | 23% | 12 | 328 |
| Festival Lead | Alakazam Dusknoir | 25% | 51% | 12 | 123 |
| Alakazam Dusknoir | Dragapult Blaziken | 67% | 41% | 12 | 134 |
| Basic Box | Festival Lead | 75% | 50% | 12 | 333 |
| N's Zoroark | Dragapult Dusknoir | 33% | 57% | 12 | 481 |
| Hydrapple | Alakazam Dusknoir | 58% | 35% | 12 | 103 |
| Dragapult | Hydrapple | 42% | 64% | 12 | 957 |
| Dragapult | N's Zoroark | 67% | 44% | 12 | 1740 |
| Festival Lead | Dragapult Blaziken | 25% | 47% | 12 | 231 |
| N's Zoroark | Dragapult Blaziken | 42% | 63% | 12 | 448 |
| N's Zoroark | Alakazam Dudunsparce | 33% | 52% | 12 | 446 |
| Dragapult | Festival Lead | 50% | 64% | 12 | 905 |
| Slowking | Festival Lead | 67% | 52% | 12 | 301 |
| Dragapult Dusknoir | Alakazam Dusknoir | 33% | 46% | 12 | 117 |
| Hydrapple | Alakazam Dudunsparce | 50% | 37% | 12 | 243 |
| N's Zoroark | Slowking | 42% | 54% | 12 | 576 |
| Basic Box | Alakazam Dusknoir | 25% | 36% | 12 | 208 |
| Dragapult Dusknoir | Dragapult Blaziken | 58% | 49% | 12 | 335 |
| Festival Lead | Dragapult Dusknoir | 42% | 33% | 12 | 258 |
| Slowking | Dragapult Dusknoir | 67% | 59% | 12 | 422 |
| Slowking | Dragapult Blaziken | 50% | 56% | 12 | 412 |
| Basic Box | Hydrapple | 25% | 31% | 12 | 369 |
| Slowking | Hydrapple | 33% | 39% | 12 | 284 |
| Hydrapple | Dragapult Blaziken | 42% | 37% | 12 | 251 |
| Dragapult | Basic Box | 50% | 45% | 12 | 1863 |
| Slowking | Alakazam Dusknoir | 25% | 29% | 12 | 157 |
| Dragapult | Dragapult Blaziken | 58% | 54% | 12 | 1339 |
| Basic Box | Dragapult Blaziken | 50% | 53% | 12 | 473 |
| N's Zoroark | Hydrapple | 33% | 35% | 12 | 318 |

## How games went

- Endings: prizes 476 (88%), no Pokémon in play 41 (8%), deck out 23 (4%).
- Mean length 16.6 turns; 20 s per game in a worker.
- The player who went first won 54% of 540 decided games.

## Reading this

- Real matchups mix pilots of every level and list variants; the sim plays one list per archetype with one pilot on both sides. A perfect pilot would still not match exactly, but its errors should be close to the noise floor and its lopsidedness close to the real figure.
- Decks far above the line (overrated) are ones the pilot plays well relative to their opponents; decks far below are where its play is worst. Audit those games first (`node dist/archive.js audit --kind fidelity --run fidelity-race-material`).
