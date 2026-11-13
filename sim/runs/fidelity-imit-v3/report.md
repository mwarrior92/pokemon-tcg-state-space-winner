# Pilot fidelity: fidelity-imit-v3

Pilot `imit:runs/imit-v3/policy.json`. 10 meta decks (best-placed complete list of each archetype), every pairing played 12 times with seats alternating: 540 games. Real matchups: matchups_2026-09-19_to_10-31.json (Limitless, all rounds).

## Scores

| score | value | what it means |
|---|---|---|
| correlation, sim vs real matchup win rates | **-0.00** | 1 = same order and spacing, 0 = unrelated |
| mean absolute error | **24%** | sampling noise alone would give about 11% |
| lopsidedness (mean distance from 50%) | sim 23%, real 9% | a weak pilot exaggerates matchups; noise adds about 11% to the sim figure |
| rank correlation of deck win rates | **-0.26** | do the decks come out in the real order? |
| deck win rate error (mean absolute, each deck against all the others) | **14%** | the steadiest score: sampling noise alone would give about 4% |

## Decks: average win rate against the others

| deck | sim | real | difference |
|---|---|---|---|
| Hydrapple | 72% | 47% | +26 |
| Alakazam Dudunsparce | 67% | 49% | +18 |
| Basic Box | 60% | 47% | +13 |
| Alakazam Dusknoir | 63% | 54% | +9 |
| Dragapult | 57% | 56% | +2 |
| Slowking | 47% | 46% | +1 |
| Dragapult Dusknoir | 44% | 50% | -7 |
| Dragapult Blaziken | 38% | 51% | -13 |
| Festival Lead | 34% | 51% | -16 |
| N's Zoroark | 18% | 49% | -32 |

Sorted from most overrated by the simulator to most underrated.

## Matchups, largest disagreement first

| deck A | deck B | A wins: sim | A wins: real | sim games | real games |
|---|---|---|---|---|---|
| Hydrapple | Festival Lead | 100% | 40% | 12 | 181 |
| Dragapult | N's Zoroark | 100% | 44% | 12 | 1740 |
| Hydrapple | Dragapult Blaziken | 92% | 37% | 12 | 251 |
| N's Zoroark | Dragapult Dusknoir | 8% | 57% | 12 | 481 |
| N's Zoroark | Dragapult Blaziken | 17% | 63% | 12 | 448 |
| Hydrapple | Dragapult Dusknoir | 83% | 39% | 12 | 225 |
| Festival Lead | Alakazam Dusknoir | 8% | 51% | 12 | 123 |
| Basic Box | Festival Lead | 92% | 50% | 12 | 333 |
| Slowking | Alakazam Dusknoir | 67% | 29% | 12 | 157 |
| N's Zoroark | Slowking | 17% | 54% | 12 | 576 |
| Dragapult | Alakazam Dusknoir | 25% | 61% | 12 | 530 |
| N's Zoroark | Alakazam Dusknoir | 17% | 53% | 12 | 170 |
| Alakazam Dudunsparce | Dragapult Dusknoir | 75% | 43% | 12 | 388 |
| Festival Lead | Alakazam Dudunsparce | 25% | 56% | 12 | 233 |
| Dragapult | Slowking | 75% | 45% | 12 | 1604 |
| Slowking | Hydrapple | 8% | 39% | 12 | 284 |
| Festival Lead | Dragapult Blaziken | 75% | 47% | 12 | 231 |
| Alakazam Dudunsparce | Alakazam Dusknoir | 67% | 39% | 12 | 131 |
| Basic Box | N's Zoroark | 75% | 49% | 12 | 677 |
| Alakazam Dusknoir | Dragapult Blaziken | 67% | 41% | 12 | 134 |
| Dragapult | Hydrapple | 42% | 64% | 12 | 957 |
| Dragapult | Alakazam Dudunsparce | 42% | 63% | 12 | 1308 |
| Basic Box | Dragapult Blaziken | 75% | 53% | 12 | 473 |
| Dragapult Dusknoir | Alakazam Dusknoir | 25% | 46% | 12 | 117 |
| Slowking | Dragapult Blaziken | 75% | 56% | 12 | 412 |
| N's Zoroark | Hydrapple | 17% | 35% | 12 | 318 |
| Festival Lead | Dragapult Dusknoir | 50% | 33% | 12 | 258 |
| Dragapult | Dragapult Dusknoir | 42% | 57% | 12 | 1308 |
| Basic Box | Slowking | 67% | 52% | 12 | 624 |
| Basic Box | Alakazam Dusknoir | 50% | 36% | 12 | 208 |
| Slowking | Festival Lead | 67% | 52% | 12 | 301 |
| Dragapult | Dragapult Blaziken | 67% | 54% | 12 | 1339 |
| Hydrapple | Alakazam Dudunsparce | 25% | 37% | 12 | 243 |
| Alakazam Dudunsparce | Dragapult Blaziken | 50% | 38% | 12 | 344 |
| Basic Box | Dragapult Dusknoir | 67% | 55% | 12 | 500 |
| N's Zoroark | Alakazam Dudunsparce | 42% | 52% | 12 | 446 |
| Slowking | Alakazam Dudunsparce | 17% | 27% | 12 | 453 |
| Dragapult | Festival Lead | 75% | 64% | 12 | 905 |
| Slowking | Dragapult Dusknoir | 50% | 59% | 12 | 422 |
| Dragapult Dusknoir | Dragapult Blaziken | 42% | 49% | 12 | 335 |
| N's Zoroark | Festival Lead | 17% | 23% | 12 | 328 |
| Hydrapple | Alakazam Dusknoir | 42% | 35% | 12 | 103 |
| Basic Box | Hydrapple | 25% | 31% | 12 | 369 |
| Dragapult | Basic Box | 50% | 45% | 12 | 1863 |
| Basic Box | Alakazam Dudunsparce | 42% | 44% | 12 | 533 |

## How games went

- Endings: prizes 260 (48%), deck out 191 (35%), no Pokémon in play 89 (16%).
- Mean length 28.2 turns; 3 s per game in a worker.
- The player who went first won 52% of 540 decided games.

## Reading this

- Real matchups mix pilots of every level and list variants; the sim plays one list per archetype with one pilot on both sides. A perfect pilot would still not match exactly, but its errors should be close to the noise floor and its lopsidedness close to the real figure.
- Decks far above the line (overrated) are ones the pilot plays well relative to their opponents; decks far below are where its play is worst. Audit those games first (`node dist/archive.js audit --kind fidelity --run fidelity-imit-v3`).
