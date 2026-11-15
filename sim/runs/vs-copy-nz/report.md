# Pilot audit: vs-copy-nz

Pilot `imitrace:runs/imit-v3/policy.json`, 72 games (every game has N's Zoroark). Rates are shares of the deck's own turns; see `src/audit.ts` for what each column counts.

| deck | games | win | own turns | prizes / turn | first attack (own turn) | attacked | attack not made | no attack payable | Energy held | Supporter held | Stadium held | Basic held | Evolution held | empty Bench | hand at end | Energy in play |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Slowking | 8 | 25% | 7.4 | 0.31 | 4.9 | 36% | 2% | 32% | 3% | 10% | 20% | 14% | 3% | 0% | 5.2 | 2.9 |
| Dragapult | 8 | 38% | 6.9 | 0.56 | 3.3 | 53% | 2% | 7% | 4% | 18% | 44% | 13% | 2% | 0% | 5.0 | 2.1 |
| Basic Box | 8 | 38% | 7.4 | 0.58 | 2.1 | 69% | 0% | 24% | 8% | 14% | 7% | 14% | 0% | 0% | 4.5 | 3.4 |
| Dragapult Dusknoir | 8 | 38% | 6.8 | 0.50 | 4.0 | 48% | 6% | 4% | 11% | 15% | 15% | 20% | 6% | 0% | 4.5 | 1.9 |
| N's Zoroark | 72 | 46% | 7.0 | 0.49 | 3.2 | 49% | 0% | 22% | 9% | 20% | 6% | 11% | 3% | 1% | 5.5 | 2.3 |
| Dragapult Blaziken | 8 | 50% | 6.3 | 0.70 | 2.8 | 64% | 2% | 18% | 16% | 14% | 12% | 30% | 0% | 0% | 5.5 | 2.4 |
| Hydrapple | 8 | 63% | 7.1 | 0.60 | 3.1 | 54% | 0% | 16% | 18% | 19% | 30% | 19% | 2% | 0% | 5.7 | 4.5 |
| Festival Lead | 8 | 75% | 9.4 | 0.37 | 4.9 | 40% | 3% | 37% | 1% | 17% | 15% | 4% | 3% | 0% | 3.1 | 1.5 |
| Alakazam Dudunsparce | 8 | 75% | 6.4 | 0.80 | 1.6 | 69% | 0% | 12% | 6% | 10% | 43% | 25% | 4% | 0% | 10.6 | 1.9 |
| Alakazam Dusknoir | 8 | 88% | 5.8 | 1.00 | 2.6 | 67% | 0% | 13% | 37% | 9% | 0% | 22% | 4% | 0% | 9.3 | 1.0 |

## All decks together

| deck | games | win | own turns | prizes / turn | first attack (own turn) | attacked | attack not made | no attack payable | Energy held | Supporter held | Stadium held | Basic held | Evolution held | empty Bench | hand at end | Energy in play |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| all decks | 144 | 50% | 7.0 | 0.54 | 3.2 | 52% | 1% | 21% | 10% | 17% | 13% | 14% | 3% | 0% | 5.6 | 2.4 |

## New against old (parts off: copy)

New won 43 of 72 decided games: 60% (95% interval 48% to 71%).
Pairs of games on the same seed: new won both in 11, one each in 21, none in 4.

| deck | games | win | own turns | prizes / turn | first attack (own turn) | attacked | attack not made | no attack payable | Energy held | Supporter held | Stadium held | Basic held | Evolution held | empty Bench | hand at end | Energy in play |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| old | 72 | 40% | 7.0 | 0.48 | 3.3 | 50% | 1% | 22% | 9% | 18% | 13% | 15% | 3% | 0% | 5.6 | 2.4 |
| new | 72 | 60% | 7.1 | 0.59 | 3.1 | 53% | 1% | 19% | 11% | 16% | 13% | 13% | 2% | 0% | 5.6 | 2.4 |
