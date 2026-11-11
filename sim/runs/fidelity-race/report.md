# Pilot fidelity: fidelity-race

Pilot `race`. 10 meta decks (best-placed complete list of each archetype), every pairing played 12 times with seats alternating: 540 games. Real matchups: matchups_2026-09-19_to_10-31.json (Limitless, all rounds).

## Scores

| score | value | what it means |
|---|---|---|
| correlation, sim vs real matchup win rates | **0.16** | 1 = same order and spacing, 0 = unrelated |
| mean absolute error | **18%** | sampling noise alone would give about 11% |
| lopsidedness (mean distance from 50%) | sim 16%, real 9% | a weak pilot exaggerates matchups; noise adds about 11% to the sim figure |
| rank correlation of deck win rates | **-0.02** | do the decks come out in the real order? |
| deck win rate error (mean absolute, each deck against all the others) | **10%** | the steadiest score: sampling noise alone would give about 4% |

## Decks: average win rate against the others

| deck | sim | real | difference |
|---|---|---|---|
| Alakazam Dudunsparce | 69% | 49% | +20 |
| Basic Box | 58% | 47% | +11 |
| Alakazam Dusknoir | 62% | 54% | +8 |
| Hydrapple | 52% | 47% | +6 |
| Dragapult Blaziken | 56% | 51% | +4 |
| Slowking | 48% | 46% | +3 |
| Dragapult | 52% | 56% | -4 |
| N's Zoroark | 38% | 49% | -11 |
| Dragapult Dusknoir | 36% | 50% | -14 |
| Festival Lead | 28% | 51% | -23 |

Sorted from most overrated by the simulator to most underrated.

## Matchups, largest disagreement first

| deck A | deck B | A wins: sim | A wins: real | sim games | real games |
|---|---|---|---|---|---|
| N's Zoroark | Alakazam Dudunsparce | 8% | 52% | 12 | 446 |
| Basic Box | Festival Lead | 92% | 50% | 12 | 333 |
| Festival Lead | Alakazam Dudunsparce | 17% | 56% | 12 | 233 |
| N's Zoroark | Dragapult Blaziken | 25% | 63% | 12 | 448 |
| Hydrapple | Festival Lead | 75% | 40% | 12 | 181 |
| Dragapult Dusknoir | Dragapult Blaziken | 17% | 49% | 12 | 335 |
| Dragapult | Alakazam Dudunsparce | 33% | 63% | 12 | 1308 |
| Alakazam Dudunsparce | Dragapult Blaziken | 67% | 38% | 12 | 344 |
| Dragapult | Alakazam Dusknoir | 33% | 61% | 12 | 530 |
| Basic Box | Hydrapple | 58% | 31% | 12 | 369 |
| Dragapult | Festival Lead | 92% | 64% | 12 | 905 |
| N's Zoroark | Festival Lead | 50% | 23% | 12 | 328 |
| Basic Box | N's Zoroark | 75% | 49% | 12 | 677 |
| Festival Lead | Alakazam Dusknoir | 25% | 51% | 12 | 123 |
| Festival Lead | Dragapult Dusknoir | 58% | 33% | 12 | 258 |
| Festival Lead | Dragapult Blaziken | 25% | 47% | 12 | 231 |
| Dragapult | Dragapult Blaziken | 33% | 54% | 12 | 1339 |
| Basic Box | Dragapult Dusknoir | 75% | 55% | 12 | 500 |
| N's Zoroark | Alakazam Dusknoir | 33% | 53% | 12 | 170 |
| Basic Box | Alakazam Dudunsparce | 25% | 44% | 12 | 533 |
| N's Zoroark | Dragapult Dusknoir | 75% | 57% | 12 | 481 |
| Slowking | Hydrapple | 55% | 39% | 11 | 284 |
| Alakazam Dudunsparce | Dragapult Dusknoir | 58% | 43% | 12 | 388 |
| Hydrapple | Alakazam Dusknoir | 50% | 35% | 12 | 103 |
| Slowking | Dragapult Dusknoir | 73% | 59% | 11 | 422 |
| Hydrapple | Dragapult Blaziken | 50% | 37% | 12 | 251 |
| Basic Box | Dragapult Blaziken | 67% | 53% | 12 | 473 |
| Dragapult | Basic Box | 58% | 45% | 12 | 1863 |
| Hydrapple | Alakazam Dudunsparce | 50% | 37% | 12 | 243 |
| Slowking | Festival Lead | 64% | 52% | 11 | 301 |
| Hydrapple | Dragapult Dusknoir | 50% | 39% | 12 | 225 |
| Slowking | Dragapult Blaziken | 67% | 56% | 12 | 412 |
| Slowking | Alakazam Dudunsparce | 17% | 27% | 12 | 453 |
| N's Zoroark | Hydrapple | 25% | 35% | 12 | 318 |
| Alakazam Dusknoir | Dragapult Blaziken | 50% | 41% | 12 | 134 |
| Dragapult | Dragapult Dusknoir | 50% | 57% | 12 | 1308 |
| Basic Box | Slowking | 58% | 52% | 12 | 624 |
| Dragapult | N's Zoroark | 50% | 44% | 12 | 1740 |
| Dragapult | Slowking | 50% | 45% | 12 | 1604 |
| Slowking | Alakazam Dusknoir | 25% | 29% | 12 | 157 |
| Dragapult Dusknoir | Alakazam Dusknoir | 50% | 46% | 12 | 117 |
| Dragapult | Hydrapple | 67% | 64% | 12 | 957 |
| Alakazam Dudunsparce | Alakazam Dusknoir | 42% | 39% | 12 | 131 |
| Basic Box | Alakazam Dusknoir | 33% | 36% | 12 | 208 |
| N's Zoroark | Slowking | 55% | 54% | 11 | 576 |

## How games went

- Endings: prizes 346 (64%), no Pokémon in play 167 (31%), deck out 23 (4%), turn limit 4 (1%).
- Mean length 18.0 turns; 54 s per game in a worker.
- The player who went first won 57% of 536 decided games.

## Reading this

- Real matchups mix pilots of every level and list variants; the sim plays one list per archetype with one pilot on both sides. A perfect pilot would still not match exactly, but its errors should be close to the noise floor and its lopsidedness close to the real figure.
- Decks far above the line (overrated) are ones the pilot plays well relative to their opponents; decks far below are where its play is worst. Audit those games first (`node dist/archive.js audit --kind fidelity --run fidelity-race`).
