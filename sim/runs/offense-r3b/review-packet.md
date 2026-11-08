# Review packet: offense

100 evaluated turns. Read the worst decisions below, decide what the policy is getting wrong and why, and write the reasoning and the changes to make in sim/reviews/ (see sim/REVIEW.md).

- search (teacher): 0.57 prizes/turn; policy: 0.61; policy matched the search on 93/100

## Feature sets (validation MSE; predicting the mean gives 0.268)

| set | features | cost | MSE |
|---|---|---|---|
| all features | 1236 | probe | 0.190 |
| cheap groups only (no engine probes) | 886 | cheap | 0.204 |
| all but probe-damage | 900 | probe | 0.200 |
| all but probe-ability | 1224 | probe | 0.195 |
| all but probe-hand | 1234 | probe | 0.190 |
| cheap + probe-damage | 1222 | probe | 0.195 |
| top 200 features by importance | 200 | probe | 0.188 |
| top 100 features by importance | 100 | probe | 0.187 |
| top 50 features by importance | 50 | probe | 0.176 |
| top 25 features by importance | 25 | probe | 0.177 |
| top 200 cheap features by importance | 200 | cheap | 0.202 |
| top 100 cheap features by importance | 100 | cheap | 0.202 |
| top 50 cheap features by importance **(chosen)** | 50 | cheap | 0.198 |
| reach + board + resources only | 239 | cheap | 0.202 |

## Largest weights (full model)

- +0.032 `me.s0.a0.nowToActive`
- +0.026 `me.reach.ko0`
- +0.024 `me.reach.maxPrize`
- +0.023 `me.s0.abilityDamage`
- +0.022 `me.s0.a0.koTo0`
- +0.017 `me.reach.count`
- -0.017 `me.s0.a0.gap`
- +0.016 `me.s0.stage`
- +0.016 `me.s0.energy`
- +0.014 `me.s1.abilityDamage`
- -0.014 `energyAttached`
- +0.013 `me.s0.a1.nowToActive`
- -0.012 `me.s0.retreatGap`
- +0.012 `me.reach.bestDamageToActive`
- +0.012 `op.s0.energyP`
- -0.012 `me.deckEnergy`
- +0.012 `me.s0.energyC`
- +0.011 `op.s0.damage`
- +0.010 `me.s0.energyG`
- +0.010 `me.s2.abilityDamage`
- +0.010 `me.reach.potentialMaxPrize`
- +0.009 `me.s0.energyW`
- -0.009 `me.accelSources`
- +0.009 `me.reach.oneShortCount`
- +0.009 `me.s3.energyW`
- +0.009 `op.s5.energyG`
- -0.009 `me.s0.typeN`
- +0.008 `me.s3.a1.koTo0`
- +0.008 `op.s4.energyF`
- +0.008 `me.s0.a1.koTo0`
- +0.008 `me.s1.weakD`
- +0.008 `me.s0.a0.dmgTo0`
- -0.008 `me.discardEnergy`
- +0.008 `op.reach.oneShort2`
- -0.008 `me.handEnergyF`
- +0.008 `op.s3.energyR`
- -0.008 `op.s0.hpLeft`
- +0.007 `me.s0.a0.dmgTo1`
- +0.007 `me.counterAbilities`
- +0.007 `op.s2.energyG`

## Worst decisions

### Clefairy Ogerpon vs Absol Audino (seed 803015) - gap 2

