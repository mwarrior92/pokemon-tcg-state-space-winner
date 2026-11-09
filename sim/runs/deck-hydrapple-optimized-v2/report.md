# Deck report: Hydrapple optimized v2

- Started from the list in hydrapple-meta.txt.
- Tested in 120 full games from turn 1 against the meta field (by share of decklists), pilot: race.

## Deck list

```
Pokémon: 20
4 Teal Mask Ogerpon ex TWM 25
2 Applin TWM 17
2 Bayleef MEG 9
2 Chikorita ASC 8
2 Dipplin TWM 18
2 Hydrapple ex SCR 14
2 Meowth ex POR 62
1 Celebi MEG 12
1 Fezandipiti ex ASC 142
1 Meganium MEG 10
1 Tapu Bulu SFA 6

Trainer: 26
4 Bug Catching Set TWM 143
4 Forest of Vitality MEG 117
4 Lillie's Determination MEG 119
4 Ultra Ball MEG 131
2 Boss's Orders MEG 114
2 Night Stretcher ASC 196
1 Briar SCR 132
1 Ciphermaniac's Codebreaking TEF 145
1 Judge POR 76
1 Lana's Aid TWM 155
1 Poké Pad POR 81
1 Unfair Stamp TWM 165

Energy: 14
14 Grass Energy MEE 9

Total Cards: 60
```

## Changes made by the optimiser

