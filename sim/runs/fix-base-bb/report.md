# Pilot audit: fix-base-bb

Pilot `imitrace:runs/imit-v3/policy.json`, 36 games (every game has Basic Box). Rates are shares of the deck's own turns; see `src/audit.ts` for what each column counts.

| deck | games | win | own turns | prizes / turn | first attack (own turn) | attacked | attack not made | no attack payable | Energy held | Supporter held | Stadium held | Basic held | Evolution held | empty Bench | hand at end | Energy in play |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Festival Lead | 4 | 0% | 7.5 | 0.13 | 2.3 | 43% | 0% | 50% | 0% | 3% | 23% | 0% | 0% | 3% | 2.2 | 0.7 |
| N's Zoroark | 4 | 25% | 8.0 | 0.47 | 3.5 | 59% | 0% | 6% | 9% | 22% | 53% | 3% | 0% | 0% | 8.8 | 2.9 |
| Basic Box | 36 | 44% | 7.4 | 0.48 | 3.3 | 54% | 1% | 37% | 9% | 18% | 37% | 14% | 0% | 2% | 5.7 | 3.5 |
| Dragapult | 4 | 50% | 7.3 | 0.45 | 2.0 | 69% | 0% | 21% | 10% | 21% | 3% | 24% | 0% | 10% | 4.2 | 2.0 |
| Slowking | 4 | 50% | 8.5 | 0.56 | 3.0 | 56% | 0% | 29% | 6% | 41% | 24% | 18% | 0% | 0% | 6.9 | 3.5 |
| Dragapult Dusknoir | 4 | 50% | 8.5 | 0.41 | 3.8 | 50% | 0% | 3% | 9% | 15% | 12% | 15% | 0% | 0% | 4.3 | 1.6 |
| Hydrapple | 4 | 75% | 6.5 | 0.88 | 2.5 | 69% | 0% | 23% | 19% | 27% | 62% | 27% | 0% | 0% | 7.6 | 4.3 |
| Alakazam Dusknoir | 4 | 75% | 5.8 | 0.91 | 2.5 | 57% | 0% | 17% | 17% | 17% | 0% | 52% | 0% | 0% | 9.4 | 0.7 |
| Dragapult Blaziken | 4 | 75% | 8.8 | 0.54 | 2.8 | 74% | 0% | 6% | 6% | 20% | 17% | 9% | 0% | 3% | 7.5 | 3.7 |
| Alakazam Dudunsparce | 4 | 100% | 5.3 | 1.14 | 2.3 | 71% | 0% | 10% | 10% | 14% | 62% | 5% | 0% | 0% | 13.3 | 1.9 |

## All decks together

| deck | games | win | own turns | prizes / turn | first attack (own turn) | attacked | attack not made | no attack payable | Energy held | Supporter held | Stadium held | Basic held | Evolution held | empty Bench | hand at end | Energy in play |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| all decks | 72 | 50% | 7.3 | 0.53 | 3.0 | 57% | 1% | 28% | 9% | 19% | 32% | 15% | 0% | 2% | 6.3 | 3.0 |
