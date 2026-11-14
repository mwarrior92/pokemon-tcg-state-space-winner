# Pilot audit: fix1-sk

Pilot `imitrace:runs/imit-v3/policy.json`, 36 games (every game has Slowking). Rates are shares of the deck's own turns; see `src/audit.ts` for what each column counts.

| deck | games | win | own turns | prizes / turn | first attack (own turn) | attacked | attack not made | no attack payable | Energy held | Supporter held | Stadium held | Basic held | Evolution held | empty Bench | hand at end | Energy in play |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Slowking | 36 | 28% | 6.3 | 0.40 | 3.1 | 41% | 2% | 43% | 5% | 21% | 36% | 18% | 2% | 0% | 5.9 | 2.2 |
| Dragapult | 4 | 50% | 6.8 | 0.44 | 3.0 | 48% | 7% | 11% | 11% | 19% | 78% | 22% | 0% | 7% | 8.5 | 2.2 |
| Basic Box | 4 | 50% | 7.8 | 0.61 | 1.8 | 74% | 0% | 10% | 13% | 26% | 13% | 26% | 0% | 0% | 3.8 | 4.1 |
| N's Zoroark | 4 | 50% | 8.0 | 0.53 | 5.8 | 41% | 0% | 34% | 3% | 6% | 28% | 25% | 3% | 0% | 6.7 | 2.3 |
| Festival Lead | 4 | 50% | 6.5 | 0.46 | 1.8 | 54% | 0% | 42% | 0% | 8% | 15% | 4% | 0% | 0% | 3.7 | 0.9 |
| Hydrapple | 4 | 75% | 5.8 | 0.78 | 2.0 | 70% | 0% | 22% | 13% | 30% | 39% | 39% | 0% | 0% | 6.9 | 3.3 |
| Alakazam Dudunsparce | 4 | 75% | 5.3 | 0.95 | 1.3 | 67% | 0% | 14% | 19% | 14% | 38% | 14% | 0% | 0% | 16.2 | 1.8 |
| Dragapult Dusknoir | 4 | 100% | 6.3 | 0.96 | 2.5 | 68% | 0% | 20% | 8% | 24% | 16% | 20% | 0% | 0% | 6.3 | 3.4 |
| Alakazam Dusknoir | 4 | 100% | 4.8 | 1.26 | 2.5 | 63% | 5% | 5% | 16% | 16% | 0% | 63% | 11% | 0% | 12.5 | 1.3 |
| Dragapult Blaziken | 4 | 100% | 7.3 | 0.83 | 1.8 | 83% | 0% | 3% | 17% | 21% | 38% | 17% | 0% | 3% | 7.2 | 2.8 |

## All decks together

| deck | games | win | own turns | prizes / turn | first attack (own turn) | attacked | attack not made | no attack payable | Energy held | Supporter held | Stadium held | Basic held | Evolution held | empty Bench | hand at end | Energy in play |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| all decks | 72 | 50% | 6.4 | 0.57 | 2.8 | 52% | 2% | 30% | 8% | 20% | 33% | 21% | 2% | 1% | 6.7 | 2.4 |
