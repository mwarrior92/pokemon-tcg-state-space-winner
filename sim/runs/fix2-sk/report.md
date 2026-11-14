# Pilot audit: fix2-sk

Pilot `imitrace:runs/imit-v3/policy.json`, 36 games (every game has Slowking). Rates are shares of the deck's own turns; see `src/audit.ts` for what each column counts.

| deck | games | win | own turns | prizes / turn | first attack (own turn) | attacked | attack not made | no attack payable | Energy held | Supporter held | Stadium held | Basic held | Evolution held | empty Bench | hand at end | Energy in play |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Slowking | 36 | 31% | 6.8 | 0.41 | 2.8 | 50% | 2% | 37% | 2% | 22% | 34% | 23% | 0% | 0% | 6.4 | 2.4 |
| N's Zoroark | 4 | 50% | 7.5 | 0.40 | 4.0 | 43% | 0% | 50% | 7% | 13% | 7% | 3% | 3% | 0% | 4.4 | 1.5 |
| Festival Lead | 4 | 50% | 6.5 | 0.46 | 2.3 | 50% | 0% | 42% | 0% | 8% | 19% | 8% | 0% | 0% | 4.3 | 0.8 |
| Dragapult Dusknoir | 4 | 50% | 7.8 | 0.45 | 3.0 | 65% | 0% | 16% | 3% | 16% | 3% | 23% | 0% | 0% | 5.7 | 2.5 |
| Dragapult | 4 | 75% | 8.3 | 0.55 | 3.3 | 58% | 6% | 9% | 18% | 15% | 45% | 6% | 0% | 6% | 6.4 | 2.3 |
| Basic Box | 4 | 75% | 8.3 | 0.58 | 2.0 | 73% | 0% | 12% | 12% | 21% | 42% | 30% | 0% | 0% | 5.3 | 3.6 |
| Hydrapple | 4 | 75% | 6.8 | 0.67 | 2.3 | 67% | 4% | 11% | 7% | 30% | 19% | 22% | 0% | 0% | 6.4 | 4.1 |
| Alakazam Dusknoir | 4 | 75% | 5.0 | 1.15 | 2.8 | 65% | 5% | 0% | 25% | 15% | 0% | 55% | 10% | 0% | 12.1 | 1.1 |
| Dragapult Blaziken | 4 | 75% | 7.3 | 0.79 | 2.0 | 79% | 0% | 7% | 24% | 21% | 28% | 14% | 0% | 3% | 6.8 | 2.7 |
| Alakazam Dudunsparce | 4 | 100% | 5.8 | 1.04 | 1.3 | 78% | 0% | 13% | 22% | 30% | 65% | 9% | 0% | 0% | 15.1 | 2.2 |

## All decks together

| deck | games | win | own turns | prizes / turn | first attack (own turn) | attacked | attack not made | no attack payable | Energy held | Supporter held | Stadium held | Basic held | Evolution held | empty Bench | hand at end | Energy in play |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| all decks | 72 | 50% | 6.9 | 0.53 | 2.7 | 57% | 2% | 27% | 8% | 20% | 30% | 20% | 1% | 1% | 6.7 | 2.4 |