```
Turn 9, P2 to move
Stadium: Area Zero Underdepths
P1: prizes 1  deck 43  discard 3  hand 4
  Active: Meowth ex 140/170 E:-
  Bench0: Mega Kangaskhan ex 300/300 E:-
  Bench1: Meowth ex 30/170 E:- +Lillie's Pearl
  Bench2: Fezandipiti ex 210/210 E:Telepathic Psychic F +Lillie's Pearl
  Hand: Special Red Card, Energy Switch, Boss's Orders, Area Zero Underdepths
P2 (to move): prizes 3  deck 29  discard 17  hand 6
  Active: Mega Audino ex 160/270 E:P D
  Bench0: Munkidori 30/110 E:-
  Bench1: Psyduck 70/70 E:-
  Hand: Boss's Orders, Pokégear 3.0, Team Rocket's Petrel, Xerosic's Machinations, Darkness Energy, Team Rocket's Petrel
```
- reference (search): 2 - play Boss's Orders | opp bench1 Meowth ex -> attach Darkness Energy -> bench0 Munkidori -> ability Adrena-Brain (bench0 Munkidori) | move 3 counters -> opp active Meowth ex | take 2 prizes -> (end turn)
- policy: 0 - play Boss's Orders | opp bench2 Fezandipiti ex -> play Pokégear 3.0 | Lisia's Appeal -> attach Darkness Energy -> bench0 Munkidori -> ability Adrena-Brain (bench0 Munkidori) | move 2 counters -> opp active Fezandipiti ex -> attack Kaleidowaltz | Darkness Energy -> own bench0 Munkidori, Darkness Energy -> own bench1 Psyduck
  - chose `play Boss's Orders | opp bench2 Fezandipiti ex` (predicted 0.28); others: `play Pokégear 3.0 | Lisia's Appeal` 0.28, `play Boss's Orders | opp bench1 Meowth ex` 0.28, `play Pokégear 3.0 | Team Rocket's Petrel` 0.27, `play Pokégear 3.0 | nothing` 0.25, `play Team Rocket's Petrel | Lillie's Determination` 0.25
  - chose `play Pokégear 3.0 | Lisia's Appeal` (predicted 0.28); others: `play Pokégear 3.0 | Team Rocket's Petrel` 0.28, `play Pokégear 3.0 | nothing` 0.27, `attach Darkness Energy -> active Mega Audino ex` 0.24, `attach Darkness Energy -> bench1 Psyduck` 0.23, `attach Darkness Energy -> bench0 Munkidori` 0.20
  - chose `attach Darkness Energy -> bench0 Munkidori` (predicted 0.23); others: `retreat to bench0 Munkidori | Darkness Energy` 0.20, `attach Darkness Energy -> bench1 Psyduck` 0.16, `retreat to bench1 Psyduck | Darkness Energy` 0.16, `retreat to bench0 Munkidori | Psychic Energy` 0.15, `retreat to bench1 Psyduck | Psychic Energy` 0.12
  - chose `ability Adrena-Brain (bench0 Munkidori) | move 2 counters -> opp active Fezandipiti ex` (predicted 0.23); others: `ability Adrena-Brain (bench0 Munkidori) | move 1 counters -> opp active Fezandipiti ex` 0.22, `ability Adrena-Brain (bench0 Munkidori) | move 1 counters -> opp active Fezandipiti ex` 0.22, `ability Adrena-Brain (bench0 Munkidori) | move 3 counters -> opp active Fezandipiti ex` 0.21, `ability Adrena-Brain (bench0 Munkidori) | move 3 counters -> opp active Fezandipiti ex` 0.21, `ability Adrena-Brain (bench0 Munkidori) | move 2 counters -> opp active Fezandipiti ex` 0.21
  - chose `attack Kaleidowaltz | Darkness Energy -> own bench0 Munkidori, Darkness Energy -> own bench1 Psyduck` (exact 0.00); others: `retreat to bench0 Munkidori | Psychic Energy` 0.00, `retreat to bench0 Munkidori | Darkness Energy` 0.00, `retreat to bench1 Psyduck | Psychic Energy` 0.00, `retreat to bench1 Psyduck | Darkness Energy` 0.00, `attack Kaleidowaltz | Darkness Energy -> own active Mega Audino ex, Darkness Energy -> own bench1 Psyduck` 0.00

### Lopunny Dusknoir vs Mega Excadrill (seed 803053) - gap 2

