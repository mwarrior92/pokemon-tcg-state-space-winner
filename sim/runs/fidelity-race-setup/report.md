# Pilot fidelity: fidelity-race-setup

Pilot `race`. 10 meta decks (best-placed complete list of each archetype), every pairing played 12 times with seats alternating: 540 games. Real matchups: matchups_2026-09-19_to_10-31.json (Limitless, all rounds).

## Scores

| score | value | what it means |
|---|---|---|
| correlation, sim vs real matchup win rates | **-0.18** | 1 = same order and spacing, 0 = unrelated |
| mean absolute error | **23%** | sampling noise alone would give about 12% |
| lopsidedness (mean distance from 50%) | sim 21%, real 9% | a weak pilot exaggerates matchups; noise adds about 12% to the sim figure |
| rank correlation of deck win rates | **-0.12** | do the decks come out in the real order? |
| deck win rate error (mean absolute, each deck against all the others) | **14%** | the steadiest score: sampling noise alone would give about 4% |

## Decks: average win rate against the others

| deck | sim | real | difference |
|---|---|---|---|
| Alakazam Dudunsparce | 78% | 49% | +29 |
| Hydrapple | 68% | 47% | +21 |
| Basic Box | 56% | 47% | +9 |
| Dragapult Blaziken | 58% | 51% | +7 |
| Alakazam Dusknoir | 61% | 54% | +6 |
| Slowking | 39% | 46% | -6 |
| Dragapult Dusknoir | 37% | 50% | -13 |
| N's Zoroark | 34% | 49% | -15 |
| Dragapult | 39% | 56% | -16 |
| Festival Lead | 29% | 51% | -22 |

Sorted from most overrated by the simulator to most underrated.

## Matchups, largest disagreement first

| deck A | deck B | A wins: sim | A wins: real | sim games | real games |
|---|---|---|---|---|---|
| Alakazam Dudunsparce | Dragapult Blaziken | 100% | 38% | 12 | 344 |
| Hydrapple | Festival Lead | 92% | 40% | 12 | 181 |
| Festival Lead | Alakazam Dudunsparce | 8% | 56% | 12 | 233 |
| Dragapult | Alakazam Dusknoir | 17% | 61% | 12 | 530 |
| N's Zoroark | Alakazam Dusknoir | 8% | 53% | 12 | 170 |
| N's Zoroark | Alakazam Dudunsparce | 8% | 52% | 12 | 446 |
| Dragapult | Alakazam Dudunsparce | 25% | 63% | 12 | 1308 |
| N's Zoroark | Dragapult Blaziken | 25% | 63% | 12 | 448 |
| Dragapult | Dragapult Blaziken | 17% | 54% | 12 | 1339 |
| Hydrapple | Dragapult Dusknoir | 75% | 39% | 12 | 225 |
| N's Zoroark | Festival Lead | 58% | 23% | 12 | 328 |
| Festival Lead | Alakazam Dusknoir | 17% | 51% | 12 | 123 |
| Festival Lead | Dragapult Dusknoir | 67% | 33% | 12 | 258 |
| Hydrapple | Alakazam Dusknoir | 67% | 35% | 12 | 103 |
| Dragapult | Hydrapple | 33% | 64% | 12 | 957 |
| Slowking | Dragapult Blaziken | 25% | 56% | 12 | 412 |
| Slowking | Festival Lead | 82% | 52% | 11 | 301 |
| Basic Box | Slowking | 80% | 52% | 10 | 624 |
| Alakazam Dudunsparce | Alakazam Dusknoir | 67% | 39% | 12 | 131 |
| Dragapult Dusknoir | Dragapult Blaziken | 25% | 49% | 12 | 335 |
| N's Zoroark | Dragapult Dusknoir | 33% | 57% | 12 | 481 |
| Basic Box | Alakazam Dusknoir | 58% | 36% | 12 | 208 |
| Dragapult | Basic Box | 25% | 45% | 12 | 1863 |
| Basic Box | Dragapult Dusknoir | 75% | 55% | 12 | 500 |
| Dragapult | Slowking | 64% | 45% | 11 | 1604 |
| Basic Box | Alakazam Dudunsparce | 25% | 44% | 12 | 533 |
| Alakazam Dusknoir | Dragapult Blaziken | 58% | 41% | 12 | 134 |
| Basic Box | Festival Lead | 67% | 50% | 12 | 333 |
| Alakazam Dudunsparce | Dragapult Dusknoir | 58% | 43% | 12 | 388 |
| Slowking | Hydrapple | 25% | 39% | 12 | 284 |
| Festival Lead | Dragapult Blaziken | 33% | 47% | 12 | 231 |
| N's Zoroark | Slowking | 42% | 54% | 12 | 576 |
| Slowking | Alakazam Dudunsparce | 17% | 27% | 12 | 453 |
| N's Zoroark | Hydrapple | 25% | 35% | 12 | 318 |
| Dragapult | Dragapult Dusknoir | 67% | 57% | 12 | 1308 |
| Slowking | Alakazam Dusknoir | 36% | 29% | 11 | 157 |
| Basic Box | Hydrapple | 25% | 31% | 12 | 369 |
| Hydrapple | Dragapult Blaziken | 42% | 37% | 12 | 251 |
| Slowking | Dragapult Dusknoir | 55% | 59% | 11 | 422 |
| Dragapult Dusknoir | Alakazam Dusknoir | 42% | 46% | 12 | 117 |
| Hydrapple | Alakazam Dudunsparce | 42% | 37% | 12 | 243 |
| Basic Box | Dragapult Blaziken | 50% | 53% | 12 | 473 |
| Dragapult | N's Zoroark | 42% | 44% | 12 | 1740 |
| Dragapult | Festival Lead | 67% | 64% | 12 | 905 |
| Basic Box | N's Zoroark | 50% | 49% | 12 | 677 |

## How games went

- Endings: prizes 453 (84%), no Pokémon in play 55 (10%), deck out 26 (5%), turn limit 6 (1%).
- Mean length 19.9 turns; 18 s per game in a worker.
- The player who went first won 50% of 534 decided games.

## Reading this

- Real matchups mix pilots of every level and list variants; the sim plays one list per archetype with one pilot on both sides. A perfect pilot would still not match exactly, but its errors should be close to the noise floor and its lopsidedness close to the real figure.
- Decks far above the line (overrated) are ones the pilot plays well relative to their opponents; decks far below are where its play is worst. Audit those games first (`node dist/archive.js audit --kind fidelity --run fidelity-race-setup`).
