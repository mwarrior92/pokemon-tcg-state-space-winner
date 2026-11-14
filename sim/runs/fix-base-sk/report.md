# Pilot audit: fix-base-sk

Pilot `imitrace:runs/imit-v3/policy.json`, 36 games (every game has Slowking). Rates are shares of the deck's own turns; see `src/audit.ts` for what each column counts.

| deck | games | win | own turns | prizes / turn | first attack (own turn) | attacked | attack not made | no attack payable | Energy held | Supporter held | Stadium held | Basic held | Evolution held | empty Bench | hand at end | Energy in play |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Dragapult Dusknoir | 4 | 0% | 7.8 | 0.32 | 2.8 | 61% | 0% | 19% | 0% | 23% | 19% | 19% | 3% | 0% | 6.3 | 2.0 |
| Slowking | 36 | 36% | 6.8 | 0.40 | 3.0 | 50% | 1% | 38% | 4% | 40% | 36% | 8% | 0% | 1% | 6.7 | 2.4 |
| Dragapult | 4 | 50% | 8.5 | 0.35 | 3.5 | 62% | 0% | 18% | 3% | 21% | 62% | 9% | 0% | 3% | 6.0 | 2.4 |
| Basic Box | 4 | 50% | 8.3 | 0.55 | 2.5 | 58% | 0% | 27% | 3% | 24% | 24% | 9% | 0% | 0% | 3.4 | 3.9 |
| Hydrapple | 4 | 50% | 5.8 | 0.70 | 2.0 | 78% | 0% | 17% | 4% | 35% | 35% | 26% | 0% | 0% | 5.1 | 3.0 |
| N's Zoroark | 4 | 75% | 8.8 | 0.51 | 4.5 | 57% | 0% | 40% | 6% | 14% | 14% | 9% | 0% | 0% | 6.3 | 2.2 |
| Festival Lead | 4 | 75% | 6.0 | 0.75 | 1.8 | 67% | 8% | 21% | 13% | 38% | 8% | 13% | 0% | 0% | 5.9 | 1.3 |
| Dragapult Blaziken | 4 | 75% | 6.8 | 0.70 | 2.0 | 81% | 0% | 4% | 11% | 22% | 44% | 11% | 0% | 4% | 7.0 | 2.8 |
| Alakazam Dudunsparce | 4 | 100% | 5.5 | 1.09 | 1.5 | 86% | 0% | 5% | 9% | 14% | 41% | 9% | 0% | 0% | 13.8 | 2.3 |
| Alakazam Dusknoir | 4 | 100% | 5.3 | 1.14 | 2.5 | 71% | 5% | 10% | 19% | 10% | 0% | 57% | 10% | 0% | 12.7 | 1.4 |

## All decks together

| deck | games | win | own turns | prizes / turn | first attack (own turn) | attacked | attack not made | no attack payable | Energy held | Supporter held | Stadium held | Basic held | Evolution held | empty Bench | hand at end | Energy in play |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| all decks | 72 | 50% | 6.9 | 0.52 | 2.8 | 59% | 1% | 28% | 6% | 31% | 32% | 12% | 1% | 1% | 6.9 | 2.4 |
