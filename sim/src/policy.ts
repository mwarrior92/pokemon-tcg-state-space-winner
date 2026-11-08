// Fast turn players driven by a value model ("intuition") instead of exhaustive search.
//
// At each step every child of the current position is generated (same move generator as the
// search). A child that ends the turn is scored exactly (prizes taken / its outcome); any other
// child is scored by the model's prediction for the position. The best child is played; repeat.
import { ALL_GROUPS, Group, features } from './features';
import { LinearModel, Predictor } from './model';
import { prizesLeft } from './rules';
import { ExpandOptions, SearchNode, children, offenseSearch, replayStep } from './search';
import { GamePhase, PassTurnAction } from './engine';
import { Rng } from './rng';
import { Sim, randomChooser, resolvePrompts } from './sim';

export interface StepLog {
  chosen: string;
  value: number;
  exact: boolean;
  alternatives: { label: string; value: number; exact: boolean }[];
}

export interface TurnPlay {
  prizes: number;
  line: string[];
  steps: StepLog[];
  end: Sim;
  ms: number;
}

/** Feature groups a model needs (so only those are computed). */
export function groupsFor(m: LinearModel): Group[] {
  const need = new Set(m.groups ?? ALL_GROUPS);
  return ALL_GROUPS.filter(g => need.has(g));
}

export interface PolicyOptions extends ExpandOptions {
  maxSteps?: number;
}

/** Offense: play the turn to maximise predicted prizes taken this turn. */
export function playOffense(root: Sim, model: LinearModel, opts: PolicyOptions = {}): TurnPlay {
  const t0 = Date.now();
  const mover = root.state.activePlayer;
  const start = prizesLeft(root.state.players[mover]);
  const pred = new Predictor(model);
  const groups = groupsFor(model);
  const only = new Set(model.names);
  const line: string[] = [];
  const steps: StepLog[] = [];
  let cur = root;
  for (let step = 0; step < (opts.maxSteps ?? 15); step++) {
    const kids = children(cur, mover, start, opts);
    if (!kids.length) {
      break;
    }
    const scored = kids.map(c => {
      if (c.terminal) {
        return { c, value: c.prizes, exact: true };
      }
      const fv = features(c.sim, mover, groups, { only });
      // a position can never be worth less than the prizes already taken on the way to it
      return { c, value: Math.max(c.prizes, pred.predict(fv.names, fv.values)), exact: false };
    });
    scored.sort((a, b) => (b.value - a.value) || (Number(b.exact) - Number(a.exact)));
    const pick = scored[0];
    steps.push({
      chosen: pick.c.label, value: pick.value, exact: pick.exact,
      alternatives: scored.slice(1, 6).map(s => ({ label: s.c.label, value: s.value, exact: s.exact })),
    });
    line.push(pick.c.label);
    cur = pick.c.sim;
    if (pick.c.terminal) {
      break;
    }
  }
  return { prizes: start - prizesLeft(cur.state.players[mover]), line, steps, end: cur, ms: Date.now() - t0 };
}

export interface SearchPolicyOptions {
  budget?: number;        // children generated per search (offenseSearch budget)
  maxSteps?: number;
  maxMs?: number;         // per search
  /** expansion order: breadth-first (default; exact for short tactics such as gust + attack) or
   *  best-first by predicted value (follows the model's mistakes; worse in the round-2 review) */
  order?: 'breadth' | 'best';
}

/** Offense, search version: at each step a search of `budget` children from the current
 *  position, exact where it searched and valued by the model beyond. The moves along the best line are played
 *  while they lead into searched positions; then it searches again from there. The greedy policy
 *  above is the special case of one expansion per step. */
