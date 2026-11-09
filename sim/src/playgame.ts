// One game played to the end by turn policies, for playouts (cli/playout.ts) and deck testing
// (cli/deckbuilder.ts).
//
// A game starts either from a generated mid-game state (stategen) or from a real game set-up:
// shuffled decks, opening hands, mulligans, Active and Bench chosen, then turn 1. Set-up choices
// and the opponent's prompts during a turn (e.g. a new Active after a Knock Out) are answered at
// random - a known limit.
//
// Seat policies:
//   v0        offense search policy; if it finds no prize, the defense policy
//   race      v1: one-turn planner on the two-turn prize race (offense + defense models)
//   race2     v2: the prize race tested against sampled opponent replies (disruption-aware)
//   plan:F    one-turn planner on the win model in file F
//   plan2:F   the win model tested against sampled replies
import { categorize } from './categories';
import { describeState } from './describe';
import { CHEAP_GROUPS, features } from './features';
import { GamePhase, GameWinner, PassTurnAction } from './engine';
import { LinearModel, loadModel } from './model';
import { playDefense, playOffenseSearch } from './policy';
import { planTurn, planTurn2, raceEvaluator } from './planner';
import { prizesLeft } from './rules';
import { Rng } from './rng';
import { Sim, randomChooser, resolvePrompts } from './sim';
import { generateState } from './stategen';
import { WinModel } from './value';

export interface GameSpec {
  seed: number;
  decks: [string[], string[]];    // engine card full names, 60 each
  names: [string, string];        // deck names for the record
  start: 'generated' | 'full';
  offense: string;                // offense model file
  defense?: string;               // defense model file
  budget: number;
  maxTurns: number;
  seats: [string, string];        // policy of player 1 and player 2
  vectors?: boolean;              // record the cheap feature vector at every turn start
  log?: 'board' | 'lines';        // record each turn's moves (and the board before it)
}

export interface TurnRec {
  turn: number;
  mover: number;
  cat: string;
  prizes: [number, number];
  took: number;
  policy: 'offense' | 'defense' | 'plan' | 'pass';
  ms: number;
  x?: number[];
  board?: string;
  line?: string[];
}

export interface GameRec {
  seed: number;
  decks: [string, string];
  seats: [string, string];
  startTurn: number;
  turns: TurnRec[];
  winner: number;                 // 0 / 1, 2 = draw, -1 = undecided
  reason: string;
  ms: number;
  first?: number;                 // who took the first turn (full games)
}

const wins = new Map<string, WinModel>();
const winModel = (f: string) => {
  let w = wins.get(f);
  if (!w) {
    w = new WinModel(loadModel(f));
    wins.set(f, w);
  }
  return w;
};
const models = new Map<string, LinearModel>();
const model = (f: string) => {
  let m = models.get(f);
  if (!m) {
    m = loadModel(f);
    models.set(f, m);
  }
  return m;
};

/** End the turn in place (the engine runs the turn change); prompts that come up are answered at
 *  random. */
function passInPlace(sim: Sim, rng: Rng): boolean {
  try {
    if (!sim.finished && sim.state.phase === GamePhase.PLAYER_TURN) {
      sim.apply(new PassTurnAction(sim.state.players[sim.state.activePlayer].id));
    }
    resolvePrompts(sim, randomChooser(rng), rng);
    return true;
  } catch {
    return false;
  }
}

/** A real game start: set-up resolved, the first player to move at turn 1. */
export function newGameStart(deckA: string[], deckB: string[], seed: number): Sim {
  const rng = new Rng(seed);
  const sim = Sim.newGame(deckA, deckB, rng);
  resolvePrompts(sim, randomChooser(rng), rng);
  // fixed hidden information within each turn, as in generated states (shuffles follow card
  // ranks that change every turn); the deck's current order is kept
  sim.chanceSeed = (seed * 2654435761) >>> 0;
  return sim;
}

/** Play the turn with the seat's policy; returns the position after the turn's line (not yet
 *  passed unless the line ended the turn) and the line. */
