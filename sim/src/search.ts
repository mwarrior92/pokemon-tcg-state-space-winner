// One-turn search. A node is a settled position inside the mover's turn; an edge is a macro step
// (a main-phase action plus one way of answering every prompt it raises). Prompt answers branch by
// replay: prompt continuations cannot be copied, so each branch re-applies the action on a fresh
// copy and feeds the same answer prefix, with all chance seeded so replays are identical.
//
// offenseSearch: the most prize cards the mover can take this turn (the exhaustive "teacher").
// Positions reached by different orders of the same actions are merged by a canonical key.
import { CardList, GameError, GamePhase, Player, PokemonCardList, Prompt, State } from './engine';
import { prizesLeft } from './rules';
import { Rng } from './rng';
import { DeadEnd, MainOption, Sim, mainCandidates, promptOptions } from './sim';
import { firstDifference, sameState } from './clone';

// ---------------------------------------------------------------- canonical key

function names(l: CardList): string {
  return l.cards.map(c => c.fullName).sort().join(',');
}

function markers(x: any): string {
  const ms = x?.marker?.markers ?? x?.markers;
  return Array.isArray(ms) ? ms.map((m: any) => m.name).sort().join('+') : '';
}

function slotKey(l: PokemonCardList): string {
  if (!l.cards.length) {
    return '-';
  }
  return [l.getPokemons().map(c => c.fullName).join('<'), l.damage, names(l.energies), l.tools.map(t => t.fullName).sort().join(','),
    l.specialConditions.slice().sort().join(','), markers(l), (l.boardEffect ?? []).slice().sort().join(','),
    l.getPokemons().map(c => markers(c)).join('|'), l.pokemonPlayedTurn].join('/');
}

function ordered(l: CardList): string {
  return l.cards.map(c => c.fullName).join(',');
}

// The deck is keyed in order (with fixed shuffles, Sim.chanceSeed, the same deck contents are
// nearly always in the same order anyway) and the prizes by content: two positions with one key
// have the same future, so a search may expand either one and skip the other.
function playerKey(p: Player, st: State): string {
  return [names(p.hand), names(p.discard), p.deck.cards.length, ordered(p.deck), p.prizes.map(ordered).join('/'), names(p.lostzone), names(p.stadium),
    names(p.supporter), slotKey(p.active), p.bench.map(slotKey).sort().join(';'), markers(p),
    p.energyPlayedTurn === st.turn ? 'E' : '', p.retreatedTurn === st.turn ? 'R' : '', p.stadiumPlayedTurn === st.turn ? 'S' : '',
    p.usedVSTAR ? 'V' : '', p.supporterTurn].join('|');
}

export function stateKey(st: State): string {
  return `${st.turn}|${st.activePlayer}|${st.phase}|${playerKey(st.players[0], st)}#${playerKey(st.players[1], st)}`;
}

/** 64-bit hash of stateKey as 16 hex digits: the position's identity in transposition tables
 *  (shared across workers in the parallel search). Two independent 32-bit hashes; a collision
 *  needs ~4 billion positions per search to become likely. */
export function stateHash(st: State): string {
  const k = stateKey(st);
  let h1 = 0x811c9dc5, h2 = 0x01000193 ^ k.length;
  for (let i = 0; i < k.length; i++) {
    const c = k.charCodeAt(i);
    h1 = Math.imul(h1 ^ c, 0x01000193);
    h2 = Math.imul(h2 ^ c, 0x5bd1e995);
    h2 ^= h2 >>> 13;
  }
  return (h1 >>> 0).toString(16).padStart(8, '0') + (h2 >>> 0).toString(16).padStart(8, '0');
}

// ---------------------------------------------------------------- children

export interface Child {
  sim: Sim;
  label: string;          // action + prompt answers, readable
  step: Step;             // how to replay it from the parent (option + the mover's answers)
  terminal: boolean;      // the mover's turn is over (attack resolved, turn passed, game over)
  prizes: number;         // prize cards the mover has taken this turn so far
}

/** One macro step, replayable: the main-phase option's label and the index of the mover's answer
 *  at each prompt (opponent prompts and chance are seeded, so they replay identically). */
export interface Step {
  o: string;
  a: number[];
}

export interface ExpandOptions {
  promptCap?: number;     // options considered per prompt
  branchCap?: number;     // leaves per action
  seed?: number;
  /** replay exactly this answer path (no branching) - see replayStep */
  only?: number[];
}

function hashStr(s: string): number {
  let h = 2166136261;
  for (let i = 0; i < s.length; i++) {
    h = Math.imul(h ^ s.charCodeAt(i), 16777619);
  }
  return h >>> 0;
}

