# Writing match logs from tournament transcripts

Match logs turn a commentated match (caption transcript in `sim/data/transcripts/`) into the real
games' actions, so `node dist/align.js` can rebuild every position and compare the pilot's choice
with the real player's. Logs go in `sim/data/matches/` (local, never committed: they come from
third-party broadcasts). The format is defined in `src/matchlog.ts` (`MatchLog`, `LogTurn`,
`LogAction`, `LogDeck`); the logs already in the folder are worked examples
(`2027-baltimore-final-g1.json` is a complete game).

## Steps

1. **Read the transcript** (`sim/data/transcripts/<date>-<video id>.txt`, `index.json` has the title
   and event). One video holds one to three games. The captions are automatic: card names are
   misspelled ("Fasendipity" = Fezandipiti ex, "Cerno"/"Sino"/"Zero" = Cyrano, "Draclo" = Drakloak,
   "Diplin" = Dipplin, "Kierum"/"Curum" = Kyurem, "Boo"/"Bed" = Budew, "Ldios" = Latias ex,
   "Sob"/"Saab" = Sob). Check every name against the decklist.
2. **Find the decklists**: `node sim/dist-logs/align.js --lists "<event words>"` lists the saved top
   cuts (rank, player, archetype, list id; "engine lacks" marks cards the engine does not have). Use
   the player names in the video title to pick each list. Junior and Senior players are not listed:
   use the same event's Masters list of the archetype the commentators name, with `"approx": true`,
   and `"swap": [["<card in list>", "<card seen played>"], ...]` for cards played that the list
   lacks. If the event is not saved at all, use the nearest event's list of that archetype
   (`approx`).
3. **Get the engine names**: `node sim/dist-logs/align.js --cards <list id>` prints every card with
   stage, HP, retreat cost, ability names and attack names with their Energy count. Use these names
   exactly (abilities and attacks too).
4. **Write one JSON file per game**: `sim/data/matches/<season>-<event>-<round>-g<N>.json`, e.g.
   `2025-worlds-final-g2.json`, `2026-stuttgart-top4a-g1.json`, `2025-worlds-junior-final-g1.json`.
5. **Check it**: `node sim/dist-logs/align.js --check --game <file name without .json>` replays it.
   Every action must apply ("0 failed"). The boards are in `sim/runs/align-check/replay-<game>.md`;
   read them to see why an action failed (a missing earlier action, a wrong target, no Energy).
   Fix the log (add the missing step as inferred, correct a name, give the choices) and check again.
   If a turn cannot be made consistent, end the log before it.

## The log

```json
{
  "source": "<transcript file>",
  "event": "2025 World Championships, Masters final",
  "game": 1,
  "decks": [{ "archetype": "Dragapult", "list": "18916" }, { "archetype": "Gardevoir", "list": "18917" }],
  "first": 0,
  "setup": [{ "active": "Dreepy", "bench": ["Budew"] }, { "active": "Ralts" }],
  "prizes": [["Dunsparce"], ["Psychic Energy", "Psychic Energy"]],
  "notes": "what was inferred, where the log stops and why",
  "turns": [
    { "player": 0, "t": "0:01:10", "hand": ["Ultra Ball", "Lillie's Determination"], "actions": [ ... ] }
  ]
}
```

- Players are 0 and 1 in the order of `decks`; `first` is who took the first turn. Turns alternate
  and must be listed in order, starting with the first player's turn 1.
- `setup`: the opening Active and any opening Bench. `prizes`: cards the commentators saw in each
  player's prizes. `hand`: cards seen in the mover's hand at the start of a turn (optional).
