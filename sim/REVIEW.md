# AI review step

After every training round (`node dist/train.js ...`), an AI reviewer (Claude) reads
`runs/<run>/review-packet.md` and the battles it points to, and writes `reviews/<run>.md`:

1. **What went wrong.** For each of the worst decisions, the decision the policy made, what the
   search did instead, and the most likely reason. Typical reasons: a feature that is missing,
   wrong or mis-scaled; a rule the move generator gets wrong; the model's form being too weak; or
   the search itself being wrong.
2. **Patterns.** Mistakes that repeat across battles, and whether the feature-reduction step
   dropped something the mistakes depend on.
3. **Changes.** Concrete edits. These are deliberately bigger steps than refitting weights:
   - add, fix or rescale features;
   - force a feature group back into the reduced set;
   - change the model form;
   - change move generation, prompt-answer caps or search budget;
   - fix engine or card bugs found while reading;
   - add training states for a weak area.

   Each change is listed with the evidence for it.
4. **Next round.** What to run, and what result would show the change worked.

The reviewer then makes the changes and starts the next round. When a review finds nothing new
to fix, the step is stable; the next stage is categorising generated states (step 6).

Reviews are kept in order (`reviews/`); each one names the run it reviewed and the run that tested
its changes.