```
Turn 19, P2 to move
P1: prizes 5  deck 9  discard 41  hand 3
  Active: Mega Kangaskhan ex 250/300 E:-
  Bench0: Latias ex 60/210 E:-
  Hand: Duskull, Switch, Hilda
P2 (to move): prizes 3  deck 29  discard 9  hand 7
  Active: Genesect ex 320/320 E:- +Hero's Cape
  Bench0: Metang (on Beldum) 10/100 E:M
  Bench1: Drilbur 70/70 E:2M
  Bench2: Fezandipiti ex 100/210 E:3M
  Hand: Metang, Pokégear 3.0, Mega Excadrill ex, Pokégear 3.0, Mega Skarmory ex, Mega Excadrill ex, Team Rocket's Petrel
```
- reference (search): 2 - play Team Rocket's Petrel | Switch -> play Switch | own bench2 Fezandipiti ex -> attack Cruel Arrow | opp bench0 Latias ex | take 2 prizes
- policy: 0 - end turn
  - chose `end turn` (exact 0.00); others: `play Pokégear 3.0 | Team Rocket's Petrel` 0.00, `play Pokégear 3.0 | Brock's Scouting` 0.00, `play Pokégear 3.0 | nothing` 0.00, `evolve bench1 Drilbur -> Mega Excadrill ex` 0.00, `bench Mega Skarmory ex` 0.00

### Mega Lucario vs Clefairy Ogerpon (seed 803056) - gap 2

```
Turn 13, P1 to move
Stadium: Gravity Mountain
P1 (to move): prizes 3  deck 25  discard 18  hand 1
  Active: Dunsparce 60/70 E:4F
  Bench0: Dudunsparce (on Dunsparce) 140/140 E:F
  Bench1: Mega Lucario ex (on Riolu) 340/340 E:F Legacy
  Hand: Hilda
P2: prizes 4  deck 41  discard 2  hand 9
  Active: Chien-Pao 40/120 E:2G
  Bench0: Mega Kangaskhan ex 190/300 E:-
  Hand: Telepathic Psychic Energy, Energy Switch, Fighting Energy, Teal Mask Ogerpon ex, Meowth ex, Lillie's Clefairy ex, Latias ex, Mew ex, Crispin
```
- reference (search): 3 - ability Run Away Draw (bench0 Dudunsparce) -> play Boss's Orders | opp bench0 Mega Kangaskhan ex -> retreat to bench1 Mega Lucario ex -> attack Aura Jab | Fighting Energy -> own bench1 Dunsparce, Fighting Energy -> own bench1 Dunsparce
- policy: 1 - play Hilda | Dudunsparce + Rocky Fighting Energy -> evolve active Dunsparce -> Dudunsparce -> ability Run Away Draw (active Dudunsparce) | own bench0 Dudunsparce -> ability Run Away Draw (active Dudunsparce) | own bench1 Mega Lucario ex -> attack Aura Jab | attach nothing | take a prize
  - chose `play Hilda | Dudunsparce + Rocky Fighting Energy` (predicted 1.00); others: `play Hilda | Dudunsparce` 1.00, `play Hilda | Mega Lucario ex + Rocky Fighting Energy` 1.00, `play Hilda | Mega Lucario ex` 1.00, `play Hilda | Rocky Fighting Energy` 1.00, `play Hilda | nothing` 1.00
  - chose `evolve active Dunsparce -> Dudunsparce` (predicted 1.00); others: `retreat to bench1 Mega Lucario ex` 1.00, `ability Run Away Draw (bench0 Dudunsparce)` 0.72, `attach Rocky Fighting Energy -> active Dunsparce` 0.66, `attach Rocky Fighting Energy -> bench0 Dudunsparce` 0.64, `attach Rocky Fighting Energy -> bench1 Mega Lucario ex` 0.64
  - chose `ability Run Away Draw (active Dudunsparce) | own bench0 Dudunsparce` (predicted 1.07); others: `ability Run Away Draw (active Dudunsparce) | own bench1 Mega Lucario ex` 1.07, `ability Run Away Draw (bench0 Dudunsparce)` 1.07, `attach Rocky Fighting Energy -> active Dudunsparce` 1.00, `attach Rocky Fighting Energy -> bench0 Dudunsparce` 1.00, `attach Rocky Fighting Energy -> bench1 Mega Lucario ex` 1.00
  - chose `ability Run Away Draw (active Dudunsparce) | own bench1 Mega Lucario ex` (predicted 1.07); others: `attach Rocky Fighting Energy -> active Dudunsparce` 1.00, `play Premium Power Pro` 0.34, `attach Rocky Fighting Energy -> bench1 Mega Lucario ex` 0.27, `end turn` 0.00
  - chose `attack Aura Jab | attach nothing | take a prize` (exact 1.00); others: `attach Rocky Fighting Energy -> active Mega Lucario ex` 1.00, `play Premium Power Pro` 1.00, `attack Mega Brave | take a prize` 1.00, `end turn` 0.00

