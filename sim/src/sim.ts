// Headless game wrapper around the Twinleaf Store: seeded chance (shuffles, coin flips), automatic
// handling of no-choice prompts, legal-action enumeration and cheap copies at settled points.
import {
  CoinFlipPrompt,
  Action, AddPlayerAction, AttackAction, Card, CardTarget, EnergyCard, GameError, GamePhase, GameSettings, PassTurnAction,
  PlayCardAction, Player, PlayerType, PokemonCard, PokemonCardList, Prompt, ResolvePromptAction, RetreatAction,
  SlotType, State, Store, StoreHandler, TrainerCard, TrainerType, UseAbilityAction, UseStadiumAction, StateUtils,
} from './engine';
import { deepCopy } from './clone';
import { chanceResult, decodeValid, isChancePrompt, promptOptions } from './prompts';
import { Rng } from './rng';

// UI-only bookkeeping in the engine (see engine/twinleaf/UPSTREAM.md, patch 002)
Store.computePlayability = false;
// Every dispatch happens on a disposable copy that is dropped when the engine rejects the action,
// so the engine's per-action rollback backup is unnecessary (patch 004).
Store.backupOnReduce = false;
// patch 015: no wall-clock timestamps on engine log entries
Store.logTimestamps = false;

export class Sim implements StoreHandler {
  store: Store;
  rng: Rng;
  /** every action / prompt answer applied, for logs */
  trace: string[] = [];
  /** engine log entries, kept only when keepEngineLog is set; the engine's own state.logs is
   *  drained after every step so copies stay small */
  engineLog: { message: string; params: any; turn: number }[] = [];
  keepEngineLog = false;
  /** Fixed hidden information. When set, every card has a random rank that depends only on this
   *  seed, the turn number and the card, and every deck shuffle puts the deck in rank order. So
   *  within a turn, the same cards in a deck always shuffle (and then draw) the same way, whatever
   *  order the turn's actions came in: a search cannot see different hidden cards on different
   *  lines, and orderings of the same plays merge into one position. A new turn gives new ranks.
   *  Set by determinize(); copies keep it. */
  chanceSeed?: number;
  /** results of the next coin flips (true = heads), used before chance (replays of real games) */
  forcedFlips?: boolean[];

  constructor(state: State | undefined, rng: Rng) {
    this.rng = rng;
    this.store = new Store(this);
    if (state) {
      this.store.state = state;
    }
  }

  get state(): State {
    return this.store.state;
  }

  onStateChange(_state: State): void { /* driven synchronously by dispatch() */ }

  static newGame(deckA: string[], deckB: string[], rng: Rng, settings?: Partial<GameSettings>): Sim {
    const sim = new Sim(undefined, rng);
    const gs = Object.assign(new GameSettings(), settings ?? {});
    sim.state.gameSettings = gs;
    sim.state.rules = gs.rules;
    sim.apply(new AddPlayerAction(1, 'A', deckA));
    sim.apply(new AddPlayerAction(2, 'B', deckB));
    return sim;
  }

  /** Independent copy. Only valid when no decision prompt is pending (prompt continuations are
   *  closures inside the Store and cannot be copied). */
  copy(rng?: Rng): Sim {
    if (this.pendingPrompt()) {
      throw new Error('copy() with a pending prompt');
    }
    const s = new Sim(deepCopy(this.state), rng ?? this.rng.fork());
    s.trace = this.trace.slice();
    s.keepEngineLog = this.keepEngineLog;
    s.chanceSeed = this.chanceSeed;
    s.forcedFlips = this.forcedFlips?.slice();
    if (this.keepEngineLog) {
      s.engineLog = this.engineLog.slice();
    }
    return s;
  }

  /** Apply an action, then answer chance / no-choice prompts until a decision is needed. */
  apply(action: Action, label?: string): void {
    this.store.dispatch(action);
    if (label) {
      this.trace.push(label);
    }
    this.settle();
  }

  private drainLogs(): void {
    const logs = this.state.logs;
    if (logs.length) {
      if (this.keepEngineLog) {
        for (const l of logs) {
          this.engineLog.push({ message: String(l.message), params: l.params, turn: this.state.turn });
        }
      }
      this.state.logs = [];
    }
    // resolved prompts stay in state.prompts upstream (the web client shows them); once nothing is
    // pending they are dead weight that every copy would carry
    const ps = this.state.prompts;
    if (ps.length && ps.every(p => p.result !== undefined)) {
      this.state.prompts = [];
    }
  }

