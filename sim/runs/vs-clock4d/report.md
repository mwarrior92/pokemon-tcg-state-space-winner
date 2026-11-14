# Pilot audit: vs-clock4d

Pilot `imitrace:runs/imit-v3/policy.json`, 180 games. Rates are shares of the deck's own turns; see `src/audit.ts` for what each column counts.

| deck | games | win | own turns | prizes / turn | first attack (own turn) | attacked | attack not made | no attack payable | Energy held | Supporter held | Stadium held | Basic held | Evolution held | empty Bench | hand at end | Energy in play |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Slowking | 36 | 25% | 7.1 | 0.44 | 3.0 | 47% | 1% | 39% | 6% | 25% | 19% | 25% | 2% | 0% | 6.9 | 2.5 |
| N's Zoroark | 36 | 31% | 7.2 | 0.44 | 2.7 | 58% | 0% | 20% | 7% | 16% | 8% | 14% | 0% | 0% | 5.3 | 2.1 |
| Basic Box | 36 | 39% | 6.7 | 0.49 | 3.3 | 51% | 0% | 38% | 15% | 9% | 15% | 23% | 0% | 0% | 4.5 | 3.6 |
| Festival Lead | 36 | 39% | 6.4 | 0.44 | 2.3 | 53% | 1% | 27% | 3% | 17% | 11% | 9% | 0% | 1% | 3.6 | 1.1 |
| Dragapult Dusknoir | 36 | 39% | 6.0 | 0.51 | 2.7 | 59% | 1% | 12% | 11% | 15% | 13% | 29% | 3% | 0% | 5.0 | 2.3 |
| Dragapult Blaziken | 36 | 44% | 7.1 | 0.54 | 2.7 | 58% | 0% | 11% | 9% | 16% | 23% | 20% | 2% | 2% | 6.0 | 2.3 |
| Dragapult | 36 | 58% | 6.8 | 0.57 | 2.7 | 63% | 1% | 13% | 10% | 19% | 15% | 13% | 1% | 0% | 5.1 | 2.0 |
| Hydrapple | 36 | 67% | 7.3 | 0.59 | 2.9 | 57% | 1% | 29% | 18% | 26% | 24% | 19% | 2% | 1% | 6.3 | 4.6 |
| Alakazam Dusknoir | 36 | 78% | 5.4 | 0.90 | 2.8 | 56% | 4% | 11% | 16% | 11% | 0% | 36% | 1% | 2% | 10.8 | 1.2 |
| Alakazam Dudunsparce | 36 | 81% | 6.6 | 0.72 | 2.9 | 59% | 2% | 28% | 7% | 16% | 18% | 16% | 1% | 0% | 11.1 | 2.2 |

## All decks together

| deck | games | win | own turns | prizes / turn | first attack (own turn) | attacked | attack not made | no attack payable | Energy held | Supporter held | Stadium held | Basic held | Evolution held | empty Bench | hand at end | Energy in play |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| all decks | 360 | 50% | 6.7 | 0.56 | 2.8 | 56% | 1% | 23% | 10% | 17% | 15% | 20% | 1% | 1% | 6.4 | 2.4 |

## New against old (parts off: clock)

New won 101 of 180 decided games: 56% (95% interval 49% to 63%).
Pairs of games on the same seed: new won both in 20, one each in 61, none in 9.

| deck | games | win | own turns | prizes / turn | first attack (own turn) | attacked | attack not made | no attack payable | Energy held | Supporter held | Stadium held | Basic held | Evolution held | empty Bench | hand at end | Energy in play |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| old | 180 | 44% | 6.6 | 0.52 | 2.6 | 57% | 1% | 24% | 9% | 17% | 14% | 19% | 1% | 1% | 6.1 | 2.3 |
| new | 180 | 56% | 6.7 | 0.59 | 3.0 | 55% | 1% | 22% | 12% | 18% | 16% | 21% | 1% | 0% | 6.6 | 2.5 |
