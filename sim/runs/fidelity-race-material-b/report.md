# Pilot fidelity: fidelity-race-material-b

Pilot `race`. 10 meta decks (best-placed complete list of each archetype), every pairing played 12 times with seats alternating: 540 games. Real matchups: matchups_2026-09-19_to_10-31.json (Limitless, all rounds).

## Scores

| score | value | what it means |
|---|---|---|
| correlation, sim vs real matchup win rates | **0.11** | 1 = same order and spacing, 0 = unrelated |
| mean absolute error | **17%** | sampling noise alone would give about 11% |
| lopsidedness (mean distance from 50%) | sim 15%, real 9% | a weak pilot exaggerates matchups; noise adds about 11% to the sim figure |
| rank correlation of deck win rates | **-0.03** | do the decks come out in the real order? |
| deck win rate error (mean absolute, each deck against all the others) | **10%** | the steadiest score: sampling noise alone would give about 4% |

## Decks: average win rate against the others

| deck | sim | real | difference |
|---|---|---|---|
| Hydrapple | 67% | 47% | +20 |
| Alakazam Dudunsparce | 63% | 49% | +14 |
| Basic Box | 56% | 47% | +9 |
| Dragapult | 60% | 56% | +5 |
| Alakazam Dusknoir | 56% | 54% | +1 |
| Dragapult Blaziken | 51% | 51% | -0 |
| N's Zoroark | 44% | 49% | -5 |
| Slowking | 34% | 46% | -12 |
| Festival Lead | 35% | 51% | -16 |
| Dragapult Dusknoir | 33% | 50% | -17 |

Sorted from most overrated by the simulator to most underrated.

## Matchups, largest disagreement first

| deck A | deck B | A wins: sim | A wins: real | sim games | real games |
|---|---|---|---|---|---|
| Hydrapple | Dragapult Dusknoir | 83% | 39% | 12 | 225 |
| Hydrapple | Festival Lead | 83% | 40% | 12 | 181 |
| Hydrapple | Alakazam Dudunsparce | 75% | 37% | 12 | 243 |
| Basic Box | Dragapult Dusknoir | 92% | 55% | 12 | 500 |
| Festival Lead | Alakazam Dusknoir | 17% | 51% | 12 | 123 |
| Alakazam Dudunsparce | Dragapult Dusknoir | 75% | 43% | 12 | 388 |
| Festival Lead | Alakazam Dudunsparce | 25% | 56% | 12 | 233 |
| Dragapult | Slowking | 75% | 45% | 12 | 1604 |
| Festival Lead | Dragapult Blaziken | 17% | 47% | 12 | 231 |
| Hydrapple | Dragapult Blaziken | 67% | 37% | 12 | 251 |
| Alakazam Dudunsparce | Alakazam Dusknoir | 67% | 39% | 12 | 131 |
| N's Zoroark | Festival Lead | 50% | 23% | 12 | 328 |
| Slowking | Dragapult Blaziken | 33% | 56% | 12 | 412 |
| Dragapult | Alakazam Dudunsparce | 42% | 63% | 12 | 1308 |
| Alakazam Dudunsparce | Dragapult Blaziken | 58% | 38% | 12 | 344 |
| Slowking | Festival Lead | 33% | 52% | 12 | 301 |
| N's Zoroark | Alakazam Dudunsparce | 33% | 52% | 12 | 446 |
| Basic Box | N's Zoroark | 67% | 49% | 12 | 677 |
| Alakazam Dusknoir | Dragapult Blaziken | 58% | 41% | 12 | 134 |
| Dragapult | Dragapult Dusknoir | 75% | 57% | 12 | 1308 |
| Dragapult Dusknoir | Dragapult Blaziken | 33% | 49% | 12 | 335 |
| Basic Box | Slowking | 67% | 52% | 12 | 624 |
| Hydrapple | Alakazam Dusknoir | 50% | 35% | 12 | 103 |
| Basic Box | Alakazam Dusknoir | 50% | 36% | 12 | 208 |
| Slowking | Hydrapple | 25% | 39% | 12 | 284 |
| N's Zoroark | Dragapult Blaziken | 50% | 63% | 12 | 448 |
| Dragapult | Dragapult Blaziken | 67% | 54% | 12 | 1339 |
| Dragapult | Alakazam Dusknoir | 50% | 61% | 12 | 530 |
| Basic Box | Hydrapple | 42% | 31% | 12 | 369 |
| Basic Box | Alakazam Dudunsparce | 33% | 44% | 12 | 533 |
| N's Zoroark | Hydrapple | 25% | 35% | 12 | 318 |
| Slowking | Dragapult Dusknoir | 50% | 59% | 12 | 422 |
| Festival Lead | Dragapult Dusknoir | 42% | 33% | 12 | 258 |
| Dragapult | N's Zoroark | 50% | 44% | 12 | 1740 |
| Basic Box | Dragapult Blaziken | 58% | 53% | 12 | 473 |
| Dragapult | Basic Box | 50% | 45% | 12 | 1863 |
| Dragapult Dusknoir | Alakazam Dusknoir | 42% | 46% | 12 | 117 |
| Slowking | Alakazam Dusknoir | 33% | 29% | 12 | 157 |
| N's Zoroark | Slowking | 50% | 54% | 12 | 576 |
| N's Zoroark | Alakazam Dusknoir | 50% | 53% | 12 | 170 |
| Dragapult | Hydrapple | 67% | 64% | 12 | 957 |
| Slowking | Alakazam Dudunsparce | 25% | 27% | 12 | 453 |
| Dragapult | Festival Lead | 67% | 64% | 12 | 905 |
| N's Zoroark | Dragapult Dusknoir | 58% | 57% | 12 | 481 |
| Basic Box | Festival Lead | 50% | 50% | 12 | 333 |

## How games went

- Endings: prizes 474 (88%), no Pokémon in play 41 (8%), deck out 25 (5%).
- Mean length 17.2 turns; 22 s per game in a worker.
- The player who went first won 53% of 540 decided games.

## Reading this

- Real matchups mix pilots of every level and list variants; the sim plays one list per archetype with one pilot on both sides. A perfect pilot would still not match exactly, but its errors should be close to the noise floor and its lopsidedness close to the real figure.
- Decks far above the line (overrated) are ones the pilot plays well relative to their opponents; decks far below are where its play is worst. Audit those games first (`node dist/archive.js audit --kind fidelity --run fidelity-race-material-b`).