  /** the card rank for this turn under chanceSeed (undefined: shuffles are random) */
  rank(): ((c: Card) => number) | undefined {
    if (this.chanceSeed === undefined) {
      return undefined;
    }
    const s = mix32(this.chanceSeed ^ Math.imul(this.state.turn + 1, 0x9e3779b1));
    return (c: Card) => mix32(s ^ Math.imul(c.id + 1, 0x85ebca6b));
  }

  settle(): void {
    for (let guard = 0; guard < 500; guard++) {
      const p = this.state.prompts.find(x => x.result === undefined);
      if (!p || !isChancePrompt(p)) {
        this.drainLogs();
        return;
      }
      // coin flips a replayed real game says the result of (matchlog.ts), in order
      const raw = this.forcedFlips?.length && p instanceof CoinFlipPrompt ? this.forcedFlips.shift()! : chanceResult(p, this.state, this.rng, this.rank());
      const v = decodeValid(p, this.state, raw);
      this.store.dispatch(new ResolvePromptAction(p.id, v ? v.decoded : raw));
    }
    throw new Error('settle(): too many chance prompts');
  }

  pendingPrompt(): Prompt<any> | undefined {
    return this.state.prompts.find(x => x.result === undefined);
  }

  answer(p: Prompt<any>, decoded: any, label?: string): void {
    this.store.dispatch(new ResolvePromptAction(p.id, decoded));
    if (label) {
      this.trace.push(label);
    }
    this.settle();
  }

  get finished(): boolean {
    return this.state.phase === GamePhase.FINISHED;
  }

  /** index of the player who must act now (prompt owner, else the active player) */
  actor(): number {
    const p = this.pendingPrompt();
    const id = p ? p.playerId : this.state.players[this.state.activePlayer].id;
    return this.state.players.findIndex(x => x.id === id);
  }

  playerIndex(id: number): number {
    return this.state.players.findIndex(x => x.id === id);
  }
}

export interface MainOption {
  action: Action;
  label: string;
  kind: 'play' | 'attach' | 'evolve' | 'bench' | 'tool' | 'stadium' | 'ability' | 'retreat' | 'attack' | 'pass';
}

function slotTarget(i: number | 'active'): CardTarget {
  return i === 'active'
    ? { player: PlayerType.BOTTOM_PLAYER, slot: SlotType.ACTIVE, index: 0 }
    : { player: PlayerType.BOTTOM_PLAYER, slot: SlotType.BENCH, index: i };
}

function inPlay(p: Player): { list: PokemonCardList; t: CardTarget; name: string }[] {
  const out: { list: PokemonCardList; t: CardTarget; name: string }[] = [];
  if (p.active.cards.length) {
    out.push({ list: p.active, t: slotTarget('active'), name: 'active ' + (p.active.getPokemonCard()?.name ?? '?') });
  }
  p.bench.forEach((b, i) => {
    if (b.cards.length) {
      out.push({ list: b, t: slotTarget(i), name: `bench${i} ` + (b.getPokemonCard()?.name ?? '?') });
    }
  });
  return out;
}

/** Candidate main-phase actions for the active player (not yet checked against the rules; use
 *  legalMainOptions for that). Identical hand cards produce one candidate each. */