/** Where state copies go (instrumentation; cheap counters). */
export const copyStats = { copies: 0, illegal: 0, engineError: 0, deadEnd: 0, leaves: 0, duplicates: 0, illegalChanged: 0, illegalBy: new Map<string, number>(), changedBy: new Map<string, number>(), trackChanges: false };

/** All ways (up to caps) to play main-phase option `o` from `sim`, each a settled child. Prompts for
 *  the other player (e.g. choosing a new Active after a Knock Out) are answered at random. */
/** A copy of the parent that the engine rejected an action on without changing anything: the
 *  next option tried from the same parent reuses it instead of copying again (41% of all copies
 *  were spent on rejected actions, 95% of them unchanged). */
export interface Spare {
  sim?: Sim;
}

export function expandAction(sim: Sim, o: MainOption, mover: number, startPrizes: number, opts: ExpandOptions = {}, spare?: Spare): Child[] {
  const promptCap = opts.promptCap ?? 6;
  const branchCap = opts.branchCap ?? 12;
  const base = (opts.seed ?? 1) ^ hashStr(o.label);
  const out: Child[] = [];
  const only = opts.only;
  const pending: number[][] = [only ?? []];
  const moverId = sim.state.players[mover].id;
  while (pending.length && out.length < branchCap) {
    const prefix = pending.pop()!;
    let t: Sim;
    if (spare?.sim) {
      t = spare.sim;
      spare.sim = undefined;
      t.rng = new Rng(base);
    } else {
      t = sim.copy(new Rng(base));     // same chance on every replay of this action
      copyStats.copies++;
    }
    const labels: string[] = [o.label];
    try {
      t.apply(o.action);
    } catch (e) {
      if (e instanceof GameError) {
        copyStats.illegal++;
        // the engine logs some actions before rejecting them (e.g. "used ability X"); logs are
        // drained after every step anyway, so they do not count as a change
        if (t.state.logs.length && !sim.state.logs.length) {
          t.state.logs = [];
        }
        if (spare && !t.pendingPrompt() && sameState(sim.state, t.state)) {
          spare.sim = t;                // untouched: reuse for the next option
        } else {
          copyStats.illegalChanged++;   // the engine changed something before rejecting
          if (copyStats.trackChanges) {
            const d = t.pendingPrompt() ? 'pending prompt' : (firstDifference(sim.state, t.state) ?? '?').replace(/\[\d+\]/g, '[i]');
            const key = `${o.label.startsWith("play ") ? o.label : o.label.split(" ")[0]} | ${(e as Error).message} | ${d}`;
            copyStats.changedBy.set(key, (copyStats.changedBy.get(key) ?? 0) + 1);
          }
        }
        {
          const why = `${o.label.split(' ')[0]} ${o.label.split(' ')[0] === 'play' || o.label.split(' ')[0] === 'attack' ? '' : ''}| ${(e as Error).message}`;
          copyStats.illegalBy.set(why, (copyStats.illegalBy.get(why) ?? 0) + 1);
        }
        return out;      // illegal here
      }
      copyStats.engineError++;
      return out;        // engine error on this action: treat as unplayable
    }
    // path = answer index chosen at each of the mover's prompts so far; the first replay of a
    // prefix takes option 0 at every new prompt and queues the alternatives
    const path: number[] = [];
    let oppPrompts = 0;
    let ok = true;
    for (let guard = 0; guard < 60; guard++) {
      const p: Prompt<any> | undefined = t.pendingPrompt();
      if (!p || t.finished) {
        break;
      }
      const mine = p.playerId === moverId;
      const popts = promptOptions(p, t.state, new Rng(base + (mine ? 31 * path.length : 7919 + 97 * oppPrompts)), promptCap);
      if (!popts.length) {
        ok = false;
        break;
      }
      let pick: number;
      if (!mine) {
        pick = new Rng(base + 104729 + oppPrompts).int(0, popts.length - 1);
        oppPrompts++;
      } else if (path.length < prefix.length) {
        pick = prefix[path.length];
      } else {
        pick = 0;
        for (let i = popts.length - 1; i >= 1 && !only; i--) {
          pending.push([...path, i]);
        }
      }
      if (pick >= popts.length) {
        ok = false;
        break;
      }
      try {
        t.answer(p, popts[pick].decoded);
      } catch {
        ok = false;
        break;
      }
      if (mine) {
        path.push(pick);
        labels.push(popts[pick].label);
      }
    }
    if (!ok) {
      copyStats.deadEnd++;
      continue;
    }
    const st = t.state;
    const terminal = t.finished || st.activePlayer !== mover || st.phase !== GamePhase.PLAYER_TURN;
    copyStats.leaves++;
    out.push({ sim: t, label: labels.join(' | '), step: { o: o.label, a: path }, terminal, prizes: startPrizes - prizesLeft(st.players[mover]) });
  }
  return out;
}

