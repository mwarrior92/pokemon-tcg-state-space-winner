# Review packet: offense

100 evaluated turns. Read the worst decisions below, decide what the policy is getting wrong and why, and write the reasoning and the changes to make in sim/reviews/ (see sim/REVIEW.md).

- search (teacher): 0.47 prizes/turn; policy: 0.47; policy matched the search on 91/100

## Feature sets (validation MSE; predicting the mean gives 0.218)

| set | features | cost | MSE |
|---|---|---|---|
| all features | 1193 | probe | 0.204 |
| cheap groups only (no engine probes) | 843 | cheap | 0.215 |
| all but probe-damage | 857 | probe | 0.212 |
| all but probe-ability | 1181 | probe | 0.207 |
| all but probe-hand | 1191 | probe | 0.204 |
| cheap + probe-damage | 1179 | probe | 0.207 |
| top 200 features by importance | 200 | probe | 0.187 |
| top 100 features by importance | 100 | probe | 0.186 |
| top 50 features by importance | 50 | probe | 0.187 |
| top 25 features by importance **(chosen)** | 25 | probe | 0.187 |

## Largest weights (full model)

- +0.026 `me.s0.a0.nowToActive`
- -0.021 `me.s0.a0.gap`
- +0.021 `me.s0.energy`
- -0.020 `me.s0.retreatGap`
- +0.018 `op.s0.damage`
- +0.015 `me.handItem`
- +0.015 `me.s1.weakP`
- +0.014 `me.handEnergyF`
- +0.014 `me.s0.a0.koTo0`
- +0.014 `me.s1.stage`
- +0.013 `me.s0.energyW`
- +0.012 `me.s0.energyF`
- +0.012 `op.s0.koThreat`
- +0.012 `me.hand`
- +0.011 `me.s0.abilityDamage`
- +0.010 `me.s0.energyG`
- -0.010 `retreated`
- +0.010 `op.s5.energyL`
- +0.009 `me.s0.weakP`
- -0.009 `op.s0.hpLeft`
- +0.009 `me.handEnergy`
- +0.009 `me.s0.stage`
- +0.009 `me.s0.a1.nowToActive`
- +0.008 `me.s0.energyR`
- +0.008 `me.s0.a1.koTo0`
- -0.008 `me.prizes`
- +0.008 `me.handEnergyL`
- +0.008 `me.s2.stage`
- +0.008 `me.s0.a1.dmgTo1`
- +0.008 `me.s0.damage`
- +0.007 `me.s5.a1.koTo1`
- +0.007 `me.s1.typeF`
- +0.007 `me.handStadium`
- +0.007 `op.s5.typeW`
- +0.007 `me.s0.energyL`
- -0.007 `me.s0.a1.gap`
- +0.006 `op.s0.typeD`
- -0.006 `op.s1.typeF`
- +0.006 `me.s0.typeF`
- +0.006 `op.s0.a1.dmgTo3`

## Worst decisions

### Crustle vs Mew Box (seed 601093) - gap 3