export function mainCandidates(state: State): MainOption[] {
  const me = state.players[state.activePlayer];
  const id = me.id;
  const out: MainOption[] = [];
  const mine = inPlay(me);
  const emptyBench = me.bench.findIndex(b => b.cards.length === 0);
  const seenHand = new Set<string>();
  // once-per-turn rules the engine would reject anyway (cheap pre-filter; the engine still decides)
  const energyDone = me.energyPlayedTurn === state.turn && !state.rules.unlimitedEnergyAttachments && !(me as any).usedDragonsWish;
  // the engine and ~420 Supporter cards check supporterTurn; many Supporters leave the Supporter
  // zone right after resolving, so the zone alone misses them
  const supporterDone = me.supporter.cards.length > 0 || me.supporterTurn > 0;
  const retreatDone = me.retreatedTurn === state.turn;

  me.hand.cards.forEach((c: Card, hi: number) => {
    if (seenHand.has(c.fullName)) {
      return;
    }
    seenHand.add(c.fullName);
    if (c instanceof EnergyCard) {
      for (const s of energyDone ? [] : mine) {
        out.push({ action: new PlayCardAction(id, hi, s.t), label: `attach ${c.name} -> ${s.name}`, kind: 'attach' });
      }
    } else if (c instanceof PokemonCard) {
      if (emptyBench !== -1) {
        out.push({ action: new PlayCardAction(id, hi, slotTarget(emptyBench)), label: `bench ${c.name}`, kind: 'bench' });
      }
      for (const s of mine) {
        if (c.evolvesFrom && s.list.getPokemonCard()?.name === c.evolvesFrom) {
          out.push({ action: new PlayCardAction(id, hi, s.t), label: `evolve ${s.name} -> ${c.name}`, kind: 'evolve' });
        } else if (c.evolvesFrom || (c as any).evolvesFromBase?.length) {
          // unusual evolution rules (e.g. evolving from several names) - let the engine decide
          if (s.list.getPokemonCard() && (c as any).evolvesFromBase?.includes?.(s.list.getPokemonCard()!.name)) {
            out.push({ action: new PlayCardAction(id, hi, s.t), label: `evolve ${s.name} -> ${c.name}`, kind: 'evolve' });
          }
        }
      }
    } else if (c instanceof TrainerCard) {
      if (c.trainerType === TrainerType.TOOL) {
        for (const s of mine) {
          out.push({ action: new PlayCardAction(id, hi, s.t), label: `tool ${c.name} -> ${s.name}`, kind: 'tool' });
        }
      } else {
        if (c.trainerType === TrainerType.SUPPORTER && supporterDone) {
          return;
        }
        const kind = c.trainerType === TrainerType.STADIUM ? 'stadium' : 'play';
        out.push({ action: new PlayCardAction(id, hi, slotTarget('active')), label: `play ${c.name}`, kind });
      }
    }
  });

  for (const s of mine) {
    const pc = s.list.getPokemonCard();
    for (const pw of pc?.powers ?? []) {
      out.push({ action: new UseAbilityAction(id, pw.name, s.t), label: `ability ${pw.name} (${s.name})`, kind: 'ability' });
    }
  }
  if (StateUtils.getStadiumCard(state)) {
    out.push({ action: new UseStadiumAction(id), label: `use stadium ${StateUtils.getStadiumCard(state)!.name}`, kind: 'stadium' });
  }
  me.bench.forEach((b, i) => {
    if (b.cards.length && !retreatDone) {
      out.push({ action: new RetreatAction(id, i), label: `retreat to bench${i} ${b.getPokemonCard()?.name}`, kind: 'retreat' });
    }
  });
  const act = me.active.getPokemonCard();
  const attacks = new Set<string>();
  for (const a of act?.attacks ?? []) {
    attacks.add(a.name);
  }
  // attacks granted by tools / other cards are listed by the engine on the card list
  for (const a of (me.active as any).getAttacks?.() ?? []) {
    attacks.add(a.name);
  }
  for (const a of attacks) {
    out.push({ action: new AttackAction(id, a), label: `attack ${a}`, kind: 'attack' });
  }
  out.push({ action: new PassTurnAction(id), label: 'end turn', kind: 'pass' });
  return out;
}

/** Main-phase options that the engine accepts from this state. Each candidate is dispatched on a
 *  scratch copy; a rejected action is rolled back by the engine itself (Store.reduce restores its
 *  backup on GameError), so a fresh copy is only needed after an accepted one. */
export function legalMainOptions(sim: Sim): MainOption[] {
  const ok: MainOption[] = [];
  let scratch: Sim | undefined;
  for (const o of mainCandidates(sim.state)) {
    if (o.kind === 'pass') {
      ok.push(o);
      continue;
    }
    scratch = scratch ?? sim.copy(new Rng(1));
    try {
      scratch.apply(o.action);
      ok.push(o);
      scratch = undefined;
    } catch (e) {
      if (!(e instanceof GameError)) {
        // engine bug on an otherwise-plausible action: treat as illegal, but keep a record
        recordBug(o.label, String((e as Error)?.stack ?? e).split('\n').slice(0, 3).join(' | '));
        scratch = undefined;
      } else {
        // with the engine's rollback off (patch 004) a rejected action may leave partial changes
        scratch = undefined;
      }
    }
  }
  return ok;
}

