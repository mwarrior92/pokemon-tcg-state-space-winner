# Pilot fidelity: fidelity-imitrace-v3

Pilot `imitrace:runs/imit-v3/policy.json`. 10 meta decks (best-placed complete list of each archetype), every pairing played 12 times with seats alternating: 540 games. Real matchups: matchups_2026-09-19_to_10-31.json (Limitless, all rounds).

## Scores

| score | value | what it means |
|---|---|---|
| correlation, sim vs real matchup win rates | **0.13** | 1 = same order and spacing, 0 = unrelated |
| mean absolute error | **22%** | sampling noise alone would give about 11% |
| lopsidedness (mean distance from 50%) | sim 21%, real 9% | a weak pilot exaggerates matchups; noise adds about 11% to the sim figure |
| rank correlation of deck win rates | **-0.09** | do the decks come out in the real order? |
| deck win rate error (mean absolute, each deck against all the others) | **14%** | the steadiest score: sampling noise alone would give about 4% |

## Decks: average win rate against the others

| deck | sim | real | difference |
|---|---|---|---|
| Alakazam Dudunsparce | 78% | 49% | +29 |
| Hydrapple | 74% | 47% | +27 |
| Basic Box | 61% | 47% | +14 |
| Dragapult Blaziken | 52% | 51% | +1 |
| Alakazam Dusknoir | 53% | 54% | -2 |
| Dragapult | 48% | 56% | -7 |
| Slowking | 35% | 46% | -11 |
| Dragapult Dusknoir | 36% | 50% | -14 |
| Festival Lead | 35% | 51% | -16 |
| N's Zoroark | 28% | 49% | -22 |

Sorted from most overrated by the simulator to most underrated.

## Matchups, largest disagreement first

| deck A | deck B | A wins: sim | A wins: real | sim games | real games |
|---|---|---|---|---|---|
| Dragapult | Hydrapple | 8% | 64% | 12 | 957 |
| Dragapult | Alakazam Dudunsparce | 8% | 63% | 12 | 1308 |
| N's Zoroark | Dragapult Blaziken | 8% | 63% | 12 | 448 |
| Alakazam Dudunsparce | Dragapult Dusknoir | 92% | 43% | 12 | 388 |
| Dragapult | N's Zoroark | 92% | 44% | 12 | 1740 |
| Alakazam Dudunsparce | Dragapult Blaziken | 83% | 38% | 12 | 344 |
| Hydrapple | Alakazam Dusknoir | 75% | 35% | 12 | 103 |
| Alakazam Dudunsparce | Alakazam Dusknoir | 75% | 39% | 12 | 131 |
| Hydrapple | Festival Lead | 75% | 40% | 12 | 181 |
| Basic Box | N's Zoroark | 83% | 49% | 12 | 677 |
| Festival Lead | Alakazam Dusknoir | 17% | 51% | 12 | 123 |
| Basic Box | Festival Lead | 83% | 50% | 12 | 333 |
| Basic Box | Hydrapple | 0% | 31% | 12 | 369 |
| Slowking | Hydrapple | 8% | 39% | 12 | 284 |
| Basic Box | Dragapult Dusknoir | 83% | 55% | 12 | 500 |
| Hydrapple | Dragapult Dusknoir | 67% | 39% | 12 | 225 |
| Dragapult Dusknoir | Dragapult Blaziken | 25% | 49% | 12 | 335 |
| Basic Box | Slowking | 75% | 52% | 12 | 624 |
| Festival Lead | Alakazam Dudunsparce | 33% | 56% | 12 | 233 |
| Hydrapple | Dragapult Blaziken | 58% | 37% | 12 | 251 |
| Dragapult | Basic Box | 25% | 45% | 12 | 1863 |
| Slowking | Alakazam Dudunsparce | 8% | 27% | 12 | 453 |
| N's Zoroark | Hydrapple | 17% | 35% | 12 | 318 |
| Dragapult | Dragapult Dusknoir | 75% | 57% | 12 | 1308 |
| Basic Box | Alakazam Dusknoir | 50% | 36% | 12 | 208 |
| Slowking | Festival Lead | 67% | 52% | 12 | 301 |
| Dragapult | Slowking | 58% | 45% | 12 | 1604 |
| Basic Box | Dragapult Blaziken | 67% | 53% | 12 | 473 |
| Slowking | Alakazam Dusknoir | 17% | 29% | 12 | 157 |
| Hydrapple | Alakazam Dudunsparce | 25% | 37% | 12 | 243 |
| Dragapult | Alakazam Dusknoir | 50% | 61% | 12 | 530 |
| N's Zoroark | Alakazam Dusknoir | 42% | 53% | 12 | 170 |
| N's Zoroark | Alakazam Dudunsparce | 42% | 52% | 12 | 446 |
| Basic Box | Alakazam Dudunsparce | 33% | 44% | 12 | 533 |
| Slowking | Dragapult Dusknoir | 50% | 59% | 12 | 422 |
| Alakazam Dusknoir | Dragapult Blaziken | 50% | 41% | 12 | 134 |
| N's Zoroark | Dragapult Dusknoir | 50% | 57% | 12 | 481 |
| N's Zoroark | Festival Lead | 17% | 23% | 12 | 328 |
| Slowking | Dragapult Blaziken | 50% | 56% | 12 | 412 |
| Festival Lead | Dragapult Blaziken | 42% | 47% | 12 | 231 |
| Dragapult | Dragapult Blaziken | 50% | 54% | 12 | 1339 |
| N's Zoroark | Slowking | 50% | 54% | 12 | 576 |
| Dragapult Dusknoir | Alakazam Dusknoir | 50% | 46% | 12 | 117 |
| Dragapult | Festival Lead | 67% | 64% | 12 | 905 |
| Festival Lead | Dragapult Dusknoir | 33% | 33% | 12 | 258 |

## How games went

- Endings: prizes 389 (72%), deck out 125 (23%), no Pokémon in play 26 (5%).
- Mean length 20.7 turns; 11 s per game in a worker.
- The player who went first won 54% of 540 decided games.

## Reading this

- Real matchups mix pilots of every level and list variants; the sim plays one list per archetype with one pilot on both sides. A perfect pilot would still not match exactly, but its errors should be close to the noise floor and its lopsidedness close to the real figure.
- Decks far above the line (overrated) are ones the pilot plays well relative to their opponents; decks far below are where its play is worst. Audit those games first (`node dist/archive.js audit --kind fidelity --run fidelity-imitrace-v3`).
