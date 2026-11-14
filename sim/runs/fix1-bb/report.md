# Pilot audit: fix1-bb

Pilot `imitrace:runs/imit-v3/policy.json`, 36 games (every game has Basic Box). Rates are shares of the deck's own turns; see `src/audit.ts` for what each column counts.

| deck | games | win | own turns | prizes / turn | first attack (own turn) | attacked | attack not made | no attack payable | Energy held | Supporter held | Stadium held | Basic held | Evolution held | empty Bench | hand at end | Energy in play |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Dragapult | 4 | 25% | 7.5 | 0.23 | 2.8 | 60% | 0% | 20% | 10% | 10% | 13% | 17% | 0% | 7% | 4.2 | 2.1 |
| N's Zoroark | 4 | 25% | 8.8 | 0.31 | 4.5 | 29% | 3% | 3% | 6% | 37% | 40% | 34% | 0% | 0% | 7.7 | 3.6 |
| Festival Lead | 4 | 25% | 8.5 | 0.44 | 1.8 | 62% | 0% | 29% | 0% | 3% | 18% | 9% | 0% | 3% | 3.3 | 1.1 |
| Dragapult Dusknoir | 4 | 25% | 7.8 | 0.39 | 2.3 | 58% | 0% | 10% | 0% | 13% | 6% | 23% | 0% | 0% | 4.4 | 1.4 |
| Basic Box | 36 | 42% | 6.9 | 0.47 | 2.8 | 62% | 1% | 30% | 10% | 16% | 30% | 25% | 0% | 2% | 5.4 | 3.5 |
| Slowking | 4 | 50% | 8.0 | 0.47 | 3.8 | 50% | 6% | 31% | 6% | 25% | 25% | 19% | 3% | 0% | 5.8 | 3.2 |
| Alakazam Dusknoir | 4 | 75% | 4.8 | 1.16 | 2.5 | 68% | 0% | 11% | 0% | 11% | 0% | 53% | 0% | 0% | 11.1 | 0.9 |
| Hydrapple | 4 | 100% | 6.3 | 0.96 | 2.5 | 76% | 0% | 20% | 12% | 40% | 56% | 24% | 0% | 0% | 7.7 | 4.5 |
| Alakazam Dudunsparce | 4 | 100% | 4.8 | 1.26 | 2.5 | 68% | 5% | 11% | 32% | 16% | 68% | 47% | 0% | 0% | 14.0 | 1.6 |
| Dragapult Blaziken | 4 | 100% | 6.3 | 0.88 | 2.5 | 72% | 0% | 16% | 8% | 8% | 12% | 16% | 0% | 4% | 6.4 | 3.0 |

## All decks together

| deck | games | win | own turns | prizes / turn | first attack (own turn) | attacked | attack not made | no attack payable | Energy held | Supporter held | Stadium held | Basic held | Evolution held | empty Bench | hand at end | Energy in play |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| all decks | 72 | 50% | 6.9 | 0.54 | 2.8 | 60% | 1% | 24% | 8% | 17% | 28% | 25% | 0% | 2% | 6.0 | 2.9 |