export function playOffenseSearch(root: Sim, model: LinearModel, opts: SearchPolicyOptions = {}): TurnPlay {
  const t0 = Date.now();
  const mover = root.state.activePlayer;
  const start = prizesLeft(root.state.players[mover]);
  const pred = new Predictor(model);
  const groups = groupsFor(model);
  const only = new Set(model.names);
  const estimate = (sim: Sim) => {
    const fv = features(sim, mover, groups, { only });
    return pred.predict(fv.names, fv.values);
  };
  const line: string[] = [];
  const steps: StepLog[] = [];
  let cur = root;
  for (let round = 0; round < (opts.maxSteps ?? 15) && line.length < (opts.maxSteps ?? 15); round++) {
    const r = offenseSearch(cur, {
      budget: opts.budget ?? 400, evaluate: estimate, quiescence: true, priority: opts.order === 'best' ? (n => n.value) : undefined, keepSims: 0, maxMs: opts.maxMs ?? 5000,
    });
    let node: SearchNode = r.nodes[0];
    let ended = false;
    // follow the best line through searched positions
    for (;;) {
      const target = node.value;
      const term = node.kids.find(k => k.terminal !== undefined && k.terminal >= target);
      const next = term ?? node.kids.filter(k => k.node).sort((a, b) => (b.node!.value - a.node!.value))[0];
      if (!next || (!term && next.node!.value < node.taken) || !next.step) {
        ended = true;   // nothing better than stopping here
        break;
      }
      const alternatives = node.kids.filter(k => k !== next).map(k => ({ label: k.label, value: k.terminal ?? k.node!.value, exact: k.terminal !== undefined || !!k.node?.complete }))
        .sort((a, b) => b.value - a.value).slice(0, 5);
      const child = replayStep(cur, next.step, mover, start, { cheapPass: false });
      if (!child) {
        ended = true;
        break;
      }
      steps.push({ chosen: next.label, value: term ? term.terminal! : next.node!.value, exact: !!term || !!next.node!.complete, alternatives });
      line.push(next.label);
      cur = child.sim;
      if (child.terminal || term) {
        ended = true;
        break;
      }
      node = next.node!;
      if (!node.expanded) {
        break;          // beyond the searched part: search again from here
      }
    }
    if (ended) {
      break;
    }
  }
  return { prizes: start - prizesLeft(cur.state.players[mover]), line, steps, end: cur, ms: Date.now() - t0 };
}

/** End the mover's turn at this position (pass), letting the engine run the turn change (the
 *  opponent draws). undefined when the game ended or the engine could not settle. */
export function passTurn(sim: Sim, seed: number): Sim | undefined {
  const c = sim.copy(new Rng(seed));
  try {
    c.apply(new PassTurnAction(c.state.players[c.state.activePlayer].id));
    resolvePrompts(c, randomChooser(new Rng(seed + 1)), new Rng(seed + 2));
  } catch {
    return undefined;
  }
  return c.finished || c.state.phase !== GamePhase.PLAYER_TURN ? undefined : c;
}

export interface DefensePlay extends TurnPlay {
  afterTurn?: Sim;        // the position the opponent faces
}

/** Defense: play the turn to minimise the prizes the model predicts the opponent takes next turn.
 *  Every candidate is judged by the position the opponent would face if the turn ended there. */
export function playDefense(root: Sim, model: LinearModel, seed: number, opts: PolicyOptions = {}): DefensePlay {
  const t0 = Date.now();
  const mover = root.state.activePlayer;
  const start = prizesLeft(root.state.players[mover]);
  const pred = new Predictor(model);
  const groups = groupsFor(model);
  const only = new Set(model.names);
  const line: string[] = [];
  const steps: StepLog[] = [];
  let cur = root;
  let afterTurn: Sim | undefined;
  const judge = (s: Sim) => {
    const fv = features(s, mover, groups, { only });
    return Math.max(0, pred.predict(fv.names, fv.values));
  };
  for (let step = 0; step < (opts.maxSteps ?? 15); step++) {
    const kids = children(cur, mover, start, opts);
    if (!kids.length) {
      break;
    }
    const scored = kids.map((c, k) => {
      const after = c.terminal ? c.sim : passTurn(c.sim, seed + step * 101 + k);
      if (!after || after.finished) {
        // the game ended on our turn (we took the last prize): nothing to defend
        return { c, after, value: after?.finished ? 0 : Infinity, exact: !!after?.finished };
      }
      return { c, after, value: judge(after), exact: false };
    });
    scored.sort((a, b) => (a.value - b.value) || (Number(b.c.terminal) - Number(a.c.terminal)));
    const pick = scored[0];
    steps.push({
      chosen: pick.c.label, value: pick.value, exact: pick.exact,
      alternatives: scored.slice(1, 6).map(s => ({ label: s.c.label, value: s.value, exact: s.exact })),
    });
    line.push(pick.c.label);
    cur = pick.c.sim;
    if (pick.c.terminal) {
      afterTurn = pick.after;
      break;
    }
  }
  if (!afterTurn) {
    afterTurn = passTurn(cur, seed + 999);
    line.push('end turn');
  }
  return { prizes: start - prizesLeft(cur.state.players[mover]), line, steps, end: cur, afterTurn, ms: Date.now() - t0 };
}
