// Real games from commentated tournament matches, replayed in the engine one action at a time.
//
// A match log (sim/data/matches/*.json, written from the caption transcripts in sim/data/transcripts;
// both stay local) records one game: the two decklists, who went first, the opening Pokémon, cards
// the commentators saw in the prizes, and every turn as the list of actions taken, with the choices
// made inside them (what Ultra Ball discarded and found, the Boss's Orders target, ...).
//
// replayLog() rebuilds the game in the engine: a state before every real action. Hidden information
// is filled in so the real play is possible: the opening Pokémon are put in the opening hand, known
// prizes in the prizes, and before each action every card the player is about to play from hand -
// up to the next action that draws or searches (cards played after it may have come from it) - is
// swapped into the hand from the deck. Everything else (the rest of both hands, the prizes, the deck
// order) is random.
//
// At each state the pilot plans from there and its first action is compared with the real one. A
// later action of the same turn counts too when it is independent of the actions before it: playing
// it first and then those actions reaches the same board (checked in the engine), so the order was a
// free choice.
import * as fs from 'fs';
import * as path from 'path';
import * as fsx from 'fs';
import { REPO_ROOT, buildDeck, cardsNamed, loadMetaLists } from './cards';
import { describeState } from './describe';
import { Card, CardManager, ChooseCardsPrompt, ChoosePokemonPrompt, GameMessage, GamePhase, PokemonCard, Prompt, Stage, State, TrainerCard } from './engine';
import { decodeValid, promptOptions } from './prompts';
import { Rng } from './rng';
import { MainOption, PromptChooser, Sim, mainCandidates, runStep } from './sim';

export interface LogAction {
  do: 'bench' | 'evolve' | 'attach' | 'tool' | 'play' | 'ability' | 'retreat' | 'attack' | 'end' | 'promote' | 'concede';
  /** the card played from hand (bench, evolve, attach, tool, play); the Pokémon (ability, promote) */
  card?: string;
  /** attach / tool target, the Pokémon evolved (evolve), the Pokémon retreated into (retreat) */
  to?: string;
  /** ability or attack name */
  name?: string;
  /** other hand cards the action spends (Ultra Ball's discards, the Energy Teal Dance attaches) */
  uses?: string[];
  /** prompt answers in order, by card names ("yes" / "no" for confirmations, "*" for not known) */
  choices?: (string | string[])[];
  /** not said by the commentators, implied by what came after */
  inferred?: boolean;
  t?: string;
  note?: string;
}

export interface LogTurn {
  player: 0 | 1;
  actions: LogAction[];
  /** cards the commentators saw in the mover's hand at the start of the turn */
  hand?: string[];
  t?: string;
}

/** A player's deck: a Limitless list id (meta/decklists_*.json, meta/decklists_topcut.json). Junior and
 *  Senior players' lists are not published there: `approx` marks a stand-in (the same event's Masters
 *  list of the archetype), and `swap` replaces cards ([out, in] by name) with ones seen played. */
export interface LogDeck {
  archetype: string;
  list: string;
  approx?: boolean;
  swap?: [string, string][];
}

export interface MatchLog {
  source: string;
  event?: string;
  game: number;
  decks: [LogDeck, LogDeck];
  first: 0 | 1;
  setup: [{ active: string; bench?: string[] }, { active: string; bench?: string[] }];
  prizes?: [string[], string[]];
  turns: LogTurn[];
  result?: string;
  notes?: string;
}

