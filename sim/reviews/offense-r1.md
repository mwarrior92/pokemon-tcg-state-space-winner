# Review of run offense-r1

Reviewer: Claude (AI review step, see ../REVIEW.md). Packet: `runs/offense-r1/review-packet.md`.

## Results

- **Data:** 1,000 generated states produced 2,798 labelled positions, but they came from only 393 states. 266 of those searches were complete.
- **Fit:** the full model's validation R² is 0.065, close to useless. The chosen reduced model ("top 25 features", still using engine probes) reaches R² 0.143.
- **Evaluation on 100 fresh states:** the policy took 0.47 prizes per turn, the same as the search. It matched the search on 91 of 100 turns, but it takes 24.5 s per turn.

The policy does well only because it scores attack moves exactly, one step ahead. The model adds almost nothing, and the policy is far too slow to be the "intuition" layer.

## What went wrong (worst decisions)

1. **Mew Box (gap 3).** The search played: Wondrous Patch (Psychic Energy onto Unown), then Boss's Orders on the 20-HP Mega Kangaskhan ex, then retreat, then Rapid-Fire Combo, taking 3 prizes.
   - The policy played the same cards in the wrong order and ended up attacking the wrong target, taking 0.
   - The model rated "retreat to Mega Kangaskhan ex" (0.58) above Boss's Orders on the KO-able target (0.18).
   - Nothing in the vector says that Boss's Orders turns a 20-HP, 3-prize bench Pokémon into a Knock Out.
2. **Rocket's Mewtwo (gap 2).** Transceiver searches for Giovanni, which switches in the 10-HP Ceruledge ex, and Rocket Rush KOs it for 2 prizes.
   - The model scored Transceiver→Giovanni at 0.02, its lowest option.
   - The two-step resource chain (a search card fetching a gust Supporter) is invisible to the features.
3. **Mega Starmie (gap 1).** Night Stretcher should take back Mega Starmie ex, then evolve Staryu and attack.
   - All Night Stretcher choices scored the same 0.33, so it took Patrat.
   - No feature says which evolution in hand would create an attacker that can KO.
4. **Seaking Festival Lead and Festival Lead (gap 1 each).** Same pattern: the attacker that can KO is on the Bench, and it needs an Energy plus a retreat or switch. The policy powered up the wrong Pokémon.

## Patterns

- Every loss is a **reachability** failure. A prize needs an attacker that can deal enough damage, Energy it can still get this turn, a way into the Active Spot, and the target in the Active Spot (or a gust card). These are interaction terms; a linear model over separate per-slot facts cannot build them.
- The engine-probe group helps only slightly: removing it raises validation MSE by 4%.
- **Label bias.** Only completely searched positions were used, and breadth-first search rarely completes deep subtrees. So 607 of 1,000 states contributed nothing, and the data over-represents simple boards. That is likely part of the low R².
- **The teacher is not an upper bound.** On some turns the greedy policy beat the search, because the search ran out of budget.

## Changes (more aggressive than refitting)

1. **New feature group `reach`.** It covers the interaction terms above and is computed from rules and board facts. Per (my attacker, attack, opposing target):
   - **Damage:** analytic damage (base damage × Weakness − Resistance), or the exact probe value when probes are on.
   - **Energy:** the cost gap after this turn's attachment, if an Energy is in hand and none has been attached yet.
   - **Getting the attacker Active:** it already is, a retreat is affordable, or a switch card is in hand.
   - **Getting the target Active:** it already is, or a gust card is in hand.

   It also covers evolutions in hand that evolve a Pokémon in play, treated as the attacker they would become. Summaries: the largest prize value reachable by a KO this turn, the number of reachable KO pairs, and the same counts allowing one missing resource. Gust and switch cards are recognised from card text.
2. **Labels.** Use every expanded position; incomplete ones give a lower bound and are flagged. Also raise the labelling budget to 3,000 steps.
3. **Feature selection weighs cost.** A probe set is chosen only if it beats the best cheap set by more than 10% in validation MSE. The `reach` group is always kept.
4. **Reference value.** Evaluate against the larger of the search's and the policy's result, so the policy is never credited with beating a weak teacher.

## Next round

`offense-r2`, with the same evaluation size. The change worked if:
- validation R² rises clearly above 0.15;
- the policy runs well under 5 s per turn;
- prize capture stays at or above the search on most turns.
