# Pilot fidelity: fidelity-plan2

Pilot `plan2:runs/value-v2/value-model.json`. 10 meta decks (best-placed complete list of each archetype), every pairing played 12 times with seats alternating: 540 games. Real matchups: matchups_2026-09-19_to_10-31.json (Limitless, all rounds).

## Scores

| score | value | what it means |
|---|---|---|
| correlation, sim vs real matchup win rates | **0.02** | 1 = same order and spacing, 0 = unrelated |
| mean absolute error | **18%** | sampling noise alone would give about 11% |
| lopsidedness (mean distance from 50%) | sim 16%, real 9% | a weak pilot exaggerates matchups; noise adds about 11% to the sim figure |
| rank correlation of deck win rates | **0.16** | do the decks come out in the real order? |
| deck win rate error (mean absolute, each deck against all the others) | **11%** | the steadiest score: sampling noise alone would give about 4% |

## Decks: average win rate against the others

| deck | sim | real | difference |
|---|---|---|---|
| Alakazam Dudunsparce | 65% | 49% | +16 |
| Dragapult Blaziken | 61% | 51% | +10 |
| Hydrapple | 56% | 47% | +10 |
| Alakazam Dusknoir | 64% | 54% | +9 |
| Basic Box | 56% | 47% | +9 |
| N's Zoroark | 42% | 49% | -7 |
| Dragapult Dusknoir | 43% | 50% | -8 |
| Dragapult | 47% | 56% | -8 |
| Slowking | 36% | 46% | -10 |
| Festival Lead | 30% | 51% | -21 |

Sorted from most overrated by the simulator to most underrated.

## Matchups, largest disagreement first

| deck A | deck B | A wins: sim | A wins: real | sim games | real games |
|---|---|---|---|---|---|
| Dragapult | Alakazam Dusknoir | 8% | 61% | 12 | 530 |
| Hydrapple | Festival Lead | 83% | 40% | 12 | 181 |
| Basic Box | Slowking | 91% | 52% | 11 | 624 |
| N's Zoroark | Dragapult Blaziken | 25% | 63% | 12 | 448 |
| Festival Lead | Alakazam Dusknoir | 17% | 51% | 12 | 123 |
| Dragapult Dusknoir | Dragapult Blaziken | 17% | 49% | 12 | 335 |
| Slowking | Dragapult Blaziken | 25% | 56% | 12 | 412 |
| Dragapult | Alakazam Dudunsparce | 33% | 63% | 12 | 1308 |
| Slowking | Festival Lead | 82% | 52% | 11 | 301 |
| N's Zoroark | Alakazam Dudunsparce | 25% | 52% | 12 | 446 |
| Dragapult | Festival Lead | 92% | 64% | 12 | 905 |
| Slowking | Dragapult Dusknoir | 33% | 59% | 12 | 422 |
| Alakazam Dudunsparce | Dragapult Dusknoir | 67% | 43% | 12 | 388 |
| Festival Lead | Alakazam Dudunsparce | 33% | 56% | 12 | 233 |
| Dragapult | Hydrapple | 42% | 64% | 12 | 957 |
| Dragapult Dusknoir | Alakazam Dusknoir | 25% | 46% | 12 | 117 |
| Dragapult | Basic Box | 25% | 45% | 12 | 1863 |
| Alakazam Dudunsparce | Dragapult Blaziken | 58% | 38% | 12 | 344 |
| Basic Box | Hydrapple | 50% | 31% | 12 | 369 |
| N's Zoroark | Alakazam Dusknoir | 33% | 53% | 12 | 170 |
| Alakazam Dudunsparce | Alakazam Dusknoir | 58% | 39% | 12 | 131 |
| N's Zoroark | Festival Lead | 42% | 23% | 12 | 328 |
| Basic Box | N's Zoroark | 33% | 49% | 12 | 677 |
| Hydrapple | Alakazam Dusknoir | 50% | 35% | 12 | 103 |
| Dragapult | N's Zoroark | 58% | 44% | 12 | 1740 |
| Dragapult | Slowking | 58% | 45% | 12 | 1604 |
| Festival Lead | Dragapult Blaziken | 33% | 47% | 12 | 231 |
| Basic Box | Dragapult Dusknoir | 67% | 55% | 12 | 500 |
| Slowking | Hydrapple | 27% | 39% | 11 | 284 |
| Hydrapple | Dragapult Dusknoir | 50% | 39% | 12 | 225 |
| Festival Lead | Dragapult Dusknoir | 42% | 33% | 12 | 258 |
| Basic Box | Festival Lead | 58% | 50% | 12 | 333 |
| Dragapult | Dragapult Dusknoir | 50% | 57% | 12 | 1308 |
| N's Zoroark | Dragapult Dusknoir | 50% | 57% | 12 | 481 |
| N's Zoroark | Hydrapple | 42% | 35% | 12 | 318 |
| Basic Box | Alakazam Dusknoir | 42% | 36% | 12 | 208 |
| Hydrapple | Dragapult Blaziken | 42% | 37% | 12 | 251 |
| Hydrapple | Alakazam Dudunsparce | 42% | 37% | 12 | 243 |
| Slowking | Alakazam Dusknoir | 33% | 29% | 12 | 157 |
| Dragapult | Dragapult Blaziken | 58% | 54% | 12 | 1339 |
| Basic Box | Dragapult Blaziken | 50% | 53% | 12 | 473 |
| Slowking | Alakazam Dudunsparce | 25% | 27% | 12 | 453 |
| Basic Box | Alakazam Dudunsparce | 42% | 44% | 12 | 533 |
| Alakazam Dusknoir | Dragapult Blaziken | 42% | 41% | 12 | 134 |
| N's Zoroark | Slowking | 55% | 54% | 11 | 576 |

## How games went

- Endings: prizes 479 (89%), no Pokémon in play 47 (9%), deck out 10 (2%), turn limit 4 (1%).
- Mean length 21.7 turns; 200 s per game in a worker.
- The player who went first won 52% of 536 decided games.

## Reading this

- Real matchups mix pilots of every level and list variants; the sim plays one list per archetype with one pilot on both sides. A perfect pilot would still not match exactly, but its errors should be close to the noise floor and its lopsidedness close to the real figure.
- Decks far above the line (overrated) are ones the pilot plays well relative to their opponents; decks far below are where its play is worst. Audit those games first (`node dist/archive.js audit --kind fidelity --run fidelity-plan2`).
