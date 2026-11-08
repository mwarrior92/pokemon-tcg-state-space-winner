# Review of defense round 1 (`runs/defense-r1`)

## Results

- **Opponent's next-turn prizes:** 0.22 after the defense policy's turn, 0.33 after passing at
  once, 0.12 for the best of 12 sampled end-of-turn positions (an approximate optimum).
- **Against passing at once:** better on 6 of 60 turns, worse on 1, the same on 53 (mostly it
  passes or plays something neutral).
- **Model:** the label (prizes the opponent takes next turn after we end the turn here) is harder
  to predict than offense's. R² is 0.14 with all features; the chosen set is 50 cheap features,
  R² 0.13. Policy time: 0.53 s per turn.

## What went wrong

1. **Hand refresh helped the opponent** (Dragapult Blaziken vs Mega Lucario). Judge shuffles both
   hands into the decks and both draw 4. The model predicted that as safe; the opponent's new
   hand took 2 prizes, where passing at once gave 0. What a shuffle-draw effect hands the
   opponent is random and depends on their unseen cards. A single prediction cannot price it.
2. **Half the labelled states were dropped.** Only 205 of 400 states produced labels: a position
   is skipped when the opponent's reply search found 0 prizes without finishing (unknown). The
   kept states lean towards simple boards, the same bias offense round 1 had.
3. **Mostly passive.** On 53 of 60 turns the policy's choice gave the same result as passing:
   with weak predictions it seldom finds a move that changes the opponent's reach.

## Changes

1. Disruption and hidden information go through **sampled replies**, not a single prediction.
   This is the two-turn planner (`planner.ts`, `planTurn2`):
   - the opponent's unseen cards are redealt for each sampled reply;
   - the opponent plans that reply;
   - candidates are scored on the lower quartile as well as the average.

   Case 1 is exactly what it prices.
2. **Opponent reply labels use the quiescence-capped search** (same change as the offense
   review). An incomplete reply search is then a lower bound rather than unknown, and the
   dropped states can be kept.
3. The defense policy stays as v0's fallback for turns with no prize. Its successor is the
   win-model planner, which weighs both sides at once rather than one objective at a time.

## Next

Playouts with v0 (offense search policy, defense as fallback) to get the first categories and a
win model. Then the planners play head to head against v0.
