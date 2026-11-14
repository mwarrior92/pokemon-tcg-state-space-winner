# Pilot audit: vs-clock4

Pilot `imitrace:runs/imit-v3/policy.json`, 180 games. Rates are shares of the deck's own turns; see `src/audit.ts` for what each column counts.

| deck | games | win | own turns | prizes / turn | first attack (own turn) | attacked | attack not made | no attack payable | Energy held | Supporter held | Stadium held | Basic held | Evolution held | empty Bench | hand at end | Energy in play |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Dragapult | 36 | 28% | 7.2 | 0.39 | 2.5 | 61% | 1% | 12% | 8% | 17% | 16% | 17% | 1% | 2% | 4.9 | 2.1 |
| N's Zoroark | 36 | 28% | 6.9 | 0.48 | 3.4 | 46% | 0% | 21% | 4% | 22% | 6% | 15% | 2% | 2% | 5.7 | 2.3 |
| Slowking | 36 | 28% | 7.2 | 0.32 | 3.7 | 39% | 1% | 44% | 4% | 22% | 17% | 17% | 1% | 0% | 6.5 | 2.4 |
| Festival Lead | 36 | 33% | 6.6 | 0.33 | 2.4 | 49% | 0% | 40% | 3% | 22% | 9% | 5% | 4% | 1% | 3.5 | 1.0 |
| Basic Box | 36 | 47% | 7.6 | 0.48 | 3.2 | 54% | 0% | 38% | 13% | 16% | 10% | 25% | 0% | 1% | 5.1 | 3.2 |
| Hydrapple | 36 | 58% | 6.6 | 0.62 | 2.6 | 60% | 1% | 24% | 17% | 25% | 16% | 21% | 1% | 2% | 6.7 | 4.4 |
| Dragapult Dusknoir | 36 | 61% | 6.3 | 0.69 | 2.7 | 61% | 0% | 16% | 10% | 13% | 14% | 18% | 0% | 0% | 4.9 | 2.1 |
| Alakazam Dusknoir | 36 | 67% | 5.7 | 0.87 | 2.5 | 61% | 3% | 12% | 13% | 17% | 0% | 36% | 5% | 0% | 10.1 | 1.1 |
| Dragapult Blaziken | 36 | 72% | 7.1 | 0.65 | 2.2 | 70% | 0% | 8% | 9% | 16% | 13% | 19% | 3% | 1% | 6.2 | 2.9 |
| Alakazam Dudunsparce | 36 | 78% | 6.6 | 0.77 | 2.6 | 67% | 2% | 21% | 13% | 17% | 30% | 17% | 2% | 0% | 13.0 | 1.9 |

## All decks together

| deck | games | win | own turns | prizes / turn | first attack (own turn) | attacked | attack not made | no attack payable | Energy held | Supporter held | Stadium held | Basic held | Evolution held | empty Bench | hand at end | Energy in play |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| all decks | 360 | 50% | 6.8 | 0.55 | 2.8 | 56% | 1% | 24% | 9% | 19% | 13% | 19% | 2% | 1% | 6.6 | 2.4 |

## New against old (parts off: clock)

New won 103 of 180 decided games: 57% (95% interval 50% to 64%).
Pairs of games on the same seed: new won both in 21, one each in 61, none in 8.

| deck | games | win | own turns | prizes / turn | first attack (own turn) | attacked | attack not made | no attack payable | Energy held | Supporter held | Stadium held | Basic held | Evolution held | empty Bench | hand at end | Energy in play |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| old | 180 | 43% | 6.7 | 0.50 | 2.7 | 56% | 1% | 26% | 8% | 18% | 13% | 18% | 2% | 1% | 6.4 | 2.3 |
| new | 180 | 57% | 6.8 | 0.60 | 2.9 | 57% | 1% | 22% | 11% | 19% | 13% | 19% | 2% | 1% | 6.8 | 2.5 |
