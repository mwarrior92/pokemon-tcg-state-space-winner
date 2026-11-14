# Pilot audit: vs-benchpos-b

Pilot `imitrace:runs/imit-v3/policy.json`, 180 games. Rates are shares of the deck's own turns; see `src/audit.ts` for what each column counts.

| deck | games | win | own turns | prizes / turn | first attack (own turn) | attacked | attack not made | no attack payable | Energy held | Supporter held | Stadium held | Basic held | Evolution held | empty Bench | hand at end | Energy in play |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Slowking | 36 | 31% | 6.6 | 0.40 | 3.5 | 44% | 1% | 50% | 7% | 25% | 14% | 15% | 6% | 2% | 6.9 | 2.4 |
| N's Zoroark | 36 | 33% | 7.1 | 0.43 | 3.6 | 45% | 1% | 35% | 7% | 15% | 4% | 8% | 3% | 2% | 5.4 | 2.3 |
| Festival Lead | 36 | 36% | 6.6 | 0.40 | 2.4 | 52% | 2% | 28% | 6% | 25% | 16% | 10% | 1% | 4% | 3.7 | 1.3 |
| Dragapult Dusknoir | 36 | 39% | 6.4 | 0.57 | 3.8 | 45% | 3% | 17% | 7% | 15% | 14% | 23% | 4% | 0% | 4.7 | 2.0 |
| Dragapult Blaziken | 36 | 50% | 6.9 | 0.65 | 2.1 | 66% | 0% | 7% | 16% | 14% | 15% | 14% | 1% | 0% | 5.9 | 2.5 |
| Alakazam Dusknoir | 36 | 53% | 5.4 | 0.77 | 2.3 | 54% | 2% | 13% | 15% | 7% | 0% | 33% | 6% | 0% | 9.8 | 1.2 |
| Basic Box | 36 | 61% | 6.5 | 0.63 | 2.7 | 62% | 1% | 30% | 13% | 15% | 16% | 33% | 0% | 0% | 6.3 | 3.8 |
| Dragapult | 36 | 64% | 6.4 | 0.72 | 2.2 | 68% | 0% | 13% | 12% | 19% | 20% | 24% | 1% | 2% | 6.1 | 2.2 |
| Hydrapple | 36 | 67% | 7.3 | 0.61 | 2.6 | 66% | 0% | 28% | 19% | 26% | 21% | 24% | 2% | 2% | 6.0 | 4.0 |
| Alakazam Dudunsparce | 36 | 67% | 6.1 | 0.75 | 2.7 | 59% | 0% | 24% | 12% | 14% | 20% | 18% | 0% | 0% | 11.6 | 1.9 |

## All decks together

| deck | games | win | own turns | prizes / turn | first attack (own turn) | attacked | attack not made | no attack payable | Energy held | Supporter held | Stadium held | Basic held | Evolution held | empty Bench | hand at end | Energy in play |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| all decks | 360 | 50% | 6.5 | 0.59 | 2.8 | 56% | 1% | 25% | 11% | 18% | 14% | 20% | 2% | 1% | 6.5 | 2.4 |

## New against old (parts off: benchpos)

New won 90 of 180 decided games: 50% (95% interval 43% to 57%).
Pairs of games on the same seed: new won both in 12, one each in 66, none in 12.

| deck | games | win | own turns | prizes / turn | first attack (own turn) | attacked | attack not made | no attack payable | Energy held | Supporter held | Stadium held | Basic held | Evolution held | empty Bench | hand at end | Energy in play |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| new | 180 | 50% | 6.5 | 0.58 | 2.7 | 57% | 1% | 26% | 11% | 17% | 14% | 21% | 2% | 1% | 6.6 | 2.3 |
| old | 180 | 50% | 6.5 | 0.59 | 2.9 | 55% | 1% | 24% | 11% | 18% | 15% | 19% | 3% | 1% | 6.5 | 2.5 |
