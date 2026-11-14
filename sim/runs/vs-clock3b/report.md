# Pilot audit: vs-clock3b

Pilot `imitrace:runs/imit-v3/policy.json`, 180 games. Rates are shares of the deck's own turns; see `src/audit.ts` for what each column counts.

| deck | games | win | own turns | prizes / turn | first attack (own turn) | attacked | attack not made | no attack payable | Energy held | Supporter held | Stadium held | Basic held | Evolution held | empty Bench | hand at end | Energy in play |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Slowking | 36 | 28% | 6.9 | 0.40 | 3.3 | 44% | 0% | 46% | 7% | 26% | 12% | 17% | 2% | 2% | 6.6 | 2.6 |
| Festival Lead | 36 | 33% | 6.8 | 0.42 | 2.5 | 52% | 0% | 30% | 5% | 28% | 17% | 7% | 3% | 3% | 4.0 | 1.2 |
| N's Zoroark | 36 | 36% | 6.9 | 0.40 | 3.4 | 46% | 0% | 31% | 12% | 16% | 8% | 12% | 2% | 2% | 5.3 | 2.2 |
| Basic Box | 36 | 47% | 6.7 | 0.55 | 2.9 | 57% | 1% | 33% | 12% | 17% | 21% | 26% | 0% | 0% | 5.6 | 3.5 |
| Dragapult Dusknoir | 36 | 47% | 6.6 | 0.50 | 3.5 | 49% | 2% | 12% | 11% | 22% | 14% | 23% | 7% | 0% | 5.1 | 2.1 |
| Dragapult | 36 | 50% | 6.6 | 0.58 | 2.0 | 71% | 0% | 10% | 9% | 16% | 16% | 18% | 1% | 2% | 5.7 | 2.2 |
| Dragapult Blaziken | 36 | 56% | 7.2 | 0.55 | 2.4 | 67% | 0% | 8% | 9% | 14% | 14% | 15% | 1% | 0% | 5.5 | 2.6 |
| Hydrapple | 36 | 64% | 6.9 | 0.66 | 2.5 | 65% | 2% | 20% | 10% | 19% | 23% | 17% | 0% | 2% | 5.7 | 4.4 |
| Alakazam Dusknoir | 36 | 64% | 5.3 | 0.84 | 2.2 | 61% | 1% | 14% | 15% | 8% | 0% | 34% | 7% | 0% | 9.7 | 1.1 |
| Alakazam Dudunsparce | 36 | 75% | 6.1 | 0.82 | 2.6 | 67% | 1% | 22% | 9% | 18% | 29% | 16% | 1% | 0% | 12.2 | 2.1 |

## All decks together

| deck | games | win | own turns | prizes / turn | first attack (own turn) | attacked | attack not made | no attack payable | Energy held | Supporter held | Stadium held | Basic held | Evolution held | empty Bench | hand at end | Energy in play |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| all decks | 360 | 50% | 6.6 | 0.56 | 2.7 | 58% | 1% | 23% | 10% | 19% | 16% | 18% | 2% | 1% | 6.4 | 2.4 |

## New against old (parts off: clock)

New won 94 of 180 decided games: 52% (95% interval 45% to 60%).
Pairs of games on the same seed: new won both in 17, one each in 60, none in 13.

| deck | games | win | own turns | prizes / turn | first attack (own turn) | attacked | attack not made | no attack payable | Energy held | Supporter held | Stadium held | Basic held | Evolution held | empty Bench | hand at end | Energy in play |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| old | 180 | 48% | 6.6 | 0.53 | 2.6 | 59% | 1% | 24% | 8% | 18% | 14% | 20% | 2% | 1% | 6.2 | 2.3 |
| new | 180 | 52% | 6.6 | 0.59 | 2.9 | 56% | 1% | 21% | 11% | 20% | 17% | 16% | 3% | 1% | 6.7 | 2.6 |
