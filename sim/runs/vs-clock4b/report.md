# Pilot audit: vs-clock4b

Pilot `imitrace:runs/imit-v3/policy.json`, 180 games. Rates are shares of the deck's own turns; see `src/audit.ts` for what each column counts.

| deck | games | win | own turns | prizes / turn | first attack (own turn) | attacked | attack not made | no attack payable | Energy held | Supporter held | Stadium held | Basic held | Evolution held | empty Bench | hand at end | Energy in play |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Slowking | 36 | 31% | 6.9 | 0.41 | 3.4 | 44% | 0% | 46% | 7% | 26% | 12% | 18% | 3% | 2% | 6.7 | 2.6 |
| N's Zoroark | 36 | 33% | 6.8 | 0.39 | 3.4 | 45% | 0% | 32% | 11% | 14% | 8% | 11% | 2% | 2% | 5.3 | 2.2 |
| Festival Lead | 36 | 33% | 6.8 | 0.43 | 2.4 | 54% | 0% | 28% | 6% | 28% | 16% | 7% | 3% | 3% | 4.1 | 1.2 |
| Dragapult | 36 | 47% | 6.5 | 0.57 | 2.0 | 71% | 0% | 10% | 10% | 16% | 16% | 17% | 1% | 2% | 5.7 | 2.2 |
| Dragapult Dusknoir | 36 | 47% | 6.7 | 0.51 | 3.5 | 49% | 2% | 12% | 12% | 22% | 15% | 23% | 7% | 0% | 5.2 | 2.1 |
| Basic Box | 36 | 50% | 6.7 | 0.55 | 3.0 | 57% | 1% | 34% | 11% | 15% | 21% | 25% | 0% | 0% | 5.6 | 3.5 |
| Dragapult Blaziken | 36 | 56% | 7.2 | 0.55 | 2.4 | 67% | 0% | 8% | 9% | 14% | 14% | 15% | 1% | 0% | 5.6 | 2.6 |
| Hydrapple | 36 | 61% | 6.8 | 0.66 | 2.5 | 65% | 2% | 21% | 12% | 20% | 25% | 18% | 0% | 2% | 5.6 | 4.3 |
| Alakazam Dusknoir | 36 | 64% | 5.3 | 0.83 | 2.2 | 61% | 1% | 14% | 15% | 8% | 0% | 34% | 7% | 0% | 9.7 | 1.1 |
| Alakazam Dudunsparce | 36 | 78% | 6.1 | 0.82 | 2.7 | 67% | 1% | 22% | 9% | 18% | 28% | 16% | 1% | 0% | 12.3 | 2.1 |

## All decks together

| deck | games | win | own turns | prizes / turn | first attack (own turn) | attacked | attack not made | no attack payable | Energy held | Supporter held | Stadium held | Basic held | Evolution held | empty Bench | hand at end | Energy in play |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| all decks | 360 | 50% | 6.6 | 0.56 | 2.8 | 58% | 1% | 23% | 10% | 18% | 16% | 18% | 2% | 1% | 6.4 | 2.4 |

## New against old (parts off: clock)

New won 95 of 180 decided games: 53% (95% interval 45% to 60%).
Pairs of games on the same seed: new won both in 17, one each in 61, none in 12.

| deck | games | win | own turns | prizes / turn | first attack (own turn) | attacked | attack not made | no attack payable | Energy held | Supporter held | Stadium held | Basic held | Evolution held | empty Bench | hand at end | Energy in play |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| old | 180 | 47% | 6.6 | 0.53 | 2.6 | 59% | 1% | 24% | 8% | 18% | 14% | 20% | 2% | 1% | 6.2 | 2.3 |
| new | 180 | 53% | 6.6 | 0.59 | 2.9 | 57% | 1% | 21% | 12% | 19% | 17% | 17% | 3% | 1% | 6.6 | 2.6 |
