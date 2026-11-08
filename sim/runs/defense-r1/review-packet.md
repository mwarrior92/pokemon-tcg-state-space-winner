# Review packet: defense

60 evaluated turns. Read the worst decisions below, decide what the policy is getting wrong and why, and write the reasoning and the changes to make in sim/reviews/ (see sim/REVIEW.md).

- opponent's next-turn prizes after the policy's turn: 0.22; after passing at once: 0.33; best of a sample of positions: 0.12

## Feature sets (validation MSE; predicting the mean gives 0.441)

| set | features | cost | MSE |
|---|---|---|---|
| all features | 1236 | probe | 0.379 |
| cheap groups only (no engine probes) | 886 | cheap | 0.399 |
| all but probe-damage | 900 | probe | 0.391 |
| all but probe-ability | 1224 | probe | 0.387 |
| all but probe-hand | 1234 | probe | 0.379 |
| cheap + probe-damage | 1222 | probe | 0.387 |
| top 200 features by importance | 200 | probe | 0.359 |
| top 100 features by importance | 100 | probe | 0.352 |
| top 50 features by importance | 50 | probe | 0.358 |
| top 25 features by importance | 25 | probe | 0.362 |
| top 200 cheap features by importance | 200 | cheap | 0.391 |
| top 100 cheap features by importance | 100 | cheap | 0.380 |
| top 50 cheap features by importance **(chosen)** | 50 | cheap | 0.383 |
| reach + board + resources only | 239 | cheap | 0.370 |

## Largest weights (full model)

- +0.020 `op.hand`
- +0.019 `op.reach.maxPrize`
- +0.016 `op.s0.a0.nowToActive`
- +0.016 `op.reach.bestDamageToActive`
- +0.016 `op.reach.potentialMaxPrize`
- +0.015 `op.reach.oneShortMaxPrize`
- +0.013 `op.s0.energy`
- +0.013 `op.reach.oneShort1`
- +0.013 `me.s0.damage`
- +0.012 `op.reach.ko0`
- +0.012 `me.s0.koThreat`
- +0.012 `op.reach.oneShortCount`
- -0.012 `op.s0.a0.gap`
- -0.011 `op.s0.retreatGap`
- +0.011 `op.s0.a1.dmgTo0`
- +0.010 `op.s0.damage`
- +0.010 `op.s0.stage`
- +0.010 `op.s2.energyC`
- +0.010 `op.reach.count`
- +0.010 `op.s0.energyW`
- +0.009 `op.reach.oneShort2`
- +0.009 `op.s1.energyP`
- +0.009 `me.deckBasic`
- +0.009 `me.s1.damage`
- +0.009 `op.s3.typeW`
- +0.009 `op.s2.abilityDamage`
- +0.009 `op.s2.stage`
- +0.009 `op.s3.weakL`
- +0.009 `op.s0.a0.koTo0`
- -0.009 `me.discardEnergy`
- +0.008 `me.reach.oneShortMaxPrize`
- +0.008 `op.s0.resistF`
- -0.008 `me.s0.retreatGap`
- +0.008 `op.s0.weakD`
- +0.008 `me.s0.typeD`
- +0.008 `op.s2.energyP`
- -0.008 `op.s3.mega`
- +0.008 `me.s0.ex`
- +0.008 `me.s1.typeC`
- -0.008 `op.s4.energyW`

## Worst decisions

### Dragapult Blaziken vs Mega Lucario (seed 904002) - gap 2