### Festival Lead vs N's Zoroark (seed 803020) - gap 1

```
Turn 14, P2 to move
P1: prizes 1  deck 12  discard 25  hand 10
  Active: Dipplin (on Applin) 100/100 E:2G Growing [G] +Brave Bangle
  Bench0: Seaking (on Goldeen) 20/110 E:-
  Bench1: Grookey 10/70 E:-
  Bench2: Rabsca (on Rellor) 70/70 E:-
  Bench3: Applin 30/40 E:-
  Hand: Grookey, Ultra Ball, Lillie's Determination, Lillie's Determination, Kieran, Poké Pad, Night Stretcher, Pokémon Catcher, Gladion's Final Battle, Ultra Ball
P2 (to move): prizes 3  deck 33  discard 13  hand 7
  Active: Pecharunt ex 190/190 E:2D
  Bench0: N's Zorua 10/70 E:-
  Hand: Boss's Orders, N's Zorua, Special Red Card, Buddy-Buddy Poffin, Boss's Orders, N's Reshiram, Yveltal
```
- reference (search): 1 - play Boss's Orders | opp bench1 Grookey -> bench N's Zorua -> play Buddy-Buddy Poffin | Budew -> retreat to bench2 Budew -> attack Itchy Pollen | take a prize
- policy: 0 - play Boss's Orders | opp bench0 Seaking -> bench Yveltal -> play Special Red Card -> play Buddy-Buddy Poffin | Budew -> ability Subjugating Chains (active Pecharunt ex) | own bench1 Yveltal -> retreat to bench1 Pecharunt ex -> attack Irritated Outburst
  - chose `play Boss's Orders | opp bench0 Seaking` (predicted 0.58); others: `play Buddy-Buddy Poffin | Budew` 0.57, `play Boss's Orders | opp bench1 Grookey` 0.56, `bench N's Zorua` 0.55, `play Buddy-Buddy Poffin | nothing` 0.48, `play Boss's Orders | opp bench3 Applin` 0.46
  - chose `bench Yveltal` (predicted 0.58); others: `play Buddy-Buddy Poffin | Budew` 0.57, `bench N's Zorua` 0.55, `bench N's Reshiram` 0.53, `play Buddy-Buddy Poffin | nothing` 0.48, `play Special Red Card` 0.45
  - chose `play Special Red Card` (predicted 0.55); others: `play Buddy-Buddy Poffin | Budew` 0.55, `ability Subjugating Chains (active Pecharunt ex) | own bench1 Yveltal` 0.55, `play Buddy-Buddy Poffin | nothing` 0.55, `bench N's Zorua` 0.54, `bench N's Reshiram` 0.49
  - chose `play Buddy-Buddy Poffin | Budew` (predicted 0.55); others: `play Buddy-Buddy Poffin | nothing` 0.55, `bench N's Zorua` 0.50, `ability Subjugating Chains (active Pecharunt ex) | own bench1 Yveltal` 0.47, `bench N's Reshiram` 0.45, `retreat to bench1 Yveltal` 0.17
  - chose `ability Subjugating Chains (active Pecharunt ex) | own bench1 Yveltal` (predicted 0.52); others: `bench N's Zorua` 0.46, `bench N's Reshiram` 0.44, `retreat to bench0 N's Zorua` 0.17, `retreat to bench2 Budew` 0.17, `retreat to bench1 Yveltal` 0.11
  - chose `retreat to bench1 Pecharunt ex` (predicted 0.52); others: `bench N's Zorua` 0.46, `bench N's Reshiram` 0.44, `retreat to bench2 Budew` 0.13, `retreat to bench0 N's Zorua` 0.08, `end turn` 0.00
  - chose `attack Irritated Outburst` (exact 0.00); others: `bench N's Zorua` 0.00, `bench N's Reshiram` 0.00, `end turn` 0.00