export const norm = (s: string | undefined): string =>
  (s ?? '').normalize('NFD').replace(/[̀-ͯ]/g, '').replace(/[’`]/g, "'").toLowerCase().replace(/\s+/g, ' ').trim();

/** Card definitions by (normalized) name, from the decks' full names. */
function cardDefs(decks: string[][]): Map<string, Card> {
  const m = new Map<string, Card>();
  for (const fn of decks.flat()) {
    const c = CardManager.getInstance().getCardByName(fn);
    if (c && !m.has(norm(c.name))) {
      m.set(norm(c.name), c);
    }
  }
  return m;
}

let allLists: ReturnType<typeof loadMetaLists> | undefined;

export function logDecks(log: MatchLog): [string[], string[]] {
  logDecksInit();
  return log.decks.map(d => {
    const l = allLists!.find(x => x.list === d.list && x.deck === d.archetype) ?? allLists!.find(x => x.list === d.list);
    if (!l) {
      throw new Error(`decklist ${d.list} (${d.archetype}) not in the meta decklists`);
    }
    const deck = buildDeck(d.list, d.archetype, l.cards);
    const cards = deck.cards.slice();
    // cards the engine does not have: the list's most common basic Energy stands in
    if (deck.missing.length) {
      const energy = l.cards.filter(c => / Energy$/.test(c.name) && !/Special|Telepathic|Growing|Boomerang|Mist|Enriching/.test(c.name)).sort((a, b) => b.count - a.count)[0];
      const stand = energy ? cardsNamed(energy.name)[0]?.fullName : undefined;
      deck.missing.forEach(m => { for (let i = 0; i < m.count && stand; i++) { cards.push(stand); } });
    }
    for (const [out, inn] of d.swap ?? []) {
      const i = cards.findIndex(fn => norm(CardManager.getInstance().getCardByName(fn)?.name) === norm(out));
      const c = cardsNamed(inn)[0];
      if (i >= 0 && c) {
        cards[i] = c.fullName;
      }
    }
    if (cards.length !== 60) {
      throw new Error(`decklist ${d.list} has ${cards.length} cards in the engine`);
    }
    return cards;
  }) as [string[], string[]];
}

/** The hand card an action plays, if any. */
const handCard = (a: LogAction): string | undefined =>
  ['bench', 'evolve', 'attach', 'tool', 'play'].includes(a.do) ? a.card : undefined;

const DRAWS = /\bdraws?\b|search your deck|into your hand|look at the top|top \d+ cards/i;

/** Whether the action may put unknown cards into the hand (draw, search). */
function drawsCards(a: LogAction, defs: Map<string, Card>): boolean {
  const c = defs.get(norm(a.card));
  if (!c) {
    return false;
  }
  if (a.do === 'play' || a.do === 'tool') {
    return DRAWS.test((c as TrainerCard).text ?? '');
  }
  const pc = c as PokemonCard;
  if (a.do === 'ability') {
    return (pc.powers ?? []).some(p => (!a.name || norm(p.name) === norm(a.name)) && DRAWS.test(p.text ?? ''));
  }
  if (a.do === 'bench' || a.do === 'evolve') {
    // abilities that trigger when played (Meowth ex Last-Ditch Catch, Alakazam Psychic Draw)
    return (pc.powers ?? []).some(p => /when you play this Pokémon/i.test(p.text ?? '') && DRAWS.test(p.text ?? ''));
  }
  return false;
}

/** Put cards with these names into player `pi`'s hand (from the deck, else from prizes not known to
 *  hold them), returning a random other hand card to the deck for each, so the hand size stays. */
function ensureHand(sim: Sim, pi: number, names: string[], locked: Set<Card>, rng: Rng): string[] {
  const p = sim.state.players[pi];
  const keep = new Set<Card>();
  const missing: string[] = [];
  for (const n of names) {
    const inHand = p.hand.cards.find(c => !keep.has(c) && norm(c.name) === norm(n));
    if (inHand) {
      keep.add(inHand);
      continue;
    }
    let card: Card | undefined;
    const di = p.deck.cards.findIndex(c => norm(c.name) === norm(n));
    if (di >= 0) {
      card = p.deck.cards.splice(di, 1)[0];
    } else {
      // from a prize card not known to hold it: it was really in the deck; a random deck card takes its place
      for (const pr of p.prizes) {
        const k = pr.cards.findIndex(c => norm(c.name) === norm(n) && !locked.has(c));
        if (k >= 0 && p.deck.cards.length) {
          card = pr.cards.splice(k, 1)[0];
          pr.cards.push(p.deck.cards.splice(rng.int(0, p.deck.cards.length - 1), 1)[0]);
          break;
        }
      }
    }
    if (!card) {
      missing.push(n);
      continue;
    }
    const spare = p.hand.cards.filter(c => !keep.has(c));
    if (spare.length) {
      const out = rng.pick(spare);
      p.hand.cards.splice(p.hand.cards.indexOf(out), 1);
      p.deck.cards.splice(rng.int(0, p.deck.cards.length), 0, out);
    }
    p.hand.cards.push(card);
    keep.add(card);
  }
  return missing;
}

/** Board signature for "same position": slots (bench as a multiset), hands, discards, counts. */
export function boardSig(st: State): string {
  const slot = (l: any) => l.cards.length
    ? `${l.cards.filter((c: Card) => c instanceof PokemonCard).map((c: Card) => c.name).join('<')}|${l.energies.cards.map((c: Card) => c.name).sort().join(',')}|${l.tools.map((c: Card) => c.name).sort().join(',')}|${l.damage}|${l.specialConditions.slice().sort().join(',')}`
    : '-';
  const names = (cs: Card[]) => cs.map(c => c.name).sort().join(',');
  return st.players.map(p => [slot(p.active), p.bench.map(slot).sort().join(';'), names(p.hand.cards), names(p.discard.cards),
    names(p.lostzone.cards), p.deck.cards.length, p.prizes.filter(x => x.cards.length).length, p.supporterTurn, p.energyPlayedTurn, p.retreatedTurn].join('#')).join('@')
    + `@${names(st.players.flatMap(p => p.stadium.cards))}@${st.turn}@${st.activePlayer}`;
}

/** Strip "own"/"opp" and a slot prefix from a target label. */
const bare = (s: string) => norm(s).replace(/^(own|opp) /, '').replace(/^(active|bench\d) /, '');
const optNames = (label: string) => label.split(/ \+ |, | -> /).map(bare).filter(Boolean);

/** The option whose names best match `want` (a name or names), or -1. */
function bestOption(opts: { label: string }[], want: string | string[]): number {
  const w = (Array.isArray(want) ? want : [want]).map(norm);
  let best = -1, bestS = -Infinity;
  opts.forEach((o, i) => {
    const have = optNames(o.label);
    if (w.length === 1 && (w[0] === 'yes' || w[0] === 'no')) {
      const s = norm(o.label) === w[0] ? 1 : -1;
      if (s > bestS) {
        bestS = s;
        best = i;
      }
      return;
    }
    const left = have.slice();
    let hit = 0;
    for (const x of w) {
      const k = left.indexOf(x);
      if (k >= 0) {
        left.splice(k, 1);
        hit++;
      }
    }
    const s = 2 * hit - (w.length - hit) - left.length;
    if (s > bestS) {
      bestS = s;
      best = i;
    }
  });
  return best;
}

/** Main options that carry out a logged action. */
export function optionsFor(sim: Sim, a: LogAction): MainOption[] {
  const all = mainCandidates(sim.state);
  const card = norm(a.card), to = norm(a.to), name = norm(a.name);
  const target = (label: string) => bare(label.slice(label.lastIndexOf(' -> ') + 4));
  return all.filter(o => {
    const l = norm(o.label);
    switch (a.do) {
      case 'bench': return o.kind === 'bench' && l === `bench ${card}`;
      case 'evolve': return o.kind === 'evolve' && l.endsWith(`-> ${card}`) && (!to || bare(l.slice(7, l.lastIndexOf(' -> '))) === to);
      case 'attach': return o.kind === 'attach' && l.startsWith(`attach ${card} -> `) && (!to || target(o.label) === to || (to === 'active' && / -> active /.test(l)));
      case 'tool': return o.kind === 'tool' && l.startsWith(`tool ${card} -> `) && (!to || target(o.label) === to || (to === 'active' && / -> active /.test(l)));
      case 'play': return (o.kind === 'play' || o.kind === 'stadium') && l === `play ${card}`;
      case 'ability': {
        const m = /^ability (.*) \((.*)\)$/.exec(l);
        return o.kind === 'ability' && !!m && (!name || m[1] === name) && (!card || bare(m[2]) === card);
      }
      case 'retreat': return o.kind === 'retreat' && (!to || bare(l.replace(/^retreat to /, '')) === to);
      case 'attack': return o.kind === 'attack' && (!name || l === `attack ${name}`);
      case 'end': return o.kind === 'pass';
      default: return false;
    }
  });
}

export interface Step {
  game: string;
  turn: number;          // index in log.turns
  k: number;             // index in the turn's actions
  mover: number;         // log player
  board: string;
  real: string;          // main action label (engine wording)
  realFull: string;      // with the prompt answers
  inferred: boolean;
  ai: string;            // the pilot's first action (main label)
  aiFull: string;
  aiLine: string[];
  admissible: string[];  // real actions of this turn that could have been played now (independent)
  exact: boolean;        // ai === real
  aligned: boolean;      // ai is one of the admissible actions
  sameCard: boolean;     // same kind and card, other target
  fullMatch: boolean;    // same action and same prompt answers
  inLine: boolean;       // the real action is somewhere in the pilot's planned turn
  kind: string;
}

export interface ReplayResult {
  steps: Step[];
  applied: number;
  failed: { turn: number; k: number; action: string; why: string }[];
  stopped?: string;
}

const mainOf = (label: string) => label.split(' | ')[0];
const cardOf = (label: string) => mainOf(label).replace(/ -> .*$/, '').replace(/ \(.*\)$/, '');

/**
 * Replay a match log; at each real action ask `decide` for the pilot's line from that state.
 * `decide` gets a copy of the state (mover to act) and returns the line it would play.
 */
export function replayLog(log: MatchLog, gameId: string, decide: (s: Sim, seed: number) => string[], seed = 1, onlyTurns?: number): ReplayResult {
  const decks = logDecks(log);
  const defs = cardDefs(decks);
  const eng = (lp: number) => (lp === log.first ? 0 : 1);
  const rng = new Rng(seed * 7919 + 13);
  const steps: Step[] = [];
  const failed: ReplayResult['failed'] = [];
  const consumed = new Set<LogAction>();
  let applied = 0;

  // promotions are answered from the log: the next 'promote' of that player not yet used
  const pos = { t: 0, k: 0 };
  const nextPromote = (lp: number): LogAction | undefined => {
    for (let t = pos.t; t < log.turns.length; t++) {
      for (const a of log.turns[t].actions) {
        if (a.do === 'promote' && !consumed.has(a) && (log.turns[t].player === lp)) {
          return a;
        }
      }
    }
    return undefined;
  };
  const chooserFor = (a: LogAction | undefined, mover: number, record: string[], dryRun = false, replay?: string[]): PromptChooser => {
    let ci = 0, ri = 0;
    return (s, p, opts) => {
      const owner = s.playerIndex(p.playerId);
      let i = -1;
      if (replay && ri < replay.length) {
        i = opts.findIndex(o => o.label === replay[ri]);
        ri++;
        if (i >= 0) {
          record.push(opts[i].label);
          return i;
        }
      }
      const yesNo = opts.length <= 2 && opts.every(o => o.label === 'yes' || o.label === 'no');
      const next = a?.choices?.[ci];
      if (owner === mover && yesNo && !(next === 'yes' || next === 'no')) {
        // "you may" with no yes/no in the log: yes when the log still names what came of it (Meowth ex
        // finding Boss's Orders), otherwise no (Iron Leaves ex switching in when benched)
        i = opts.findIndex(o => o.label === (next !== undefined ? 'yes' : 'no'));
      } else if (owner === mover && a?.choices && ci < a.choices.length) {
        const c = a.choices[ci++];
        i = c === '*' ? -1 : bestOption(opts, c);         // "*": not known, answered at random
      } else if (owner !== mover && p instanceof ChoosePokemonPrompt) {
        const lp = owner === 0 ? log.first : 1 - log.first;
        const pr = nextPromote(lp);
        if (pr?.card) {
          i = bestOption(opts, pr.card);
          if (!dryRun) {
            consumed.add(pr);
          }
        }
      }
      if (i < 0 && owner === mover && a?.uses?.length && p instanceof ChooseCardsPrompt) {
        i = bestOption(opts, a.uses);                      // the cards the action spends (Teal Dance's Energy)
      }
      if (i < 0) {
        // not in the log: at random, but a real selection rather than "nothing" when there is one
        const some = opts.map((o, k) => k).filter(k => !/^(nothing|move nothing|none|discard nothing|attach nothing)$/.test(opts[k].label));
        i = some.length ? some[rng.int(0, some.length - 1)] : rng.int(0, opts.length - 1);
      }
      record.push(opts[i].label);
      return i;
    };
  };

  // ---- set-up: who goes first (deck order + seed), opening Pokémon, known prizes
  let sim: Sim | undefined;
  const locked = new Set<Card>();
  for (let s = seed; s < seed + 400 && !sim; s++) {
    const r = new Rng(s);
    const t = Sim.newGame(decks[log.first], decks[1 - log.first], r);
    try {
      for (let g = 0; g < 200; g++) {
        const p = t.pendingPrompt();
        if (!p || t.finished) {
          break;
        }
        const e = t.playerIndex(p.playerId);
        if (p instanceof ChooseCardsPrompt && p.message === GameMessage.CHOOSE_STARTING_POKEMONS) {
          const pl = t.state.players[e];
          const su = log.setup[e === 0 ? log.first : 1 - log.first];
          if (pl.active.cards.length) {
            t.answer(p, decodeValid(p, t.state, [])!.decoded);      // extra Bench placement after a mulligan: none
            continue;
          }
          const want = [su.active, ...(su.bench ?? [])];
          if (ensureHand(t, e, want, locked, r).length) {
            throw new Error('opening Pokémon not in the deck');
          }
          p.options.blocked = pl.hand.cards.map((c, i) => (c instanceof PokemonCard && c.stage === Stage.BASIC ? -1 : i)).filter(i => i >= 0);
          const used = new Set<number>();
          const raw = want.map(n => {
            const i = pl.hand.cards.findIndex((c, k) => !used.has(k) && norm(c.name) === norm(n));
            used.add(i);
            return i;
          });
          const v = decodeValid(p, t.state, raw);
          if (!v) {
            throw new Error('set-up rejected');
          }
          t.answer(p, v.decoded);
          continue;
        }
        const opts = promptOptions(p, t.state, r);
        t.answer(p, opts[r.int(0, opts.length - 1)].decoded);
      }
    } catch {
      continue;
    }
    if (t.state.phase === GamePhase.PLAYER_TURN && t.state.activePlayer === 0 && !t.pendingPrompt()) {
      sim = t;
    }
  }
  if (!sim) {
    return { steps, applied, failed, stopped: 'could not reproduce the set-up' };
  }
  sim.chanceSeed = (seed * 2654435761) >>> 0;
  (log.prizes ?? [[], []]).forEach((names, lp) => {
    const p = sim!.state.players[eng(lp)];
    for (const n of names) {
      if (p.prizes.some(pr => pr.cards.some(c => norm(c.name) === norm(n) && locked.has(c)))) {
        continue;
      }
      const di = p.deck.cards.findIndex(c => norm(c.name) === norm(n));
      const slot = p.prizes.find(pr => pr.cards.length && !pr.cards.some(c => locked.has(c)));
      if (di >= 0 && slot) {
        const c = p.deck.cards.splice(di, 1)[0];
        p.deck.cards.splice(rng.int(0, p.deck.cards.length), 0, slot.cards.pop()!);
        slot.cards.push(c);
        locked.add(c);
      }
    }
  });

  // ---- turns
  const nTurns = Math.min(log.turns.length, onlyTurns ?? Infinity);
  for (let ti = 0; ti < nTurns; ti++) {
    const turn = log.turns[ti];
    const mover = eng(turn.player);
    if (sim.finished) {
      return { steps, applied, failed, stopped: `game over before turn ${ti}` };
    }
    if (sim.state.activePlayer !== mover) {
      return { steps, applied, failed, stopped: `turn ${ti}: P${turn.player} to move in the log, the other player in the replay` };
    }
    const acts = turn.actions.filter(a => a.do !== 'promote' && a.do !== 'concede');
    const draws = acts.map(a => drawsCards(a, defs));
    const seen = (turn.hand ?? []).slice();
    // states before and after each real action, for the independence check
    const answers: string[][] = [];
    const before: (Sim | undefined)[] = [];
    const after: (Sim | undefined)[] = [];
    const turnSteps: Step[] = [];
    for (let k = 0; k < acts.length; k++) {
      pos.t = ti;
      pos.k = k;
      const a = acts[k];
      // cards the player must hold now: this action's, and the following ones' up to the next draw
      const need: string[] = [...seen];
      for (let j = k; j < acts.length; j++) {
        const c = handCard(acts[j]);
        if (c) {
          need.push(c);
        }
        need.push(...(acts[j].uses ?? []));
        if (draws[j]) {
          break;
        }
      }
      ensureHand(sim, mover, need, locked, rng);
      const opts = optionsFor(sim, a);
      const s0 = sim.copy(rng.fork());
      before[k] = s0;
      let next: Sim | undefined;
      let real = '', realFull = '';
      const why: string[] = [];
      for (const o of opts.flatMap(x => Array(5).fill(x) as MainOption[])) {
        // a few tries: answers the log leaves open are random, and a card may reject one (Crispin
        // with two Energy of one type)
        const rec: string[] = [];
        const r = runStep(sim, o, chooserFor(a, mover, rec), rng, 2);
        if (r.sim) {
          next = r.sim;
          answers[k] = rec;
          real = o.label;
          realFull = [o.label, ...rec].join(' | ');
          break;
        }
        why.push(...r.deadEnds);
      }
      if (!next) {
        failed.push({ turn: ti, k, action: JSON.stringify(a), why: opts.length ? why.slice(0, 2).join('; ') : 'no matching legal action' });
        after[k] = undefined;
        continue;
      }
      applied++;
      // the pilot's choice from the same state
      const line = decide(s0.copy(rng.fork()), seed * 1000 + ti * 37 + k);
      const ai = mainOf(line[0] ?? 'end turn');
      turnSteps.push({
        game: gameId, turn: ti, k, mover: turn.player, board: describeState(s0.state, mover),
        real, realFull, inferred: !!a.inferred, ai, aiFull: line[0] ?? 'end turn', aiLine: line, admissible: [real],
        exact: ai === real, aligned: ai === real, sameCard: cardOf(ai) === cardOf(real), fullMatch: (line[0] ?? 'end turn') === realFull, kind: a.do,
        inLine: (line.length ? line : ['end turn']).map(mainOf).includes(real) || (real === 'end turn' && !line.some(x => /^attack /.test(x))),
      });
      for (const c of [handCard(a)].filter(Boolean)) {
        const i = seen.findIndex(x => norm(x) === norm(c));
        if (i >= 0) {
          seen.splice(i, 1);
        }
      }
      sim = next;
      after[k] = sim.copy(rng.fork());
      if (sim.finished || sim.state.activePlayer !== mover) {
        break;                                      // an attack (or a Knock Out that ended the game) ended the turn
      }
    }
    // independence: a later action j is admissible at step k when playing it first and then the
    // actions k..j-1 reaches the board the real order reached after j (only up to the next draw)
    for (const st of turnSteps) {
      const k = st.k;
      for (let j = k + 1; j < acts.length && after[j]; j++) {
        if (draws.slice(k, j).some(Boolean)) {
          break;
        }
        let t: Sim | undefined = before[k]!.copy(rng.fork());
        const order = [j, ...Array.from({ length: j - k }, (_, i) => k + i)];
        for (let q = 0; q < order.length && t; q++) {
          let nx: Sim | undefined;
          for (const op of optionsFor(t, acts[order[q]])) {
            nx = runStep(t, op, chooserFor(acts[order[q]], mover, [], true, answers[order[q]]), rng, 2).sim;
            if (nx) {
              break;
            }
          }
          // the turn may only end with the last action of the reordered sequence
          t = nx && (q === order.length - 1 || (!nx.finished && nx.state.activePlayer === mover)) ? nx : undefined;
        }
        if (t && boardSig(t.state) === boardSig(after[j]!.state)) {
          const lab = turnSteps.find(x => x.k === j)?.real;
          if (lab && !st.admissible.includes(lab)) {
            st.admissible.push(lab);
          }
        }
      }
      st.aligned = st.admissible.includes(st.ai);
    }
    steps.push(...turnSteps);
    if (turn.actions.some(a => a.do === 'concede')) {
      return { steps, applied, failed, stopped: 'conceded' };
    }
    // end the turn if the log's actions did not (no attack)
    if (!sim.finished && sim.state.activePlayer === mover) {
      const end = mainCandidates(sim.state).find(o => o.kind === 'pass')!;
      const r = runStep(sim, end, chooserFor(undefined, mover, []), rng, 2);
      if (!r.sim) {
        return { steps, applied, failed, stopped: `turn ${ti}: could not end the turn` };
      }
      sim = r.sim;
    }
  }
  return { steps, applied, failed, stopped: sim.finished ? 'game over' : undefined };
}

export function loadLogs(dir: string, only?: string): { id: string; log: MatchLog }[] {
  if (!fs.existsSync(dir)) {
    return [];
  }
  const out: { id: string; log: MatchLog }[] = [];
  for (const f of fs.readdirSync(dir).filter(f => f.endsWith('.json')).sort()) {
    const id = f.replace(/\.json$/, '');
    if (only && id !== only) {
      continue;
    }
    try {
      out.push({ id, log: JSON.parse(fs.readFileSync(path.join(dir, f), 'utf8')) as MatchLog });
    } catch (e) {
      console.error(`${id}: not valid JSON (${(e as Error).message.slice(0, 120)}), skipped`);
    }
  }
  return out;
}

/** Every saved decklist (meta decklists + top cuts), for log writers. */
export function knownLists(): ReturnType<typeof loadMetaLists> {
  logDecksInit();
  return allLists!;
}
function logDecksInit(): void {
  if (!allLists) {
    const topcut = path.join(REPO_ROOT, 'meta', 'decklists_topcut.json');
    allLists = [...loadMetaLists(), ...(fsx.existsSync(topcut) ? loadMetaLists(topcut) : [])];
  }
}
