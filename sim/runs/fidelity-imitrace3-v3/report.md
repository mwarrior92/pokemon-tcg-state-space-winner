# Pilot fidelity: fidelity-imitrace3-v3

Pilot `imitrace:runs/imit-v3/policy.json`. 10 meta decks (best-placed complete list of each archetype), every pairing played 12 times with seats alternating: 540 games. Real matchups: matchups_2026-09-19_to_10-31.json (Limitless, all rounds).

## Scores

| score | value | what it means |
|---|---|---|
| correlation, sim vs real matchup win rates | **-0.01** | 1 = same order and spacing, 0 = unrelated |
| mean absolute error | **21%** | sampling noise alone would give about 11% |
| lopsidedness (mean distance from 50%) | sim 19%, real 9% | a weak pilot exaggerates matchups; noise adds about 11% to the sim figure |
| rank correlation of deck win rates | **-0.14** | do the decks come out in the real order? |
| deck win rate error (mean absolute, each deck against all the others) | **13%** | the steadiest score: sampling noise alone would give about 4% |

## Decks: average win rate against the others

| deck | sim | real | difference |
|---|---|---|---|
| Alakazam Dudunsparce | 79% | 49% | +30 |
| Hydrapple | 63% | 47% | +16 |
| Basic Box | 62% | 47% | +15 |
| Alakazam Dusknoir | 57% | 54% | +3 |
| Slowking | 41% | 46% | -5 |
| Dragapult Blaziken | 45% | 51% | -7 |
| Dragapult | 49% | 56% | -7 |
| Dragapult Dusknoir | 41% | 50% | -9 |
| Festival Lead | 35% | 51% | -16 |
| N's Zoroark | 29% | 49% | -21 |

Sorted from most overrated by the simulator to most underrated.

## Matchups, largest disagreement first

| deck A | deck B | A wins: sim | A wins: real | sim games | real games |
|---|---|---|---|---|---|
| Dragapult | N's Zoroark | 100% | 44% | 12 | 1740 |
| Alakazam Dudunsparce | Dragapult Blaziken | 92% | 38% | 12 | 344 |
| Dragapult | Alakazam Dudunsparce | 17% | 63% | 12 | 1308 |
| Alakazam Dudunsparce | Alakazam Dusknoir | 83% | 39% | 12 | 131 |
| Hydrapple | Festival Lead | 83% | 40% | 12 | 181 |
| Basic Box | Festival Lead | 92% | 50% | 12 | 333 |
| Festival Lead | Alakazam Dudunsparce | 17% | 56% | 12 | 233 |
| Basic Box | Dragapult Dusknoir | 92% | 55% | 12 | 500 |
| N's Zoroark | Alakazam Dudunsparce | 17% | 52% | 12 | 446 |
| Hydrapple | Alakazam Dusknoir | 67% | 35% | 12 | 103 |
| Dragapult | Hydrapple | 33% | 64% | 12 | 957 |
| N's Zoroark | Dragapult Blaziken | 33% | 63% | 12 | 448 |
| Basic Box | Dragapult Blaziken | 83% | 53% | 12 | 473 |
| Dragapult | Alakazam Dusknoir | 33% | 61% | 12 | 530 |
| Hydrapple | Dragapult Dusknoir | 67% | 39% | 12 | 225 |
| N's Zoroark | Alakazam Dusknoir | 25% | 53% | 12 | 170 |
| Festival Lead | Alakazam Dusknoir | 25% | 51% | 12 | 123 |
| Alakazam Dudunsparce | Dragapult Dusknoir | 67% | 43% | 12 | 388 |
| Dragapult | Festival Lead | 42% | 64% | 12 | 905 |
| Slowking | Dragapult Blaziken | 33% | 56% | 12 | 412 |
| Dragapult | Dragapult Blaziken | 73% | 54% | 11 | 1339 |
| Alakazam Dusknoir | Dragapult Blaziken | 58% | 41% | 12 | 134 |
| N's Zoroark | Dragapult Dusknoir | 42% | 57% | 12 | 481 |
| Basic Box | Alakazam Dusknoir | 50% | 36% | 12 | 208 |
| Festival Lead | Dragapult Blaziken | 33% | 47% | 12 | 231 |
| Hydrapple | Dragapult Blaziken | 50% | 37% | 12 | 251 |
| Slowking | Alakazam Dusknoir | 17% | 29% | 12 | 157 |
| Dragapult | Slowking | 33% | 45% | 12 | 1604 |
| Basic Box | Hydrapple | 42% | 31% | 12 | 369 |
| Slowking | Alakazam Dudunsparce | 17% | 27% | 12 | 453 |
| Basic Box | Alakazam Dudunsparce | 33% | 44% | 12 | 533 |
| N's Zoroark | Hydrapple | 25% | 35% | 12 | 318 |
| Basic Box | N's Zoroark | 58% | 49% | 12 | 677 |
| Slowking | Dragapult Dusknoir | 50% | 59% | 12 | 422 |
| Festival Lead | Dragapult Dusknoir | 42% | 33% | 12 | 258 |
| Dragapult Dusknoir | Dragapult Blaziken | 42% | 49% | 12 | 335 |
| Basic Box | Slowking | 58% | 52% | 12 | 624 |
| Slowking | Festival Lead | 58% | 52% | 12 | 301 |
| Slowking | Hydrapple | 33% | 39% | 12 | 284 |
| Dragapult | Basic Box | 50% | 45% | 12 | 1863 |
| Dragapult Dusknoir | Alakazam Dusknoir | 42% | 46% | 12 | 117 |
| N's Zoroark | Slowking | 50% | 54% | 12 | 576 |
| Hydrapple | Alakazam Dudunsparce | 33% | 37% | 12 | 243 |
| N's Zoroark | Festival Lead | 25% | 23% | 12 | 328 |
| Dragapult | Dragapult Dusknoir | 58% | 57% | 12 | 1308 |

## How games went

- Endings: prizes 403 (75%), deck out 117 (22%), no Pokémon in play 19 (4%), turn limit 1 (0%).
- Mean length 27.3 turns; 14 s per game in a worker.
- The player who went first won 56% of 539 decided games.

## Reading this

- Real matchups mix pilots of every level and list variants; the sim plays one list per archetype with one pilot on both sides. A perfect pilot would still not match exactly, but its errors should be close to the noise floor and its lopsidedness close to the real figure.
- Decks far above the line (overrated) are ones the pilot plays well relative to their opponents; decks far below are where its play is worst. Audit those games first (`node dist/archive.js audit --kind fidelity --run fidelity-imitrace3-v3`).
