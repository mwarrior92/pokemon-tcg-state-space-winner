# Win-probability model from playout-win2-vs-v2, playout-v1

3926 turn-start positions from 500 decided games; 3150 train, 776 validation (by game).

Predicting 50% everywhere: log loss 0.693. Share of validation positions whose mover lost: 47%.

| model | features | log loss | AUC | accuracy | lambda |
|---|---|---|---|---|---|
| prize counts only | 2 | 0.534 | 0.819 | 72.7% | 1 |
| prizes + reach + bench/hand/deck | 67 | 0.444 | 0.889 | 82.3% | 10 |
| all cheap features | 886 | 0.497 | 0.853 | 80.4% | 1000 |

saved: prizes + reach + bench/hand/deck (lower validation log loss)

Largest weights of the saved model (standardized):
- -0.660 `me.prizes`
- -0.637 `op.deck`
- +0.630 `op.prizes`
- +0.608 `me.deck`
- +0.371 `me.reach.potentialMaxPrize`
- -0.341 `op.benchCount`
- -0.319 `me.deckBasic`
- -0.295 `op.reach.potentialMaxPrize`
- +0.240 `me.reach.oneShortCount`
- -0.230 `me.hand`
- -0.223 `op.reach.maxPrize`
- +0.216 `me.reach.ko0`
- +0.212 `me.benchCount`
- +0.207 `me.reach.ko1`
- +0.197 `me.reach.bestDamageToActive`
- -0.178 `op.reach.oneShortCount`
- +0.169 `me.handEnergyP`
- +0.159 `op.hand`
- -0.141 `op.reach.bestDamageToActive`
- +0.141 `me.reach.ko4`
- -0.141 `op.reach.ko4`
- -0.139 `me.handEnergyF`
- -0.136 `me.handSupporter`
- +0.124 `me.handEnergyC`
- -0.113 `me.reach.oneShort3`