```
Turn 16, P1 to move
P1 (to move): prizes 6  deck 2  discard 36  hand 8
  Active: Meowth ex 170/170 E:D P F
  Bench0: Chi-Yu 110/110 E:F P
  Bench1: Budew 30/30 E:-
  Hand: Munkidori, Dragapult ex, Dawn, Judge, Crispin, Lillie's Determination, Boss's Orders, Crispin
P2: prizes 2  deck 40  discard 6  hand 8
  Active: Riolu 60/70 E:-
  Bench0: Lunatone 40/110 E:F +Lucky Helmet
  Hand: Fighting Energy, Riolu, Legacy Energy, Ultra Ball, Fighting Gong, Lillie's Determination, Boss's Orders, Gravity Mountain
```
- reference (best sampled): 0 - (end turn immediately)
- policy: 2 - play Judge -> end turn
  - chose `play Judge` (predicted 0.60); others: `play Dawn | nothing` 0.63, `play Crispin | nothing` 0.63, `end turn` 0.64, `bench Munkidori` 0.64, `play Lillie's Determination` 0.65
  - chose `end turn` (predicted 0.60); others: `attack Tuck Tail | take a prize | own bench1 Budew` 0.67, `retreat to bench0 Chi-Yu | Darkness Energy` 0.69, `retreat to bench0 Chi-Yu | Psychic Energy` 0.69, `retreat to bench0 Chi-Yu | Fire Energy` 0.69, `retreat to bench1 Budew | Darkness Energy` 0.72

### Ogerpon Meganium vs Dragapult (seed 904023) - gap 2

```
Turn 5, P1 to move
P1 (to move): prizes 5  deck 29  discard 19  hand 3
  Active: Meowth ex 10/170 E:-
  Bench0: Meganium (on Chikorita<Bayleef) 160/160 E:-
  Hand: Ultra Ball, Fezandipiti ex, Grass Energy
P2: prizes 3  deck 30  discard 9  hand 10
  Active: Drakloak (on Dreepy) 90/90 E:P
  Bench0: Budew 30/30 E:-
  Bench1: Dragapult ex (on Dreepy<Drakloak) 320/320 E:-
  Bench2: Dunsparce 70/70 E:-
  Hand: Rosa's Encouragement, Lillie's Determination, Lillie's Determination, Dudunsparce, Buddy-Buddy Poffin, Poké Pad, Ultra Ball, Budew, Poké Pad, Crushing Hammer
```
- reference (best sampled): 0 - (a searched position at depth 2; key 7af305e139316081...)
- policy: 2 - play Ultra Ball | Grass Energy + Fezandipiti ex | Teal Mask Ogerpon ex -> end turn
  - chose `play Ultra Ball | Grass Energy + Fezandipiti ex | Teal Mask Ogerpon ex` (predicted 0.99); others: `play Ultra Ball | Grass Energy + Fezandipiti ex | Smoliv` 0.99, `play Ultra Ball | Grass Energy + Fezandipiti ex | Arboliva ex` 1.00, `play Ultra Ball | Grass Energy + Fezandipiti ex | Noctowl` 1.00, `play Ultra Ball | Grass Energy + Fezandipiti ex | Dolliv` 1.00, `play Ultra Ball | Grass Energy + Fezandipiti ex | nothing` 1.00
  - chose `end turn` (predicted 0.99); others: `bench Teal Mask Ogerpon ex` 1.01

### Dragapult Dusknoir vs Toucannon (seed 904019) - gap 1

