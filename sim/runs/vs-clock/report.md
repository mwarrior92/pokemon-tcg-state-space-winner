# Pilot audit: vs-clock

Pilot `imitrace:runs/imit-v3/policy.json`, 180 games. Rates are shares of the deck's own turns; see `src/audit.ts` for what each column counts.

| deck | games | win | own turns | prizes / turn | first attack (own turn) | attacked | attack not made | no attack payable | Energy held | Supporter held | Stadium held | Basic held | Evolution held | empty Bench | hand at end | Energy in play |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Slowking | 36 | 28% | 7.3 | 0.38 | 3.8 | 42% | 1% | 42% | 8% | 19% | 18% | 22% | 1% | 0% | 6.2 | 2.7 |
| Festival Lead | 36 | 33% | 6.7 | 0.34 | 2.6 | 50% | 0% | 40% | 5% | 20% | 12% | 10% | 4% | 1% | 3.9 | 1.0 |
| Basic Box | 36 | 36% | 7.5 | 0.44 | 3.3 | 52% | 0% | 41% | 13% | 13% | 12% | 23% | 0% | 1% | 5.3 | 3.0 |
| Dragapult | 36 | 39% | 7.6 | 0.45 | 2.3 | 65% | 0% | 13% | 13% | 22% | 21% | 23% | 1% | 1% | 5.4 | 2.1 |
| N's Zoroark | 36 | 39% | 7.1 | 0.46 | 3.3 | 52% | 1% | 20% | 7% | 22% | 11% | 16% | 7% | 2% | 5.7 | 2.3 |
| Hydrapple | 36 | 58% | 7.3 | 0.58 | 2.7 | 58% | 0% | 28% | 15% | 23% | 14% | 21% | 2% | 2% | 6.2 | 4.1 |
| Alakazam Dusknoir | 36 | 58% | 6.1 | 0.72 | 2.6 | 55% | 2% | 17% | 17% | 16% | 0% | 39% | 6% | 0% | 10.0 | 1.2 |
| Alakazam Dudunsparce | 36 | 67% | 6.6 | 0.70 | 2.6 | 62% | 2% | 26% | 10% | 19% | 26% | 18% | 3% | 0% | 12.9 | 1.9 |
| Dragapult Dusknoir | 36 | 67% | 6.6 | 0.68 | 2.7 | 59% | 1% | 17% | 15% | 18% | 10% | 22% | 3% | 0% | 5.3 | 2.1 |
| Dragapult Blaziken | 36 | 75% | 7.3 | 0.64 | 2.0 | 70% | 0% | 10% | 11% | 16% | 15% | 27% | 1% | 1% | 6.2 | 2.7 |

## All decks together

| deck | games | win | own turns | prizes / turn | first attack (own turn) | attacked | attack not made | no attack payable | Energy held | Supporter held | Stadium held | Basic held | Evolution held | empty Bench | hand at end | Energy in play |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| all decks | 360 | 50% | 7.0 | 0.53 | 2.8 | 56% | 1% | 25% | 11% | 19% | 14% | 22% | 3% | 1% | 6.6 | 2.3 |

## New against old (parts off: clock)

New won 93 of 180 decided games: 52% (95% interval 44% to 59%).
Pairs of games on the same seed: new won both in 17, one each in 59, none in 14.

| deck | games | win | own turns | prizes / turn | first attack (own turn) | attacked | attack not made | no attack payable | Energy held | Supporter held | Stadium held | Basic held | Evolution held | empty Bench | hand at end | Energy in play |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| old | 180 | 48% | 7.0 | 0.53 | 2.6 | 59% | 1% | 24% | 9% | 17% | 13% | 19% | 2% | 1% | 6.6 | 2.4 |
| new | 180 | 52% | 7.0 | 0.54 | 3.0 | 54% | 0% | 27% | 14% | 20% | 15% | 25% | 4% | 1% | 6.7 | 2.3 |
