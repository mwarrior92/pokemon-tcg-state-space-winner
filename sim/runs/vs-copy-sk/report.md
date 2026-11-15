# Pilot audit: vs-copy-sk

Pilot `imitrace:runs/imit-v3/policy.json`, 72 games (every game has Slowking). Rates are shares of the deck's own turns; see `src/audit.ts` for what each column counts.

| deck | games | win | own turns | prizes / turn | first attack (own turn) | attacked | attack not made | no attack payable | Energy held | Supporter held | Stadium held | Basic held | Evolution held | empty Bench | hand at end | Energy in play |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Festival Lead | 8 | 13% | 7.0 | 0.34 | 1.6 | 54% | 4% | 23% | 5% | 25% | 20% | 9% | 0% | 2% | 3.1 | 1.4 |
| Slowking | 72 | 33% | 6.4 | 0.45 | 3.5 | 44% | 0% | 42% | 7% | 24% | 12% | 17% | 3% | 2% | 6.5 | 2.5 |
| Dragapult Blaziken | 8 | 50% | 7.6 | 0.46 | 3.4 | 54% | 0% | 25% | 7% | 13% | 11% | 18% | 0% | 3% | 5.0 | 2.4 |
| Basic Box | 8 | 63% | 7.3 | 0.60 | 3.9 | 50% | 0% | 38% | 16% | 9% | 48% | 21% | 0% | 0% | 5.9 | 3.3 |
| Dragapult | 8 | 75% | 7.5 | 0.72 | 3.4 | 65% | 0% | 13% | 18% | 33% | 13% | 23% | 3% | 0% | 6.3 | 2.2 |
| N's Zoroark | 8 | 75% | 7.4 | 0.64 | 3.1 | 54% | 0% | 5% | 10% | 22% | 12% | 17% | 3% | 0% | 7.2 | 2.8 |
| Hydrapple | 8 | 75% | 5.9 | 0.87 | 2.6 | 66% | 0% | 32% | 28% | 15% | 13% | 9% | 0% | 0% | 7.3 | 4.4 |
| Dragapult Dusknoir | 8 | 75% | 5.5 | 0.91 | 2.6 | 64% | 0% | 0% | 18% | 20% | 7% | 25% | 0% | 0% | 4.5 | 2.3 |
| Alakazam Dusknoir | 8 | 75% | 5.5 | 0.86 | 3.0 | 41% | 5% | 32% | 20% | 9% | 0% | 25% | 11% | 0% | 10.0 | 1.0 |
| Alakazam Dudunsparce | 8 | 100% | 5.6 | 1.02 | 2.6 | 71% | 0% | 18% | 18% | 11% | 38% | 31% | 0% | 0% | 13.3 | 1.9 |

## All decks together

| deck | games | win | own turns | prizes / turn | first attack (own turn) | attacked | attack not made | no attack payable | Energy held | Supporter held | Stadium held | Basic held | Evolution held | empty Bench | hand at end | Energy in play |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| all decks | 144 | 50% | 6.5 | 0.57 | 3.2 | 51% | 1% | 31% | 11% | 21% | 15% | 18% | 2% | 1% | 6.6 | 2.4 |

## New against old (parts off: copy)

New won 38 of 72 decided games: 53% (95% interval 41% to 64%).
Pairs of games on the same seed: new won both in 4, one each in 30, none in 2.

| deck | games | win | own turns | prizes / turn | first attack (own turn) | attacked | attack not made | no attack payable | Energy held | Supporter held | Stadium held | Basic held | Evolution held | empty Bench | hand at end | Energy in play |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| old | 72 | 47% | 6.5 | 0.57 | 3.3 | 51% | 0% | 32% | 12% | 19% | 16% | 15% | 3% | 1% | 6.6 | 2.5 |
| new | 72 | 53% | 6.5 | 0.57 | 3.2 | 51% | 1% | 31% | 11% | 23% | 14% | 22% | 2% | 1% | 6.6 | 2.4 |
