# Pilot audit: vs-inplay

Pilot `imitrace:runs/imit-v3/policy.json`, 180 games. Rates are shares of the deck's own turns; see `src/audit.ts` for what each column counts.

| deck | games | win | own turns | prizes / turn | first attack (own turn) | attacked | attack not made | no attack payable | Energy held | Supporter held | Stadium held | Basic held | Evolution held | empty Bench | hand at end | Energy in play |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Slowking | 36 | 25% | 7.0 | 0.38 | 3.1 | 45% | 2% | 36% | 4% | 23% | 23% | 19% | 0% | 0% | 5.9 | 2.4 |
| Festival Lead | 36 | 31% | 6.3 | 0.30 | 2.5 | 47% | 0% | 44% | 3% | 26% | 20% | 7% | 0% | 1% | 4.1 | 0.9 |
| Dragapult | 36 | 39% | 7.3 | 0.43 | 2.1 | 71% | 1% | 13% | 8% | 17% | 19% | 22% | 1% | 3% | 5.1 | 2.0 |
| Basic Box | 36 | 39% | 6.9 | 0.48 | 2.9 | 51% | 2% | 40% | 12% | 13% | 19% | 29% | 0% | 2% | 5.2 | 3.6 |
| N's Zoroark | 36 | 42% | 6.9 | 0.49 | 3.1 | 53% | 1% | 14% | 3% | 22% | 16% | 13% | 2% | 2% | 5.3 | 2.2 |
| Dragapult Dusknoir | 36 | 50% | 6.5 | 0.61 | 2.8 | 59% | 1% | 12% | 13% | 12% | 21% | 19% | 4% | 0% | 5.2 | 2.3 |
| Hydrapple | 36 | 58% | 6.9 | 0.57 | 2.5 | 60% | 3% | 20% | 14% | 29% | 29% | 16% | 1% | 2% | 7.2 | 4.3 |
| Alakazam Dudunsparce | 36 | 69% | 6.8 | 0.73 | 2.3 | 70% | 2% | 24% | 11% | 16% | 32% | 22% | 2% | 0% | 12.0 | 1.9 |
| Alakazam Dusknoir | 36 | 69% | 5.7 | 0.81 | 2.2 | 68% | 3% | 10% | 9% | 18% | 0% | 35% | 3% | 0% | 10.2 | 1.3 |
| Dragapult Blaziken | 36 | 78% | 7.1 | 0.69 | 1.8 | 75% | 0% | 7% | 10% | 15% | 17% | 22% | 0% | 1% | 6.1 | 3.0 |

## All decks together

| deck | games | win | own turns | prizes / turn | first attack (own turn) | attacked | attack not made | no attack payable | Energy held | Supporter held | Stadium held | Basic held | Evolution held | empty Bench | hand at end | Energy in play |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| all decks | 360 | 50% | 6.7 | 0.54 | 2.5 | 60% | 2% | 22% | 9% | 19% | 20% | 20% | 1% | 1% | 6.6 | 2.4 |

## New against old (parts off: inplay)

New won 104 of 180 decided games: 58% (95% interval 51% to 65%).
Pairs of games on the same seed: new won both in 18, one each in 68, none in 4.

| deck | games | win | own turns | prizes / turn | first attack (own turn) | attacked | attack not made | no attack payable | Energy held | Supporter held | Stadium held | Basic held | Evolution held | empty Bench | hand at end | Energy in play |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| old | 180 | 42% | 6.7 | 0.49 | 2.5 | 59% | 1% | 23% | 9% | 19% | 29% | 23% | 1% | 1% | 6.6 | 2.3 |
| new | 180 | 58% | 6.8 | 0.59 | 2.5 | 61% | 2% | 21% | 8% | 18% | 11% | 18% | 2% | 1% | 6.6 | 2.6 |
