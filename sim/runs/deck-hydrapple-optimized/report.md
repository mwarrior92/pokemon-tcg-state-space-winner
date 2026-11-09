# Deck report: Hydrapple optimized

- Started from the list in hydrapple.txt.
- Tested in 120 full games from turn 1 against the meta field (by share of decklists), pilot: race.

## Deck list

```
Pokémon: 20
4 Teal Mask Ogerpon ex TWM 25
2 Applin TWM 17
2 Bayleef MEG 9
2 Chikorita ASC 8
2 Hydrapple ex SCR 14
2 Meganium MEG 10
1 Celebi MEG 12
1 Dipplin TWM 18
1 Fezandipiti ex ASC 142
1 Mega Kangaskhan ex MEG 104
1 Meowth ex POR 62
1 Tapu Bulu SFA 6

Trainer: 26
4 Forest of Vitality MEG 117
4 Lillie's Determination MEG 119
4 Ultra Ball MEG 131
3 Bug Catching Set TWM 143
3 Night Stretcher ASC 196
2 Boss's Orders MEG 114
1 Black Belt's Training ASC 255
1 Briar SCR 132
1 Crushing Hammer POR 71
1 Judge POR 76
1 Lana's Aid TWM 155
1 Poké Pad POR 81

Energy: 14
14 Grass Energy MEE 9

Total Cards: 60
```

## Changes made by the optimiser

- Round 1: -1 Teal Mask Ogerpon ex, +1 Meowth ex; -1 Bug Catching Set, +1 Black Belt's Training (score 0.38 -> 0.49: win rate 42% -> 52% on the same 24 games)
- Round 2: -1 Meowth ex, +1 Night Stretcher; -1 Unfair Stamp, +1 Teal Mask Ogerpon ex (score 0.46 -> 0.61: win rate 50% -> 65% on the same 24 games)
- Round 3: -1 Meowth ex, +1 Mega Kangaskhan ex (score 0.51 -> 0.61: win rate 54% -> 63% on the same 24 games)
- Round 4: -1 Ciphermaniac's Codebreaking, +1 Grass Energy; -1 Dipplin, +1 Crushing Hammer (score 0.48 -> 0.51: win rate 50% -> 54% on the same 24 games)

## Win statistics

- **Win rate against the meta field: 55%** (95% range 46%–64%), 66 of 120 games.
- Games last 16.0 turns on average; 0.40 prizes per own turn; first prize on own turn 4 (median).
- How games ended: won: prizes 49, lost: no Pokémon in play 29, lost: prizes 23, won: no Pokémon in play 14, won: deck out 3, lost: deck out 2.

## Meta matchups

| opponent | games | won | win rate (95% range) |
|---|---|---|---|
| Dragapult | 34 | 20 | 59% (42%–74%) |
| Basic Box | 10 | 4 | 40% (17%–69%) |
| N's Zoroark | 10 | 9 | 90% (60%–98%) |
| Slowking | 9 | 6 | 67% (35%–88%) |
| Hydrapple | 6 | 3 | 50% (19%–81%) |
| Festival Lead | 6 | 3 | 50% (19%–81%) |
| Alakazam Dudunsparce | 5 | 3 | 60% (23%–88%) |
| Dragapult Dusknoir | 4 | 3 | 75% (30%–95%) |
| Alakazam Dusknoir | 4 | 1 | 25% (5%–70%) |
| Dragapult Blaziken | 4 | 2 | 50% (15%–85%) |
| Dhelmise | 4 | 2 | 50% (15%–85%) |
| Crustle | 4 | 0 | 0% (0%–49%) |
| Mega Excadrill | 3 | 2 | 67% (21%–94%) |
| Lopunny Dusknoir | 3 | 2 | 67% (21%–94%) |
| Dragapult Dudunsparce | 2 | 1 | 50% (9%–91%) |
| Rocket's Honchkrow | 2 | 1 | 50% (9%–91%) |
| Seaking Festival Lead | 2 | 1 | 50% (9%–91%) |
| Lucario Hariyama | 1 | 0 | 0% (0%–79%) |
| Sharpedo Toxtricity | 1 | 0 | 0% (0%–79%) |
| Clefairy Ogerpon | 1 | 1 | 100% (21%–100%) |
| Cynthia's Garchomp | 1 | 0 | 0% (0%–79%) |
| Rocket's Mewtwo | 1 | 0 | 0% (0%–79%) |
| Lopunny Dudunsparce | 1 | 1 | 100% (21%–100%) |
| Greninja | 1 | 0 | 0% (0%–79%) |
| Mega Lucario | 1 | 1 | 100% (21%–100%) |

