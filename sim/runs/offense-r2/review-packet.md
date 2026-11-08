# Review packet: offense

100 evaluated turns. Read the worst decisions below, decide what the policy is getting wrong and why, and write the reasoning and the changes to make in sim/reviews/ (see sim/REVIEW.md).

- search (teacher): 0.57 prizes/turn; policy: 0.60; policy matched the search on 93/100

## Feature sets (validation MSE; predicting the mean gives 0.235)

| set | features | cost | MSE |
|---|---|---|---|
| all features | 1236 | probe | 0.185 |
| cheap groups only (no engine probes) | 886 | cheap | 0.185 |
| all but probe-damage | 900 | probe | 0.182 |
| all but probe-ability | 1224 | probe | 0.190 |
| all but probe-hand | 1234 | probe | 0.185 |
| cheap + probe-damage | 1222 | probe | 0.190 |
| top 200 features by importance | 200 | probe | 0.181 |
| top 100 features by importance | 100 | probe | 0.177 |
| top 50 features by importance | 50 | probe | 0.176 |
| top 25 features by importance **(chosen)** | 25 | probe | 0.162 |
| top 200 cheap features by importance | 200 | cheap | 0.183 |
| top 100 cheap features by importance | 100 | cheap | 0.182 |
| top 50 cheap features by importance | 50 | cheap | 0.181 |
| reach + board + resources only | 239 | cheap | 0.182 |

## Largest weights (full model)

- +0.035 `me.reach.maxPrize`
- +0.031 `me.reach.ko0`
- +0.026 `me.s0.a0.nowToActive`
- +0.025 `me.s2.abilityDamage`
- +0.025 `me.reach.count`
- +0.022 `me.s0.abilityDamage`
- +0.019 `me.s1.abilityDamage`
- -0.016 `me.s0.a0.gap`
- +0.016 `op.s1.energyM`
- +0.016 `me.s0.energy`
- +0.015 `me.s3.abilityDamage`
- +0.014 `me.s1.energyW`
- +0.013 `me.s0.a0.koTo0`
- +0.012 `op.s5.a1.koTo4`
- +0.011 `me.s4.energyW`
- +0.011 `me.counterAbilities`
- +0.011 `me.s0.a1.nowToActive`
- +0.010 `op.s0.damage`
- +0.010 `me.s0.energyP`
- -0.010 `me.s0.retreatGap`
- +0.009 `me.reach.oneShort3`
- +0.009 `op.s4.typeD`
- -0.009 `retreated`
- +0.009 `me.s0.energyC`
- +0.009 `me.s1.stage`
- +0.009 `me.s2.stage`
- +0.009 `me.reach.oneShort1`
- +0.008 `me.s0.stage`
- +0.008 `op.s4.energyD`
- +0.008 `me.s0.energyG`
- +0.008 `me.s3.energyW`
- +0.008 `me.s2.energyW`
- +0.008 `me.s0.weakM`
- +0.008 `me.s4.abilityDamage`
- -0.008 `op.s5.energyR`
- -0.007 `energyAttached`
- +0.007 `me.s5.energyW`
- -0.007 `me.handPokemon`
- -0.007 `me.handEnergyP`
- +0.007 `me.s3.a1.koTo0`

## Worst decisions

### Crustle vs Lopunny Dusknoir (seed 702009) - gap 1

