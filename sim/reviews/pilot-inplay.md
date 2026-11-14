# Review: pilot with in-play material and hand-need (2026-11-13)

Pilot `imitrace:runs/imit-v3/policy.json` with the parts `inplay` and `handneed` on (`src/variant.ts`),
against the same pilot with both off, which is how the committed pilot plays.

## Results

Every game is played twice on the same seed, each deck once in the new pilot's hands
(`pilotaudit --versus`). All pairings of the top 10 decks, 180 games per run.

| run | new against | new won | 95% interval | pairs: both / one each / none |
|---|---|---|---|---|
| vs-confirm (seeds 1) | handneed, inplay off | 104 of 180, 58% | 51% to 65% | 20 / 64 / 6 |
| vs-inplay | inplay off | 104 of 180, 58% | 51% to 65% | 18 / 68 / 4 |
| vs-handneed | handneed off | 100 of 180, 56% | 48% to 63% | 16 / 68 / 6 |
| vs-supply | supply off | 87 of 180, 48% | 41% to 56% | 7 / 73 / 10 |
| vs-targets | targets off | 89 of 180, 49% | 42% to 57% | 2 / 85 / 3 |

`supply` and `targets` were not shown to help and are off by default (opt in with `SIM_PARTS`).

In vs-confirm the new pilot left a Stadium in hand on 11% of its turns (old 31%), took 0.57 prizes
per turn (old 0.48) and attacked on 58% of turns (old 54%). Turns with no attack payable stayed at
24% for both. By deck, new won most with Alakazam Dudunsparce (15 of 18) and least with Slowking
(5 of 18) and Festival Lead and Alakazam Dusknoir (9 of 18 each).

## Audit of six games the new pilot won (vs-confirm, picked at random)

Read from the turn lines in `runs/vs-confirm/games.jsonl` (no boards).

1. **Dragapult Dusknoir beat Dragapult.** Poffin, Energy to a Benched Dreepy, evolved both lines,
   Phantom Dive from its fourth turn; took 3 prizes in one turn. Logical throughout.
2. **N's Zoroark beat Basic Box.** Punk Helmet on the Active on the first turn, N's Castle played,
   three N's Zoroark ex trading each turn, Night Joker for 3, 2 and 1 prizes. Logical.
3. **Basic Box beat Dragapult Blaziken** (12 turns). Stadium and Hero's Cape down on turn one. Weak
   spots: a turn of Boss's Orders on Fezandipiti ex with no attack after it (flagged
   `idleAttack`), and two attacks that took nothing while the Energy was spread over three
   Pokémon. It won on Myriad Leaf Shower late; the opponent was slow too.
4. **Dragapult Dusknoir beat Hydrapple.** Boss's Orders with Adrena-Brain for a prize, then two
   Phantom Dives. Logical.
5. **Festival Lead beat Hydrapple** (10 turns). No attack payable on its first five turns: Boom Boom
   Groove fetched more Thwackey before any Energy, and the first Energy went on a Grookey that then
   retreated. From turn six it built Dipplin and Seaking properly and won. On the last turn it spent
   three search cards for nothing before the winning attack (harmless there, wasteful anywhere else).
6. **Alakazam Dusknoir beat Hydrapple.** Cursed Blast plus Hand Power for a prize or more every turn
   from its second turn. Logical.

## Verdict

Adopt. None of the wins rests on a play the new parts made worse; Tools and Stadiums now go down on
the first turn they can, which is what the change was for. Still open, in the order they cost games:

- Festival Lead (and Slowking) spend their early turns with no attack payable: a search for the
  board's first Energy is not preferred over a fourth engine piece.
- Boss's Orders and Pokémon Catcher are still played with no attack to follow.
- The `next` term of the race evaluator moves by up to 0.07 between near-identical boards and
  decides close choices at random.
- Search cards are spent for nothing when the turn is already decided.
