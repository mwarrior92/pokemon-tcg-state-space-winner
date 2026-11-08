# Review of offense round 3 (`runs/offense-r3`)

Reviewed after round 3; tested by the refit `offense-r3b` (same labels, new selection and policy).

## Results against the round-2 targets

| Target from the round-2 review | Round 3 | Met? |
|---|---|---|
| Search policy at least as good as the teacher on ≥ 97/100 | 97/100; better than the teacher on 14 | yes |
| Under 1 s per turn | 3.88 s in the round (5 workers; tail 11–20 s) | no |
| Greedy's kinds of miss do not repeat | 1 of 3 misses is greedy's case 3 again (overestimate) | partly |

The search policy took 0.62 prizes/turn against the teacher's 0.50 and the greedy policy's 0.50.
The value model's R² was 0.29 with all features and 0.34 for the chosen "top 50"; that set was
chosen because it beat the best cheap set (R² 0.26) by about 11% in MSE.

## What went wrong (3 turns)

1. **Gust a weak two-prize target, then attack** (Cynthia's Garchomp vs Mega Starmie). Boss's
   Orders on Meowth ex (40 HP left), then Dragon Slice: 2 prizes. The root had dozens of setup
   options (Hilda, Champion's Call, Poké Pad...), so the 100-child budget was spent at depth 1.
   The two-move line was left to the model's estimate, which missed it.
2. **Overestimate beat an exact game win** (Lopunny Dusknoir, 1 prize left). Cursed Blast on
   Genesect ex (40 HP left) wins the game. The policy's line had an estimate above 1, more than
   the 1 prize left to take, so the exact 1 lost. This is the same failure as round-2 case 3.
3. **Four-move combination** (Ogerpon Meganium): attach to Arboliva ex, recover, retreat into
   it, Oil Salvo spread to KO Budew. Out of reach of both the budget and the model.

Time: the probe-feature model makes every frontier estimate cost engine probes. Turns with big
boards hit the 5 s per-search cap several times.

## Changes

1. **Estimates are capped at the prizes left to take** (case 2). An estimate above the maximum
   is impossible, and it let a guess outrank an exact result.
2. **Quiescence:** every unexpanded position is also valued by its best immediate attack, played
   out exactly (case 1). It's the chess-engine fix for leaving tactics at the edge of the search to
   the evaluation. "Gust, then attack" becomes exact even when the budget ends at depth 1.
3. **Probe sets must beat cheap sets by 20%** (was 10%), so the policy runs on cheap features
   unless probes are clearly better. Its time feeds into every playout turn.

## Next

Refit from round 3's labels (`--data offense-r3 --states 0`) with these changes, evaluated on the
same 100 states. The changes worked if:
- the policy stays at ≥ 97/100;
- it takes ≤ 1 s per turn in the round;
- cases 1 and 2 do not recur.

Then the offense step is stable enough to move on: playouts and categories.
