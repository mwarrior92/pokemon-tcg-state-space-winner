# Pilot fidelity: fidelity-imitraceb

Pilot `imitrace:runs/imit-v3/policy.json`. 10 meta decks (best-placed complete list of each archetype), every pairing played 12 times with seats alternating: 540 games. Real matchups: matchups_2026-09-19_to_10-31.json (Limitless, all rounds).

## Scores

| score | value | what it means |
|---|---|---|
| correlation, sim vs real matchup win rates | **0.29** | 1 = same order and spacing, 0 = unrelated |
| mean absolute error | **20%** | sampling noise alone would give about 11% |
| lopsidedness (mean distance from 50%) | sim 22%, real 9% | a weak pilot exaggerates matchups; noise adds about 11% to the sim figure |
| rank correlation of deck win rates | **0.21** | do the decks come out in the real order? |
| deck win rate error (mean absolute, each deck against all the others) | **14%** | the steadiest score: sampling noise alone would give about 4% |

## Decks: average win rate against the others

| deck | sim | real | difference |
|---|---|---|---|
| Alakazam Dudunsparce | 71% | 49% | +22 |
| Hydrapple | 67% | 47% | +20 |
| Alakazam Dusknoir | 68% | 54% | +13 |
| Dragapult Blaziken | 62% | 51% | +11 |
| Basic Box | 51% | 47% | +4 |
| Dragapult | 54% | 56% | -2 |
| Slowking | 31% | 46% | -14 |
| Dragapult Dusknoir | 35% | 50% | -15 |
| Festival Lead | 33% | 51% | -17 |
| N's Zoroark | 28% | 49% | -22 |

Sorted from most overrated by the simulator to most underrated.

## Matchups, largest disagreement first

| deck A | deck B | A wins: sim | A wins: real | sim games | real games |
|---|---|---|---|---|---|
| N's Zoroark | Dragapult Blaziken | 8% | 63% | 12 | 448 |
| Alakazam Dudunsparce | Dragapult Dusknoir | 92% | 43% | 12 | 388 |
| Dragapult | N's Zoroark | 92% | 44% | 12 | 1740 |
| Dragapult | Alakazam Dudunsparce | 17% | 63% | 12 | 1308 |
| Dragapult | Hydrapple | 25% | 64% | 12 | 957 |
| Slowking | Hydrapple | 0% | 39% | 12 | 284 |
| Hydrapple | Dragapult Dusknoir | 75% | 39% | 12 | 225 |
| N's Zoroark | Alakazam Dusknoir | 17% | 53% | 12 | 170 |
| Festival Lead | Alakazam Dusknoir | 17% | 51% | 12 | 123 |
| Festival Lead | Dragapult Blaziken | 17% | 47% | 12 | 231 |
| Slowking | Alakazam Dusknoir | 0% | 29% | 12 | 157 |
| Basic Box | Dragapult Dusknoir | 83% | 55% | 12 | 500 |
| N's Zoroark | Alakazam Dudunsparce | 25% | 52% | 12 | 446 |
| Slowking | Alakazam Dudunsparce | 0% | 27% | 12 | 453 |
| Hydrapple | Festival Lead | 67% | 40% | 12 | 181 |
| Basic Box | Festival Lead | 75% | 50% | 12 | 333 |
| Festival Lead | Alakazam Dudunsparce | 33% | 56% | 12 | 233 |
| Hydrapple | Alakazam Dusknoir | 58% | 35% | 12 | 103 |
| Slowking | Dragapult Blaziken | 33% | 56% | 12 | 412 |
| Dragapult | Alakazam Dusknoir | 42% | 61% | 12 | 530 |
| Basic Box | Alakazam Dusknoir | 17% | 36% | 12 | 208 |
| Dragapult | Dragapult Dusknoir | 75% | 57% | 12 | 1308 |
| Dragapult Dusknoir | Dragapult Blaziken | 33% | 49% | 12 | 335 |
| Basic Box | Hydrapple | 17% | 31% | 12 | 369 |
| Dragapult | Slowking | 58% | 45% | 12 | 1604 |
| Hydrapple | Alakazam Dudunsparce | 25% | 37% | 12 | 243 |
| Alakazam Dudunsparce | Dragapult Blaziken | 50% | 38% | 12 | 344 |
| Dragapult | Festival Lead | 75% | 64% | 12 | 905 |
| Basic Box | Alakazam Dudunsparce | 33% | 44% | 12 | 533 |
| N's Zoroark | Hydrapple | 25% | 35% | 12 | 318 |
| Basic Box | N's Zoroark | 58% | 49% | 12 | 677 |
| Festival Lead | Dragapult Dusknoir | 25% | 33% | 12 | 258 |
| Slowking | Dragapult Dusknoir | 67% | 59% | 12 | 422 |
| N's Zoroark | Dragapult Dusknoir | 50% | 57% | 12 | 481 |
| N's Zoroark | Festival Lead | 17% | 23% | 12 | 328 |
| Basic Box | Slowking | 58% | 52% | 12 | 624 |
| Alakazam Dudunsparce | Alakazam Dusknoir | 33% | 39% | 12 | 131 |
| Slowking | Festival Lead | 58% | 52% | 12 | 301 |
| Hydrapple | Dragapult Blaziken | 42% | 37% | 12 | 251 |
| Basic Box | Dragapult Blaziken | 58% | 53% | 12 | 473 |
| N's Zoroark | Slowking | 58% | 54% | 12 | 576 |
| Dragapult | Dragapult Blaziken | 58% | 54% | 12 | 1339 |
| Dragapult Dusknoir | Alakazam Dusknoir | 50% | 46% | 12 | 117 |
| Dragapult | Basic Box | 42% | 45% | 12 | 1863 |
| Alakazam Dusknoir | Dragapult Blaziken | 42% | 41% | 12 | 134 |

## How games went

- Endings: prizes 443 (82%), deck out 72 (13%), no Pokémon in play 25 (5%).
- Mean length 16.9 turns; 18 s per game in a worker.
- The player who went first won 56% of 540 decided games.

## Reading this

- Real matchups mix pilots of every level and list variants; the sim plays one list per archetype with one pilot on both sides. A perfect pilot would still not match exactly, but its errors should be close to the noise floor and its lopsidedness close to the real figure.
- Decks far above the line (overrated) are ones the pilot plays well relative to their opponents; decks far below are where its play is worst. Audit those games first (`node dist/archive.js audit --kind fidelity --run fidelity-imitraceb`).