```
Turn 19, P2 to move
P1: prizes 1  deck 38  discard 5  hand 9
  Active: Mega Kangaskhan ex 300/300 E:-
  Bench0: Mega Kangaskhan ex 260/300 E:Mist P
  Bench1: Mega Kangaskhan ex 300/300 E:-
  Bench2: Mega Kangaskhan ex 300/300 E:- +Hero's Cape
  Hand: Mist Energy, Lillie's Determination, Growing [G] Energy, Eri, Jumbo Ice Cream, Buddy-Buddy Poffin, Lumiose City, Boss's Orders, Grass Energy
P2 (to move): prizes 3  deck 31  discard 10  hand 3
  Active: Mew ex 160/160 E:-
  Bench0: Mega Kangaskhan ex 20/300 E:2P F
  Bench1: Unown 80/80 E:Telepathic Psychic
  Bench2: Jirachi ex 90/160 E:-
  Bench3: Iron Crown ex 150/220 E:F Telepathic Psychic P
  Bench4: Meowth ex 10/170 E:-
  Hand: Wondrous Patch, Boss's Orders, Crispin
```
- reference (search): 3 - play Wondrous Patch | Psychic Energy -> own bench1 Unown -> play Boss's Orders | opp bench1 Mega Kangaskhan ex -> retreat to bench0 Mega Kangaskhan ex -> attack Rapid-Fire Combo
- policy: 0 - retreat to bench0 Mega Kangaskhan ex -> ability Run Errand (active Mega Kangaskhan ex) -> play Boss's Orders | opp bench1 Mega Kangaskhan ex -> play Wondrous Patch | Psychic Energy -> own bench1 Unown -> play Area Zero Underdepths -> attack Rapid-Fire Combo
  - chose `retreat to bench0 Mega Kangaskhan ex` (predicted 0.58); others: `retreat to bench3 Iron Crown ex` 0.29, `play Boss's Orders | opp bench0 Mega Kangaskhan ex` 0.18, `play Crispin | Water Energy` 0.15, `play Wondrous Patch | Psychic Energy -> own bench1 Unown` 0.14, `play Wondrous Patch | Psychic Energy -> own bench3 Iron Crown ex` 0.14
  - chose `ability Run Errand (active Mega Kangaskhan ex)` (predicted 0.61); others: `play Boss's Orders | opp bench2 Mega Kangaskhan ex` 0.57, `play Wondrous Patch | Psychic Energy -> own bench3 Iron Crown ex` 0.55, `play Boss's Orders | opp bench0 Mega Kangaskhan ex` 0.55, `play Wondrous Patch | Psychic Energy -> own bench0 Mew ex` 0.50, `play Crispin | Water Energy` 0.48
  - chose `play Boss's Orders | opp bench1 Mega Kangaskhan ex` (predicted 0.59); others: `play Area Zero Underdepths` 0.59, `play Ciphermaniac's Codebreaking | Mega Kangaskhan ex + Mega Kangaskhan ex | keep order` 0.59, `play Boss's Orders | opp bench0 Mega Kangaskhan ex` 0.56, `play Boss's Orders | opp bench2 Mega Kangaskhan ex` 0.53, `play Crispin | Water Energy` 0.49
  - chose `play Wondrous Patch | Psychic Energy -> own bench1 Unown` (predicted 0.56); others: `play Area Zero Underdepths` 0.52, `play Wondrous Patch | Psychic Energy -> own bench0 Mew ex` 0.44, `play Wondrous Patch | Psychic Energy -> own bench3 Iron Crown ex` 0.44, `attack Rapid-Fire Combo` 0.00, `end turn` 0.00
  - chose `play Area Zero Underdepths` (predicted 0.44); others: `attack Rapid-Fire Combo` 0.00, `end turn` 0.00
  - chose `attack Rapid-Fire Combo` (exact 0.00); others: `end turn` 0.00

### Ceruledge vs Rocket's Mewtwo (seed 601079) - gap 2

