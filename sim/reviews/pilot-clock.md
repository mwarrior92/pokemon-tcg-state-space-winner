# Review: pilot with the clock (2026-11-14)

Pilot `imitrace:runs/imit-v3/policy.json` with the part `clock` on (`src/variant.ts`, `src/clock.ts`),
against the same pilot with it off. With the clock on, the mover's expected turns to the win along
its shortest likely path (weight 0.5 prizes a turn) take the place of the race's next-turn term.

## Results

Every game is played twice on the same seed, each deck once in the new pilot's hands
(`pilotaudit --versus clock`). All pairings of the top 10 decks, 180 games per run.

| run | seeds | new won | 95% interval | pairs: both / one each / none |
|---|---|---|---|---|
| vs-clock4 | 0 | 103 of 180, 57% | 50% to 64% | 21 / 61 / 8 |
| vs-clock4b | 1 | 95 of 180, 53% | 45% to 60% | 17 / 61 / 12 |
| vs-clock4c | 2 | 96 of 180, 53% | 46% to 61% | 25 / 46 / 19 |
| vs-clock4d | 3 | 101 of 180, 56% | 49% to 63% | 20 / 61 / 9 |
| pooled | | 395 of 720, 55% | 51% to 59% | 83 / 229 / 48 |

Seeds 2 and 3 were run after the last change to the clock and its weight: 197 of 360, 55%.

In every run the new pilot took more prizes per turn (0.58 to 0.60 against 0.50 to 0.53) and
attacked for the first time later (own turn 2.9 or 3.0 against 2.6 or 2.7).

Weight (`SIM_CLOCK`, seeds 0): 0.25 won 102 of 180, 0.5 won 103, 1 won 88 (49%, with an empty Bench
on 6% of turns against 1%). The weight stays 0.5.

Before two fixes of 2026-11-14 the same seeds 0 and 1 gave 193 of 360 (vs-clock3, vs-clock3b). The
fixes: an Ability that attaches Energy "to this Pokémon" (Teal Dance) counts for its own Pokémon
only, and an attack that does more for each Energy attached counts with the Energy it will have.
Without them the clock took Teal Mask Ogerpon ex out of the Active Spot for Tapu Bulu on the first
turn (Basic Box against Hydrapple, seed 710401: 19 turns to win; 11 after the fixes).

## Audit of six games the new pilot won (vs-clock4d, picked at random)

Read from the turn lines in `runs/vs-clock4d/games.jsonl`; game 3 also replayed with boards.

1. **Alakazam Dudunsparce beat Basic Box.** Slow: one turn of only benching a Dunsparce, no attack
   payable until its fifth turn. Then three Kadabra evolved together and Hand Power took 3 and 3
   prizes. Logical.
2. **Basic Box beat Dragapult Blaziken** (11 own turns). Weak: two Heart Sign attacks that took
   nothing, then on two turns in a row an Energy to Benched Latias ex followed by a retreat into it,
   and a second Area Zero Underdepths held for seven turns. It won on Mega Kangaskhan ex from its
   eighth turn; the opponent took one prize in ten turns.
3. **Dragapult beat Festival Lead** (14 own turns). On the first turn it played Ultra Ball,
   discarding Unfair Stamp and Night Stretcher for a Moltres, which left an empty hand; it then
   passed three turns with nothing to play. With the clock off the same seat kept its hand and won
   in 11 turns of the game. The planner's printout for that turn: the Ultra Ball line led by 0.08,
   of which the clock gave 0.03 (a thinner deck), the defense model 0.07, readiness 0.02, and
   material took back 0.05. The clock tipped a close choice; the cause is that two discarded cards
   cost 0.05.
4. **Alakazam Dusknoir beat Dragapult Dusknoir.** Cursed Blast and Rare Candy into Hand Power, 3
   prizes in one turn. Logical.
5. **Hydrapple beat Slowking.** Teal Dance every turn it could, Myriad Leaf Shower for 2, 2, 1, 1.
   Logical; this is the line the two fixes were for.
6. **Alakazam Dusknoir beat Slowking.** Itchy Pollen while setting up, then Hand Power for 2 prizes
   on three turns running. Logical.

## Verdict

Adopt: `clock` is on by default. Four of the six wins are sound and none rests on a play the clock
made worse, but game 3 shows what it can tip. Still open:

- A search card's discard cost is too small (two cards for 0.05 of a prize), so a hand can be thrown
  away for a marginal Basic on the first turn.
- First attack comes about a quarter of a turn later with the clock on.
- Basic Box moved Energy and the Active Spot back and forth between two Pokémon (game 2).
- Not in the clock: Energy acceleration from Trainers, Rare Candy, Bench position, the opponent's
  Energy for attacks that count both Active Pokémon's.
- From the earlier review (`pilot-inplay.md`): Boss's Orders with no attack to follow; search cards
  spent when the turn is already decided.

## Follow-up (2026-11-14): two changes measured, neither kept on

**Hand size** (part `handsize`): each of the first three cards in hand counts 0.04 of a prize more,
so that emptying the hand has a price (game 3 above). It reverses that first-turn Ultra Ball, and
changes almost no results: 91 of 180 at three cards and 0.04 (`runs/vs-hand-a`), 90 of 180 at four
cards and 0.03 (`runs/vs-hand-b`); more than 80 of 90 same-seed pairs split. Off by default.

**Where the first attack is later.** Over the four runs above, by deck (own turn of the first
attack, clock on against off; wins of 72):

| deck | clock on | clock off | wins on / off |
|---|---|---|---|
| Hydrapple | 3.17 | 2.33 | 44 / 42 |
| N's Zoroark | 3.61 | 2.96 | 24 / 24 |
| Slowking | 3.56 | 3.18 | 27 / 15 |
| Dragapult Blaziken | 2.50 | 2.19 | 48 / 33 |
| the other six | within 0.25 | | |

In same-seed pairs the clock pilot put every Energy on a Benched attacker (Yveltal, Teal Mask
Ogerpon ex, Tapu Bulu) and none on an Active that then could not retreat.

**Bench position** (part `benchpos`): a path on a Benched Pokémon also needs the Energy the Active
lacks for its Retreat Cost. 178 of 359 (`runs/vs-benchpos` 88 of 179, `vs-benchpos-b` 90 of 180).
It does bring the first attack forward where it was late (Slowking 3.81 against 5.08, N's Zoroark
3.31 against 3.92, Hydrapple 2.69 against 3.03) and pushes it back for Dragapult Blaziken (3.69
against 2.39, 19 wins against 24 of 36). Off by default; the Dragapult Blaziken games are the
place to look before trying it again.

