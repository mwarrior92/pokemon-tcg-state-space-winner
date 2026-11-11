# Pilot fidelity: fidelity-race-material-rsetup

Pilot `race`. 10 meta decks (best-placed complete list of each archetype), every pairing played 12 times with seats alternating: 540 games. Real matchups: matchups_2026-09-19_to_10-31.json (Limitless, all rounds).

## Scores

| score | value | what it means |
|---|---|---|
| correlation, sim vs real matchup win rates | **0.17** | 1 = same order and spacing, 0 = unrelated |
| mean absolute error | **20%** | sampling noise alone would give about 11% |
| lopsidedness (mean distance from 50%) | sim 20%, real 9% | a weak pilot exaggerates matchups; noise adds about 11% to the sim figure |
| rank correlation of deck win rates | **-0.12** | do the decks come out in the real order? |
| deck win rate error (mean absolute, each deck against all the others) | **13%** | the steadiest score: sampling noise alone would give about 4% |

## Decks: average win rate against the others

| deck | sim | real | difference |
|---|---|---|---|
| Alakazam Dudunsparce | 80% | 49% | +31 |
| Hydrapple | 62% | 47% | +15 |
| Alakazam Dusknoir | 63% | 54% | +9 |
| Basic Box | 53% | 47% | +6 |
| Dragapult Blaziken | 54% | 51% | +2 |
| Slowking | 45% | 46% | -0 |
| Dragapult | 44% | 56% | -11 |
| N's Zoroark | 33% | 49% | -16 |
| Festival Lead | 33% | 51% | -17 |
| Dragapult Dusknoir | 32% | 50% | -18 |

Sorted from most overrated by the simulator to most underrated.

## Matchups, largest disagreement first

| deck A | deck B | A wins: sim | A wins: real | sim games | real games |
|---|---|---|---|---|---|
| Alakazam Dudunsparce | Alakazam Dusknoir | 92% | 39% | 12 | 131 |
| Dragapult | Alakazam Dusknoir | 17% | 61% | 12 | 530 |
| Hydrapple | Dragapult Dusknoir | 83% | 39% | 12 | 225 |
| Alakazam Dudunsparce | Dragapult Dusknoir | 83% | 43% | 12 | 388 |
| Basic Box | Slowking | 92% | 52% | 12 | 624 |
| Dragapult | Alakazam Dudunsparce | 25% | 63% | 12 | 1308 |
| N's Zoroark | Alakazam Dusknoir | 17% | 53% | 12 | 170 |
| N's Zoroark | Alakazam Dudunsparce | 17% | 52% | 12 | 446 |
| Hydrapple | Festival Lead | 75% | 40% | 12 | 181 |
| Basic Box | Festival Lead | 83% | 50% | 12 | 333 |
| N's Zoroark | Dragapult Blaziken | 33% | 63% | 12 | 448 |
| Dragapult Dusknoir | Alakazam Dusknoir | 17% | 46% | 12 | 117 |
| Dragapult | Dragapult Blaziken | 25% | 54% | 12 | 1339 |
| N's Zoroark | Slowking | 25% | 54% | 12 | 576 |
| Alakazam Dudunsparce | Dragapult Blaziken | 67% | 38% | 12 | 344 |
| Slowking | Alakazam Dudunsparce | 0% | 27% | 12 | 453 |
| Festival Lead | Alakazam Dudunsparce | 33% | 56% | 12 | 233 |
| Hydrapple | Alakazam Dusknoir | 58% | 35% | 12 | 103 |
| Slowking | Festival Lead | 75% | 52% | 12 | 301 |
| Basic Box | Hydrapple | 8% | 31% | 12 | 369 |
| Basic Box | Alakazam Dudunsparce | 25% | 44% | 12 | 533 |
| N's Zoroark | Festival Lead | 42% | 23% | 12 | 328 |
| N's Zoroark | Hydrapple | 17% | 35% | 12 | 318 |
| Festival Lead | Alakazam Dusknoir | 33% | 51% | 12 | 123 |
| Slowking | Dragapult Dusknoir | 75% | 59% | 12 | 422 |
| Dragapult | Hydrapple | 50% | 64% | 12 | 957 |
| Dragapult | N's Zoroark | 58% | 44% | 12 | 1740 |
| Slowking | Alakazam Dusknoir | 17% | 29% | 12 | 157 |
| Hydrapple | Alakazam Dudunsparce | 25% | 37% | 12 | 243 |
| Slowking | Hydrapple | 50% | 39% | 12 | 284 |
| Dragapult | Festival Lead | 75% | 64% | 12 | 905 |
| Basic Box | N's Zoroark | 58% | 49% | 12 | 677 |
| N's Zoroark | Dragapult Dusknoir | 67% | 57% | 12 | 481 |
| Alakazam Dusknoir | Dragapult Blaziken | 50% | 41% | 12 | 134 |
| Festival Lead | Dragapult Dusknoir | 42% | 33% | 12 | 258 |
| Dragapult Dusknoir | Dragapult Blaziken | 42% | 49% | 12 | 335 |
| Dragapult | Slowking | 50% | 45% | 12 | 1604 |
| Festival Lead | Dragapult Blaziken | 42% | 47% | 12 | 231 |
| Hydrapple | Dragapult Blaziken | 42% | 37% | 12 | 251 |
| Basic Box | Dragapult Blaziken | 58% | 53% | 12 | 473 |
| Dragapult | Basic Box | 42% | 45% | 12 | 1863 |
| Basic Box | Dragapult Dusknoir | 58% | 55% | 12 | 500 |
| Slowking | Dragapult Blaziken | 58% | 56% | 12 | 412 |
| Basic Box | Alakazam Dusknoir | 33% | 36% | 12 | 208 |
| Dragapult | Dragapult Dusknoir | 58% | 57% | 12 | 1308 |

## How games went

- Endings: prizes 477 (88%), no Pokémon in play 39 (7%), deck out 24 (4%).
- Mean length 16.5 turns; 22 s per game in a worker.
- The player who went first won 53% of 540 decided games.

## Reading this

- Real matchups mix pilots of every level and list variants; the sim plays one list per archetype with one pilot on both sides. A perfect pilot would still not match exactly, but its errors should be close to the noise floor and its lopsidedness close to the real figure.
- Decks far above the line (overrated) are ones the pilot plays well relative to their opponents; decks far below are where its play is worst. Audit those games first (`node dist/archive.js audit --kind fidelity --run fidelity-race-material-rsetup`).
