# Pilot audit: vs-benchpos

Pilot `imitrace:runs/imit-v3/policy.json`, 180 games. Rates are shares of the deck's own turns; see `src/audit.ts` for what each column counts.

| deck | games | win | own turns | prizes / turn | first attack (own turn) | attacked | attack not made | no attack payable | Energy held | Supporter held | Stadium held | Basic held | Evolution held | empty Bench | hand at end | Energy in play |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Slowking | 36 | 26% | 8.4 | 0.31 | 5.1 | 35% | 0% | 54% | 3% | 14% | 17% | 14% | 3% | 0% | 5.0 | 2.2 |
| N's Zoroark | 36 | 31% | 6.8 | 0.44 | 3.4 | 48% | 0% | 22% | 6% | 19% | 5% | 14% | 3% | 1% | 5.7 | 2.2 |
| Festival Lead | 36 | 33% | 6.5 | 0.41 | 2.3 | 54% | 0% | 34% | 6% | 22% | 5% | 6% | 3% | 1% | 3.6 | 1.1 |
| Dragapult | 36 | 44% | 6.7 | 0.48 | 2.5 | 61% | 1% | 15% | 9% | 18% | 14% | 16% | 1% | 2% | 5.2 | 1.9 |
| Basic Box | 36 | 44% | 6.9 | 0.48 | 3.3 | 50% | 0% | 43% | 10% | 12% | 8% | 19% | 0% | 2% | 4.8 | 2.8 |
| Dragapult Dusknoir | 36 | 47% | 6.5 | 0.57 | 2.8 | 56% | 0% | 12% | 13% | 16% | 6% | 20% | 5% | 0% | 4.8 | 2.1 |
| Alakazam Dusknoir | 36 | 56% | 5.7 | 0.83 | 2.5 | 64% | 3% | 11% | 9% | 14% | 0% | 30% | 5% | 0% | 10.0 | 1.2 |
| Hydrapple | 36 | 61% | 6.5 | 0.61 | 3.0 | 56% | 1% | 31% | 16% | 24% | 19% | 22% | 3% | 3% | 6.9 | 4.1 |
| Dragapult Blaziken | 36 | 71% | 8.0 | 0.57 | 3.9 | 54% | 1% | 7% | 9% | 15% | 15% | 17% | 1% | 2% | 5.4 | 2.4 |
| Alakazam Dudunsparce | 36 | 86% | 6.4 | 0.81 | 2.8 | 66% | 5% | 22% | 15% | 20% | 30% | 20% | 2% | 0% | 13.4 | 1.9 |

## All decks together

| deck | games | win | own turns | prizes / turn | first attack (own turn) | attacked | attack not made | no attack payable | Energy held | Supporter held | Stadium held | Basic held | Evolution held | empty Bench | hand at end | Energy in play |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| all decks | 360 | 50% | 6.8 | 0.54 | 3.1 | 54% | 1% | 26% | 9% | 17% | 12% | 18% | 2% | 1% | 6.3 | 2.2 |

## New against old (parts off: benchpos)

New won 88 of 179 decided games: 49% (95% interval 42% to 56%).
Pairs of games on the same seed: new won both in 10, one each in 68, none in 11.

| deck | games | win | own turns | prizes / turn | first attack (own turn) | attacked | attack not made | no attack payable | Energy held | Supporter held | Stadium held | Basic held | Evolution held | empty Bench | hand at end | Energy in play |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| new | 180 | 49% | 6.8 | 0.53 | 3.1 | 55% | 1% | 24% | 9% | 17% | 13% | 19% | 2% | 1% | 6.3 | 2.1 |
| old | 180 | 51% | 6.8 | 0.54 | 3.2 | 52% | 1% | 27% | 9% | 18% | 12% | 16% | 3% | 1% | 6.3 | 2.3 |