```
Turn 20, P2 to move
Stadium: Lumiose City
P1: prizes 1  deck 38  discard 4  hand 8
  Active: Dwebble 50/70 E:F Spiky
  Bench0: Mega Kangaskhan ex 20/300 E:-
  Bench1: Mega Kangaskhan ex 300/300 E:2Growing [G] P
  Hand: Switch, Mist Energy, Boss's Orders, Hilda, Mist Energy, Prism Tower, Growing [G] Energy, Xerosic's Machinations
P2 (to move): prizes 1  deck 26  discard 21  hand 1
  Active: Bloodmoon Ursaluna ex 50/260 E:Enriching 3Telepathic Psychic
  Bench0: Dusknoir (on Duskull<Dusclops) 120/160 E:P
  Bench1: Bronzong (on Bronzor) 80/110 E:-
  Hand: Switch
```
- reference (search): 1 - attack Blood Moon
- policy: 0 - play Switch | own bench1 Bronzong -> ability Cursed Blast (bench0 Dusknoir) | opp active Dwebble
  - chose `play Switch | own bench1 Bronzong` (predicted 1.22); others: `retreat to bench1 Bronzong | Telepathic Psychic Energy + Telepathic Psychic Energy + Telepathic Psychic Energy` 1.17, `retreat to bench1 Bronzong | Telepathic Psychic Energy + Telepathic Psychic Energy + Enriching Energy` 1.17, `play Switch | own bench0 Dusknoir` 1.09, `retreat to bench0 Dusknoir | Telepathic Psychic Energy + Telepathic Psychic Energy + Telepathic Psychic Energy` 1.04, `retreat to bench0 Dusknoir | Telepathic Psychic Energy + Telepathic Psychic Energy + Enriching Energy` 1.04
  - chose `ability Cursed Blast (bench0 Dusknoir) | opp active Dwebble` (exact 0.00); others: `ability Cursed Blast (bench0 Dusknoir) | opp bench0 Mega Kangaskhan ex` 0.00, `ability Cursed Blast (bench0 Dusknoir) | opp bench1 Mega Kangaskhan ex` 0.00, `use stadium Lumiose City | Buneary` 0.00, `use stadium Lumiose City | Duskull` 0.00, `use stadium Lumiose City | Meowth ex` 0.00

### Dragapult Toucannon vs Toxtricity Box (seed 702014) - gap 1

```
Turn 11, P2 to move
Stadium: Team Rocket's Watchtower
P1: prizes 5  deck 27  discard 17  hand 4
  Active: Budew 30/30 E:-
  Bench0: Drakloak (on Dreepy) 10/90 E:-
  Bench1: Toucannon (on Pikipek) 140/150 E:-
  Bench2: Dreepy 20/70 E:-
  Bench3: Dreepy 60/70 E:-
  Hand: Rare Candy, Rare Candy, Lillie's Determination, Poké Pad
P2 (to move): prizes 1  deck 31  discard 17  hand 3
  Active: Pecharunt 10/80 E:-
  Bench0: Toxtricity (on Toxel) 30/140 E:D
  Bench1: Munkidori 20/110 E:-
  Bench2: Tatsugiri 70/70 E:-
  Bench3: Toxel 70/70 E:-
  Hand: Chi-Yu, Munkidori, Team Rocket's Petrel
```
- reference (search): 1 - bench Chi-Yu -> play Team Rocket's Petrel | Energy Switch -> play Energy Switch | Darkness Energy own bench0 Toxtricity -> own bench1 Munkidori -> ability Adrena-Brain (bench1 Munkidori) | move 3 counters -> opp active Budew
- policy: 0 - bench Chi-Yu -> play Team Rocket's Petrel | Lillie's Determination -> ability Sinister Surge (bench0 Toxtricity) | Darkness Energy -> own bench0 Toxtricity -> end turn
  - chose `bench Chi-Yu` (predicted 0.14); others: `bench Munkidori` 0.14, `play Team Rocket's Petrel | Lillie's Determination` 0.14, `play Team Rocket's Petrel | Secret Box` 0.14, `play Team Rocket's Petrel | Energy Switch` 0.14, `play Team Rocket's Petrel | Judge` 0.14
  - chose `play Team Rocket's Petrel | Lillie's Determination` (predicted 0.14); others: `play Team Rocket's Petrel | Secret Box` 0.14, `play Team Rocket's Petrel | Energy Switch` 0.14, `play Team Rocket's Petrel | Judge` 0.14, `play Team Rocket's Petrel | Air Balloon` 0.14, `play Team Rocket's Petrel | Energy Recycler` 0.14
  - chose `ability Sinister Surge (bench0 Toxtricity) | Darkness Energy -> own bench0 Toxtricity` (predicted 0.14); others: `ability Sinister Surge (bench0 Toxtricity) | Darkness Energy -> own bench3 Toxel` 0.14, `ability Sinister Surge (bench0 Toxtricity) | Darkness Energy -> own bench4 Chi-Yu` 0.14, `ability Sinister Surge (bench0 Toxtricity) | attach nothing` 0.14, `ability Sinister Surge (bench0 Toxtricity) | Darkness Energy -> own active Pecharunt | own bench0 Toxtricity` 0.12, `ability Sinister Surge (bench0 Toxtricity) | Darkness Energy -> own active Pecharunt | own bench1 Munkidori` 0.11
  - chose `end turn` (exact 0.00); others: 