### Clefairy Ogerpon vs Lopunny Dusknoir (seed 803025) - gap 1

```
Turn 3, P1 to move
P1 (to move): prizes 6  deck 40  discard 3  hand 3
  Active: Mew ex 160/160 E:W
  Bench0: Meowth ex 160/170 E:- +Lillie's Pearl
  Bench1: Passimian 80/110 E:-
  Bench2: Latias ex 90/210 E:-
  Bench3: Wellspring Mask Ogerpon ex 210/210 E:-
  Bench4: Paldean Tauros 130/130 E:-
  Hand: Fire Energy, Special Red Card, Crispin
P2: prizes 5  deck 42  discard 1  hand 0
  Active: Bronzong (on Bronzor) 110/110 E:-
  Bench0: Buneary 10/70 E:-
  Bench1: Duskull 60/60 E:Telepathic Psychic
  Bench2: Meowth ex 170/170 E:-
  Bench3: Dusknoir (on Duskull<Dusclops) 160/160 E:-
  Bench4: Dusknoir (on Duskull<Dusclops) 160/160 E:-
  Hand: -
```
- reference (search): 1 - attach Fire Energy -> active Mew ex -> play Crispin | Fighting Energy + Grass Energy | Fighting Energy -> own active Mew ex -> ability Memory Helix (active Mew ex) | Passimian: Coordinated Throwing | take a prize
- policy: 0 - attach Fire Energy -> bench1 Passimian -> retreat to bench1 Passimian -> end turn
  - chose `attach Fire Energy -> bench1 Passimian` (predicted 0.31); others: `retreat to bench1 Passimian` 0.30, `attach Fire Energy -> active Mew ex` 0.24, `attach Fire Energy -> bench0 Meowth ex` 0.24, `attach Fire Energy -> bench2 Latias ex` 0.24, `play Crispin | Fighting Energy + Grass Energy | Fighting Energy -> own active Mew ex` 0.22
  - chose `retreat to bench1 Passimian` (predicted 0.31); others: `play Crispin | Fighting Energy + Grass Energy | Fighting Energy -> own bench3 Wellspring Mask Ogerpon ex` 0.14, `play Crispin | Fighting Energy + Grass Energy | Fighting Energy -> own active Mew ex` 0.13, `play Crispin | Fighting Energy + Grass Energy | Fighting Energy -> own bench1 Passimian` 0.11, `play Crispin | Fighting Energy + Psychic Energy | Fighting Energy -> own bench3 Wellspring Mask Ogerpon ex` 0.11, `play Crispin | Fighting Energy + Grass Energy | Fighting Energy -> own bench0 Meowth ex` 0.11
  - chose `end turn` (exact 0.00); others: `play Crispin | Fighting Energy + Grass Energy | Fighting Energy -> own active Passimian` 0.00, `play Crispin | Fighting Energy + Grass Energy | Fighting Energy -> own bench0 Meowth ex` 0.00, `play Crispin | Fighting Energy + Grass Energy | Fighting Energy -> own bench1 Mew ex` 0.00, `play Crispin | Fighting Energy + Grass Energy | Fighting Energy -> own bench2 Latias ex` 0.00, `play Crispin | Fighting Energy + Grass Energy | Fighting Energy -> own bench3 Wellspring Mask Ogerpon ex` 0.00