/** Re-play one recorded macro step from `sim` (the parent position). Deterministic: the same
 *  parent, option and answers give the same child, which is how a worker rebuilds a position it
 *  did not create from the path that leads to it. */
export function replayStep(sim: Sim, step: Step, mover: number, startPrizes: number, opts: ExpandOptions = {}): Child | undefined {
  const o = mainCandidates(sim.state).find(x => x.label === step.o);
  return o ? expandAction(sim, o, mover, startPrizes, { ...opts, only: step.a })[0] : undefined;
}

/** Every child of a node (all main-phase options, all prompt branches), de-duplicated by position. */
export function children(sim: Sim, mover: number, startPrizes: number, opts: ExpandOptions = {}): Child[] {
  const seen = new Set<string>();
  const out: Child[] = [];
  const spare: Spare = {};
  for (const o of mainCandidates(sim.state)) {
    for (const c of expandAction(sim, o, mover, startPrizes, opts, spare)) {
      const k = c.terminal ? `T${c.prizes}|${c.label}` : stateHash(c.sim.state);
      if (seen.has(k)) {
        copyStats.duplicates++;
      } else {
        seen.add(k);
        out.push(c);
      }
    }
  }
  return out;
}

// ---------------------------------------------------------------- offense search

export interface SearchNode {
  key: string;
  /** the position; released after expansion unless the node is in the kept sample (memory) */
  sim?: Sim;
  depth: number;
  taken: number;          // prizes taken on the way here
  value: number;          // best prizes reachable from here this turn (lower bound if !complete)
  complete: boolean;      // every line from here was searched
  expanded: boolean;
  kids: { node?: SearchNode; terminal?: number; label: string }[];
  kept?: boolean;
}

export interface SearchResult {
  value: number;          // most prizes found
  line: string[];         // the actions that take them
  nodes: SearchNode[];    // every searched position with its value (sims only on `sample`)
  sample: SearchNode[];   // root + the uniformly sampled positions whose sims were kept
  expansions: number;     // macro steps tried
  complete: boolean;      // the whole turn was searched within budget
  ms: number;
}

export interface SearchOptions extends ExpandOptions {
  budget?: number;        // max macro steps tried
  maxDepth?: number;      // max actions in a line
  /** order in which queued positions are expanded (default breadth-first) */
  priority?: (n: SearchNode) => number;
  /** keep the positions (sims) of only this many sampled nodes besides the root; the rest are
   *  released as soon as they are expanded. A full search holds ~0.3 MB per position, so keeping
   *  all of them (the default) costs hundreds of MB per search. */
  keepSims?: number;
  /** sample uniformly among expanded positions (default) or among all created positions */
  sampleFrom?: 'expanded' | 'all';
  sampleSeed?: number;
  /** wall-clock cap for one search (default 15 s); the result is then marked incomplete */
  maxMs?: number;
  /** instrumentation: called for every generated child; `known` = its position was already
   *  reached by another path (the work of generating it was redundant) */
  onChild?: (c: Child, known: boolean, parentDepth: number) => void;
}

/** Breadth-first over the turn (shortest lines first), positions merged by key, values backed up
 *  from the leaves. Stops at the budget or when every remaining prize is taken. */
