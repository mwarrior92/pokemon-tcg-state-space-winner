// Deck diagnosis: why a deck's turns went nowhere and how it lost, as flags the deck search can act
// on (cli/deckbuilder.ts, deckgen.ts fixIssue). Rules facts only, read off the position after the
// pilot's turn; cheap enough to record on every turn of every search game (GameSpec.diagnose).
//
// Flags on a turn of the deck (shares are of its own turns):
//   noEnergy      no attack, nothing in play can pay for one, no Energy attached from hand this turn
//                 and none in hand
//   slowEnergy    no attack and nothing in play can pay for one, although an Energy was attached
//   activeStuck   no attack: a Benched Pokémon could pay for one, the Active could not
//   deadHand      nothing played, put down, evolved or used but an Energy / a retreat, and no prize
//   emptyBench    the turn ended with no Benched Pokémon
// (No attack flag on the first turn of the game, when attacking is not allowed, nor when the Active
// could have attacked: that is the pilot's choice, not the deck's lack.)
// Flags on a lost game (shares are of the deck's decided games):
//   boardWipe     lost with no Pokémon left in play
//   deckOut       lost with no card left to draw
//   prizes        the opponent took all its prize cards (no card change is tied to this one)
import { Card, EnergyCard, PokemonCard, Stage, TrainerCard } from './engine';
import { isBasicEnergy } from './decklist';
import { ACCEL_TEXT, SWITCH_TEXT, energyGap } from './features';
import { prizesLeft } from './rules';
import { Sim } from './sim';
import type { GameRec } from './playgame';

export const ISSUE_TEXT = {
  noEnergy: 'could not attack, no Energy to attach',
  slowEnergy: 'could not attack, Energy attached but no attack paid for yet',
  activeStuck: 'could not attack, a Benched Pokémon was ready and the Active was not',
  deadHand: 'dead hand (nothing to play)',
  emptyBench: 'no Benched Pokémon at the end of the turn',
  boardWipe: 'lost with no Pokémon left in play',
  deckOut: 'lost by running out of cards',
  prizes: 'lost on prize cards',
} as const;
export type Issue = keyof typeof ISSUE_TEXT;
const TURN_ISSUES: Issue[] = ['noEnergy', 'slowEnergy', 'activeStuck', 'deadHand', 'emptyBench'];
const LOSS_OF: Record<string, Issue> = { 'no Pokémon in play': 'boardWipe', 'deck out': 'deckOut', prizes: 'prizes' };

/** `before`: the position at the start of the turn; `after`: after the pilot's line; `line`: its steps */
export function turnIssues(before: Sim, after: Sim, line: string[], mover: number): Issue[] {
  const p = after.state.players[mover];
  const out: Issue[] = [];
  const inPlay = [p.active, ...p.bench].filter(l => l.cards.length);
  if (!inPlay.length) {
    return out;
  }
  const attacked = line.some(l => l.startsWith('attack '));
  const canPay = (l: typeof p.active) => (l.getPokemonCard()?.attacks ?? []).some(a => energyGap(a.cost, l) === 0);
  if (!attacked && before.state.turn > 1 && !canPay(p.active)) {
    if (p.bench.some(l => l.cards.length && canPay(l))) {
      out.push('activeStuck');
    } else if (line.some(l => l.startsWith('attach '))) {
      out.push('slowEnergy');
    } else if (!p.hand.cards.some(c => c instanceof EnergyCard)) {
      out.push('noEnergy');
    }
  }
  const took = prizesLeft(before.state.players[mover]) - prizesLeft(p);
  if (took <= 0 && !line.some(l => /^(play|bench|evolve|tool|ability|use stadium) /.test(l))) {
    out.push('deadHand');
  }
  if (!p.bench.some(l => l.cards.length)) {
    out.push('emptyBench');
  }
  return out;
}

export interface Diagnosis {
  games: number;                  // decided games
  lost: number;
  turns: number;                  // own turns with flags recorded
  /** most flagged first; share of own turns (turn flags) or of decided games (loss flags) */
  issues: { issue: Issue; n: number; share: number }[];
  /** prizes the deck had taken, on average, in the games it lost on prize cards */
  prizesTakenInPrizeLosses: number;
}