```
Turn 19, P1 to move
P1 (to move): prizes 5  deck 1  discard 35  hand 7
  Active: Duskull 50/60 E:F
  Bench0: Drakloak (on Dreepy) 50/90 E:F
  Bench1: Meowth ex 160/170 E:-
  Bench2: Budew 10/30 E:-
  Bench3: Drakloak (on Dreepy) 90/90 E:-
  Bench4: Dragapult ex (on Dreepy<Drakloak) 320/320 E:-
  Hand: Ultra Ball, Crispin, Rosa's Encouragement, Boss's Orders, Lillie's Determination, Lillie's Determination, Lillie's Determination
P2: prizes 2  deck 38  discard 3  hand 8
  Active: Trumbeak (on Pikipek) 90/90 E:-
  Bench0: Pikipek 10/70 E:Mist
  Bench1: Tatsugiri 70/70 E:2Spiky Legacy +Air Balloon
  Hand: Rare Candy, Mist Energy, Toucannon, Air Balloon, Buddy-Buddy Poffin, Rare Candy, Fan Rotom, Genesect
```
- reference (best sampled): 0 - (a searched position at depth 2; key ad2ba6bdd781831f...)
- policy: 1 - retreat to bench3 Drakloak -> play Ultra Ball | Rosa's Encouragement + Lillie's Determination | nothing -> play Crispin | nothing -> end turn
  - chose `retreat to bench3 Drakloak` (predicted 0.79); others: `retreat to bench1 Meowth ex` 0.81, `play Ultra Ball | Rosa's Encouragement + Lillie's Determination | nothing` 0.81, `play Ultra Ball | Rosa's Encouragement + Boss's Orders | nothing` 0.81, `play Ultra Ball | Rosa's Encouragement + Crispin | nothing` 0.81, `play Ultra Ball | Lillie's Determination + Lillie's Determination | nothing` 0.81
  - chose `play Ultra Ball | Rosa's Encouragement + Lillie's Determination | nothing` (predicted 0.78); others: `play Ultra Ball | Rosa's Encouragement + Boss's Orders | nothing` 0.78, `play Ultra Ball | Rosa's Encouragement + Crispin | nothing` 0.78, `play Ultra Ball | Lillie's Determination + Lillie's Determination | nothing` 0.78, `play Ultra Ball | Lillie's Determination + Boss's Orders | nothing` 0.78, `play Ultra Ball | Lillie's Determination + Crispin | nothing` 0.78
  - chose `play Crispin | nothing` (predicted 0.77); others: `end turn` 0.78, `play Lillie's Determination` 0.78, `ability Recon Directive (active Drakloak) | Crispin` 0.78, `ability Recon Directive (bench0 Drakloak) | Crispin` 0.78, `play Boss's Orders | opp bench1 Tatsugiri` 0.79
  - chose `end turn` (predicted 0.77); others: `ability Recon Directive (active Drakloak) | Crispin` 0.78, `ability Recon Directive (bench0 Drakloak) | Crispin` 0.78

### Mega Starmie vs Ethan's Typhlosion (seed 904056) - gap 1

```
Turn 9, P2 to move
P1: prizes 5  deck 32  discard 3  hand 7
  Active: Staryu 70/70 E:-
  Bench0: Mega Starmie ex (on Staryu) 80/330 E:W Ignition Bubbly Water
  Bench1: Drakloak (on Dreepy) 190/190 E:W Ignition +Hero's Cape
  Bench2: Snorunt 50/70 E:-
  Bench3: Fezandipiti ex 210/210 E:-
  Hand: Staryu, Buddy-Buddy Poffin, Mega Starmie ex, Drakloak, Buddy-Buddy Poffin, Switch, Ultra Ball
P2 (to move): prizes 5  deck 40  discard 1  hand 4
  Active: Fezandipiti ex 210/210 E:F
  Bench0: Ethan's Typhlosion (on Ethan's Cyndaquil<Ethan's Quilava) 170/170 E:2F
  Bench1: Victini 40/70 E:2F
  Hand: Special Red Card, Dreepy, Night Stretcher, Ethan's Cyndaquil
```
- reference (best sampled): 1 - (a searched position at depth 2; key f083329e3da4793a...)
- policy: 2 - bench Dreepy -> retreat to bench2 Dreepy -> end turn
  - chose `bench Dreepy` (predicted 0.78); others: `bench Ethan's Cyndaquil` 0.78, `end turn` 0.81, `play Night Stretcher | Ethan's Cyndaquil` 0.81, `play Night Stretcher | nothing` 0.81, `retreat to bench0 Ethan's Typhlosion` 0.83
  - chose `retreat to bench2 Dreepy` (predicted 0.76); others: `end turn` 0.78, `play Night Stretcher | Ethan's Cyndaquil` 0.78, `play Night Stretcher | nothing` 0.78, `bench Ethan's Cyndaquil` 0.78, `retreat to bench0 Ethan's Typhlosion` 0.80
  - chose `end turn` (predicted 0.76); others: `play Night Stretcher | Ethan's Cyndaquil` 0.76, `play Night Stretcher | nothing` 0.76, `bench Ethan's Cyndaquil` 0.76, `play Night Stretcher | Fire Energy` 0.78