### Mega Excadrill vs Dragapult Alakazam (seed 702025) - gap 1

```
Turn 18, P2 to move
Stadium: Team Rocket's Watchtower
P1: prizes 1  deck 18  discard 30  hand 3
  Active: Genesect ex 170/220 E:-
  Bench0: Genesect ex 80/220 E:2M
  Bench1: Drilbur 70/70 E:M
  Bench2: Mega Skarmory ex 70/260 E:- +Hero's Cape
  Hand: Brock's Scouting, Beldum, Boss's Orders
P2 (to move): prizes 3  deck 15  discard 23  hand 10
  Active: Dragapult ex (on Dreepy<Drakloak) 320/320 E:F P
  Bench0: Kadabra (on Abra) 20/80 E:F
  Hand: Kadabra, Crispin, Buddy-Buddy Poffin, Dawn, Boss's Orders, Boss's Orders, Abra, Night Stretcher, Poké Pad, Unfair Stamp
```
- reference (search): 3 - play Boss's Orders | opp bench2 Mega Skarmory ex -> attack Phantom Dive | 60 on opp bench0 Genesect ex
- policy: 2 - attack Phantom Dive | 60 on opp bench0 Genesect ex | take 2 prizes
  - chose `attack Phantom Dive | 60 on opp bench0 Genesect ex | take 2 prizes` (exact 2.00); others: `attack Phantom Dive | 60 on opp bench1 Drilbur | take 2 prizes` 2.00, `attack Phantom Dive | 60 on opp bench2 Mega Skarmory ex | take 2 prizes` 2.00, `play Boss's Orders | opp bench2 Mega Skarmory ex` 1.56, `play Crispin | nothing` 1.24, `play Buddy-Buddy Poffin | nothing` 1.24

### Mew Box vs Crustle (seed 702026) - gap 1