/** engine exceptions on candidate actions: the first 500 are kept, all are counted (a long run
 *  must not grow this without bound) */
export function mix32(x: number): number {
  x = Math.imul(x ^ (x >>> 16), 0x7feb352d);
  x = Math.imul(x ^ (x >>> 15), 0x846ca68b);
  return (x ^ (x >>> 16)) >>> 0;
}

/** Fix the hidden information of a position (see Sim.chanceSeed): both decks are put in rank order
 *  now (a shuffle of a face-down deck) and every later shuffle follows the same ranks. */
export function determinize(sim: Sim, seed: number): void {
  sim.chanceSeed = seed >>> 0;
  const rank = sim.rank()!;
  for (const p of sim.state.players) {
    p.deck.cards.sort((a, b) => rank(a) - rank(b));
  }
}

export const bugLog: { label: string; error: string }[] = [];
export const bugStats = { count: 0 };
function recordBug(label: string, error: string): void {
  bugStats.count++;
  if (bugLog.length < 500) {
    bugLog.push({ label, error });
  }
}

export { promptOptions };

/** Picks one of the valid options for a decision prompt (index into opts). */
export type PromptChooser = (sim: Sim, p: Prompt<any>, opts: ReturnType<typeof promptOptions>) => number;

export const randomChooser = (rng: Rng): PromptChooser => (_sim, _p, opts) => Math.floor(rng.next() * opts.length);

export class DeadEnd extends Error {}

/** Answer decision prompts until the game settles. Throws DeadEnd when a prompt has no valid
 *  answer (an engine card bug, or an earlier answer that left nothing legal to pick). */
export function resolvePrompts(sim: Sim, choose: PromptChooser, rng: Rng, cap = 24): void {
  for (let guard = 0; guard < 400; guard++) {
    const p = sim.pendingPrompt();
    if (!p || sim.finished) {
      return;
    }
    const opts = promptOptions(p, sim.state, rng, cap);
    if (opts.length === 0) {
      throw new DeadEnd(`no valid answer for "${p.type}" (${(p as any).message}): ${describePrompt(p)}`);
    }
    const o = opts[choose(sim, p, opts)];
    const who = sim.playerIndex(p.playerId);
    sim.answer(p, o.decoded, `  P${who + 1} ${p.type}: ${o.label}`);
  }
  throw new DeadEnd('prompt loop did not settle');
}

export function describePrompt(p: Prompt<any>): string {
  return JSON.stringify(p, (k, v) => (k === 'sourceCard' || (k === 'player' && v && typeof v === 'object')) ? undefined
    : (v && typeof v === 'object' && 'fullName' in v && 'superType' in v) ? `<${v.fullName}>` : v).slice(0, 700);
}

export interface StepResult {
  sim?: Sim;
  deadEnds: string[];
}

/** One macro step: a main action plus every prompt it raises, on a copy of `sim`. Dead ends are
 *  retried with fresh prompt answers; after `attempts` failures the action counts as unplayable. */
export function runStep(sim: Sim, o: MainOption, choose: PromptChooser, rng: Rng, attempts = 3): StepResult {
  const deadEnds: string[] = [];
  for (let a = 0; a < attempts; a++) {
    const t = sim.copy(rng.fork());
    try {
      t.apply(o.action, `P${t.state.activePlayer + 1} T${t.state.turn}: ${o.label}`);
      resolvePrompts(t, choose, rng);
      return { sim: t, deadEnds };
    } catch (e) {
      if (e instanceof DeadEnd) {
        deadEnds.push(`${o.label}: ${e.message}`);
        continue;
      }
      if (e instanceof GameError) {
        deadEnds.push(`${o.label}: rejected after prompts (${(e as Error).message})`);
        return { deadEnds };
      }
      // an exception inside card code: an engine bug. The copy is discarded, so the game is safe.
      const where = String((e as Error)?.stack ?? e).split('\n').slice(0, 3).join(' | ');
      recordBug(o.label, where);
      deadEnds.push(`${o.label}: ENGINE BUG ${where}`);
      continue;
    }
  }
  return { deadEnds };
}
