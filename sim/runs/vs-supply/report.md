# Pilot audit: vs-supply

Pilot `imitrace:runs/imit-v3/policy.json`, 180 games. Rates are shares of the deck's own turns; see `src/audit.ts` for what each column counts.

| deck | games | win | own turns | prizes / turn | first attack (own turn) | attacked | attack not made | no attack payable | Energy held | Supporter held | Stadium held | Basic held | Evolution held | empty Bench | hand at end | Energy in play |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Slowking | 36 | 28% | 7.0 | 0.38 | 3.3 | 44% | 2% | 38% | 6% | 23% | 11% | 13% | 1% | 0% | 5.9 | 2.5 |
| Festival Lead | 36 | 28% | 6.8 | 0.28 | 2.6 | 44% | 0% | 44% | 3% | 23% | 15% | 6% | 1% | 2% | 3.8 | 1.0 |
| N's Zoroark | 36 | 36% | 6.6 | 0.47 | 3.0 | 49% | 1% | 18% | 5% | 17% | 9% | 16% | 3% | 3% | 5.5 | 2.2 |
| Dragapult | 36 | 39% | 7.4 | 0.43 | 2.3 | 72% | 0% | 12% | 6% | 18% | 17% | 19% | 3% | 3% | 5.2 | 2.2 |
| Basic Box | 36 | 44% | 7.4 | 0.50 | 3.1 | 53% | 2% | 42% | 11% | 13% | 9% | 32% | 0% | 2% | 4.9 | 3.3 |
| Hydrapple | 36 | 56% | 6.9 | 0.53 | 2.5 | 55% | 2% | 27% | 13% | 31% | 17% | 15% | 2% | 2% | 6.2 | 3.9 |
| Dragapult Dusknoir | 36 | 58% | 6.8 | 0.61 | 2.8 | 56% | 1% | 15% | 12% | 20% | 25% | 20% | 7% | 0% | 6.1 | 2.2 |
| Alakazam Dusknoir | 36 | 64% | 5.6 | 0.87 | 2.2 | 65% | 3% | 13% | 11% | 16% | 0% | 42% | 2% | 0% | 10.7 | 1.2 |
| Alakazam Dudunsparce | 36 | 72% | 6.5 | 0.79 | 2.3 | 71% | 2% | 22% | 10% | 15% | 25% | 23% | 1% | 0% | 12.1 | 1.9 |
| Dragapult Blaziken | 36 | 75% | 7.3 | 0.69 | 1.8 | 76% | 0% | 8% | 13% | 14% | 18% | 18% | 1% | 1% | 6.2 | 2.8 |

## All decks together

| deck | games | win | own turns | prizes / turn | first attack (own turn) | attacked | attack not made | no attack payable | Energy held | Supporter held | Stadium held | Basic held | Evolution held | empty Bench | hand at end | Energy in play |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| all decks | 360 | 50% | 6.8 | 0.55 | 2.6 | 59% | 1% | 24% | 9% | 19% | 15% | 20% | 2% | 1% | 6.5 | 2.3 |

## New against old (parts off: supply)

New won 87 of 180 decided games: 48% (95% interval 41% to 56%).
Pairs of games on the same seed: new won both in 7, one each in 73, none in 10.

| deck | games | win | own turns | prizes / turn | first attack (own turn) | attacked | attack not made | no attack payable | Energy held | Supporter held | Stadium held | Basic held | Evolution held | empty Bench | hand at end | Energy in play |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| new | 180 | 48% | 6.8 | 0.55 | 2.5 | 59% | 1% | 24% | 9% | 19% | 15% | 20% | 2% | 1% | 6.5 | 2.3 |
| old | 180 | 52% | 6.8 | 0.55 | 2.6 | 59% | 1% | 24% | 9% | 19% | 14% | 20% | 2% | 1% | 6.6 | 2.4 |