export function diagnose(name: string, games: GameRec[]): Diagnosis {
  const n = new Map<Issue, number>();
  const bump = (i: Issue) => n.set(i, (n.get(i) ?? 0) + 1);
  let turns = 0, decided = 0, lost = 0, prizeLosses = 0, taken = 0;
  for (const g of games) {
    if (g.winner !== 0 && g.winner !== 1) {
      continue;
    }
    decided++;
    const me = g.decks[0] === name ? 0 : 1;
    const own = g.turns.filter(t => t.mover === me);
    own.forEach(t => {
      if (t.issues) {
        turns++;
        t.issues.forEach(i => bump(i as Issue));
      }
    });
    if (g.winner !== me) {
      lost++;
      const mode = LOSS_OF[g.reason];
      if (mode) {
        bump(mode);
      }
      if (mode === 'prizes') {
        prizeLosses++;
        taken += own.reduce((s, t) => s + t.took, 0);
      }
    }
  }
  const issues = [...n].map(([issue, k]) => ({ issue, n: k, share: k / Math.max(1, TURN_ISSUES.includes(issue) ? turns : decided) }))
    .sort((a, b) => b.share - a.share);
  return { games: decided, lost, turns, issues, prizesTakenInPrizeLosses: prizeLosses ? taken / prizeLosses : 0 };
}

const pct = (x: number) => `${(100 * x).toFixed(0)}%`;

/** "could not attack, no Energy to attach 31% of turns; dead hand 12% of turns; lost: ... " */
export function describeDiagnosis(d: Diagnosis, top = 99): string {
  const turn = d.issues.filter(i => TURN_ISSUES.includes(i.issue)).slice(0, top).map(i => `${ISSUE_TEXT[i.issue]} ${pct(i.share)} of turns`);
  const loss = d.issues.filter(i => !TURN_ISSUES.includes(i.issue)).map(i => `${ISSUE_TEXT[i.issue]} ${i.n}${i.issue === 'prizes' ? ` (it had taken ${d.prizesTakenInPrizeLosses.toFixed(1)} prizes itself on average)` : ''}`);
  return [turn.length ? turn.join('; ') : 'no turn flagged', `of ${d.lost} lost games: ${loss.length ? loss.join(', ') : 'none'}`].join('. ');
}

/** The flags a card change can answer, with how much each weighs when one is drawn to work on. */
export function fixable(d: Diagnosis): { issue: Issue; weight: number }[] {
  return d.issues.filter(i => i.issue !== 'prizes' && i.n >= 2).map(i => ({ issue: i.issue, weight: i.share }));
}

/** Does this card answer the flag? Read from the card's own text (a Trainer's, or an Ability's). */
export function remedies(issue: Issue, c: Card): boolean {
  const text = [c instanceof TrainerCard ? (c as { text?: string }).text ?? '' : '', ...(c instanceof PokemonCard ? c.powers.map(p => p.text ?? '') : [])].join(' ');
  switch (issue) {
    case 'noEnergy':        // more Energy, or cards that find it
      return isBasicEnergy(c) || /search your deck for [^.]{0,60}basic [^.]{0,30}energy/i.test(text) || /energy cards? from your discard pile into your hand/i.test(text);
    case 'slowEnergy':      // Energy beyond the one attachment a turn
      return ACCEL_TEXT.test(text);
    case 'activeStuck':     // switching, or a smaller Retreat Cost
      return SWITCH_TEXT.test(text) || /retreat cost[^.]{0,60}less|no retreat cost/i.test(text);
    case 'deadHand':        // cards that draw
      return /\bdraw (a card|\d+ cards|cards)/i.test(text);
    case 'emptyBench':
    case 'boardWipe':       // Basic Pokémon, or cards that find them
      return /search your deck for [^.]{0,80}basic pok[ée]mon/i.test(text) || (c instanceof PokemonCard && c.stage === Stage.BASIC);
    case 'deckOut':         // cards back into the deck
      return /shuffle [^.]{0,120}discard pile[^.]{0,60}into your deck/i.test(text);
    default:
      return false;
  }
}
