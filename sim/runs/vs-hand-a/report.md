# Pilot audit: vs-hand-a

Pilot `imitrace:runs/imit-v3/policy.json`, 180 games. Rates are shares of the deck's own turns; see `src/audit.ts` for what each column counts.

| deck | games | win | own turns | prizes / turn | first attack (own turn) | attacked | attack not made | no attack payable | Energy held | Supporter held | Stadium held | Basic held | Evolution held | empty Bench | hand at end | Energy in play |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Slowking | 36 | 17% | 6.8 | 0.34 | 3.5 | 43% | 0% | 40% | 4% | 19% | 19% | 14% | 2% | 0% | 5.8 | 2.5 |
| N's Zoroark | 36 | 31% | 6.9 | 0.41 | 3.9 | 42% | 0% | 20% | 6% | 21% | 11% | 11% | 8% | 1% | 5.7 | 2.3 |
| Dragapult | 36 | 39% | 6.8 | 0.45 | 2.4 | 60% | 0% | 16% | 9% | 18% | 17% | 15% | 1% | 2% | 5.3 | 1.9 |
| Basic Box | 36 | 44% | 6.7 | 0.53 | 2.9 | 51% | 0% | 39% | 13% | 14% | 8% | 27% | 0% | 2% | 5.3 | 2.8 |
| Hydrapple | 36 | 44% | 6.8 | 0.54 | 3.1 | 51% | 0% | 26% | 17% | 32% | 16% | 23% | 2% | 1% | 7.3 | 4.7 |
| Festival Lead | 36 | 44% | 6.5 | 0.47 | 2.1 | 55% | 0% | 34% | 8% | 25% | 7% | 10% | 6% | 0% | 3.8 | 1.1 |
| Dragapult Dusknoir | 36 | 53% | 5.9 | 0.70 | 2.7 | 59% | 1% | 12% | 16% | 11% | 14% | 23% | 3% | 0% | 4.8 | 1.8 |
| Dragapult Blaziken | 36 | 67% | 6.7 | 0.64 | 2.4 | 68% | 1% | 9% | 13% | 17% | 18% | 21% | 4% | 2% | 6.6 | 2.6 |
| Alakazam Dusknoir | 36 | 75% | 5.7 | 0.88 | 2.6 | 64% | 3% | 12% | 16% | 11% | 0% | 36% | 5% | 0% | 10.3 | 1.2 |
| Alakazam Dudunsparce | 36 | 86% | 6.2 | 0.82 | 2.5 | 67% | 2% | 21% | 17% | 20% | 29% | 21% | 1% | 0% | 12.8 | 1.9 |

## All decks together

| deck | games | win | own turns | prizes / turn | first attack (own turn) | attacked | attack not made | no attack payable | Energy held | Supporter held | Stadium held | Basic held | Evolution held | empty Bench | hand at end | Energy in play |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| all decks | 360 | 50% | 6.5 | 0.57 | 2.8 | 56% | 1% | 23% | 12% | 19% | 14% | 20% | 3% | 1% | 6.7 | 2.3 |

## New against old (parts off: handsize)

New won 91 of 180 decided games: 51% (95% interval 43% to 58%).
Pairs of games on the same seed: new won both in 4, one each in 83, none in 3.

| deck | games | win | own turns | prizes / turn | first attack (own turn) | attacked | attack not made | no attack payable | Energy held | Supporter held | Stadium held | Basic held | Evolution held | empty Bench | hand at end | Energy in play |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| old | 180 | 49% | 6.5 | 0.57 | 2.9 | 56% | 1% | 24% | 12% | 19% | 14% | 18% | 3% | 1% | 6.6 | 2.3 |
| new | 180 | 51% | 6.5 | 0.57 | 2.8 | 56% | 1% | 23% | 12% | 20% | 14% | 21% | 3% | 1% | 6.8 | 2.3 |
