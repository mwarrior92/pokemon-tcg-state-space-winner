# Imitation policy: imit-v3

972 real states (stated actions) from 39 matches (62 game logs). Each state's candidates are the turn search's steps (action + prompt answers); the policy scores them by the change in the mover's features, the kind of action and Trainer, and prizes taken.

| | states | top choice is the real action (or interchangeable) |
|---|---|---|
| policy, held out by match (5 folds, λ 1) | 972 | **45%** (same prompt answers too: 37%) |
| chance (a random main action) | 972 | 17% |
| runs/align-race-27 (first action of its planned line) | 468 | 17% |

Cross-validation over λ: 0.1: 44%, 1: 45%, 3: 42%.

## Largest weights (standardized)

- +0.16 kind.evolve
- +0.13 d.me.hand
- +0.11 kind.ability
- -0.09 d.energyAttached
- -0.08 d.me.s0.a0.gap
- -0.08 d.me.deck
- +0.08 d.me.handSupporter
- +0.07 d.me.handItem
- -0.06 kind.stadium
- +0.06 d.me.accelSources
- +0.06 d.me.s1.stage
- -0.06 d.me.altPokemon
- -0.06 d.me.discardPokemon
- +0.05 d.op.discardEnergy
- -0.05 d.me.discard
- +0.05 d.me.handBasic
- -0.05 d.me.s0.retreatGap
- -0.05 kind.tool
- -0.05 d.me.s0.a0.cost
- +0.04 d.me.reach.bestDamageToActive
- +0.04 d.me.handPokemon
- -0.04 trainer.item
- +0.04 trainer.supporter
- -0.04 d.me.discardTrainer
- -0.04 kind.attach
