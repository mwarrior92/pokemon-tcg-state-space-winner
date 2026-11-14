# Pilot audit: vs-all

Pilot `imitrace:runs/imit-v3/policy.json`, 180 games. Rates are shares of the deck's own turns; see `src/audit.ts` for what each column counts.

| deck | games | win | own turns | prizes / turn | first attack (own turn) | attacked | attack not made | no attack payable | Energy held | Supporter held | Stadium held | Basic held | Evolution held | empty Bench | hand at end | Energy in play |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Slowking | 36 | 19% | 7.0 | 0.31 | 3.2 | 45% | 2% | 39% | 3% | 35% | 25% | 12% | 1% | 0% | 6.1 | 2.4 |
| Festival Lead | 36 | 33% | 7.0 | 0.30 | 2.7 | 47% | 2% | 39% | 2% | 26% | 14% | 8% | 1% | 1% | 4.1 | 1.1 |
| N's Zoroark | 36 | 36% | 7.3 | 0.48 | 3.1 | 51% | 1% | 21% | 5% | 21% | 17% | 12% | 2% | 2% | 5.7 | 2.1 |
| Dragapult | 36 | 42% | 7.8 | 0.44 | 2.3 | 66% | 0% | 15% | 6% | 18% | 17% | 16% | 1% | 1% | 5.0 | 2.1 |
| Basic Box | 36 | 42% | 7.5 | 0.46 | 3.2 | 51% | 1% | 39% | 12% | 14% | 18% | 24% | 0% | 1% | 4.6 | 3.5 |
| Hydrapple | 36 | 56% | 7.1 | 0.54 | 2.3 | 57% | 2% | 19% | 14% | 31% | 26% | 16% | 0% | 1% | 7.1 | 4.5 |
| Alakazam Dusknoir | 36 | 61% | 5.6 | 0.81 | 2.3 | 65% | 2% | 11% | 12% | 16% | 0% | 30% | 1% | 0% | 9.6 | 1.1 |
| Dragapult Dusknoir | 36 | 64% | 7.0 | 0.58 | 2.7 | 57% | 2% | 13% | 12% | 20% | 22% | 20% | 4% | 0% | 5.7 | 2.2 |
| Alakazam Dudunsparce | 36 | 72% | 6.6 | 0.74 | 2.3 | 68% | 1% | 22% | 10% | 15% | 36% | 22% | 1% | 0% | 13.1 | 1.8 |
| Dragapult Blaziken | 36 | 75% | 7.2 | 0.70 | 1.8 | 75% | 0% | 7% | 10% | 17% | 16% | 15% | 0% | 1% | 6.2 | 2.9 |

## All decks together

| deck | games | win | own turns | prizes / turn | first attack (own turn) | attacked | attack not made | no attack payable | Energy held | Supporter held | Stadium held | Basic held | Evolution held | empty Bench | hand at end | Energy in play |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| all decks | 360 | 50% | 7.0 | 0.53 | 2.6 | 58% | 1% | 23% | 9% | 21% | 19% | 17% | 1% | 1% | 6.6 | 2.4 |

## New against old (parts off: handneed,supply,targets,inplay)

New won 98 of 180 decided games: 54% (95% interval 47% to 62%).
Pairs of games on the same seed: new won both in 15, one each in 68, none in 7.

| deck | games | win | own turns | prizes / turn | first attack (own turn) | attacked | attack not made | no attack payable | Energy held | Supporter held | Stadium held | Basic held | Evolution held | empty Bench | hand at end | Energy in play |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| old | 180 | 46% | 7.0 | 0.50 | 2.6 | 58% | 1% | 23% | 7% | 23% | 30% | 17% | 1% | 1% | 6.6 | 2.3 |
| new | 180 | 54% | 7.0 | 0.56 | 2.5 | 59% | 2% | 22% | 10% | 20% | 9% | 18% | 2% | 1% | 6.5 | 2.5 |