- Round 1: no change beat the current list (best tried: -1 Boss's Orders, +1 Judge; -1 Meganium, +1 Grass Energy, score 0.59 vs 0.60)
- Round 2: no change beat the current list (best tried: -1 Poké Pad, +1 Iron Crown ex; -1 Grass Energy, +1 Kieran, score 0.51 vs 0.68)
- Round 3: no change beat the current list (best tried: -1 Fezandipiti ex, +1 Poké Pad; -1 Bug Catching Set, +1 Grass Energy, score 0.61 vs 0.59)
- Round 4: -1 Meganium, +1 Grass Energy (on the same 48 games: win rate 49% -> 50%, score 0.45 -> 0.47)
- **Starting list vs optimised list, on the same 119 games:** 45% -> 59% (difference +14 points, 95% range 2 to 27); time stuck 15% -> 13% of turns.

## Win statistics

- **Win rate against the meta field: 59%** (95% range 50%–68%), 71 of 120 games.
- Games last 15.0 turns on average; 0.44 prizes per own turn; first prize on own turn 4 (median).
- How games ended: won: prizes 53, lost: no Pokémon in play 28, lost: prizes 21, won: no Pokémon in play 17, won: deck out 1.

## Meta matchups

| opponent | games | won | win rate (95% range) |
|---|---|---|---|
| Dragapult | 34 | 19 | 56% (39%–71%) |
| Basic Box | 10 | 5 | 50% (24%–76%) |
| N's Zoroark | 10 | 8 | 80% (49%–94%) |
| Slowking | 9 | 8 | 89% (56%–98%) |
| Hydrapple | 6 | 5 | 83% (44%–97%) |
| Festival Lead | 6 | 4 | 67% (30%–90%) |
| Alakazam Dudunsparce | 5 | 0 | 0% (-0%–43%) |
| Dragapult Dusknoir | 4 | 3 | 75% (30%–95%) |
| Alakazam Dusknoir | 4 | 2 | 50% (15%–85%) |
| Dragapult Blaziken | 4 | 2 | 50% (15%–85%) |
| Dhelmise | 4 | 3 | 75% (30%–95%) |
| Crustle | 4 | 0 | 0% (0%–49%) |
| Mega Excadrill | 3 | 2 | 67% (21%–94%) |
| Lopunny Dusknoir | 3 | 2 | 67% (21%–94%) |
| Dragapult Dudunsparce | 2 | 1 | 50% (9%–91%) |
| Rocket's Honchkrow | 2 | 2 | 100% (34%–100%) |
| Seaking Festival Lead | 2 | 1 | 50% (9%–91%) |
| Lucario Hariyama | 1 | 0 | 0% (0%–79%) |
| Sharpedo Toxtricity | 1 | 1 | 100% (21%–100%) |
| Clefairy Ogerpon | 1 | 1 | 100% (21%–100%) |
| Cynthia's Garchomp | 1 | 0 | 0% (0%–79%) |
| Rocket's Mewtwo | 1 | 1 | 100% (21%–100%) |
| Lopunny Dudunsparce | 1 | 0 | 0% (0%–79%) |
| Greninja | 1 | 1 | 100% (21%–100%) |
| Mega Lucario | 1 | 0 | 0% (0%–79%) |

## Stuck statistics

- Turns in an **ideal** spot (the side to move usually wins from there): 20%; it won 91% of those games.
- Turns in a **non-ideal** spot (the side to move usually loses): 25%; **still in the same spot on its next turn 49%** of the time.
- Games that reached a non-ideal spot: 57 (48%); won 46% of them, against 30% expected for an average deck (+15 points).

| most frequent non-ideal spots | turns | stuck next turn |
|---|---|---|
| race:behind ready:0-1 ko:no threat:no exposed:none | 38 | 61% |
| race:behind ready:0-1 ko:no threat:yes exposed:none | 28 | 70% |
| race:behind ready:0-2 ko:no threat:yes exposed:none | 27 | 75% |
| race:behind ready:0-2 ko:no threat:no exposed:none | 26 | 52% |

## How it takes prizes

| attack / ability | Pokémon | prizes | share | times used |
|---|---|---|---|---|
| attack Myriad Leaf Shower | Teal Mask Ogerpon ex | 220 | 56% | 188 |
| attack Syrup Storm | Hydrapple ex | 85 | 22% | 73 |
| attack Solar Beam | Meganium | 24 | 6% | 31 |
| attack Do the Wave | Dipplin | 17 | 4% | 36 |
| attack Wood Hammer | Tapu Bulu | 15 | 4% | 12 |
| attack Cruel Arrow | Fezandipiti ex | 13 | 3% | 17 |
| attack Push Down | Bayleef | 10 | 3% | 34 |
| attack Solar Cutter | Celebi | 4 | 1% | 5 |

## Recommended play style

- **Win condition.** Prizes come mostly from Myriad Leaf Shower (Teal Mask Ogerpon ex) – 56% of prizes; Syrup Storm (Hydrapple ex) – 22% of prizes; Solar Beam (Meganium) – 6% of prizes. Build towards Teal Mask Ogerpon ex first.
- **Tempo.** First prize typically on its own turn 4; 0.44 prizes per own turn.
- **Opening (first two turns).** Most games: ability Teal Dance (Teal Mask Ogerpon ex) (58%), play Ultra Ball (52%), play Bug Catching Set (51%), attach Grass Energy to Teal Mask Ogerpon ex (49%), play Lillie's Determination (48%).
- **Cards that show up in wins.** Grass Energy (4.7 uses per won game vs 3.7 per lost game); Bug Catching Set (1.8 uses per won game vs 1.3 per lost game); Lillie's Determination (1.5 uses per won game vs 1.2 per lost game); Hydrapple ex (0.3 uses per won game vs 0.1 per lost game); Dipplin (0.5 uses per won game vs 0.3 per lost game); Teal Mask Ogerpon ex (0.7 uses per won game vs 0.4 per lost game). Prioritise getting these into play / using them.
- **Cards that show up in losses.** Unfair Stamp (0.2 vs 0.0); Poké Pad (0.4 vs 0.3); Celebi (0.3 vs 0.2) – often a sign of playing from behind with them, or of a weak slot.
- **Where it gets stuck.** Most often "race:behind ready:0-1 ko:no threat:no exposed:none" (38 turns; still there the next turn 61% of the time). To get out: get a second attacker ready earlier (bench and power up the next attacker before the first is Knocked Out); keep a way to take a prize every turn (gust for weak benched targets, damage spread).
- **Matchups.** Best against Slowking (89%), Hydrapple (83%); weakest against Crustle (0%), Alakazam Dudunsparce (0%).

## Card implementation checks

- All cards in the list match their printed text and work in play (engine card checks).

## How to read this

- Games are full games from turn 1 against meta decks chosen by their share of the decklists, piloted by the same simulator policy on both sides. Set-up choices (opening Active and Bench) and the opponent's prompts during a turn are made at random.
- The result says how well this simulator plays the deck, not only how strong the deck is: decks whose plan relies on long ability chains are likely under-piloted. Compare a new deck with known meta decks tested the same way.