### Basic Box vs Ethan's Typhlosion (seed 803058) - gap 1

```
Turn 17, P1 to move
P1 (to move): prizes 4  deck 32  discard 12  hand 4
  Active: Teal Mask Ogerpon ex 100/210 E:-
  Bench0: Wellspring Mask Ogerpon ex 210/210 E:G P
  Bench1: Raging Bolt ex 200/240 E:G F W
  Hand: Crispin, Lillie's Clefairy ex, Crispin, Glass Trumpet
P2: prizes 3  deck 13  discard 36  hand 1
  Active: Drakloak (on Dreepy) 90/90 E:F +Brave Bangle
  Bench0: Shaymin 50/80 E:-
  Bench1: Ethan's Cyndaquil 70/70 E:F
  Hand: Boss's Orders
```
- reference (search): 1 - play Crispin | Grass Energy + Lightning Energy | Grass Energy -> own active Teal Mask Ogerpon ex -> bench Lillie's Clefairy ex -> attach Lightning Energy -> bench1 Raging Bolt ex -> retreat to bench1 Raging Bolt ex -> attack Bellowing Thunder | Grass Energy@own active Raging Bolt ex, Grass Energy@own bench0 Wellspring Mask Ogerpon ex, Lightning Energy@own active Raging Bolt ex, Psychic Energy@own bench0 Wellspring Mask Ogerpon ex, Fighting Energy@own active Raging Bolt ex, Water Energy@own active Raging Bolt ex | take a prize
- policy: 0 - play Crispin | Grass Energy + Psychic Energy | Psychic Energy -> own bench1 Raging Bolt ex -> ability Teal Dance (active Teal Mask Ogerpon ex) | Grass Energy -> end turn
  - chose `play Crispin | Grass Energy + Psychic Energy | Psychic Energy -> own bench1 Raging Bolt ex` (predicted 0.40); others: `play Crispin | Grass Energy + Psychic Energy | Psychic Energy -> own active Teal Mask Ogerpon ex` 0.40, `play Crispin | Grass Energy + Psychic Energy | Psychic Energy -> own bench0 Wellspring Mask Ogerpon ex` 0.40, `play Crispin | Grass Energy + Lightning Energy | Lightning Energy -> own active Teal Mask Ogerpon ex` 0.39, `play Crispin | Grass Energy + Lightning Energy | Lightning Energy -> own bench0 Wellspring Mask Ogerpon ex` 0.36, `play Crispin | Grass Energy + Lightning Energy | Lightning Energy -> own bench1 Raging Bolt ex` 0.36
  - chose `ability Teal Dance (active Teal Mask Ogerpon ex) | Grass Energy` (predicted 0.40); others: `attach Grass Energy -> active Teal Mask Ogerpon ex` 0.33, `bench Lillie's Clefairy ex` 0.00, `attach Grass Energy -> bench0 Wellspring Mask Ogerpon ex` 0.00, `attach Grass Energy -> bench1 Raging Bolt ex` 0.00, `end turn` 0.00
  - chose `end turn` (exact 0.00); others: `bench Lillie's Clefairy ex` 0.00, `retreat to bench0 Wellspring Mask Ogerpon ex` 0.00, `retreat to bench1 Raging Bolt ex` 0.00

### Raging Bolt Ogerpon vs Dragapult Toucannon (seed 803099) - gap 1