```
Turn 11, P2 to move
Stadium: Team Rocket's Factory
P1: prizes 1  deck 36  discard 9  hand 0
  Active: Ceruledge ex (on Charcadet) 270/270 E:F
  Bench0: Charcadet 70/70 E:2F
  Bench1: Charcadet 50/70 E:-
  Bench2: Ceruledge ex (on Charcadet) 10/270 E:2F
  Bench3: Solrock 90/110 E:Mist
  Bench4: Solrock 110/110 E:-
  Hand: -
P2 (to move): prizes 6  deck 14  discard 20  hand 3
  Active: Team Rocket's Mewtwo ex 80/280 E:-
  Bench0: Team Rocket's Spidops (on Team Rocket's Tarountula) 130/130 E:P 2G
  Bench1: Team Rocket's Mewtwo ex 50/280 E:G 3Team Rocket's +Lucky Helmet
  Bench2: Team Rocket's Mimikyu 50/60 E:-
  Bench3: Lillie's Clefairy ex 190/190 E:G
  Bench4: Team Rocket's Articuno 50/120 E:-
  Hand: Team Rocket's Ariana, Energy Search, Team Rocket's Transceiver
```
- reference (search): 2 - play Team Rocket's Transceiver | Team Rocket's Giovanni -> play Team Rocket's Giovanni | own bench0 Team Rocket's Spidops | opp bench2 Ceruledge ex -> attack Rocket Rush | take 2 prizes
- policy: 0 - ability Charge Up (bench0 Team Rocket's Spidops) | Grass Energy -> play Team Rocket's Ariana -> use stadium Team Rocket's Factory -> play Energy Switch | Grass Energy own bench0 Team Rocket's Spidops -> own active Team Rocket's Mewtwo ex -> play Night Stretcher | Grass Energy -> attach Grass Energy -> active Team Rocket's Mewtwo ex -> play Team Rocket's Transceiver | Team Rocket's Proton -> play Team Rocket's Transceiver | Team Rocket's Giovanni -> play Energy Search | nothing -> end turn
  - chose `ability Charge Up (bench0 Team Rocket's Spidops) | Grass Energy` (predicted 0.11); others: `play Team Rocket's Ariana` 0.10, `play Team Rocket's Transceiver | Team Rocket's Giovanni` 0.02, `play Team Rocket's Transceiver | Team Rocket's Proton` 0.02, `play Team Rocket's Transceiver | Team Rocket's Ariana` 0.02, `play Energy Search | nothing` 0.01
  - chose `play Team Rocket's Ariana` (predicted 0.17); others: `play Team Rocket's Transceiver | Team Rocket's Giovanni` 0.09, `play Team Rocket's Transceiver | Team Rocket's Proton` 0.09, `play Team Rocket's Transceiver | Team Rocket's Ariana` 0.09, `play Energy Search | nothing` 0.08, `play Team Rocket's Transceiver | nothing` 0.08
  - chose `use stadium Team Rocket's Factory` (predicted 0.21); others: `play Night Stretcher | Grass Energy` 0.16, `play Team Rocket's Transceiver | Team Rocket's Giovanni` 0.15, `play Team Rocket's Transceiver | Team Rocket's Proton` 0.15, `play Team Rocket's Transceiver | Team Rocket's Ariana` 0.15, `play Night Stretcher | Team Rocket's Spidops` 0.15
  - chose `play Energy Switch | Grass Energy own bench0 Team Rocket's Spidops -> own active Team Rocket's Mewtwo ex` (predicted 0.20); others: `play Night Stretcher | Grass Energy` 0.19, `play Team Rocket's Transceiver | Team Rocket's Proton` 0.18, `play Team Rocket's Transceiver | Team Rocket's Giovanni` 0.18, `play Night Stretcher | Team Rocket's Spidops` 0.18, `play Night Stretcher | Team Rocket's Articuno` 0.18
  - chose `play Night Stretcher | Grass Energy` (predicted 0.19); others: `play Team Rocket's Transceiver | Team Rocket's Proton` 0.17, `play Team Rocket's Transceiver | Team Rocket's Giovanni` 0.17, `play Night Stretcher | Team Rocket's Spidops` 0.17, `play Night Stretcher | Team Rocket's Articuno` 0.17, `play Night Stretcher | Team Rocket's Mimikyu` 0.17
  - chose `attach Grass Energy -> active Team Rocket's Mewtwo ex` (predicted 0.26); others: `attach Grass Energy -> bench0 Team Rocket's Spidops` 0.23, `attach Grass Energy -> bench1 Team Rocket's Mewtwo ex` 0.23, `attach Grass Energy -> bench2 Team Rocket's Mimikyu` 0.23, `attach Grass Energy -> bench3 Lillie's Clefairy ex` 0.23, `attach Grass Energy -> bench4 Team Rocket's Articuno` 0.23
  - chose `play Team Rocket's Transceiver | Team Rocket's Proton` (predicted 0.24); others: `play Team Rocket's Transceiver | Team Rocket's Giovanni` 0.24, `play Energy Search | nothing` 0.23, `play Team Rocket's Transceiver | nothing` 0.23, `end turn` 0.00
  - chose `play Team Rocket's Transceiver | Team Rocket's Giovanni` (predicted 0.22); others: `play Energy Search | nothing` 0.21, `play Team Rocket's Transceiver | nothing` 0.21, `end turn` 0.00
  - chose `play Energy Search | nothing` (predicted 0.19); others: `end turn` 0.00
  - chose `end turn` (exact 0.00); others: 

### Mega Starmie vs Ceruledge (seed 601012) - gap 1

```
Turn 13, P1 to move
P1 (to move): prizes 1  deck 22  discard 29  hand 4
  Active: Staryu 20/70 E:-
  Bench0: Mega Froslass ex (on Snorunt) 310/310 E:-
  Bench1: Snorunt 50/70 E:-
  Hand: Wally's Compassion, Water Energy, Wally's Compassion, Night Stretcher
P2: prizes 1  deck 33  discard 15  hand 6
  Active: Armarouge (on Charcadet) 140/140 E:-
  Bench0: Solrock 60/110 E:-
  Bench1: Drilbur 60/70 E:-
  Bench2: Lunatone 80/110 E:-
  Hand: Fighting Energy, Fighting Energy, Mist Energy, Fighting Gong, Pokémon Catcher, Fighting Energy
```
- reference (search): 1 - attach Water Energy -> active Staryu -> play Night Stretcher | Mega Starmie ex -> evolve active Staryu -> Mega Starmie ex -> attack Jetting Blow | opp bench0 Solrock
- policy: 0 - attach Water Energy -> active Staryu -> play Night Stretcher | Patrat -> bench Patrat -> retreat to bench0 Mega Froslass ex -> end turn
  - chose `attach Water Energy -> active Staryu` (predicted 0.36); others: `attach Water Energy -> bench0 Mega Froslass ex` 0.18, `attach Water Energy -> bench1 Snorunt` 0.18, `play Night Stretcher | Patrat` 0.18, `play Night Stretcher | Meowth ex` 0.18, `play Night Stretcher | Mega Froslass ex` 0.18
  - chose `play Night Stretcher | Patrat` (predicted 0.33); others: `play Night Stretcher | Meowth ex` 0.33, `play Night Stretcher | Mega Froslass ex` 0.33, `play Night Stretcher | Dreepy` 0.33, `play Night Stretcher | Drakloak` 0.33, `play Night Stretcher | Mega Starmie ex` 0.33
  - chose `bench Patrat` (predicted 0.33); others: `retreat to bench0 Mega Froslass ex` 0.21, `retreat to bench1 Snorunt` 0.13, `attack Water Gun` 0.00, `end turn` 0.00
  - chose `retreat to bench0 Mega Froslass ex` (predicted 0.20); others: `retreat to bench1 Snorunt` 0.13, `retreat to bench2 Patrat` 0.13, `attack Water Gun` 0.00, `end turn` 0.00
  - chose `end turn` (exact 0.00); others: 

### Seaking Festival Lead vs Mew Box (seed 601023) - gap 1

```
Turn 8, P2 to move
Stadium: Area Zero Underdepths
P1: prizes 1  deck 34  discard 11  hand 8
  Active: Moltres 120/120 E:2Mist +Air Balloon
  Bench0: Seaking (on Goldeen) 110/110 E:-
  Hand: Brave Bangle, Night Stretcher, Air Balloon, Night Stretcher, Air Balloon, Buddy-Buddy Poffin, Gladion's Final Battle, Boss's Orders
P2 (to move): prizes 2  deck 34  discard 7  hand 4
  Active: Jirachi ex 30/160 E:-
  Bench0: Latias ex 120/210 E:P
  Bench1: Fezandipiti ex 20/210 E:W Telepathic Psychic
  Bench2: Meowth ex 170/170 E:Telepathic Psychic 2P
  Bench3: Chien-Pao 60/120 E:-
  Bench4: Mew ex 150/160 E:-
  Hand: Meowth ex, Wondrous Patch, Ciphermaniac's Codebreaking, Crispin
```
- reference (search): 1 - play Wondrous Patch | Psychic Energy -> own bench0 Latias ex -> play Crispin | Water Energy -> attach Water Energy -> bench0 Latias ex -> retreat to bench0 Latias ex -> attack Eon Blade | take a prize
- policy: 0 - retreat to bench2 Meowth ex -> play Crispin | Water Energy -> attach Water Energy -> active Meowth ex -> play Wondrous Patch | Psychic Energy -> own bench0 Latias ex -> attack Tuck Tail | own bench0 Latias ex
  - chose `retreat to bench2 Meowth ex` (predicted 0.32); others: `retreat to bench1 Fezandipiti ex` 0.27, `play Crispin | Water Energy` 0.22, `play Ciphermaniac's Codebreaking | Mega Kangaskhan ex + Mega Kangaskhan ex | keep order` 0.20, `play Crispin | nothing` 0.20, `retreat to bench0 Latias ex` 0.18
  - chose `play Crispin | Water Energy` (predicted 0.34); others: `play Ciphermaniac's Codebreaking | Mega Kangaskhan ex + Mega Kangaskhan ex | keep order` 0.32, `play Crispin | nothing` 0.32, `play Wondrous Patch | Psychic Energy -> own bench0 Latias ex` 0.30, `play Wondrous Patch | Psychic Energy -> own bench4 Mew ex` 0.30, `attack Tuck Tail | own bench0 Latias ex` 0.00
  - chose `attach Water Energy -> active Meowth ex` (predicted 0.40); others: `attach Water Energy -> bench0 Latias ex` 0.32, `attach Water Energy -> bench1 Fezandipiti ex` 0.32, `attach Water Energy -> bench2 Jirachi ex` 0.32, `attach Water Energy -> bench3 Chien-Pao` 0.32, `attach Water Energy -> bench4 Mew ex` 0.32
  - chose `play Wondrous Patch | Psychic Energy -> own bench0 Latias ex` (predicted 0.37); others: `play Wondrous Patch | Psychic Energy -> own bench4 Mew ex` 0.37, `attack Tuck Tail | own bench0 Latias ex` 0.00, `attack Tuck Tail | own bench1 Fezandipiti ex` 0.00, `attack Tuck Tail | own bench2 Jirachi ex` 0.00, `attack Tuck Tail | own bench3 Chien-Pao` 0.00
  - chose `attack Tuck Tail | own bench0 Latias ex` (exact 0.00); others: `attack Tuck Tail | own bench1 Fezandipiti ex` 0.00, `attack Tuck Tail | own bench2 Jirachi ex` 0.00, `attack Tuck Tail | own bench3 Chien-Pao` 0.00, `attack Tuck Tail | own bench4 Mew ex` 0.00, `end turn` 0.00

### Festival Lead vs Basic Box (seed 601036) - gap 1

```
Turn 5, P2 to move
Stadium: Area Zero Underdepths
P1: prizes 1  deck 42  discard 7  hand 3
  Active: Thwackey (on Grookey) 100/100 E:-
  Bench0: Grookey 70/70 E:G Growing [G] +Air Balloon
  Bench1: Goldeen 50/50 E:-
  Hand: Festival Grounds, Dipplin, Buddy-Buddy Poffin
P2 (to move): prizes 3  deck 38  discard 9  hand 4
  Active: Meowth ex 120/170 E:3G L
  Hand: Psychic Energy, Mega Kangaskhan ex, Cyrano, Crispin
```
- reference (search): 1 - play Cyrano | Fezandipiti ex + Meowth ex + Iron Leaves ex -> bench Iron Leaves ex | yes | Grass Energy own bench0 Meowth ex -> own active Iron Leaves ex, Grass Energy own bench0 Meowth ex -> own active Iron Leaves ex, Lightning Energy own bench0 Meowth ex -> own active Iron Leaves ex, Grass Energy own bench0 Meowth ex -> own active Iron Leaves ex -> attack Prism Edge | take a prize
- policy: 0 - play Crispin | Grass Energy + Lightning Energy | Grass Energy -> own active Meowth ex -> bench Mega Kangaskhan ex -> play Cyrano | Fezandipiti ex + Meowth ex + Mega Kangaskhan ex -> attach Psychic Energy -> active Meowth ex -> bench Meowth ex | yes | Crispin -> bench Fezandipiti ex -> bench Mega Kangaskhan ex -> retreat to bench2 Fezandipiti ex | Grass Energy -> end turn
  - chose `play Crispin | Grass Energy + Lightning Energy | Grass Energy -> own active Meowth ex` (predicted 0.44); others: `play Crispin | Grass Energy + Psychic Energy | Grass Energy -> own active Meowth ex` 0.44, `play Crispin | Grass Energy + Lightning Energy | Lightning Energy -> own active Meowth ex` 0.42, `play Crispin | Grass Energy + Psychic Energy | Psychic Energy -> own active Meowth ex` 0.42, `play Crispin | Lightning Energy + Psychic Energy | Lightning Energy -> own active Meowth ex` 0.42, `play Crispin | Lightning Energy + Psychic Energy | Psychic Energy -> own active Meowth ex` 0.42
  - chose `bench Mega Kangaskhan ex` (predicted 0.46); others: `play Cyrano | Fezandipiti ex + Meowth ex + Mega Kangaskhan ex` 0.45, `play Cyrano | Fezandipiti ex + Meowth ex + Iron Leaves ex` 0.45, `play Cyrano | Fezandipiti ex + Meowth ex + Lillie's Clefairy ex` 0.45, `play Cyrano | Fezandipiti ex + Meowth ex + Latias ex` 0.45, `play Cyrano | Fezandipiti ex + Meowth ex + Teal Mask Ogerpon ex` 0.45
  - chose `play Cyrano | Fezandipiti ex + Meowth ex + Mega Kangaskhan ex` (predicted 0.47); others: `play Cyrano | Fezandipiti ex + Meowth ex + Iron Leaves ex` 0.47, `play Cyrano | Fezandipiti ex + Meowth ex + Lillie's Clefairy ex` 0.47, `play Cyrano | Fezandipiti ex + Meowth ex + Latias ex` 0.47, `play Cyrano | Fezandipiti ex + Meowth ex + Teal Mask Ogerpon ex` 0.47, `play Cyrano | Fezandipiti ex + Meowth ex + Wellspring Mask Ogerpon ex` 0.47
  - chose `attach Psychic Energy -> active Meowth ex` (predicted 0.48); others: `attach Lightning Energy -> active Meowth ex` 0.48, `bench Meowth ex | yes | Crispin` 0.47, `bench Meowth ex | yes | Cyrano` 0.47, `bench Meowth ex | yes | Boss's Orders` 0.47, `bench Fezandipiti ex` 0.47
  - chose `bench Meowth ex | yes | Crispin` (predicted 0.48); others: `bench Meowth ex | yes | Cyrano` 0.48, `bench Meowth ex | yes | Boss's Orders` 0.48, `bench Fezandipiti ex` 0.47, `bench Meowth ex | yes | nothing` 0.47, `bench Meowth ex | no` 0.47
  - chose `bench Fezandipiti ex` (predicted 0.47); others: `bench Mega Kangaskhan ex` 0.47, `retreat to bench1 Meowth ex | Grass Energy` 0.09, `retreat to bench1 Meowth ex | Lightning Energy` 0.09, `retreat to bench1 Meowth ex | Psychic Energy` 0.09, `retreat to bench0 Mega Kangaskhan ex | Grass Energy` 0.07
  - chose `bench Mega Kangaskhan ex` (predicted 0.46); others: `retreat to bench2 Fezandipiti ex | Grass Energy` 0.12, `retreat to bench2 Fezandipiti ex | Lightning Energy` 0.12, `retreat to bench2 Fezandipiti ex | Psychic Energy` 0.12, `retreat to bench1 Meowth ex | Grass Energy` 0.08, `retreat to bench1 Meowth ex | Lightning Energy` 0.08
  - chose `retreat to bench2 Fezandipiti ex | Grass Energy` (predicted 0.11); others: `retreat to bench2 Fezandipiti ex | Lightning Energy` 0.11, `retreat to bench2 Fezandipiti ex | Psychic Energy` 0.11, `retreat to bench1 Meowth ex | Grass Energy` 0.07, `retreat to bench1 Meowth ex | Lightning Energy` 0.07, `retreat to bench1 Meowth ex | Psychic Energy` 0.07
  - chose `end turn` (exact 0.00); others: 

### Lucario Hariyama vs Lucario Hariyama (seed 601049) - gap 1

```
Turn 8, P2 to move
P1: prizes 5  deck 34  discard 9  hand 8
  Active: Riolu 80/80 E:3F
  Hand: Riolu, Solrock, Fighting Energy, Lillie's Determination, Fighting Gong, Fighting Energy, Makuhita, Poké Pad
P2 (to move): prizes 4  deck 28  discard 10  hand 3
  Active: Riolu 80/80 E:-
  Bench0: Mega Lucario ex (on Riolu) 60/340 E:2F +Air Balloon
  Bench1: Mega Lucario ex (on Riolu) 130/340 E:3F
  Bench2: Shaymin 30/80 E:- +Air Balloon
  Bench3: Hariyama (on Makuhita) 150/150 E:-
  Hand: Lillie's Determination, Premium Power Pro, Gravity Mountain
```
- reference (search): 1 - play Premium Power Pro -> play Lillie's Determination -> bench Meowth ex | yes | Lillie's Determination -> play Switch | own bench0 Mega Lucario ex -> attack Aura Jab | Fighting Energy -> own bench4 Meowth ex, Fighting Energy -> own bench1 Mega Lucario ex
- policy: 0 - play Lillie's Determination -> attach Fighting Energy -> active Riolu -> bench Lunatone -> play Gravity Mountain -> attack Accelerating Stab
  - chose `play Lillie's Determination` (predicted 0.48); others: `play Gravity Mountain` 0.30, `play Premium Power Pro` 0.28, `end turn` 0.00
  - chose `attach Fighting Energy -> active Riolu` (predicted 0.53); others: `bench Lunatone` 0.48, `play Gravity Mountain` 0.48, `attach Fighting Energy -> bench0 Mega Lucario ex` 0.40, `attach Fighting Energy -> bench1 Mega Lucario ex` 0.40, `attach Fighting Energy -> bench2 Shaymin` 0.40
  - chose `bench Lunatone` (predicted 0.53); others: `play Gravity Mountain` 0.53, `attack Accelerating Stab` 0.00, `end turn` 0.00
  - chose `play Gravity Mountain` (predicted 0.52); others: `attack Accelerating Stab` 0.00, `end turn` 0.00
  - chose `attack Accelerating Stab` (exact 0.00); others: `end turn` 0.00

### Ceruledge vs Dhelmise (seed 601063) - gap 1

```
Turn 10, P2 to move
P1: prizes 2  deck 39  discard 12  hand 3
  Active: Armarouge (on Charcadet) 60/140 E:-
  Bench0: Solrock 110/110 E:-
  Bench1: Lunatone 110/110 E:-
  Hand: Boss's Orders, Fire Energy, Fighting Energy
P2 (to move): prizes 1  deck 28  discard 22  hand 4
  Active: Dhelmise 120/140 E:-
  Bench0: Banette (on Shuppet) 70/80 E:-
  Bench1: Sinistcha (on Poltchageist) 20/60 E:-
  Hand: Latias ex, Boss's Orders, Shuppet, Explorer's Guidance
```
- reference (search): 1 - play Explorer's Guidance | Lillie's Determination + Telepathic Psychic Energy -> attach Telepathic Psychic Energy -> active Dhelmise | Lillie's Clefairy ex + Shuppet -> attack Vengeful Anchor
- policy: 0 - play Explorer's Guidance | Lillie's Determination + Poké Pad -> bench Shuppet -> play Poké Pad | Sinistcha -> bench Latias ex -> retreat to bench0 Banette -> end turn
  - chose `play Explorer's Guidance | Lillie's Determination + Poké Pad` (predicted 0.22); others: `play Explorer's Guidance | Lillie's Determination + Ultra Ball` 0.22, `play Explorer's Guidance | Poké Pad + Lillie's Clefairy ex` 0.22, `play Explorer's Guidance | Lillie's Determination + Telepathic Psychic Energy` 0.21, `play Explorer's Guidance | Lillie's Determination + Lillie's Clefairy ex` 0.19, `play Explorer's Guidance | Lillie's Determination + Boss's Orders` 0.19
  - chose `bench Shuppet` (predicted 0.21); others: `play Poké Pad | Sinistcha` 0.19, `play Poké Pad | Shuppet` 0.19, `play Poké Pad | Dhelmise` 0.19, `play Poké Pad | Spiritomb` 0.19, `bench Latias ex` 0.19
  - chose `play Poké Pad | Sinistcha` (predicted 0.19); others: `play Poké Pad | Shuppet` 0.19, `play Poké Pad | Dhelmise` 0.19, `play Poké Pad | Spiritomb` 0.19, `bench Latias ex` 0.18, `play Poké Pad | nothing` 0.18
  - chose `bench Latias ex` (predicted 0.16); others: `end turn` 0.00
  - chose `retreat to bench0 Banette` (predicted 0.21); others: `retreat to bench1 Sinistcha` 0.17, `retreat to bench2 Shuppet` 0.15, `retreat to bench3 Latias ex` 0.11, `end turn` 0.00
  - chose `end turn` (exact 0.00); others: 

### Alakazam Dusknoir vs Dragapult Blaziken (seed 601085) - gap 1

```
Turn 3, P1 to move
Stadium: Team Rocket's Watchtower
P1 (to move): prizes 6  deck 35  discard 3  hand 6
  Active: Alakazam (on Abra<Kadabra) 140/140 E:-
  Bench0: Dusclops (on Duskull) 90/90 E:Telepathic Psychic
  Bench1: Kadabra (on Abra) 80/80 E:-
  Bench2: Abra 30/50 E:-
  Bench3: Duskull 50/60 E:-
  Hand: Kadabra, Abra, Rare Candy, Hilda, Strange Timepiece, Night Stretcher
P2: prizes 5  deck 43  discard 4  hand 0
  Active: Fezandipiti ex 100/210 E:F P
  Bench0: Budew 10/30 E:-
  Bench1: Dreepy 70/70 E:-
  Bench2: Dreepy 70/70 E:-
  Bench3: Munkidori 30/110 E:-
  Hand: -
```
- reference (search): 2 - evolve bench2 Abra -> Kadabra | yes -> attach Psychic Energy -> active Alakazam -> attack Hand Power | take 2 prizes
- policy: 1 - ability Cursed Blast (bench0 Dusclops) | opp bench0 Budew | take a prize -> end turn
  - chose `ability Cursed Blast (bench0 Dusclops) | opp bench0 Budew | take a prize` (predicted 1.00); others: `ability Cursed Blast (bench0 Dusclops) | opp bench3 Munkidori | take a prize` 1.00, `ability Cursed Blast (bench0 Dusclops) | opp active Fezandipiti ex` 0.39, `evolve bench2 Abra -> Kadabra | yes` 0.39, `play Hilda | Dusclops + Psychic Energy` 0.39, `play Hilda | Dusclops + Telepathic Psychic Energy` 0.39
  - chose `end turn` (exact 1.00); others: `evolve bench2 Abra -> Kadabra | yes` 1.00, `evolve bench2 Abra -> Kadabra | no` 1.00, `bench Abra` 1.00, `play Hilda | Dusclops + Psychic Energy` 1.00, `play Hilda | Dusclops + Telepathic Psychic Energy` 1.00

### Dhelmise vs Sharpedo Toxtricity (seed 601088) - gap 1

```
Turn 4, P2 to move
Stadium: Prism Tower
P1: prizes 3  deck 44  discard 5  hand 0
  Active: Dhelmise 20/140 E:Legacy Telepathic Psychic
  Bench0: Shuppet 10/50 E:P Telepathic Psychic
  Bench1: Poltchageist 20/30 E:-
  Hand: -
P2 (to move): prizes 4  deck 45  discard 3  hand 5
  Active: Mega Sharpedo ex (on Carvanha) 330/330 E:D
  Hand: Judge, Poké Pad, Boss's Orders, Toxtricity, Judge
```
- reference (search): 1 - play Poké Pad | Yveltal -> play Boss's Orders | opp bench0 Shuppet -> attack Greedy Fang | take a prize
- policy: 0 - play Judge -> attach Darkness Energy -> active Mega Sharpedo ex -> use stadium Prism Tower | Boss's Orders + Darkness Energy -> play Poké Pad | Yveltal -> bench Yveltal -> retreat to bench0 Yveltal -> end turn
  - chose `play Judge` (predicted 0.43); others: `use stadium Prism Tower | Judge + Judge` 0.42, `use stadium Prism Tower | Judge + Boss's Orders` 0.42, `use stadium Prism Tower | Judge + Toxtricity` 0.42, `use stadium Prism Tower | Judge + Poké Pad` 0.40, `use stadium Prism Tower | Poké Pad + Boss's Orders` 0.40
  - chose `attach Darkness Energy -> active Mega Sharpedo ex` (predicted 0.45); others: `use stadium Prism Tower | Boss's Orders + Darkness Energy` 0.43, `use stadium Prism Tower | Boss's Orders + Poké Pad` 0.42, `use stadium Prism Tower | Darkness Energy + Darkness Energy` 0.41, `play Poké Pad | Yveltal` 0.41, `play Poké Pad | Toxel` 0.41
  - chose `use stadium Prism Tower | Boss's Orders + Darkness Energy` (predicted 0.44); others: `use stadium Prism Tower | Boss's Orders + Poké Pad` 0.43, `play Poké Pad | Yveltal` 0.42, `play Poké Pad | Toxel` 0.42, `play Poké Pad | Tatsugiri` 0.42, `play Poké Pad | Munkidori` 0.42
  - chose `play Poké Pad | Yveltal` (predicted 0.42); others: `play Poké Pad | Toxel` 0.42, `play Poké Pad | Tatsugiri` 0.42, `play Poké Pad | Munkidori` 0.42, `play Poké Pad | Toxtricity` 0.42, `play Poké Pad | nothing` 0.41
  - chose `bench Yveltal` (predicted 0.41); others: `attack Greedy Fang` 0.00, `attack Hungry Jaws` 0.00, `end turn` 0.00
  - chose `retreat to bench0 Yveltal` (predicted 0.29); others: `attack Greedy Fang` 0.00, `attack Hungry Jaws` 0.00, `end turn` 0.00
  - chose `end turn` (exact 0.00); others: 
