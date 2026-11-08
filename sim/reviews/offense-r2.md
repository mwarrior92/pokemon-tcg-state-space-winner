# Review of offense round 2 (`runs/offense-r2`)

Reviewed after round 2; tested by round 3.

## Results against the round-1 targets

| Target from the round-1 review | Round 2 | Met? |
|---|---|---|
| Validation R² clearly above 0.15 | 0.313 (chosen "top 25" set); 0.212 for all features | yes |
| Policy well under 5 s per turn | 10.1 s in the round (9 workers); 3.85 s alone, worst 18.6 s | no (fixed since: 0.30 s, see below) |
| Prize capture at or above the search on most turns | 0.60 against 0.57 prizes/turn; at least as good on 93/100 | yes |

Labelling took 13 min for 800 states (the interrupted first attempt took 70 min for 400).

## What went wrong (the 7 turns where the policy took fewer prizes)

1. **Attacked at once when a gust first was worth more** (Mega Excadrill vs Dragapult Alakazam).
   Attacking now was exact (2.00). Boss's Orders on Mega Skarmory ex, then the same attack, was
   worth 3, but the model predicted 1.56 for it, so the greedy step took the exact 2.
2. **Gust on the wrong target** (Mega Starmie vs Dragapult Dudunsparce). Boss's Orders on Budew
   (1 prize) was predicted 0.22, about the same as on Fezandipiti ex (2 prizes). The model does
   not see that one gust target is worth two prizes.
3. **Overestimate leading away from an exact prize** (Crustle vs Lopunny Dusknoir). Switching out
   was predicted 1.22, above attacking with Blood Moon for an exact 1. After the switch, no attack
   could take a prize.
4. **Flat predictions on long combinations** (Toxtricity Box x2, Mew Box, Lopunny Dudunsparce).
   Every candidate scored the same (e.g. all 0.14), so ties were broken by option order. The
   search's lines had 4 to 8 steps (Petrel for Energy Switch, then Munkidori's ability; benching
   Iron Crown ex so Mew ex can copy Twin Shotels).

## Patterns

- Cases 1 to 3 have one cause: **the greedy step compares a guess with an exact value one move
  ahead.** "Gust, then attack" and "switch, then attack" are two-move tactics. The exact values
  are cheap to get by looking one move further, but the policy never looks.
- Case 4 is a **model-capacity** problem. A linear value of the position cannot tell which order
  of 5 plays reaches a KO. Better features help at the margin, but this needs search.
- Labels are 87% zeros (6,487 of 7,489). Most of what the model learns is "nothing happens".

## Changes

1. **The policy becomes a budgeted search with the model at the frontier** (the main change).
   - The search is best-first, expanding the most promising positions first: highest predicted
     value, with exact values for finished lines.
   - Unexpanded positions are valued at max(prizes taken, model prediction). Expanded positions
     take the best of their children.
   - After the budget, it plays the best line.
   - The greedy policy is the special case "one expansion per step". With even a few hundred
     expansions, cases 1 to 3 are resolved exactly, because gust + attack is two moves deep.
   - This is also the building block for multi-turn planning: the same search, with a value model
     for "future" positions.
   - Evidence: cases 1 to 3.
2. **Probe features only as needed; reach always analytic** (done before this round).
   - The policy used to compute every probe in a group for the 6 probe features it uses. It now
     computes only the model's features: 3.85 → 0.30 s per turn alone, worst 18.6 → 0.8 s.
   - `reach` switched to probe damage whenever the probe group was on. Labels use every group, so
     "cheap" models were trained on probe-based reach and played with the estimate. Reach now
     always uses the estimate.
3. **Engine and generator fixes found while measuring** (done):
   - patches 016–020: Salvatore, rejected actions changing state, faster effect dispatch;
   - HP bonuses computed in generated states (they were 0, so features saw printed HP for
     boosted Pokémon);
   - damage capped below effective HP.

## Next round

Round 3: same settings as round 2, evaluated three ways on the same 100 fresh states: the
search (teacher), the greedy policy, and the search policy at budgets of 100 and 400.

The change worked if:
- the search policy at 400 matches or beats the teacher on at least 97/100 turns;
- it stays under 1 s per turn;
- the greedy policy's 7 kinds of miss do not repeat for the search policy.
