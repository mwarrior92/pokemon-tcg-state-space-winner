# Pilot audit: vs-copy

Pilot `imitrace:runs/imit-v3/policy.json`, 180 games. Rates are shares of the deck's own turns; see `src/audit.ts` for what each column counts.

| deck | games | win | own turns | prizes / turn | first attack (own turn) | attacked | attack not made | no attack payable | Energy held | Supporter held | Stadium held | Basic held | Evolution held | empty Bench | hand at end | Energy in play |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Slowking | 36 | 22% | 6.7 | 0.36 | 3.5 | 45% | 1% | 39% | 6% | 28% | 20% | 16% | 2% | 0% | 5.9 | 2.3 |
| Dragapult | 36 | 33% | 7.3 | 0.43 | 2.4 | 62% | 0% | 13% | 8% | 22% | 15% | 16% | 2% | 2% | 5.3 | 2.0 |
| N's Zoroark | 36 | 33% | 6.3 | 0.55 | 3.4 | 49% | 0% | 20% | 8% | 19% | 5% | 13% | 3% | 1% | 5.8 | 2.2 |
| Festival Lead | 36 | 39% | 6.5 | 0.43 | 2.3 | 53% | 0% | 34% | 9% | 19% | 7% | 8% | 3% | 1% | 3.6 | 1.2 |
| Hydrapple | 36 | 44% | 6.5 | 0.58 | 3.1 | 54% | 0% | 27% | 16% | 28% | 19% | 21% | 3% | 2% | 7.0 | 4.3 |
| Dragapult Dusknoir | 36 | 44% | 6.2 | 0.61 | 2.7 | 58% | 0% | 13% | 15% | 12% | 13% | 18% | 4% | 0% | 4.7 | 1.8 |
| Basic Box | 36 | 47% | 6.9 | 0.56 | 3.0 | 56% | 0% | 35% | 13% | 12% | 10% | 20% | 0% | 2% | 5.2 | 3.1 |
| Alakazam Dusknoir | 36 | 75% | 5.6 | 0.87 | 2.9 | 58% | 3% | 14% | 19% | 9% | 0% | 38% | 5% | 0% | 10.5 | 1.2 |
| Dragapult Blaziken | 36 | 75% | 7.1 | 0.67 | 2.4 | 68% | 2% | 9% | 11% | 17% | 16% | 27% | 4% | 2% | 6.6 | 2.8 |
| Alakazam Dudunsparce | 36 | 86% | 6.4 | 0.81 | 2.6 | 66% | 2% | 21% | 16% | 19% | 29% | 23% | 1% | 0% | 12.5 | 1.9 |

## All decks together

| deck | games | win | own turns | prizes / turn | first attack (own turn) | attacked | attack not made | no attack payable | Energy held | Supporter held | Stadium held | Basic held | Evolution held | empty Bench | hand at end | Energy in play |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| all decks | 360 | 50% | 6.5 | 0.58 | 2.8 | 57% | 1% | 23% | 12% | 19% | 14% | 20% | 3% | 1% | 6.6 | 2.3 |

## New against old (parts off: copy)

New won 95 of 180 decided games: 53% (95% interval 45% to 60%).
Pairs of games on the same seed: new won both in 10, one each in 75, none in 5.

| deck | games | win | own turns | prizes / turn | first attack (own turn) | attacked | attack not made | no attack payable | Energy held | Supporter held | Stadium held | Basic held | Evolution held | empty Bench | hand at end | Energy in play |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| old | 180 | 47% | 6.5 | 0.57 | 2.8 | 57% | 1% | 23% | 11% | 17% | 14% | 19% | 2% | 1% | 6.5 | 2.3 |
| new | 180 | 53% | 6.6 | 0.60 | 2.8 | 58% | 1% | 22% | 12% | 20% | 13% | 20% | 3% | 1% | 6.7 | 2.3 |
