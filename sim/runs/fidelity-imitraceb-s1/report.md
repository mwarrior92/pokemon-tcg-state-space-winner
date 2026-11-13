# Pilot fidelity: fidelity-imitraceb-s1

Pilot `imitrace:runs/imit-v3/policy.json`. 10 meta decks (best-placed complete list of each archetype), every pairing played 12 times with seats alternating: 540 games. Real matchups: matchups_2026-09-19_to_10-31.json (Limitless, all rounds).

## Scores

| score | value | what it means |
|---|---|---|
| correlation, sim vs real matchup win rates | **0.18** | 1 = same order and spacing, 0 = unrelated |
| mean absolute error | **22%** | sampling noise alone would give about 11% |
| lopsidedness (mean distance from 50%) | sim 22%, real 9% | a weak pilot exaggerates matchups; noise adds about 11% to the sim figure |
| rank correlation of deck win rates | **0.15** | do the decks come out in the real order? |
| deck win rate error (mean absolute, each deck against all the others) | **12%** | the steadiest score: sampling noise alone would give about 4% |

## Decks: average win rate against the others

| deck | sim | real | difference |
|---|---|---|---|
| Alakazam Dudunsparce | 74% | 49% | +25 |
| Hydrapple | 70% | 47% | +24 |
| Dragapult Blaziken | 59% | 51% | +8 |
| Dragapult | 61% | 56% | +5 |
| Basic Box | 46% | 47% | -1 |
| Alakazam Dusknoir | 51% | 54% | -4 |
| Slowking | 38% | 46% | -8 |
| Dragapult Dusknoir | 40% | 50% | -10 |
| Festival Lead | 39% | 51% | -12 |
| N's Zoroark | 21% | 49% | -28 |

Sorted from most overrated by the simulator to most underrated.

## Matchups, largest disagreement first

| deck A | deck B | A wins: sim | A wins: real | sim games | real games |
|---|---|---|---|---|---|
| Hydrapple | Alakazam Dusknoir | 83% | 35% | 12 | 103 |
| Dragapult | Alakazam Dudunsparce | 17% | 63% | 12 | 1308 |
| N's Zoroark | Dragapult Blaziken | 17% | 63% | 12 | 448 |
| N's Zoroark | Slowking | 8% | 54% | 12 | 576 |
| N's Zoroark | Alakazam Dudunsparce | 8% | 52% | 12 | 446 |
| Basic Box | Alakazam Dudunsparce | 0% | 44% | 12 | 533 |
| Festival Lead | Alakazam Dusknoir | 8% | 51% | 12 | 123 |
| Alakazam Dudunsparce | Alakazam Dusknoir | 75% | 39% | 12 | 131 |
| N's Zoroark | Hydrapple | 0% | 35% | 12 | 318 |
| N's Zoroark | Dragapult Dusknoir | 25% | 57% | 12 | 481 |
| Alakazam Dudunsparce | Dragapult Dusknoir | 75% | 43% | 12 | 388 |
| Slowking | Hydrapple | 8% | 39% | 12 | 284 |
| Hydrapple | Alakazam Dudunsparce | 67% | 37% | 12 | 243 |
| Dragapult | Dragapult Blaziken | 25% | 54% | 12 | 1339 |
| Alakazam Dudunsparce | Dragapult Blaziken | 67% | 38% | 12 | 344 |
| Basic Box | Dragapult Dusknoir | 83% | 55% | 12 | 500 |
| Dragapult | Slowking | 73% | 45% | 11 | 1604 |
| Hydrapple | Dragapult Dusknoir | 67% | 39% | 12 | 225 |
| N's Zoroark | Alakazam Dusknoir | 25% | 53% | 12 | 170 |
| Hydrapple | Festival Lead | 67% | 40% | 12 | 181 |
| Dragapult | N's Zoroark | 67% | 44% | 12 | 1740 |
| Dragapult | Alakazam Dusknoir | 83% | 61% | 12 | 530 |
| Festival Lead | Dragapult Blaziken | 25% | 47% | 12 | 231 |
| Slowking | Alakazam Dudunsparce | 8% | 27% | 12 | 453 |
| Dragapult | Festival Lead | 83% | 64% | 12 | 905 |
| Festival Lead | Dragapult Dusknoir | 50% | 33% | 12 | 258 |
| Basic Box | Festival Lead | 67% | 50% | 12 | 333 |
| Basic Box | Slowking | 67% | 52% | 12 | 624 |
| Slowking | Dragapult Blaziken | 42% | 56% | 12 | 412 |
| Basic Box | Hydrapple | 17% | 31% | 12 | 369 |
| Hydrapple | Dragapult Blaziken | 50% | 37% | 12 | 251 |
| Dragapult | Basic Box | 58% | 45% | 12 | 1863 |
| Dragapult | Hydrapple | 75% | 64% | 12 | 957 |
| Slowking | Festival Lead | 42% | 52% | 12 | 301 |
| Dragapult | Dragapult Dusknoir | 67% | 57% | 12 | 1308 |
| Dragapult Dusknoir | Dragapult Blaziken | 42% | 49% | 12 | 335 |
| Slowking | Dragapult Dusknoir | 67% | 59% | 12 | 422 |
| Festival Lead | Alakazam Dudunsparce | 50% | 56% | 12 | 233 |
| Basic Box | Dragapult Blaziken | 58% | 53% | 12 | 473 |
| Slowking | Alakazam Dusknoir | 25% | 29% | 12 | 157 |
| Dragapult Dusknoir | Alakazam Dusknoir | 50% | 46% | 12 | 117 |
| Basic Box | Alakazam Dusknoir | 33% | 36% | 12 | 208 |
| N's Zoroark | Festival Lead | 25% | 23% | 12 | 328 |
| Basic Box | N's Zoroark | 50% | 49% | 12 | 677 |
| Alakazam Dusknoir | Dragapult Blaziken | 42% | 41% | 12 | 134 |

## How games went

- Endings: prizes 442 (82%), deck out 63 (12%), no Pokémon in play 34 (6%), turn limit 1 (0%).
- Mean length 17.3 turns; 20 s per game in a worker.
- The player who went first won 54% of 539 decided games.

## Reading this

- Real matchups mix pilots of every level and list variants; the sim plays one list per archetype with one pilot on both sides. A perfect pilot would still not match exactly, but its errors should be close to the noise floor and its lopsidedness close to the real figure.
- Decks far above the line (overrated) are ones the pilot plays well relative to their opponents; decks far below are where its play is worst. Audit those games first (`node dist/archive.js audit --kind fidelity --run fidelity-imitraceb-s1`).