## Stuck statistics

- Turns in an **ideal** spot (the side to move usually wins from there): 22%; it won 87% of those games.
- Turns in a **non-ideal** spot (the side to move usually loses): 27%; **still in the same spot on its next turn 39%** of the time.
- Games that reached a non-ideal spot: 71 (59%); won 42% of them, against 31% expected for an average deck (+11 points).

| most frequent non-ideal spots | turns | stuck next turn |
|---|---|---|
| race:even ready:0-2 ko:no threat:no exposed:none | 57 | 53% |
| race:behind ready:0-1 ko:no threat:no exposed:none | 46 | 51% |
| race:behind ready:0-1 ko:no threat:yes exposed:none | 39 | 60% |
| race:behind ready:0-2 ko:no threat:no exposed:none | 26 | 29% |

## How it takes prizes

| attack / ability | Pokémon | prizes | share | times used |
|---|---|---|---|---|
| attack Myriad Leaf Shower | Teal Mask Ogerpon ex | 184 | 48% | 167 |
| attack Rapid-Fire Combo | Mega Kangaskhan ex | 53 | 14% | 46 |
| attack Syrup Storm | Hydrapple ex | 47 | 12% | 46 |
| attack Wood Hammer | Tapu Bulu | 41 | 11% | 34 |
| attack Solar Beam | Meganium | 31 | 8% | 39 |
| attack Do the Wave | Dipplin | 13 | 3% | 17 |
| attack Solar Cutter | Celebi | 5 | 1% | 5 |
| attack Tumbling Attack | Applin | 2 | 1% | 29 |

## Recommended play style

- **Win condition.** Prizes come mostly from Myriad Leaf Shower (Teal Mask Ogerpon ex) – 48% of prizes; Rapid-Fire Combo (Mega Kangaskhan ex) – 14% of prizes; Syrup Storm (Hydrapple ex) – 12% of prizes. Build towards Teal Mask Ogerpon ex first.
- **Tempo.** First prize typically on its own turn 4; 0.40 prizes per own turn.
- **Opening (first two turns).** Most games: play Lillie's Determination (53%), play Ultra Ball (52%), ability Teal Dance (Teal Mask Ogerpon ex) (52%), play Bug Catching Set (43%), attach Grass Energy to Teal Mask Ogerpon ex (39%).
- **Cards that show up in wins.** Grass Energy (5.1 uses per won game vs 3.8 per lost game); Teal Mask Ogerpon ex (0.9 uses per won game vs 0.5 per lost game); Lillie's Determination (1.5 uses per won game vs 1.1 per lost game); Bug Catching Set (1.4 uses per won game vs 1.1 per lost game); Forest of Vitality (0.7 uses per won game vs 0.5 per lost game); Ultra Ball (1.7 uses per won game vs 1.5 per lost game). Prioritise getting these into play / using them.
- **Cards that show up in losses.** Prism Tower (0.1 vs 0.0); Tapu Bulu (0.5 vs 0.4); Crushing Hammer (0.4 vs 0.3); Applin (0.6 vs 0.5) – often a sign of playing from behind with them, or of a weak slot.
- **Where it gets stuck.** Most often "race:even ready:0-2 ko:no threat:no exposed:none" (57 turns; still there the next turn 53% of the time). To get out: get a second attacker ready earlier (bench and power up the next attacker before the first is Knocked Out).
- **Matchups.** Best against N's Zoroark (90%), Dragapult Dusknoir (75%); weakest against Crustle (0%), Alakazam Dusknoir (25%).

## Card implementation checks

- All cards in the list match their printed text and work in play (engine card checks).

## How to read this

- Games are full games from turn 1 against meta decks chosen by their share of the decklists, piloted by the same simulator policy on both sides. Set-up choices (opening Active and Bench) and the opponent's prompts during a turn are made at random.
- The result says how well this simulator plays the deck, not only how strong the deck is: decks whose plan relies on long ability chains are likely under-piloted. Compare a new deck with known meta decks tested the same way.
