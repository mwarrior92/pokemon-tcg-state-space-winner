# Pilot audit: vs-norepeat-sk

Pilot `imitrace:runs/imit-v3/policy.json`, 144 games (every game has Slowking). Rates are shares of the deck's own turns; see `src/audit.ts` for what each column counts.

| deck | games | win | own turns | prizes / turn | first attack (own turn) | attacked | attack not made | no attack payable | Energy held | Supporter held | Stadium held | Basic held | Evolution held | empty Bench | hand at end | Energy in play |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Festival Lead | 16 | 25% | 8.0 | 0.23 | 4.8 | 33% | 0% | 48% | 3% | 22% | 11% | 2% | 0% | 3% | 3.3 | 1.1 |
| Slowking | 144 | 31% | 6.5 | 0.45 | 3.3 | 47% | 2% | 41% | 8% | 27% | 9% | 22% | 2% | 1% | 6.4 | 2.4 |
| Dragapult Dusknoir | 16 | 38% | 6.3 | 0.68 | 3.6 | 52% | 0% | 10% | 24% | 18% | 20% | 52% | 2% | 2% | 6.6 | 2.3 |
| Basic Box | 16 | 63% | 8.4 | 0.61 | 4.1 | 54% | 0% | 36% | 15% | 10% | 16% | 19% | 0% | 1% | 4.5 | 3.4 |
| Dragapult Blaziken | 16 | 63% | 6.8 | 0.56 | 3.1 | 63% | 0% | 15% | 20% | 22% | 19% | 13% | 0% | 0% | 6.4 | 2.4 |
| Dragapult | 16 | 75% | 8.0 | 0.61 | 4.0 | 56% | 0% | 9% | 13% | 22% | 20% | 14% | 0% | 0% | 5.5 | 2.3 |
| Hydrapple | 16 | 75% | 7.1 | 0.70 | 3.3 | 54% | 2% | 25% | 14% | 33% | 53% | 32% | 9% | 2% | 6.9 | 4.3 |
| Alakazam Dusknoir | 16 | 88% | 5.3 | 1.08 | 2.4 | 68% | 2% | 5% | 30% | 15% | 0% | 35% | 7% | 0% | 12.1 | 1.4 |
| N's Zoroark | 16 | 100% | 6.8 | 0.88 | 3.0 | 66% | 0% | 14% | 28% | 28% | 22% | 18% | 2% | 0% | 5.8 | 2.0 |
| Alakazam Dudunsparce | 16 | 100% | 5.1 | 1.17 | 2.4 | 68% | 0% | 15% | 12% | 10% | 17% | 15% | 2% | 0% | 13.5 | 1.9 |

## All decks together

| deck | games | win | own turns | prizes / turn | first attack (own turn) | attacked | attack not made | no attack payable | Energy held | Supporter held | Stadium held | Basic held | Evolution held | empty Bench | hand at end | Energy in play |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| all decks | 288 | 50% | 6.7 | 0.57 | 3.3 | 52% | 1% | 31% | 13% | 24% | 15% | 22% | 2% | 1% | 6.6 | 2.4 |

## New against old (parts off: norepeat)

New won 72 of 144 decided games: 50% (95% interval 42% to 58%).
Pairs of games on the same seed: new won both in 0, one each in 72, none in 0.

| deck | games | win | own turns | prizes / turn | first attack (own turn) | attacked | attack not made | no attack payable | Energy held | Supporter held | Stadium held | Basic held | Evolution held | empty Bench | hand at end | Energy in play |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| new | 144 | 50% | 6.7 | 0.57 | 3.3 | 52% | 1% | 31% | 13% | 24% | 15% | 22% | 2% | 1% | 6.6 | 2.4 |
| old | 144 | 50% | 6.7 | 0.57 | 3.3 | 52% | 1% | 30% | 13% | 24% | 15% | 22% | 2% | 1% | 6.6 | 2.4 |