- Actions (`do`):
  - `bench` (card), `evolve` (card, `to` = the Pokémon evolved), `attach` (card, `to` = Pokémon or
    `"active"`), `tool` (card, `to`), `play` (Item, Supporter or Stadium card), `ability` (card = the
    Pokémon using it, `name`), `retreat` (`to` = the Pokémon coming in), `attack` (`name`), `end`
    (the turn ended without an attack), `stadium` (use the Stadium in play's ability, e.g. Academy at
    Night, Team Rocket's Factory; `card` = the Stadium, `choices` as usual), `promote` (after a Knock Out: put as the **first action of
    that player's next turn**, card = the new Active), `concede` (the turn a player conceded).
  - Two Pokémon with the same name: name the slot in `to`, as the replay boards print it
    (`"bench1 Slowpoke"`, `"active Slowpoke"`). Slots are filled left to right in the order the
    Pokémon were put down.
  - `choices`: answers to the action's prompts **in the order the card asks them**, by card names:
    `["Dipplin", "Grass Energy"]` for one prompt choosing two cards; a single name for one card or
    target; `"yes"`/`"no"` for "you may"; `"*"` for an answer not known. Examples: Ultra Ball
    `[["<discard>", "<discard>"], "<searched>"]`; Boss's Orders `["<target>"]`; Crispin
    `[["<Energy>", "<other Energy>"], ["<Energy attached>", "<Pokémon>"]]`; Cyrano
    `[["<ex>", "<ex>", "<ex>"]]`; Meowth ex benched `["<Supporter found>"]`; Telepathic Psychic
    Energy attached `[["<Basic>", "<Basic>"]]`; Cruel Arrow `["<target>"]`.
  - `uses`: other hand cards the action spends: Ultra Ball's two discards, the Grass Energy Teal
    Dance attaches, the Energy Ripening Charge attaches. They are put in the hand before the action.
  - `inferred: true`: the commentators did not say it, but it must have happened (the Ogerpon that
    Ultra Ball found was promoted later, so it was benched). Inferred actions are replayed but not
    scored. Keep them to what is needed.
  - `t`: the caption timestamp; `note`: anything worth knowing.
- Cards put onto the Bench by the card itself (Buddy-Buddy Poffin, Telepathic Psychic Energy) need no
  `bench` action; cards searched into the hand (Ultra Ball, Cyrano, Poké Pad, Dawn, Bug Catching
  Set, Night Stretcher) need one when they are benched.
- Abilities that trigger when a card is played (Meowth ex Last-Ditch Catch, Iron Leaves ex Rapid
  Vernier, Alakazam Psychic Draw): put their answers in that `bench`/`evolve` action's `choices`;
  without choices a "you may" is answered no.
- Cards a search names in `choices` (Ultra Ball's target, Buddy-Buddy Poffin's Basics, Poké Pad,
  Cyrano, Meowth ex's Supporter) are moved into the deck before the search if the random deal put
  them in the prizes or hand.
- "Up to" prompts with no `choices` take some cards at random; give `["nothing"]` when nothing was
  taken or discarded (e.g. Eri).
- Coin flips: give the results the commentators say as `"flips": ["heads", "tails"]` on the action
  (Crushing Hammer, Tumbling Attack, Mimikyu); otherwise they are left to chance and the replay may
  differ from the real game.
- Two different printings with one name (`--cards` shows them as `Applin [Applin TWM2]`): give the
  bracketed engine full name as the card (`"card": "Applin TWM2"`) when it matters which one.
- Damage-counter prompts (Phantom Dive, Cursed Blast) are labelled like `60 on opp bench1 Slowpoke`;
  a choice naming the Pokémon (`["Slowpoke"]`) or the slot (`["bench1 Slowpoke"]`) picks it.
- Rare Candy: `"uses": ["<Stage 2>"]`, choices with the Stage 2 first, then the Basic it goes on.
- Captions translated from another language (Spanish streams) are usually too loose to log; skip
  them unless the openings and turns are clear.

## What makes a good log

- Log what the commentators narrate, in their order. Stop the log (or skip a game) when the
  narration loses track: a partial game with every action right is worth more than a full game
  with guesses. Say where and why in `notes`.
- Prefer actions they state; add inferred ones only to make the stated ones possible.
- One game per file; skip games whose opening board or decks cannot be told.
