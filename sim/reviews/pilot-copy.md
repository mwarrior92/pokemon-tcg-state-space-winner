# Pilot review: copied attacks in the clock (part `copy`), 2026-11-14

## What changed

The clock (`src/clock.ts`) now follows attacks that are another card's attack: Slowking's Seek
Inspiration by the best two attacks of the Pokémon that can be put on top of the deck (Academy at
Night, Ciphermaniac's Codebreaking), N's Zoroark ex's Night Joker by the N's Pokémon in play or to
come. An attack that damages several Pokémon counts all its targets; an attack that discards all
its Energy or cannot be used the next turn counts as used every second turn.

## Measured (new = `copy` on, old = `@copy`, same seeds both ways)

| run | games | new won | same-seed pairs (both / neither) |
|---|---|---|---|
| `runs/vs-copy` (all decks, seeds 0) | 180 | 95 = 53% (45% to 60%) | 10 / 5 |
| `runs/vs-copy-sk` (every game has Slowking, seeds 1) | 72 | 38 = 53% (41% to 64%) | 4 / 2 |
| `runs/vs-copy-nz` (every game has N's Zoroark, seeds 1) | 72 | 43 = 60% (48% to 71%) | 11 / 4 |
| together | 324 | 176 = 54% | 25 / 11 |

The two decks it was written for, in the hands of each pilot:

| deck | run | new | old | prizes a turn new / old | first attack new / old |
|---|---|---|---|---|---|
| N's Zoroark | vs-copy | 7 of 18 | 5 of 18 | 0.61 / 0.48 | 3.65 / 3.35 |
| N's Zoroark | vs-copy-nz | 20 of 36 | 13 of 36 | 0.57 / 0.41 | 2.56 / 2.94 |
| Slowking | vs-copy | 5 of 18 | 3 of 18 | 0.37 / 0.36 | 3.31 / 3.59 |
| Slowking | vs-copy-sk | 13 of 36 | 11 of 36 | 0.46 / 0.44 | 3.55 / 3.34 |

No single run shows a gain on its own (every interval holds 50%); the direction is the same in all
three, and N's Zoroark takes clearly more prizes a turn.

## Games looked at (same-seed pairs the new pilot won and the old one lost)

- Basic Box|N's Zoroark|0: new put its Energy on an N's Zorua, evolved, and took 2, 3 and 1 prizes
  with Night Joker (Rampaging Thunder, Powerful Rage). Old put five Energy on Yveltal and N's Zekrom
  and first attacked on its sixth turn. Sound.
- N's Zoroark|Slowking|3 (N's Zoroark's side): new attacked with Night Joker as Virtuous Flame from
  its second turn, four attacks, six prizes. Old loaded Yveltal, attacked once in nine turns. Sound.
- N's Zoroark|Slowking|3 (Slowking's side): new won, but not by good play: from its seventh turn it
  put Energy on a Benched Slowking four turns running and never attacked with it. NOT sound.

## Verdict

Adopt (on by default). Open: Slowking is still played badly (33% of its games in vs-copy-sk, no
attack payable on 42% of its turns): Energy goes to a Benched Slowking that is not brought to the
Active Spot, and Lillie's Clefairy ex and Mega Kangaskhan ex get Energy the plan does not need.
