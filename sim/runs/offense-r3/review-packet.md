# Review packet: offense

100 evaluated turns. Read the worst decisions below, decide what the policy is getting wrong and why, and write the reasoning and the changes to make in sim/reviews/ (see sim/REVIEW.md).

- search (teacher): 0.50 prizes/turn; policy: 0.62; policy matched the search on 97/100

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
| top 25 features by importance **(chosen)** | 25 | probe | 0.177 |
| top 200 cheap features by importance | 200 | cheap | 0.202 |
| top 100 cheap features by importance | 100 | cheap | 0.202 |
| top 50 cheap features by importance | 50 | cheap | 0.198 |
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

### Mega Starmie vs Cynthia's Garchomp (seed 803048) - gap 1

```
Turn 17, P2 to move
P1: prizes 5  deck 30  discard 3  hand 10
  Active: Drakloak (on Dreepy) 90/90 E:Ignition W
  Bench0: Snorunt 170/170 E:- +Hero's Cape
  Bench1: Mega Froslass ex (on Snorunt) 230/310 E:-
  Bench2: Dreepy 70/70 E:-
  Bench3: Mega Starmie ex (on Staryu) 330/330 E:-
  Bench4: Meowth ex 40/170 E:-
  Hand: Switch, Poké Pad, Bubbly Water Energy, Staryu, Mega Starmie ex, Wally's Compassion, Ultra Ball, Staryu, Buddy-Buddy Poffin, Night Stretcher
P2 (to move): prizes 4  deck 28  discard 1  hand 8
  Active: Cynthia's Gabite (on Cynthia's Gible) 100/100 E:Rocky Fighting F
  Bench0: Cynthia's Garchomp ex (on Cynthia's Gible<Cynthia's Gabite) 400/400 E:- +Cynthia's Power Weight
  Bench1: Cynthia's Roserade (on Cynthia's Roselia) 130/130 E:-
  Bench2: Cynthia's Gible 70/70 E:F Rocky Fighting
  Bench3: Cynthia's Gabite (on Cynthia's Gible) 170/170 E:F +Cynthia's Power Weight
  Bench4: Cynthia's Roserade (on Cynthia's Roselia) 130/130 E:-
  Hand: Rocky Fighting Energy, Hilda, Premium Power Pro, Poké Pad, Neo Upper Energy, Buddy-Buddy Poffin, Boss's Orders, Pokégear 3.0
```
- reference (search): 2 - play Boss's Orders | opp bench4 Meowth ex -> attack Dragon Slice | take 2 prizes
- policy: 1 - play Hilda | Cynthia's Garchomp ex + Fighting Energy -> ability Champion's Call (active Cynthia's Gabite) | Cynthia's Garchomp ex -> play Poké Pad | Cynthia's Gabite -> play Premium Power Pro -> play Pokégear 3.0 | Lillie's Determination -> ability Champion's Call (bench3 Cynthia's Gabite) | Cynthia's Roselia -> evolve bench2 Cynthia's Gible -> Cynthia's Gabite -> ability Champion's Call (bench2 Cynthia's Gabite) | Cynthia's Roserade -> evolve active Cynthia's Gabite -> Cynthia's Garchomp ex -> attach Fighting Energy -> active Cynthia's Garchomp ex -> attack Corkscrew Dive | take a prize
  - chose `play Hilda | Cynthia's Garchomp ex + Fighting Energy` (predicted 1.03); others: `play Hilda | Cynthia's Garchomp ex + Rocky Fighting Energy` 1.03, `play Hilda | Cynthia's Garchomp ex` 1.02, `ability Champion's Call (active Cynthia's Gabite) | Cynthia's Garchomp ex` 1.02, `ability Champion's Call (bench3 Cynthia's Gabite) | Cynthia's Garchomp ex` 1.02, `attach Rocky Fighting Energy -> active Cynthia's Gabite` 1.00
  - chose `ability Champion's Call (active Cynthia's Gabite) | Cynthia's Garchomp ex` (predicted 1.15); others: `ability Champion's Call (bench3 Cynthia's Gabite) | Cynthia's Garchomp ex` 1.15, `play Poké Pad | Cynthia's Gabite` 1.03, `ability Champion's Call (active Cynthia's Gabite) | Cynthia's Gabite` 1.03, `ability Champion's Call (bench3 Cynthia's Gabite) | Cynthia's Gabite` 1.03, `play Premium Power Pro` 1.03
  - chose `play Poké Pad | Cynthia's Gabite` (predicted 1.15); others: `ability Champion's Call (bench3 Cynthia's Gabite) | Cynthia's Gabite` 1.15, `play Premium Power Pro` 1.15, `play Poké Pad | Cynthia's Roserade` 1.15, `play Poké Pad | Cynthia's Roselia` 1.15, `play Poké Pad | Shaymin` 1.15
  - chose `play Premium Power Pro` (predicted 1.15); others: `play Pokégear 3.0 | Lillie's Determination` 1.15, `play Pokégear 3.0 | nothing` 1.15, `ability Champion's Call (bench3 Cynthia's Gabite) | Cynthia's Roselia` 1.15, `ability Champion's Call (bench3 Cynthia's Gabite) | Cynthia's Roserade` 1.15, `ability Champion's Call (bench3 Cynthia's Gabite) | nothing` 1.15
  - chose `play Pokégear 3.0 | Lillie's Determination` (predicted 1.15); others: `play Pokégear 3.0 | nothing` 1.15, `ability Champion's Call (bench3 Cynthia's Gabite) | Cynthia's Roselia` 1.15, `ability Champion's Call (bench3 Cynthia's Gabite) | Cynthia's Roserade` 1.15, `ability Champion's Call (bench3 Cynthia's Gabite) | nothing` 1.15, `evolve bench2 Cynthia's Gible -> Cynthia's Gabite` 1.15
  - chose `ability Champion's Call (bench3 Cynthia's Gabite) | Cynthia's Roselia` (predicted 1.15); others: `ability Champion's Call (bench3 Cynthia's Gabite) | Cynthia's Roserade` 1.15, `ability Champion's Call (bench3 Cynthia's Gabite) | nothing` 1.15, `evolve bench2 Cynthia's Gible -> Cynthia's Gabite` 1.15, `evolve active Cynthia's Gabite -> Cynthia's Garchomp ex` 1.08, `evolve bench3 Cynthia's Gabite -> Cynthia's Garchomp ex` 1.03
  - chose `evolve bench2 Cynthia's Gible -> Cynthia's Gabite` (predicted 1.15); others: `evolve active Cynthia's Gabite -> Cynthia's Garchomp ex` 1.08, `evolve bench3 Cynthia's Gabite -> Cynthia's Garchomp ex` 1.03, `attach Fighting Energy -> bench3 Cynthia's Gabite` 1.02, `attach Neo Upper Energy -> active Cynthia's Gabite` 1.02, `attach Fighting Energy -> active Cynthia's Gabite` 1.01
  - chose `ability Champion's Call (bench2 Cynthia's Gabite) | Cynthia's Roserade` (predicted 1.15); others: `ability Champion's Call (bench2 Cynthia's Gabite) | nothing` 1.15, `evolve active Cynthia's Gabite -> Cynthia's Garchomp ex` 1.08, `evolve bench3 Cynthia's Gabite -> Cynthia's Garchomp ex` 1.02, `attach Fighting Energy -> bench3 Cynthia's Gabite` 1.02, `attach Neo Upper Energy -> active Cynthia's Gabite` 1.02
  - chose `evolve active Cynthia's Gabite -> Cynthia's Garchomp ex` (predicted 1.08); others: `evolve bench3 Cynthia's Gabite -> Cynthia's Garchomp ex` 1.02, `attach Fighting Energy -> bench3 Cynthia's Gabite` 1.02, `retreat to bench3 Cynthia's Gabite` 1.01, `attach Neo Upper Energy -> active Cynthia's Gabite` 1.01, `attach Fighting Energy -> active Cynthia's Gabite` 1.01
  - chose `attach Fighting Energy -> active Cynthia's Garchomp ex` (predicted 1.20); others: `evolve bench3 Cynthia's Gabite -> Cynthia's Garchomp ex` 1.07, `attach Neo Upper Energy -> active Cynthia's Garchomp ex` 1.00, `attach Rocky Fighting Energy -> active Cynthia's Garchomp ex` 1.00, `attach Rocky Fighting Energy -> bench0 Cynthia's Garchomp ex` 1.00, `attach Rocky Fighting Energy -> bench1 Cynthia's Roserade` 1.00
  - chose `attack Corkscrew Dive | take a prize` (exact 1.00); others: `evolve bench3 Cynthia's Gabite -> Cynthia's Garchomp ex` 1.00, `retreat to bench2 Cynthia's Gabite` 1.00, `retreat to bench3 Cynthia's Gabite` 1.00, `attack Draconic Buster | take a prize` 1.00, `retreat to bench0 Cynthia's Garchomp ex` 0.00

### Mega Excadrill vs Lopunny Dusknoir (seed 803070) - gap 1

```
Turn 16, P2 to move
P1: prizes 2  deck 40  discard 9  hand 4
  Active: Mega Excadrill ex (on Drilbur) 440/440 E:- +Hero's Cape
  Bench0: Beldum 70/70 E:-
  Bench1: Genesect ex 40/220 E:-
  Hand: Metal Energy, Team Rocket's Petrel, Metal Energy, Metal Energy
P2 (to move): prizes 1  deck 18  discard 21  hand 10
  Active: Duskull 10/60 E:2Telepathic Psychic Enriching P
  Bench0: Mega Lopunny ex (on Buneary) 310/330 E:Telepathic Psychic
  Bench1: Dusclops (on Duskull) 20/90 E:-
  Hand: Ultra Ball, Ultra Ball, Dusknoir, Poké Pad, Hilda, Duskull, Lillie's Determination, Special Red Card, Salvatore, Bronzong
```
- reference (search): 1 - ability Cursed Blast (bench1 Dusclops) | opp bench1 Genesect ex
- policy: 0 - retreat to bench0 Mega Lopunny ex | Telepathic Psychic Energy -> ability Cursed Blast (bench1 Dusclops) | opp active Mega Excadrill ex -> play Ultra Ball | Bronzong + Hilda | Mega Kangaskhan ex -> play Ultra Ball | Lillie's Determination + Mega Kangaskhan ex | Bronzor -> play Poké Pad | Dusclops -> bench Duskull -> play Special Red Card -> attack Gale Thrust
  - chose `retreat to bench0 Mega Lopunny ex | Telepathic Psychic Energy` (exact 1.03); others: `retreat to bench0 Mega Lopunny ex | Enriching Energy` 1.03, `retreat to bench0 Mega Lopunny ex | Psychic Energy` 1.03, `ability Cursed Blast (bench1 Dusclops) | opp bench1 Genesect ex` 1.00, `ability Cursed Blast (bench1 Dusclops) | opp active Mega Excadrill ex` 0.29, `ability Cursed Blast (bench1 Dusclops) | opp bench0 Beldum` 0.28
  - chose `ability Cursed Blast (bench1 Dusclops) | opp active Mega Excadrill ex` (exact 1.05); others: `ability Cursed Blast (bench1 Dusclops) | opp bench0 Beldum` 1.03, `play Ultra Ball | Bronzong + Hilda | Mega Kangaskhan ex` 1.03, `play Ultra Ball | Bronzong + Hilda | Bronzor` 1.03, `play Ultra Ball | Bronzong + Hilda | Dusknoir` 1.03, `play Ultra Ball | Bronzong + Hilda | Latias ex` 1.03
  - chose `play Ultra Ball | Bronzong + Hilda | Mega Kangaskhan ex` (exact 1.05); others: `play Ultra Ball | Bronzong + Hilda | Bronzor` 1.05, `play Ultra Ball | Bronzong + Hilda | Dusknoir` 1.05, `play Ultra Ball | Bronzong + Hilda | Latias ex` 1.05, `play Ultra Ball | Bronzong + Hilda | Dusclops` 1.05, `play Ultra Ball | Bronzong + Hilda | nothing` 1.05
  - chose `play Ultra Ball | Lillie's Determination + Mega Kangaskhan ex | Bronzor` (exact 1.05); others: `play Ultra Ball | Lillie's Determination + Mega Kangaskhan ex | Latias ex` 1.05, `play Ultra Ball | Lillie's Determination + Mega Kangaskhan ex | Dusknoir` 1.05, `play Ultra Ball | Lillie's Determination + Mega Kangaskhan ex | Dusclops` 1.05, `play Ultra Ball | Lillie's Determination + Mega Kangaskhan ex | nothing` 1.05, `play Ultra Ball | Lillie's Determination + Salvatore | Bronzor` 1.05
  - chose `play Poké Pad | Dusclops` (exact 1.05); others: `play Poké Pad | Dusknoir` 1.05, `play Poké Pad | nothing` 1.05, `bench Duskull` 1.05, `play Special Red Card` 1.05, `play Salvatore | cancel` 1.05
  - chose `bench Duskull` (exact 1.05); others: `play Special Red Card` 1.05, `play Salvatore | cancel` 1.05, `bench Bronzor` 1.05, `evolve bench0 Duskull -> Dusclops` 1.05, `attack Gale Thrust` 0.00
  - chose `play Special Red Card` (exact 1.05); others: `play Salvatore | cancel` 1.05, `bench Bronzor` 1.05, `evolve bench0 Duskull -> Dusclops` 1.05, `attack Gale Thrust` 0.00, `end turn` 0.00
  - chose `attack Gale Thrust` (exact 0.00); others: `play Salvatore | cancel` 0.00, `bench Bronzor` 0.00, `evolve bench0 Duskull -> Dusclops` 0.00, `end turn` 0.00

### Ogerpon Meganium vs Ogerpon Meganium (seed 803085) - gap 1

```
Turn 11, P1 to move
P1 (to move): prizes 5  deck 35  discard 8  hand 3
  Active: Dolliv (on Smoliv) 90/90 E:2G
  Bench0: Arboliva ex (on Smoliv<Dolliv) 310/310 E:-
  Bench1: Meowth ex 170/170 E:-
  Bench2: Hoothoot 70/70 E:-
  Hand: Grass Energy, Night Stretcher, Grass Energy
P2: prizes 3  deck 31  discard 16  hand 0
  Active: Arboliva ex (on Smoliv<Dolliv) 170/310 E:3G
  Bench0: Budew 30/30 E:-
  Bench1: Chikorita 50/70 E:-
  Bench2: Teal Mask Ogerpon ex 150/210 E:-
  Bench3: Teal Mask Ogerpon ex 210/210 E:-
  Hand: -
```
- reference (search): 1 - attach Grass Energy -> bench0 Arboliva ex -> play Night Stretcher | Meganium -> retreat to bench0 Arboliva ex -> attack Oil Salvo | 120 on opp bench0 Budew | take a prize
- policy: 0 - play Night Stretcher | Chikorita -> attach Grass Energy -> bench1 Meowth ex -> bench Chikorita -> attack Nutrients | own active Dolliv
  - chose `play Night Stretcher | Chikorita` (predicted 0.40); others: `play Night Stretcher | Teal Mask Ogerpon ex` 0.40, `play Night Stretcher | Grass Energy` 0.40, `play Night Stretcher | nothing` 0.40, `attach Grass Energy -> active Dolliv` 0.38, `play Night Stretcher | Meganium` 0.38
  - chose `attach Grass Energy -> bench1 Meowth ex` (predicted 0.34); others: `attach Grass Energy -> bench2 Hoothoot` 0.34, `bench Chikorita` 0.34, `attach Grass Energy -> bench0 Arboliva ex` 0.23, `retreat to bench0 Arboliva ex` 0.23, `retreat to bench2 Hoothoot` 0.13
  - chose `bench Chikorita` (predicted 0.34); others: `retreat to bench0 Arboliva ex` 0.13, `retreat to bench1 Meowth ex` 0.06, `retreat to bench2 Hoothoot` 0.03, `attack Nutrients | own active Dolliv` 0.00, `attack Nutrients | own bench0 Arboliva ex` 0.00
  - chose `attack Nutrients | own active Dolliv` (exact 0.00); others: `retreat to bench0 Arboliva ex` 0.00, `retreat to bench1 Meowth ex` 0.00, `retreat to bench2 Hoothoot` 0.00, `retreat to bench3 Chikorita` 0.00, `attack Nutrients | own bench0 Arboliva ex` 0.00