```
Turn 20, P1 to move
P1 (to move): prizes 1  deck 30  discard 16  hand 8
  Active: Mew ex 160/160 E:F 2Telepathic Psychic P
  Hand: Mega Kangaskhan ex, Telepathic Psychic Energy, Lillie's Clefairy ex, Meowth ex, Jirachi ex, Night Stretcher, Iron Crown ex, Mew ex
P2: prizes 2  deck 15  discard 30  hand 5
  Active: Mega Kangaskhan ex 260/300 E:- +Hero's Cape
  Bench0: Crustle (on Dwebble) 40/150 E:-
  Bench1: Mega Kangaskhan ex 300/300 E:D Mist Growing [G]
  Hand: Lillie's Determination, Eri, Boss's Orders, Crispin, Team Rocket's Petrel
```
- reference (search): 1 - bench Iron Crown ex -> ability Memory Helix (active Mew ex) | Iron Crown ex: Twin Shotels | opp active Mega Kangaskhan ex + opp bench0 Crustle
- policy: 0 - attach Telepathic Psychic Energy -> active Mew ex | Latias ex + Latias ex -> bench Mega Kangaskhan ex -> play Night Stretcher | Meowth ex -> bench Jirachi ex -> bench Lillie's Clefairy ex -> ability Memory Helix (active Mew ex) | Latias ex: Eon Blade
  - chose `attach Telepathic Psychic Energy -> active Mew ex | Latias ex + Latias ex` (predicted 1.79); others: `attach Telepathic Psychic Energy -> active Mew ex | Latias ex` 1.79, `bench Mega Kangaskhan ex` 1.74, `bench Jirachi ex` 1.38, `bench Lillie's Clefairy ex` 0.87, `bench Meowth ex | yes | Judge` 0.73
  - chose `bench Mega Kangaskhan ex` (predicted 1.79); others: `play Night Stretcher | Fighting Energy` 1.79, `play Night Stretcher | Unown` 1.79, `play Night Stretcher | Meowth ex` 1.79, `play Night Stretcher | Mega Kangaskhan ex` 1.79, `play Night Stretcher | Lillie's Clefairy ex` 1.79
  - chose `play Night Stretcher | Meowth ex` (predicted 2.51); others: `play Night Stretcher | Mew ex` 2.15, `play Night Stretcher | Fighting Energy` 1.79, `play Night Stretcher | Unown` 1.79, `play Night Stretcher | Mega Kangaskhan ex` 1.79, `play Night Stretcher | Lillie's Clefairy ex` 1.79
  - chose `bench Jirachi ex` (predicted 1.43); others: `bench Lillie's Clefairy ex` 1.35, `bench Meowth ex | yes | Judge` 0.78, `bench Meowth ex | yes | Cyrano` 0.78, `bench Meowth ex | yes | Crispin` 0.78, `bench Meowth ex | yes | Boss's Orders` 0.78
  - chose `bench Lillie's Clefairy ex` (predicted 1.43); others: `bench Meowth ex | yes | Judge` 1.43, `bench Meowth ex | yes | Cyrano` 1.43, `bench Meowth ex | yes | Crispin` 1.43, `bench Meowth ex | yes | Boss's Orders` 1.43, `bench Meowth ex | yes | Ciphermaniac's Codebreaking` 1.43
  - chose `ability Memory Helix (active Mew ex) | Latias ex: Eon Blade` (exact 0.00); others: `ability Memory Helix (active Mew ex) | Mega Kangaskhan ex: Rapid-Fire Combo` 0.00, `ability Memory Helix (active Mew ex) | Jirachi ex: Wish Granter` 0.00, `ability Memory Helix (active Mew ex) | Jirachi ex: Swift` 0.00, `ability Memory Helix (active Mew ex) | Lillie's Clefairy ex: Full Moon Rondo` 0.00, `attack Teleportation Burst | yes | own bench0 Latias ex` 0.00

### Toxtricity Box vs Greninja (seed 702039) - gap 1

