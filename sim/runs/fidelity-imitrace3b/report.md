# Pilot fidelity: fidelity-imitrace3b

Pilot `imitrace:runs/imit-v3/policy.json`. 10 meta decks (best-placed complete list of each archetype), every pairing played 12 times with seats alternating: 540 games. Real matchups: matchups_2026-09-19_to_10-31.json (Limitless, all rounds).

## Scores

| score | value | what it means |
|---|---|---|
| correlation, sim vs real matchup win rates | **0.16** | 1 = same order and spacing, 0 = unrelated |
| mean absolute error | **21%** | sampling noise alone would give about 11% |
| lopsidedness (mean distance from 50%) | sim 21%, real 9% | a weak pilot exaggerates matchups; noise adds about 11% to the sim figure |
| rank correlation of deck win rates | **0.03** | do the decks come out in the real order? |
| deck win rate error (mean absolute, each deck against all the others) | **13%** | the steadiest score: sampling noise alone would give about 4% |

## Decks: average win rate against the others

| deck | sim | real | difference |
|---|---|---|---|
| Alakazam Dudunsparce | 74% | 49% | +25 |
| Hydrapple | 69% | 47% | +22 |
| Alakazam Dusknoir | 62% | 54% | +8 |
| Basic Box | 54% | 47% | +7 |
| Dragapult | 57% | 56% | +2 |
| Dragapult Blaziken | 52% | 51% | +1 |
| N's Zoroark | 38% | 49% | -11 |
| Dragapult Dusknoir | 36% | 50% | -14 |
| Slowking | 31% | 46% | -15 |
| Festival Lead | 28% | 51% | -23 |

Sorted from most overrated by the simulator to most underrated.

## Matchups, largest disagreement first

| deck A | deck B | A wins: sim | A wins: real | sim games | real games |
|---|---|---|---|---|---|
| Festival Lead | Alakazam Dusknoir | 0% | 51% | 12 | 123 |
| Alakazam Dudunsparce | Dragapult Dusknoir | 92% | 43% | 12 | 388 |
| Festival Lead | Alakazam Dudunsparce | 8% | 56% | 12 | 233 |
| Alakazam Dudunsparce | Dragapult Blaziken | 83% | 38% | 12 | 344 |
| Dragapult | Slowking | 83% | 45% | 12 | 1604 |
| Slowking | Hydrapple | 0% | 39% | 12 | 284 |
| Festival Lead | Dragapult Blaziken | 8% | 47% | 12 | 231 |
| Hydrapple | Dragapult Blaziken | 75% | 37% | 12 | 251 |
| Hydrapple | Festival Lead | 75% | 40% | 12 | 181 |
| Dragapult Dusknoir | Dragapult Blaziken | 17% | 49% | 12 | 335 |
| Hydrapple | Alakazam Dusknoir | 67% | 35% | 12 | 103 |
| Dragapult | Hydrapple | 33% | 64% | 12 | 957 |
| Dragapult | N's Zoroark | 75% | 44% | 12 | 1740 |
| Dragapult | Alakazam Dudunsparce | 33% | 63% | 12 | 1308 |
| N's Zoroark | Dragapult Blaziken | 33% | 63% | 12 | 448 |
| Basic Box | Dragapult Dusknoir | 83% | 55% | 12 | 500 |
| Slowking | Dragapult Dusknoir | 33% | 59% | 12 | 422 |
| Basic Box | Festival Lead | 75% | 50% | 12 | 333 |
| Basic Box | Slowking | 75% | 52% | 12 | 624 |
| Hydrapple | Dragapult Dusknoir | 58% | 39% | 12 | 225 |
| N's Zoroark | Alakazam Dusknoir | 33% | 53% | 12 | 170 |
| N's Zoroark | Alakazam Dudunsparce | 33% | 52% | 12 | 446 |
| Slowking | Alakazam Dudunsparce | 8% | 27% | 12 | 453 |
| N's Zoroark | Hydrapple | 17% | 35% | 12 | 318 |
| Dragapult | Dragapult Dusknoir | 75% | 57% | 12 | 1308 |
| Dragapult | Basic Box | 58% | 45% | 12 | 1863 |
| N's Zoroark | Slowking | 67% | 54% | 12 | 576 |
| Hydrapple | Alakazam Dudunsparce | 25% | 37% | 12 | 243 |
| Dragapult | Alakazam Dusknoir | 50% | 61% | 12 | 530 |
| Slowking | Dragapult Blaziken | 67% | 56% | 12 | 412 |
| Basic Box | Alakazam Dusknoir | 25% | 36% | 12 | 208 |
| Basic Box | N's Zoroark | 58% | 49% | 12 | 677 |
| N's Zoroark | Dragapult Dusknoir | 67% | 57% | 12 | 481 |
| Alakazam Dusknoir | Dragapult Blaziken | 50% | 41% | 12 | 134 |
| Festival Lead | Dragapult Dusknoir | 25% | 33% | 12 | 258 |
| Dragapult | Festival Lead | 58% | 64% | 12 | 905 |
| Slowking | Festival Lead | 58% | 52% | 12 | 301 |
| Dragapult Dusknoir | Alakazam Dusknoir | 42% | 46% | 12 | 117 |
| Dragapult | Dragapult Blaziken | 50% | 54% | 12 | 1339 |
| Slowking | Alakazam Dusknoir | 33% | 29% | 12 | 157 |
| Basic Box | Dragapult Blaziken | 50% | 53% | 12 | 473 |
| Basic Box | Hydrapple | 33% | 31% | 12 | 369 |
| Alakazam Dudunsparce | Alakazam Dusknoir | 42% | 39% | 12 | 131 |
| Basic Box | Alakazam Dudunsparce | 42% | 44% | 12 | 533 |
| N's Zoroark | Festival Lead | 25% | 23% | 12 | 328 |

## How games went

- Endings: prizes 476 (88%), no Pokémon in play 32 (6%), deck out 32 (6%).
- Mean length 17.1 turns; 18 s per game in a worker.
- The player who went first won 53% of 540 decided games.

## Reading this

- Real matchups mix pilots of every level and list variants; the sim plays one list per archetype with one pilot on both sides. A perfect pilot would still not match exactly, but its errors should be close to the noise floor and its lopsidedness close to the real figure.
- Decks far above the line (overrated) are ones the pilot plays well relative to their opponents; decks far below are where its play is worst. Audit those games first (`node dist/archive.js audit --kind fidelity --run fidelity-imitrace3b`).
