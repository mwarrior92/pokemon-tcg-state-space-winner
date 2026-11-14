# Pilot audit: vs-clock2

Pilot `imitrace:runs/imit-v3/policy.json`, 180 games. Rates are shares of the deck's own turns; see `src/audit.ts` for what each column counts.

| deck | games | win | own turns | prizes / turn | first attack (own turn) | attacked | attack not made | no attack payable | Energy held | Supporter held | Stadium held | Basic held | Evolution held | empty Bench | hand at end | Energy in play |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Slowking | 36 | 31% | 7.5 | 0.35 | 3.7 | 40% | 1% | 38% | 5% | 22% | 16% | 17% | 2% | 0% | 5.9 | 2.7 |
| N's Zoroark | 36 | 33% | 6.9 | 0.47 | 3.2 | 50% | 0% | 24% | 5% | 21% | 12% | 13% | 2% | 2% | 6.0 | 2.1 |
| Festival Lead | 36 | 39% | 6.9 | 0.38 | 2.3 | 55% | 0% | 34% | 5% | 19% | 11% | 5% | 4% | 0% | 3.9 | 1.2 |
| Dragapult Dusknoir | 36 | 42% | 6.4 | 0.55 | 2.8 | 54% | 3% | 14% | 11% | 16% | 9% | 22% | 2% | 1% | 4.8 | 1.9 |
| Basic Box | 36 | 44% | 7.7 | 0.44 | 3.4 | 50% | 0% | 37% | 12% | 12% | 9% | 21% | 0% | 1% | 4.7 | 3.3 |
| Dragapult | 36 | 47% | 7.3 | 0.42 | 2.3 | 64% | 1% | 16% | 7% | 21% | 9% | 19% | 3% | 2% | 5.0 | 2.0 |
| Hydrapple | 36 | 50% | 7.3 | 0.49 | 3.0 | 53% | 2% | 30% | 12% | 20% | 19% | 17% | 2% | 2% | 5.7 | 4.2 |
| Alakazam Dusknoir | 36 | 67% | 6.1 | 0.80 | 2.6 | 59% | 3% | 12% | 14% | 19% | 0% | 39% | 6% | 0% | 10.2 | 1.2 |
| Dragapult Blaziken | 36 | 72% | 7.1 | 0.67 | 2.0 | 71% | 0% | 8% | 11% | 16% | 15% | 20% | 2% | 1% | 6.2 | 2.7 |
| Alakazam Dudunsparce | 36 | 75% | 6.8 | 0.73 | 2.5 | 65% | 3% | 19% | 13% | 19% | 29% | 19% | 3% | 0% | 12.6 | 1.9 |

## All decks together

| deck | games | win | own turns | prizes / turn | first attack (own turn) | attacked | attack not made | no attack payable | Energy held | Supporter held | Stadium held | Basic held | Evolution held | empty Bench | hand at end | Energy in play |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| all decks | 360 | 50% | 7.0 | 0.52 | 2.8 | 56% | 1% | 24% | 9% | 18% | 13% | 19% | 2% | 1% | 6.4 | 2.4 |

## New against old (parts off: clock)

New won 97 of 180 decided games: 54% (95% interval 47% to 61%).
Pairs of games on the same seed: new won both in 21, one each in 55, none in 14.

| deck | games | win | own turns | prizes / turn | first attack (own turn) | attacked | attack not made | no attack payable | Energy held | Supporter held | Stadium held | Basic held | Evolution held | empty Bench | hand at end | Energy in play |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| old | 180 | 46% | 7.0 | 0.50 | 2.6 | 57% | 1% | 24% | 8% | 18% | 14% | 18% | 2% | 1% | 6.4 | 2.3 |
| new | 180 | 54% | 7.0 | 0.55 | 3.0 | 54% | 1% | 24% | 11% | 18% | 13% | 20% | 3% | 1% | 6.5 | 2.4 |
