# Pilot audit: fix2-bb

Pilot `imitrace:runs/imit-v3/policy.json`, 36 games (every game has Basic Box). Rates are shares of the deck's own turns; see `src/audit.ts` for what each column counts.

| deck | games | win | own turns | prizes / turn | first attack (own turn) | attacked | attack not made | no attack payable | Energy held | Supporter held | Stadium held | Basic held | Evolution held | empty Bench | hand at end | Energy in play |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| N's Zoroark | 4 | 25% | 6.8 | 0.56 | 2.0 | 74% | 0% | 7% | 7% | 11% | 37% | 11% | 0% | 0% | 6.7 | 2.9 |
| Slowking | 4 | 25% | 8.3 | 0.33 | 2.8 | 58% | 0% | 27% | 3% | 24% | 15% | 30% | 0% | 0% | 5.7 | 2.6 |
| Festival Lead | 4 | 25% | 6.3 | 0.24 | 1.5 | 48% | 0% | 40% | 0% | 4% | 20% | 0% | 8% | 0% | 3.4 | 1.0 |
| Basic Box | 36 | 44% | 6.9 | 0.49 | 2.8 | 54% | 1% | 37% | 12% | 15% | 38% | 29% | 0% | 1% | 5.6 | 3.4 |
| Dragapult | 4 | 50% | 8.0 | 0.50 | 3.3 | 59% | 0% | 13% | 6% | 19% | 0% | 16% | 0% | 6% | 4.0 | 2.3 |
| Alakazam Dusknoir | 4 | 50% | 6.0 | 0.75 | 3.3 | 58% | 4% | 8% | 8% | 13% | 0% | 42% | 0% | 0% | 9.8 | 1.0 |
| Dragapult Blaziken | 4 | 50% | 7.0 | 0.68 | 2.8 | 71% | 0% | 7% | 7% | 14% | 11% | 21% | 0% | 4% | 5.9 | 2.8 |
| Dragapult Dusknoir | 4 | 75% | 9.0 | 0.50 | 2.3 | 69% | 0% | 8% | 14% | 19% | 14% | 31% | 3% | 0% | 5.4 | 2.3 |
| Hydrapple | 4 | 100% | 5.5 | 1.09 | 2.5 | 73% | 5% | 18% | 14% | 27% | 50% | 32% | 0% | 0% | 7.8 | 3.8 |
| Alakazam Dudunsparce | 4 | 100% | 4.8 | 1.26 | 2.5 | 63% | 0% | 21% | 21% | 5% | 58% | 26% | 0% | 0% | 15.4 | 1.6 |

## All decks together

| deck | games | win | own turns | prizes / turn | first attack (own turn) | attacked | attack not made | no attack payable | Energy held | Supporter held | Stadium held | Basic held | Evolution held | empty Bench | hand at end | Energy in play |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| all decks | 72 | 50% | 6.8 | 0.55 | 2.7 | 59% | 1% | 27% | 10% | 15% | 29% | 26% | 1% | 1% | 6.1 | 2.8 |
