# Pilot audit: vs-hand-b

Pilot `imitrace:runs/imit-v3/policy.json`, 180 games. Rates are shares of the deck's own turns; see `src/audit.ts` for what each column counts.

| deck | games | win | own turns | prizes / turn | first attack (own turn) | attacked | attack not made | no attack payable | Energy held | Supporter held | Stadium held | Basic held | Evolution held | empty Bench | hand at end | Energy in play |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Slowking | 36 | 17% | 6.5 | 0.35 | 3.5 | 42% | 0% | 44% | 3% | 22% | 22% | 16% | 2% | 0% | 6.1 | 2.4 |
| N's Zoroark | 36 | 31% | 6.6 | 0.41 | 3.7 | 41% | 0% | 22% | 6% | 22% | 13% | 11% | 10% | 1% | 5.7 | 2.2 |
| Dragapult | 36 | 33% | 6.6 | 0.44 | 2.4 | 59% | 0% | 17% | 10% | 20% | 17% | 16% | 2% | 2% | 5.0 | 1.8 |
| Basic Box | 36 | 44% | 6.9 | 0.50 | 3.0 | 52% | 0% | 38% | 10% | 12% | 10% | 26% | 0% | 2% | 5.4 | 2.9 |
| Festival Lead | 36 | 44% | 6.6 | 0.46 | 2.1 | 54% | 0% | 32% | 8% | 22% | 11% | 8% | 6% | 0% | 3.9 | 1.2 |
| Hydrapple | 36 | 50% | 6.9 | 0.55 | 3.1 | 52% | 0% | 26% | 17% | 30% | 15% | 25% | 3% | 1% | 7.3 | 4.7 |
| Dragapult Dusknoir | 36 | 56% | 5.9 | 0.69 | 2.7 | 60% | 2% | 13% | 13% | 13% | 13% | 25% | 3% | 0% | 5.0 | 1.8 |
| Dragapult Blaziken | 36 | 69% | 6.6 | 0.64 | 2.5 | 66% | 1% | 9% | 12% | 20% | 19% | 21% | 4% | 3% | 6.7 | 2.6 |
| Alakazam Dusknoir | 36 | 72% | 5.7 | 0.89 | 2.5 | 62% | 3% | 14% | 17% | 12% | 0% | 35% | 6% | 0% | 9.8 | 1.1 |
| Alakazam Dudunsparce | 36 | 83% | 6.2 | 0.82 | 2.6 | 66% | 2% | 22% | 16% | 19% | 32% | 21% | 1% | 0% | 13.0 | 1.9 |

## All decks together

| deck | games | win | own turns | prizes / turn | first attack (own turn) | attacked | attack not made | no attack payable | Energy held | Supporter held | Stadium held | Basic held | Evolution held | empty Bench | hand at end | Energy in play |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| all decks | 360 | 50% | 6.5 | 0.57 | 2.8 | 55% | 1% | 24% | 11% | 19% | 15% | 20% | 4% | 1% | 6.7 | 2.3 |

## New against old (parts off: handsize)

New won 90 of 180 decided games: 50% (95% interval 43% to 57%).
Pairs of games on the same seed: new won both in 5, one each in 80, none in 5.

| deck | games | win | own turns | prizes / turn | first attack (own turn) | attacked | attack not made | no attack payable | Energy held | Supporter held | Stadium held | Basic held | Evolution held | empty Bench | hand at end | Energy in play |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| old | 180 | 50% | 6.5 | 0.58 | 2.9 | 56% | 1% | 24% | 12% | 19% | 15% | 18% | 3% | 1% | 6.6 | 2.3 |
| new | 180 | 50% | 6.5 | 0.55 | 2.8 | 55% | 1% | 24% | 11% | 19% | 16% | 23% | 4% | 1% | 6.8 | 2.3 |