function playTurn(sim: Sim, seat: string, spec: GameSpec, t: number, off: LinearModel, def: LinearModel | undefined): { next: Sim; line: string[]; policy: TurnRec['policy'] } {
  const mover = sim.state.activePlayer;
  const seed = spec.seed + t;
  const tactical = () => {
    const o = playOffenseSearch(sim, off, { budget: spec.budget, maxMs: 3000 });
    return { o, extra: [{ sim: o.end, line: o.line, ended: o.end.finished || o.end.state.activePlayer !== mover }] };
  };
  if (seat.startsWith('plan:')) {
    const pl = planTurn(sim, winModel(seat.slice(5)), { budget: spec.budget, maxMs: 4000, seed, extra: tactical().extra });
    return { next: pl.end, line: pl.line, policy: 'plan' };
  }
  if (seat === 'race' && def) {
    const pl = planTurn(sim, raceEvaluator(off, def, 0.8, seed), { budget: spec.budget, maxMs: 4000, seed, extra: tactical().extra });
    return { next: pl.end, line: pl.line, policy: 'plan' };
  }
  if (seat === 'race2' && def) {
    const pl = planTurn2(sim, raceEvaluator(off, def, 0.8, seed), { budget: spec.budget, maxMs: 4000, seed, extra: tactical().extra, candidates: 5, replies: 6, replyBudget: 40, risk: 0.25 });
    return { next: pl.end, line: pl.line, policy: 'plan' };
  }
  if (seat.startsWith('plan2:')) {
    const pl = planTurn2(sim, winModel(seat.slice(6)), { budget: spec.budget, maxMs: 4000, seed, extra: tactical().extra, candidates: 5, replies: 6, replyBudget: 40, risk: 0.25 });
    return { next: pl.end, line: pl.line, policy: 'plan' };
  }
  const { o } = tactical();
  if (o.prizes > 0 || !def) {
    return { next: o.end, line: o.line, policy: 'offense' };
  }
  const d = playDefense(sim, def, seed);
  return { next: d.end, line: d.line, policy: 'defense' };
}

export function playGame(spec: GameSpec): GameRec {
  const t0 = Date.now();
  let sim: Sim;
  let startTurn: number;
  if (spec.start === 'full') {
    sim = newGameStart(spec.decks[0], spec.decks[1], spec.seed);
    startTurn = sim.state.turn;
  } else {
    const g = generateState(spec.decks[0], spec.decks[1], new Rng(spec.seed));
    sim = g.sim;
    startTurn = g.info.turn;
  }
  const first = sim.state.activePlayer;
  const rng = new Rng(spec.seed * 31 + 7);
  const off = model(spec.offense);
  const def = spec.defense ? model(spec.defense) : undefined;
  const turns: TurnRec[] = [];
  let reason = 'turn limit';
  for (let t = 0; t < spec.maxTurns && !sim.finished; t++) {
    const ts = Date.now();
    const mover = sim.state.activePlayer;
    const cat = categorize(sim, mover).key;
    // the cheap feature vector from the mover's side
    const x = spec.vectors ? features(sim, mover, CHEAP_GROUPS).values.map(v => Math.round(v * 100) / 100) : undefined;
    const before = prizesLeft(sim.state.players[mover]);
    const prizes: [number, number] = [prizesLeft(sim.state.players[0]), prizesLeft(sim.state.players[1])];
    const board = spec.log === 'board' ? describeState(sim.state) : undefined;
    let r: { next: Sim; line: string[]; policy: TurnRec['policy'] };
    try {
      r = playTurn(sim, spec.seats[mover], spec, t, off, def);
    } catch {
      r = { next: sim.copy(rng.fork()), line: ['(policy failed: pass)'], policy: 'pass' };
    }
    sim = r.next;
    // pass only if the line did not end the turn itself (an attack ends it)
    if (!sim.finished && sim.state.activePlayer === mover && !passInPlace(sim, rng)) {
      reason = 'engine error';
      break;
    }
    turns.push({
      turn: sim.state.turn, mover, cat, prizes, took: before - prizesLeft(sim.state.players[mover]), policy: r.policy, ms: Date.now() - ts,
      x, board, line: spec.log ? r.line : undefined,
    });
  }
  let winner = -1;
  if (sim.finished) {
    winner = sim.state.winner === GameWinner.PLAYER_1 ? 0 : sim.state.winner === GameWinner.PLAYER_2 ? 1 : sim.state.winner === GameWinner.DRAW ? 2 : -1;
    const w = winner === 0 || winner === 1 ? sim.state.players[winner] : undefined;
    // the loser ran out of cards to draw, or had no Pokémon left in play
    const loser = winner === 0 || winner === 1 ? sim.state.players[1 - winner] : undefined;
    const noPokemon = loser && ![loser.active, ...loser.bench].some(l => l.cards.length);
    reason = w && prizesLeft(w) === 0 ? 'prizes' : winner === 2 ? 'draw' : noPokemon ? 'no Pokémon in play' : loser && loser.deck.cards.length === 0 ? 'deck out' : 'other';
  }
  return { seed: spec.seed, decks: spec.names, seats: spec.seats, startTurn, turns, winner, reason, ms: Date.now() - t0, first };
}
