# Pilot audit: vs-prev3

Pilot `imitrace:runs/imit-v3/policy.json`, 180 games. Rates are shares of the deck's own turns; see `src/audit.ts` for what each column counts.

| deck | games | win | own turns | prizes / turn | first attack (own turn) | attacked | attack not made | no attack payable | Energy held | Supporter held | Stadium held | Basic held | Evolution held | empty Bench | hand at end | Energy in play |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Slowking | 36 | 22% | 6.9 | 0.35 | 3.1 | 45% | 2% | 39% | 4% | 30% | 13% | 10% | 1% | 0% | 5.7 | 2.4 |
| N's Zoroark | 36 | 31% | 7.5 | 0.45 | 3.2 | 48% | 1% | 25% | 4% | 19% | 7% | 12% | 2% | 2% | 5.4 | 2.2 |
| Festival Lead | 36 | 36% | 6.9 | 0.35 | 2.5 | 51% | 0% | 36% | 4% | 24% | 12% | 6% | 1% | 1% | 3.9 | 1.1 |
| Basic Box | 36 | 39% | 7.8 | 0.41 | 3.4 | 50% | 1% | 42% | 11% | 16% | 12% | 17% | 0% | 1% | 4.4 | 3.4 |
| Dragapult | 36 | 42% | 7.8 | 0.44 | 2.3 | 67% | 0% | 12% | 7% | 19% | 17% | 14% | 0% | 1% | 5.5 | 2.1 |
| Hydrapple | 36 | 53% | 8.1 | 0.46 | 2.6 | 50% | 2% | 18% | 11% | 36% | 24% | 11% | 1% | 1% | 7.1 | 4.9 |
| Alakazam Dudunsparce | 36 | 67% | 6.5 | 0.74 | 2.3 | 68% | 1% | 23% | 10% | 14% | 29% | 20% | 0% | 0% | 12.3 | 1.8 |
| Dragapult Dusknoir | 36 | 69% | 7.3 | 0.58 | 2.8 | 55% | 0% | 16% | 11% | 22% | 23% | 14% | 4% | 0% | 6.0 | 2.2 |
| Alakazam Dusknoir | 36 | 69% | 5.7 | 0.86 | 2.4 | 66% | 2% | 13% | 8% | 17% | 0% | 34% | 2% | 0% | 9.9 | 1.2 |
| Dragapult Blaziken | 36 | 72% | 7.1 | 0.68 | 1.8 | 72% | 0% | 7% | 12% | 17% | 14% | 16% | 1% | 1% | 6.2 | 2.9 |

## All decks together

| deck | games | win | own turns | prizes / turn | first attack (own turn) | attacked | attack not made | no attack payable | Energy held | Supporter held | Stadium held | Basic held | Evolution held | empty Bench | hand at end | Energy in play |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| all decks | 360 | 50% | 7.2 | 0.52 | 2.6 | 57% | 1% | 23% | 8% | 22% | 15% | 15% | 1% | 1% | 6.5 | 2.5 |

## New against old (parts off: handneed,supply,targets)

New won 96 of 180 decided games: 53% (95% interval 46% to 61%).
Pairs of games on the same seed: new won both in 14, one each in 68, none in 8.

| deck | games | win | own turns | prizes / turn | first attack (own turn) | attacked | attack not made | no attack payable | Energy held | Supporter held | Stadium held | Basic held | Evolution held | empty Bench | hand at end | Energy in play |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| old | 180 | 47% | 7.2 | 0.49 | 2.7 | 55% | 1% | 24% | 8% | 21% | 16% | 13% | 1% | 1% | 6.5 | 2.3 |
| new | 180 | 53% | 7.2 | 0.55 | 2.5 | 58% | 1% | 23% | 9% | 22% | 15% | 17% | 2% | 1% | 6.5 | 2.6 |