```
Turn 11, P1 to move
Stadium: Area Zero Underdepths
P1 (to move): prizes 3  deck 28  discard 17  hand 9
  Active: Teal Mask Ogerpon ex 180/210 E:P
  Bench0: Mega Kangaskhan ex 300/300 E:-
  Hand: Grass Energy, Ultra Ball, Grass Energy, Lillie's Clefairy ex, Crispin, Energy Switch, Boss's Orders, Grass Energy, Meowth ex
P2: prizes 4  deck 19  discard 21  hand 8
  Active: Dreepy 70/70 E:F
  Bench0: Budew 10/30 E:-
  Bench1: Dreepy 70/70 E:-
  Bench2: Toucannon (on Pikipek<Trumbeak) 150/150 E:-
  Hand: Fezandipiti ex, Drakloak, Poké Pad, Toucannon, Meowth ex, Buddy-Buddy Poffin, Lillie's Determination, Boss's Orders
```
- reference (search): 0 - end turn
- policy: 0 - play Crispin | Fighting Energy + Grass Energy | Fighting Energy -> own bench0 Mega Kangaskhan ex -> attach Grass Energy -> bench0 Mega Kangaskhan ex -> retreat to bench0 Mega Kangaskhan ex -> play Ultra Ball | Energy Switch + Meowth ex | Wellspring Mask Ogerpon ex -> bench Wellspring Mask Ogerpon ex -> end turn
  - chose `play Crispin | Fighting Energy + Grass Energy | Fighting Energy -> own bench0 Mega Kangaskhan ex` (predicted 0.14); others: `play Crispin | Fighting Energy + Lightning Energy | Fighting Energy -> own bench0 Mega Kangaskhan ex` 0.14, `play Crispin | Fighting Energy + Water Energy | Fighting Energy -> own bench0 Mega Kangaskhan ex` 0.14, `attach Grass Energy -> bench0 Mega Kangaskhan ex` 0.11, `play Crispin | Fighting Energy + Grass Energy | Grass Energy -> own bench0 Mega Kangaskhan ex` 0.10, `play Crispin | Fighting Energy + Lightning Energy | Lightning Energy -> own bench0 Mega Kangaskhan ex` 0.10
  - chose `attach Grass Energy -> bench0 Mega Kangaskhan ex` (predicted 0.29); others: `play Ultra Ball | Energy Switch + Meowth ex | Teal Mask Ogerpon ex` 0.27, `play Ultra Ball | Energy Switch + Meowth ex | Lillie's Clefairy ex` 0.27, `play Ultra Ball | Energy Switch + Meowth ex | Mega Kangaskhan ex` 0.27, `ability Teal Dance (active Teal Mask Ogerpon ex) | Grass Energy` 0.27, `retreat to bench0 Mega Kangaskhan ex` 0.23
  - chose `retreat to bench0 Mega Kangaskhan ex` (predicted 0.29); others: `ability Teal Dance (active Teal Mask Ogerpon ex) | Grass Energy` 0.22, `bench Meowth ex | yes | Crispin` 0.12, `bench Meowth ex | yes | Judge` 0.12, `bench Meowth ex | yes | Boss's Orders` 0.12, `bench Meowth ex | yes | Brock's Scouting` 0.12
  - chose `play Ultra Ball | Energy Switch + Meowth ex | Wellspring Mask Ogerpon ex` (predicted 0.34); others: `play Ultra Ball | Energy Switch + Lillie's Clefairy ex | Wellspring Mask Ogerpon ex` 0.34, `play Ultra Ball | Energy Switch + Meowth ex | Raging Bolt ex` 0.32, `play Ultra Ball | Energy Switch + Meowth ex | Teal Mask Ogerpon ex` 0.32, `play Ultra Ball | Energy Switch + Meowth ex | Lillie's Clefairy ex` 0.32, `play Ultra Ball | Energy Switch + Meowth ex | Mega Kangaskhan ex` 0.32
  - chose `bench Wellspring Mask Ogerpon ex` (predicted 0.34); others: `ability Teal Dance (bench0 Teal Mask Ogerpon ex) | Grass Energy` 0.32, `ability Run Errand (active Mega Kangaskhan ex)` 0.30, `bench Lillie's Clefairy ex` 0.29, `end turn` 0.00
  - chose `end turn` (exact 0.00); others: `bench Lillie's Clefairy ex` 0.00, `ability Run Errand (active Mega Kangaskhan ex)` 0.00, `ability Teal Dance (bench0 Teal Mask Ogerpon ex) | Grass Energy` 0.00