export function offenseSearch(root: Sim, opts: SearchOptions = {}): SearchResult {
  const t0 = Date.now();
  const mover = root.state.activePlayer;
  const startPrizes = prizesLeft(root.state.players[mover]);
  const budget = opts.budget ?? 2000;
  const maxDepth = opts.maxDepth ?? 12;
  const memo = new Map<string, SearchNode>();
  const nodes: SearchNode[] = [];
  let expansions = 0;
  let best = 0;
  const bound = startPrizes;
  const keepAll = opts.keepSims === undefined || !Number.isFinite(opts.keepSims);
  const k = opts.keepSims ?? 0;
  const fromAll = opts.sampleFrom === 'all';
  const srng = new Rng(opts.sampleSeed ?? 1);
  const sample: SearchNode[] = [];
  let offered = 0;
  const release = (n: SearchNode) => {
    if (!keepAll && !n.kept && n.depth > 0 && n.expanded) {
      n.sim = undefined;
    }
  };
  const offer = (n: SearchNode) => {
    if (keepAll || n.depth === 0) {
      return;
    }
    offered++;
    if (sample.length < k) {
      sample.push(n);
      n.kept = true;
    } else {
      const j = srng.int(0, offered - 1);
      if (j < k) {
        const out = sample[j];
        out.kept = false;
        release(out);
        sample[j] = n;
        n.kept = true;
      }
    }
  };
  const maxMs = opts.maxMs ?? 15000;

  const mk = (sim: Sim, depth: number): SearchNode => {
    const key = stateHash(sim.state);
    const hit = memo.get(key);
    if (hit) {
      return hit;
    }
    const taken = startPrizes - prizesLeft(sim.state.players[mover]);
    const n: SearchNode = { key, sim, depth, taken, value: taken, complete: false, expanded: false, kids: [] };
    memo.set(key, n);
    nodes.push(n);
    best = Math.max(best, taken);
    if (fromAll) {
      offer(n);
    }
    return n;
  };

  const rootNode = mk(root, 0);
  let queue: SearchNode[] = [rootNode];
  let head = 0;
  let expandedCount = 0;
  // breadth-first, the queue's tail is what the budget will never reach: positions queued beyond
  // the estimated number of expansions left are kept as nodes (their value counts as a lower
  // bound) but their states are dropped at once. Without this a search held ~0.3 MB for each of
  // ~1000 unexpanded positions at its peak.
  const roomLeft = () => {
    const perExpansion = expandedCount ? expansions / expandedCount : 8;
    return 1.5 * (budget - expansions) / Math.max(1, perExpansion) + 8;
  };
  while (head < queue.length && expansions < budget && best < bound && Date.now() - t0 < maxMs) {
    if (opts.priority) {
      queue = queue.slice(head).sort((a, b) => opts.priority!(b) - opts.priority!(a));
      head = 0;
    }
    const n = queue[head++];
    if (n.expanded || n.depth >= maxDepth || !n.sim) {
      continue;
    }
    const kids = children(n.sim!, mover, startPrizes, opts);
    expansions += Math.max(1, kids.length);
    n.expanded = true;
    expandedCount++;
    if (!fromAll) {
      offer(n);
    }
    release(n);
    for (const c of kids) {
      opts.onChild?.(c, !c.terminal && memo.has(stateHash(c.sim.state)), n.depth);
      if (c.terminal) {
        n.kids.push({ terminal: c.prizes, label: c.label });
        best = Math.max(best, c.prizes);
      } else {
        const m = mk(c.sim, n.depth + 1);
        if (m === n) {
          continue;   // the action changed nothing (no-op): not a real move
        }
        n.kids.push({ node: m, label: c.label });
        if (!m.expanded && m.sim) {
          if (!keepAll && !opts.priority && !m.kept && queue.length - head > roomLeft()) {
            m.sim = undefined;   // beyond the budget's reach
          } else {
            queue.push(m);
          }
        }
      }
    }
  }
  void queue;
  if (!keepAll) {
    for (const n of nodes) {
      if (!n.kept && n.depth > 0) {
        n.sim = undefined;     // the unexpanded frontier too
      }
    }
  }

  backUpValues(nodes, bound);
  const line = bestLine(rootNode);
  return { value: rootNode.value, line, nodes, sample: keepAll ? nodes : [rootNode, ...sample], expansions, complete: rootNode.complete, ms: Date.now() - t0 };
}

/** The part of a search node that value back-up and line reconstruction need (shared with the
 *  parallel search). */
export interface DagNode {
  taken: number;
  value: number;
  complete: boolean;
  expanded: boolean;
  kids: { node?: DagNode; terminal?: number; label: string }[];
}

/** Back up values from the leaves. Nodes are in creation order (parents before children), so
 *  reverse order works for a DAG built breadth-first; a second pass covers nodes reached again by
 *  a longer path. */
export function backUpValues(nodes: DagNode[], bound: number): void {
  for (let pass = 0; pass < 2; pass++) {
    for (let i = nodes.length - 1; i >= 0; i--) {
      const n = nodes[i];
      let v = n.taken;
      let complete = n.expanded;
      for (const k of n.kids) {
        if (k.terminal !== undefined) {
          v = Math.max(v, k.terminal);
        } else if (k.node) {
          v = Math.max(v, k.node.value);
          complete = complete && k.node.complete;
        }
      }
      n.value = v;
      n.complete = complete || v >= bound;
    }
  }
}

/** The best line: follow a best child from the root. */
export function bestLine(root: DagNode): string[] {
  const line: string[] = [];
  let cur: DagNode | undefined = root;
  const guard = new Set<DagNode>();
  while (cur && !guard.has(cur)) {
    guard.add(cur);
    const target: number = cur.value;
    if (cur.taken === target && !cur.kids.some(k => (k.terminal ?? -1) === target)) {
      if (!cur.kids.some(k => k.node && k.node.value === target && k.node.taken < target)) {
        line.push('(end turn)');
        break;
      }
    }
    const term = cur.kids.find(k => k.terminal === target);
    if (term) {
      line.push(term.label);
      break;
    }
    const next: DagNode['kids'][number] | undefined = cur.kids.find(k => k.node && k.node.value === target);
    if (!next) {
      break;
    }
    line.push(next.label);
    cur = next.node;
  }
  return line;
}

export { DeadEnd };
