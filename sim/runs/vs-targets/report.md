# Pilot audit: vs-targets

Pilot `imitrace:runs/imit-v3/policy.json`, 180 games. Rates are shares of the deck's own turns; see `src/audit.ts` for what each column counts.

| deck | games | win | own turns | prizes / turn | first attack (own turn) | attacked | attack not made | no attack payable | Energy held | Supporter held | Stadium held | Basic held | Evolution held | empty Bench | hand at end | Energy in play |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Festival Lead | 36 | 28% | 6.0 | 0.30 | 2.4 | 45% | 0% | 46% | 4% | 23% | 11% | 6% | 2% | 1% | 4.0 | 0.9 |
| Basic Box | 36 | 33% | 7.0 | 0.47 | 2.8 | 48% | 2% | 43% | 10% | 11% | 12% | 31% | 0% | 2% | 5.0 | 3.3 |
| Dragapult | 36 | 36% | 7.4 | 0.42 | 2.2 | 69% | 1% | 14% | 7% | 20% | 15% | 22% | 3% | 4% | 5.5 | 2.3 |
| Slowking | 36 | 36% | 7.1 | 0.44 | 3.2 | 51% | 2% | 34% | 7% | 24% | 13% | 13% | 0% | 0% | 6.0 | 2.6 |
| N's Zoroark | 36 | 39% | 6.3 | 0.53 | 3.0 | 54% | 0% | 12% | 5% | 20% | 9% | 13% | 3% | 2% | 5.3 | 2.0 |
| Hydrapple | 36 | 47% | 6.7 | 0.51 | 2.6 | 52% | 2% | 27% | 13% | 28% | 15% | 15% | 2% | 2% | 6.2 | 3.9 |
| Dragapult Dusknoir | 36 | 58% | 6.5 | 0.64 | 2.8 | 57% | 2% | 12% | 14% | 15% | 22% | 22% | 8% | 1% | 5.9 | 2.1 |
| Alakazam Dusknoir | 36 | 72% | 5.8 | 0.87 | 2.2 | 68% | 3% | 11% | 9% | 19% | 0% | 38% | 2% | 0% | 10.3 | 1.2 |
| Dragapult Blaziken | 36 | 72% | 7.2 | 0.68 | 1.7 | 78% | 1% | 7% | 16% | 15% | 17% | 17% | 1% | 1% | 6.4 | 2.8 |
| Alakazam Dudunsparce | 36 | 78% | 6.6 | 0.80 | 2.3 | 71% | 3% | 22% | 12% | 19% | 28% | 26% | 2% | 0% | 12.0 | 1.9 |

## All decks together

| deck | games | win | own turns | prizes / turn | first attack (own turn) | attacked | attack not made | no attack payable | Energy held | Supporter held | Stadium held | Basic held | Evolution held | empty Bench | hand at end | Energy in play |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| all decks | 360 | 50% | 6.7 | 0.56 | 2.5 | 59% | 2% | 23% | 10% | 19% | 14% | 20% | 2% | 1% | 6.6 | 2.3 |

## New against old (parts off: targets)

New won 89 of 180 decided games: 49% (95% interval 42% to 57%).
Pairs of games on the same seed: new won both in 2, one each in 85, none in 3.

| deck | games | win | own turns | prizes / turn | first attack (own turn) | attacked | attack not made | no attack payable | Energy held | Supporter held | Stadium held | Basic held | Evolution held | empty Bench | hand at end | Energy in play |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| new | 180 | 49% | 6.7 | 0.57 | 2.5 | 59% | 2% | 23% | 10% | 20% | 15% | 20% | 2% | 1% | 6.7 | 2.3 |
| old | 180 | 51% | 6.7 | 0.56 | 2.5 | 59% | 2% | 23% | 10% | 19% | 14% | 20% | 2% | 1% | 6.6 | 2.4 |
