# Pilot audit: vs-clock4c

Pilot `imitrace:runs/imit-v3/policy.json`, 180 games. Rates are shares of the deck's own turns; see `src/audit.ts` for what each column counts.

| deck | games | win | own turns | prizes / turn | first attack (own turn) | attacked | attack not made | no attack payable | Energy held | Supporter held | Stadium held | Basic held | Evolution held | empty Bench | hand at end | Energy in play |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Slowking | 36 | 33% | 6.9 | 0.44 | 3.1 | 42% | 2% | 44% | 6% | 23% | 10% | 10% | 2% | 0% | 6.2 | 2.3 |
| N's Zoroark | 36 | 42% | 8.0 | 0.42 | 3.4 | 48% | 0% | 20% | 9% | 21% | 12% | 12% | 2% | 0% | 5.5 | 2.2 |
| Dragapult | 36 | 42% | 6.7 | 0.48 | 2.8 | 61% | 0% | 10% | 10% | 16% | 14% | 17% | 2% | 0% | 5.2 | 2.2 |
| Dragapult Dusknoir | 36 | 42% | 6.6 | 0.53 | 2.8 | 57% | 0% | 13% | 14% | 12% | 17% | 19% | 5% | 1% | 5.5 | 2.3 |
| Basic Box | 36 | 47% | 6.7 | 0.58 | 2.7 | 57% | 1% | 33% | 14% | 13% | 12% | 32% | 0% | 2% | 5.3 | 3.4 |
| Festival Lead | 36 | 47% | 7.0 | 0.50 | 3.0 | 51% | 0% | 33% | 6% | 36% | 8% | 6% | 1% | 4% | 4.2 | 1.1 |
| Hydrapple | 36 | 53% | 7.0 | 0.59 | 2.8 | 56% | 3% | 32% | 11% | 26% | 20% | 15% | 3% | 2% | 5.5 | 3.9 |
| Dragapult Blaziken | 36 | 53% | 7.1 | 0.56 | 2.1 | 70% | 0% | 12% | 13% | 19% | 14% | 16% | 2% | 0% | 6.4 | 2.4 |
| Alakazam Dusknoir | 36 | 61% | 5.3 | 0.85 | 2.3 | 64% | 2% | 9% | 15% | 7% | 0% | 38% | 2% | 1% | 10.4 | 1.2 |
| Alakazam Dudunsparce | 36 | 81% | 6.9 | 0.70 | 2.9 | 62% | 1% | 24% | 11% | 13% | 27% | 20% | 1% | 0% | 12.0 | 2.0 |

## All decks together

| deck | games | win | own turns | prizes / turn | first attack (own turn) | attacked | attack not made | no attack payable | Energy held | Supporter held | Stadium held | Basic held | Evolution held | empty Bench | hand at end | Energy in play |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| all decks | 360 | 50% | 6.8 | 0.55 | 2.8 | 57% | 1% | 23% | 11% | 19% | 14% | 18% | 2% | 1% | 6.5 | 2.3 |

## New against old (parts off: clock)

New won 96 of 180 decided games: 53% (95% interval 46% to 61%).
Pairs of games on the same seed: new won both in 25, one each in 46, none in 19.

| deck | games | win | own turns | prizes / turn | first attack (own turn) | attacked | attack not made | no attack payable | Energy held | Supporter held | Stadium held | Basic held | Evolution held | empty Bench | hand at end | Energy in play |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| old | 180 | 47% | 6.8 | 0.53 | 2.6 | 59% | 1% | 23% | 9% | 19% | 13% | 16% | 2% | 1% | 6.4 | 2.3 |
| new | 180 | 53% | 6.8 | 0.58 | 2.9 | 54% | 1% | 24% | 12% | 20% | 14% | 19% | 2% | 1% | 6.6 | 2.4 |
