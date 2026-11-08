# Win-probability model for playout-v1

2187 turn-start positions from 300 decided games; 1772 train, 415 validation (by game).

Predicting 50% everywhere: log loss 0.693. Share of validation positions whose mover lost: 47%.

| model | features | log loss | AUC | accuracy | lambda |
|---|---|---|---|---|---|
| prize counts only | 2 | 0.552 | 0.815 | 74.0% | 1 |
| prizes + reach + bench/hand/deck | 67 | 0.499 | 0.853 | 79.8% | 100 |
| all cheap features | 886 | 0.519 | 0.825 | 73.5% | 100 |

saved: prizes + reach + bench/hand/deck (lower validation log loss)

Largest weights of the saved model (standardized):
- -0.377 `me.prizes`
- +0.342 `op.prizes`
- -0.296 `op.deck`
- -0.281 `op.benchCount`
- +0.269 `me.benchCount`
- +0.265 `me.deck`
- +0.196 `me.reach.oneShortMaxPrize`
- -0.172 `op.reach.potentialMaxPrize`
- +0.171 `me.reach.potentialMaxPrize`
- +0.169 `me.handEnergyM`
- -0.166 `op.reach.oneShortMaxPrize`
- +0.161 `me.handEnergyG`
- -0.160 `op.reach.maxPrize`
- +0.155 `me.reach.bestDamageToActive`
- -0.143 `me.hand`
- -0.140 `me.handSupporter`
- -0.137 `op.reach.bestDamageToActive`
- -0.128 `me.deckBasic`
- +0.109 `op.hand`
- +0.108 `me.deckEnergy`
- -0.106 `me.deckPokemon`
- -0.098 `me.handEnergyF`
- +0.097 `me.handEnergyW`
- +0.093 `me.reach.oneShortCount`
- +0.090 `me.handEnergy`
