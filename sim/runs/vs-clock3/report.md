# Pilot audit: vs-clock3

Pilot `imitrace:runs/imit-v3/policy.json`, 180 games. Rates are shares of the deck's own turns; see `src/audit.ts` for what each column counts.

| deck | games | win | own turns | prizes / turn | first attack (own turn) | attacked | attack not made | no attack payable | Energy held | Supporter held | Stadium held | Basic held | Evolution held | empty Bench | hand at end | Energy in play |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| N's Zoroark | 36 | 28% | 6.8 | 0.48 | 3.4 | 47% | 0% | 23% | 4% | 22% | 6% | 15% | 2% | 2% | 5.8 | 2.3 |
| Slowking | 36 | 28% | 7.2 | 0.34 | 3.7 | 39% | 2% | 44% | 5% | 22% | 17% | 17% | 1% | 0% | 6.5 | 2.4 |
| Dragapult | 36 | 31% | 7.3 | 0.39 | 2.5 | 62% | 1% | 12% | 8% | 18% | 17% | 17% | 1% | 2% | 5.0 | 2.1 |
| Festival Lead | 36 | 33% | 6.6 | 0.33 | 2.4 | 49% | 0% | 39% | 3% | 22% | 9% | 5% | 4% | 1% | 3.5 | 1.0 |
| Hydrapple | 36 | 47% | 6.9 | 0.54 | 2.6 | 55% | 1% | 25% | 14% | 26% | 17% | 19% | 2% | 2% | 6.5 | 4.5 |
| Basic Box | 36 | 50% | 7.8 | 0.46 | 3.2 | 54% | 0% | 38% | 13% | 16% | 8% | 25% | 0% | 1% | 5.3 | 3.3 |
| Dragapult Dusknoir | 36 | 64% | 6.3 | 0.70 | 2.7 | 62% | 0% | 15% | 11% | 13% | 14% | 18% | 0% | 0% | 4.9 | 2.1 |
| Alakazam Dusknoir | 36 | 69% | 5.8 | 0.88 | 2.5 | 61% | 3% | 12% | 14% | 15% | 0% | 35% | 5% | 0% | 10.2 | 1.2 |
| Dragapult Blaziken | 36 | 72% | 7.1 | 0.65 | 2.2 | 70% | 0% | 8% | 9% | 17% | 14% | 19% | 3% | 1% | 6.2 | 2.9 |
| Alakazam Dudunsparce | 36 | 78% | 6.6 | 0.76 | 2.6 | 67% | 2% | 22% | 13% | 17% | 30% | 17% | 2% | 0% | 12.8 | 1.9 |

## All decks together

| deck | games | win | own turns | prizes / turn | first attack (own turn) | attacked | attack not made | no attack payable | Energy held | Supporter held | Stadium held | Basic held | Evolution held | empty Bench | hand at end | Energy in play |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| all decks | 360 | 50% | 6.8 | 0.54 | 2.8 | 56% | 1% | 24% | 9% | 19% | 13% | 19% | 2% | 1% | 6.6 | 2.4 |

## New against old (parts off: clock)

New won 99 of 180 decided games: 55% (95% interval 48% to 62%).
Pairs of games on the same seed: new won both in 20, one each in 59, none in 11.

| deck | games | win | own turns | prizes / turn | first attack (own turn) | attacked | attack not made | no attack payable | Energy held | Supporter held | Stadium held | Basic held | Evolution held | empty Bench | hand at end | Energy in play |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| old | 180 | 45% | 6.8 | 0.51 | 2.7 | 57% | 1% | 26% | 8% | 18% | 13% | 19% | 2% | 1% | 6.4 | 2.3 |
| new | 180 | 55% | 6.9 | 0.58 | 2.9 | 56% | 1% | 23% | 10% | 19% | 13% | 19% | 2% | 1% | 6.7 | 2.5 |
