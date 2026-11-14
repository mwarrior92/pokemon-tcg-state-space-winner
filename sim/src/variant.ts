// Per-seat switches, for playing a pilot against itself with some of its parts turned off.
//
// A seat named "<pilot>@a,b" is <pilot> with the parts a and b off (playgame.ts sets the switches
// before each turn; games run one turn at a time, so one global set is enough). Parts:
//   handneed  cards in hand count by need, the deck's top two cards count (planner.ts material)
//   supply    attacks the deck's Energy can hardly pay for count less (need.ts costSupply)
//   targets   Energy attachments and moves are tried best target first (prompts.ts Guide.attach)
//   inplay    Tools attached and the player's own Stadium count as material; the first Pokémon in
//             play count more; an Evolution in hand with a Pokémon to go on counts more than a spare Basic
// cli/pilotaudit.ts --versus plays the two against each other.
//
// Measured that way (180 games each, runs/vs-*): inplay won 58% and handneed 56% of the games
// against the pilot without them; supply won 48% and targets 49%, so those two are off unless
// SIM_PARTS names them (SIM_PARTS=supply,targets).
const OPT_IN = new Set(['supply', 'targets']);
const enabled = new Set((process.env.SIM_PARTS ?? '').split(',').filter(Boolean));
let off = new Set<string>();

export function setVariant(list: string): void {
  off = new Set(list ? list.split(',').filter(Boolean) : []);
}

export const on = (part: string): boolean => !off.has(part) && (!OPT_IN.has(part) || enabled.has(part));

/** "<pilot>@a,b" -> ["<pilot>", "a,b"] */
export function splitSeat(seat: string): [string, string] {
  const i = seat.lastIndexOf('@');
  return i < 0 ? [seat, ''] : [seat.slice(0, i), seat.slice(i + 1)];
}
