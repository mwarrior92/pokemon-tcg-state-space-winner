// Per-seat switches, for playing a pilot against itself with some of its parts turned off.
//
// A seat named "<pilot>@a,b" is <pilot> with the parts a and b off (playgame.ts sets the switches
// before each turn; games run one turn at a time, so one global set is enough). Parts:
//   handneed  cards in hand count by need, the deck's top two cards count (planner.ts material)
//   supply    attacks the deck's Energy can hardly pay for count less (need.ts costSupply)
//   targets   Energy attachments and moves are tried best target first (prompts.ts Guide.attach)
//   inplay    Tools attached and the player's own Stadium count as material; the first Pokémon in
//             play count more; an Evolution in hand with a Pokémon to go on counts more than a spare Basic
//   clock     the mover's turns to the win along its shortest likely path (clock.ts) take the place
//             of the race's next-turn term
//   handsize  each of the first few cards in hand counts more, so emptying the hand has a price
//             (planner.ts material)
//   benchpos  the clock counts the Energy the Active lacks to retreat for a path on a Benched Pokémon
//   copy      the clock follows attacks that are another card's attack (Seek Inspiration by the best
//             cards that can be put on top of the deck, Night Joker by the N's Pokémon in play or to
//             come), attacks that damage several Pokémon, and counts an attack that discards all its
//             Energy or cannot be used the next turn as used every second turn
//   norepeat  the imitation steps skip a step that leads back to a position of the same turn (an
//             Ability used and its choice cancelled: Memory Helix, Teal Dance with nothing to attach)
// cli/pilotaudit.ts --versus plays the two against each other.
//
// Measured that way (180 games each, runs/vs-*): inplay won 58% and handneed 56% of the games
// against the pilot without them; supply won 48% and targets 49%, so those two are off unless
// SIM_PARTS names them (SIM_PARTS=supply,targets). clock won 395 of 720 = 55% (51% to 59%;
// runs/vs-clock4, 4b, 4c, 4d; same-seed pairs 83 against 48) and is on.
// handsize won 91 of 180 at "3,0.04" and 90 of 180 at "4,0.03" (runs/vs-hand-a, vs-hand-b; over 80 of
// 90 same-seed pairs split): no difference, so it is off unless SIM_PARTS names it.
// benchpos won 178 of 359 (runs/vs-benchpos, vs-benchpos-b): Hydrapple, N's Zoroark and Slowking attacked
// 0.3 to 1.3 turns earlier, Dragapult Blaziken 0.3 (reviews/pilot-clock.md, correction); off as well.
// copy won 95 of 180 over all decks (runs/vs-copy), 38 of 72 in games with Slowking and 43 of 72 in
// games with N's Zoroark (runs/vs-copy-sk, vs-copy-nz): 176 of 324 = 54%, same-seed pairs 25 against
// 11. N's Zoroark itself won 27 of 54 with it against 18 of 54 without (prizes a turn 0.58 against
// 0.43), Slowking 18 of 54 against 14 of 54; on.
// norepeat won 72 of 144 Slowking games (runs/vs-norepeat-sk), the same deck winning both games of
// every pair; a step repeated three times or more in 0 of 959 turns against 10 of 959. A plain fix; on.
const OPT_IN = new Set(['supply', 'targets', 'handsize', 'benchpos']);
const enabled = new Set((process.env.SIM_PARTS ?? '').split(',').filter(Boolean));
let off = new Set<string>();

export function setVariant(list: string): void {
  off = new Set(list ? list.split(',').filter(Boolean) : []);
}

/** turn an opt-in part on or off for this process (tests) */
export function optIn(part: string, yes: boolean): void {
  if (yes) {
    enabled.add(part);
  } else {
    enabled.delete(part);
  }
}

export const on = (part: string): boolean => !off.has(part) && (!OPT_IN.has(part) || enabled.has(part));

/** "<pilot>@a,b" -> ["<pilot>", "a,b"] */
export function splitSeat(seat: string): [string, string] {
  const i = seat.lastIndexOf('@');
  return i < 0 ? [seat, ''] : [seat.slice(0, i), seat.slice(i + 1)];
}
