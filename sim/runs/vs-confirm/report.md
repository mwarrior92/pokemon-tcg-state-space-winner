# Pilot audit: vs-confirm

Pilot `imitrace:runs/imit-v3/policy.json`, 180 games. Rates are shares of the deck's own turns; see `src/audit.ts` for what each column counts.

| deck | games | win | own turns | prizes / turn | first attack (own turn) | attacked | attack not made | no attack payable | Energy held | Supporter held | Stadium held | Basic held | Evolution held | empty Bench | hand at end | Energy in play |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Slowking | 36 | 19% | 6.3 | 0.34 | 3.4 | 36% | 1% | 53% | 8% | 31% | 34% | 17% | 0% | 3% | 6.8 | 2.1 |
| Festival Lead | 36 | 39% | 6.9 | 0.37 | 2.7 | 50% | 1% | 39% | 6% | 33% | 14% | 4% | 0% | 3% | 4.1 | 1.1 |
| Alakazam Dusknoir | 36 | 42% | 5.7 | 0.62 | 2.4 | 50% | 3% | 17% | 9% | 11% | 0% | 31% | 7% | 0% | 9.5 | 1.1 |
| N's Zoroark | 36 | 47% | 8.0 | 0.44 | 3.6 | 50% | 1% | 26% | 10% | 22% | 14% | 8% | 0% | 2% | 5.6 | 2.4 |
| Hydrapple | 36 | 50% | 6.6 | 0.64 | 2.2 | 66% | 3% | 21% | 11% | 28% | 30% | 23% | 0% | 3% | 6.6 | 4.8 |
| Dragapult Blaziken | 36 | 50% | 7.9 | 0.50 | 2.5 | 61% | 1% | 12% | 12% | 16% | 16% | 13% | 4% | 0% | 5.8 | 2.9 |
| Basic Box | 36 | 56% | 6.8 | 0.50 | 2.9 | 56% | 2% | 34% | 12% | 17% | 30% | 27% | 0% | 0% | 5.5 | 3.7 |
| Dragapult Dusknoir | 36 | 58% | 7.4 | 0.51 | 3.1 | 54% | 2% | 11% | 11% | 21% | 18% | 26% | 5% | 0% | 5.8 | 2.2 |
| Dragapult | 36 | 61% | 7.0 | 0.56 | 1.9 | 72% | 0% | 10% | 11% | 20% | 17% | 14% | 0% | 2% | 5.4 | 2.2 |
| Alakazam Dudunsparce | 36 | 78% | 6.3 | 0.79 | 2.5 | 66% | 0% | 22% | 9% | 19% | 36% | 15% | 0% | 0% | 12.7 | 2.0 |

## All decks together

| deck | games | win | own turns | prizes / turn | first attack (own turn) | attacked | attack not made | no attack payable | Energy held | Supporter held | Stadium held | Basic held | Evolution held | empty Bench | hand at end | Energy in play |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| all decks | 360 | 50% | 6.9 | 0.52 | 2.7 | 56% | 1% | 24% | 10% | 22% | 21% | 17% | 2% | 1% | 6.7 | 2.5 |

## New against old (parts off: handneed,inplay)

New won 104 of 180 decided games: 58% (95% interval 51% to 65%).
Pairs of games on the same seed: new won both in 20, one each in 64, none in 6.

| deck | games | win | own turns | prizes / turn | first attack (own turn) | attacked | attack not made | no attack payable | Energy held | Supporter held | Stadium held | Basic held | Evolution held | empty Bench | hand at end | Energy in play |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| old | 180 | 42% | 6.8 | 0.48 | 2.7 | 54% | 2% | 24% | 9% | 23% | 31% | 16% | 1% | 1% | 6.9 | 2.4 |
| new | 180 | 58% | 6.9 | 0.57 | 2.7 | 58% | 1% | 24% | 11% | 21% | 11% | 18% | 2% | 1% | 6.4 | 2.5 |