```
Turn 7, P1 to move
P1 (to move): prizes 5  deck 40  discard 8  hand 4
  Active: Toxel 60/70 E:-
  Bench0: Toxel 70/70 E:D
  Hand: Toxtricity, Tatsugiri, Night Stretcher, Special Red Card
P2: prizes 1  deck 43  discard 4  hand 7
  Active: Dusclops (on Duskull) 10/90 E:-
  Bench0: Budew 10/30 E:2W
  Hand: Poké Pad, Boss's Orders, Poké Pad, Buddy-Buddy Poffin, Mega Froslass ex, Ultra Ball, Buddy-Buddy Poffin
```
- reference (search): 1 - evolve bench0 Toxel -> Toxtricity -> bench Tatsugiri -> play Night Stretcher | Darkness Energy -> play Special Red Card -> attach Darkness Energy -> active Toxel -> ability Sinister Surge (bench0 Toxtricity) | Darkness Energy -> own active Toxel -> attack Rascal Kick | take a prize
- policy: 0 - play Night Stretcher | Pecharunt -> evolve bench0 Toxel -> Toxtricity -> ability Sinister Surge (bench0 Toxtricity) | Darkness Energy -> own active Toxel -> bench Tatsugiri -> play Special Red Card -> bench Pecharunt -> retreat to bench1 Tatsugiri -> ability Attract Customers (active Tatsugiri) | Boss's Orders -> play Boss's Orders | opp bench0 Budew -> end turn
  - chose `play Night Stretcher | Pecharunt` (predicted 0.06); others: `evolve bench0 Toxel -> Toxtricity` 0.06, `evolve active Toxel -> Toxtricity` 0.06, `bench Tatsugiri` 0.04, `play Night Stretcher | Mega Absol ex` 0.04, `play Night Stretcher | Toxel` 0.04
  - chose `evolve bench0 Toxel -> Toxtricity` (predicted 0.09); others: `evolve active Toxel -> Toxtricity` 0.09, `bench Tatsugiri` 0.06, `play Special Red Card` 0.06, `bench Pecharunt` 0.06, `end turn` 0.00
  - chose `ability Sinister Surge (bench0 Toxtricity) | Darkness Energy -> own active Toxel` (predicted 0.13); others: `bench Tatsugiri` 0.09, `play Special Red Card` 0.09, `bench Pecharunt` 0.09, `ability Sinister Surge (bench0 Toxtricity) | Darkness Energy -> own bench0 Toxtricity` 0.09, `ability Sinister Surge (bench0 Toxtricity) | attach nothing` 0.09
  - chose `bench Tatsugiri` (predicted 0.13); others: `play Special Red Card` 0.13, `bench Pecharunt` 0.13, `retreat to bench0 Toxtricity` 0.08, `attack Call For Family | Munkidori + Munkidori` 0.00, `attack Call For Family | Munkidori + Pecharunt ex` 0.00
  - chose `play Special Red Card` (predicted 0.13); others: `bench Pecharunt` 0.13, `retreat to bench1 Tatsugiri` 0.10, `retreat to bench0 Toxtricity` 0.08, `attack Call For Family | Munkidori + Munkidori` 0.00, `attack Call For Family | Munkidori + Pecharunt ex` 0.00
  - chose `bench Pecharunt` (predicted 0.13); others: `retreat to bench1 Tatsugiri` 0.10, `retreat to bench0 Toxtricity` 0.08, `attack Call For Family | Munkidori + Munkidori` 0.00, `attack Call For Family | Munkidori + Pecharunt ex` 0.00, `attack Call For Family | Munkidori + Brute Bonnet` 0.00
  - chose `retreat to bench1 Tatsugiri` (predicted 0.10); others: `retreat to bench2 Pecharunt` 0.10, `retreat to bench0 Toxtricity` 0.08, `attack Call For Family | Munkidori + Munkidori` 0.00, `attack Call For Family | Munkidori + Pecharunt ex` 0.00, `attack Call For Family | Munkidori + Brute Bonnet` 0.00
  - chose `ability Attract Customers (active Tatsugiri) | Boss's Orders` (predicted 0.10); others: `ability Attract Customers (active Tatsugiri) | nothing` 0.10, `end turn` 0.00
  - chose `play Boss's Orders | opp bench0 Budew` (predicted 0.07); others: `end turn` 0.00
  - chose `end turn` (exact 0.00); others: 

### Mega Starmie vs Dragapult Dudunsparce (seed 702050) - gap 1

```
Turn 18, P1 to move
P1 (to move): prizes 2  deck 38  discard 5  hand 8
  Active: Drakloak (on Dreepy) 50/90 E:-
  Bench0: Mega Starmie ex (on Staryu) 330/330 E:2Ignition +Hero's Cape
  Hand: Team Rocket's Petrel, Boss's Orders, Wally's Compassion, Poké Pad, Xerosic's Machinations, Switch, Lillie's Determination, Wally's Compassion
P2: prizes 1  deck 17  discard 21  hand 9
  Active: Dragapult ex (on Dreepy<Drakloak) 320/320 E:-
  Bench0: Dudunsparce ex (on Dunsparce) 270/270 E:2F 2P
  Bench1: Budew 30/30 E:F
  Bench2: Fezandipiti ex 210/210 E:-
  Hand: Darkness Energy, Poké Pad, Munkidori, Crispin, Rosa's Encouragement, Buddy-Buddy Poffin, Lillie's Determination, Dragapult ex, Poké Pad
```
- reference (search): 2 - play Boss's Orders | opp bench2 Fezandipiti ex -> play Switch | own bench0 Mega Starmie ex -> attack Nebula Beam
- policy: 1 - play Switch | own bench0 Mega Starmie ex -> play Boss's Orders | opp bench1 Budew -> attack Nebula Beam | take a prize
  - chose `play Switch | own bench0 Mega Starmie ex` (predicted 0.12); others: `play Boss's Orders | opp bench1 Budew` 0.09, `end turn` 0.00, `play Team Rocket's Petrel | Mega Signal` 0.00, `play Team Rocket's Petrel | Lillie's Determination` 0.00, `play Team Rocket's Petrel | Salvatore` 0.00
  - chose `play Boss's Orders | opp bench1 Budew` (predicted 0.22); others: `play Team Rocket's Petrel | Mega Signal` 0.12, `play Team Rocket's Petrel | Lillie's Determination` 0.12, `play Team Rocket's Petrel | Salvatore` 0.12, `play Team Rocket's Petrel | Switch` 0.12, `play Team Rocket's Petrel | Battle Cage` 0.12
  - chose `attack Nebula Beam | take a prize` (exact 1.00); others: `play Poké Pad | Patrat` 0.22, `play Poké Pad | Dreepy` 0.22, `play Poké Pad | Drakloak` 0.22, `play Poké Pad | Snorunt` 0.22, `play Poké Pad | nothing` 0.22

### Lopunny Dudunsparce vs Crustle (seed 702079) - gap 1

```
Turn 5, P2 to move
Stadium: Battle Cage
P1: prizes 3  deck 40  discard 7  hand 0
  Active: Buneary 30/70 E:Mist +Air Balloon
  Bench0: Dudunsparce (on Dunsparce) 140/140 E:Mist Enriching P
  Bench1: Fan Rotom 30/70 E:-
  Hand: -
P2 (to move): prizes 3  deck 37  discard 9  hand 8
  Active: Mega Kangaskhan ex 300/300 E:Growing [G] +Hero's Cape
  Hand: Team Rocket's Petrel, Lillie's Determination, Boss's Orders, Jumbo Ice Cream, Festival Grounds, Jumbo Ice Cream, Spiky Energy, Prism Tower
```
- reference (search): 1 - play Festival Grounds -> attach Spiky Energy -> active Mega Kangaskhan ex -> ability Run Errand (active Mega Kangaskhan ex) -> play Crispin | Darkness Energy + Fighting Energy | Darkness Energy -> own active Mega Kangaskhan ex -> attack Rapid-Fire Combo | take a prize
- policy: 0 - attach Spiky Energy -> active Mega Kangaskhan ex -> play Team Rocket's Petrel | Pokémon Center Lady -> play Festival Grounds -> play Pokémon Center Lady | own active Mega Kangaskhan ex -> ability Run Errand (active Mega Kangaskhan ex) -> end turn
  - chose `attach Spiky Energy -> active Mega Kangaskhan ex` (predicted 0.18); others: `play Team Rocket's Petrel | Pokémon Center Lady` 0.09, `play Team Rocket's Petrel | Eri` 0.09, `play Team Rocket's Petrel | Pokégear 3.0` 0.09, `play Team Rocket's Petrel | Team Rocket's Petrel` 0.09, `play Team Rocket's Petrel | Crispin` 0.09
  - chose `play Team Rocket's Petrel | Pokémon Center Lady` (predicted 0.18); others: `play Team Rocket's Petrel | Eri` 0.18, `play Team Rocket's Petrel | Pokégear 3.0` 0.18, `play Team Rocket's Petrel | Team Rocket's Petrel` 0.18, `play Team Rocket's Petrel | Crispin` 0.18, `play Team Rocket's Petrel | Lumiose City` 0.18
  - chose `play Festival Grounds` (predicted 0.18); others: `play Prism Tower` 0.18, `play Pokémon Center Lady | own active Mega Kangaskhan ex` 0.18, `ability Run Errand (active Mega Kangaskhan ex)` 0.18, `use stadium Battle Cage` 0.18, `end turn` 0.00
  - chose `play Pokémon Center Lady | own active Mega Kangaskhan ex` (predicted 0.18); others: `ability Run Errand (active Mega Kangaskhan ex)` 0.18, `end turn` 0.00
  - chose `ability Run Errand (active Mega Kangaskhan ex)` (predicted 0.18); others: `end turn` 0.00
  - chose `end turn` (exact 0.00); others: 
