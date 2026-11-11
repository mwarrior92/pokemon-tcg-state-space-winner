// Imitation of real play: a policy that scores the next step of a turn the way tournament players
// chose, learned from the match logs (matchlog.ts).
//
// At every real state of a replayed log, the turn search's candidate steps (children(): each main
// action with its prompt answers, and the position it leads to) are described by
//  - how the step changes the mover's cheap feature vector (after minus before),
//  - the kind of action, and for Trainers whether it is an Item, Supporter, Stadium or Tool,
//  - the prize cards it took.
// A linear score over these is fitted with a softmax: the real step (or any real step that was
// interchangeable with it, see matchlog.ts) should score above the other candidates. Positives: the
// candidates whose main action is one of the admissible real actions; for the real action itself,
// only the candidates with the real prompt answers when one of them has them.
//
// The model is a LinearModel (model.ts, target "policy ..."), so Predictor scores a candidate.
// The `imit:<model>` pilot plays the top-scoring step until its turn ends (playgame.ts).
import { CHEAP_GROUPS, features } from './features';
import { LinearModel, Predictor } from './model';
import { prizesLeft } from './rules';
import { Child, children } from './search';
import { Sim } from './sim';
import { TrainerCard, TrainerType } from './engine';

const KINDS = ['play', 'attach', 'evolve', 'bench', 'tool', 'stadium', 'ability', 'retreat', 'attack', 'pass'] as const;
const TRAINERS = ['item', 'supporter', 'stadium', 'tool'] as const;

export interface Candidate {
  label: string;
  main: string;
  x: number[];
}

export interface Decision {
  game: string;
  key: number;          // the state's seed in replayLog (links the step)
  names: string[];
  cands: Candidate[];
}

const mainOf = (label: string) => label.split(' | ')[0];

function trainerKind(sim: Sim, label: string): string | undefined {
  const m = /^play (.*)$/.exec(mainOf(label));
  if (!m) {
    return undefined;
  }
  const me = sim.state.players[sim.state.activePlayer];
  const c = me.hand.cards.find(x => x.name === m[1]);
  if (!(c instanceof TrainerCard)) {
    return undefined;
  }
  return c.trainerType === TrainerType.SUPPORTER ? 'supporter' : c.trainerType === TrainerType.STADIUM ? 'stadium' : c.trainerType === TrainerType.TOOL ? 'tool' : 'item';
}

/** Feature names and values of one candidate step from `sim` (mover to act). */
export function candidateVector(sim: Sim, before: { names: string[]; values: number[] }, c: Child, mover: number, startPrizes: number): { names: string[]; values: number[] } {
  const after = c.sim === sim ? before : features(c.sim, mover, CHEAP_GROUPS);
  const idx = new Map(after.names.map((n, i) => [n, i]));
  const names: string[] = [], values: number[] = [];
  before.names.forEach((n, i) => {
    names.push(`d.${n}`);
    const j = idx.get(n);
    values.push((j === undefined ? 0 : after.values[j]) - before.values[i]);
  });
  for (const k of KINDS) {
    names.push(`kind.${k}`);
    values.push(c.kind === k ? 1 : 0);
  }
  const tk = trainerKind(sim, c.label);
  for (const t of TRAINERS) {
    names.push(`trainer.${t}`);
    values.push(tk === t ? 1 : 0);
  }
  names.push('prizes', 'terminal');
  values.push(startPrizes - prizesLeft(c.sim.state.players[mover]) - (startPrizes - prizesLeft(sim.state.players[mover])), c.terminal ? 1 : 0);
  return { names, values };
}

/** Every candidate step from `sim` with its vector (the mover is the player to act). */
export function candidates(sim: Sim, opts: { promptCap?: number; branchCap?: number; seed?: number } = {}): { names: string[]; cands: (Candidate & { child: Child })[] } {
  const mover = sim.state.activePlayer;
  const start = prizesLeft(sim.state.players[mover]);
  const before = features(sim, mover, CHEAP_GROUPS);
  const kids = children(sim, mover, start, { promptCap: opts.promptCap ?? 6, branchCap: opts.branchCap ?? 12, seed: opts.seed ?? 1, cheapPass: true });
  let names: string[] = [];
  const cands = kids.map(k => {
    const v = candidateVector(sim, before, k, mover, start);
    names = v.names;
    return { label: k.label, main: mainOf(k.label), x: v.values, child: k };
  });
  return { names, cands };
}

/** Which candidates count as the real choice: the main action is admissible; for the real main
 *  action, only the candidates with the real prompt answers when any has them. */
export function positives(cands: Candidate[], real: string, realFull: string, admissible: string[]): boolean[] {
  const exactFull = cands.some(c => c.label === realFull);
  return cands.map(c => (c.main === real ? (!exactFull || c.label === realFull) : admissible.includes(c.main)));
}

export interface TrainRow {
  game: string;
  x: number[][];
  pos: boolean[];
}

/** Softmax regression with multiple positives and an L2 penalty, by Adam on standardized features. */
export function fitPolicy(names: string[], rows: TrainRow[], o: { lambda?: number; epochs?: number; lr?: number } = {}): LinearModel {
  const d = names.length;
  const all = rows.flatMap(r => r.x);
  const mean = Array(d).fill(0), scale = Array(d).fill(0);
  for (const x of all) {
    x.forEach((v, j) => (mean[j] += v / all.length));
  }
  for (const x of all) {
    x.forEach((v, j) => (scale[j] += (v - mean[j]) ** 2 / all.length));
  }
  for (let j = 0; j < d; j++) {
    scale[j] = Math.sqrt(scale[j]) || 1;
  }
  const Z = rows.map(r => r.x.map(x => x.map((v, j) => (v - mean[j]) / scale[j])));
  const w = Array(d).fill(0);
  const m1 = Array(d).fill(0), m2 = Array(d).fill(0);
  const lambda = o.lambda ?? 0.01, lr = o.lr ?? 0.05, epochs = o.epochs ?? 300;
  const usable = rows.map((r, i) => i).filter(i => rows[i].pos.some(Boolean) && rows[i].pos.some(p => !p));
  for (let ep = 1; ep <= epochs; ep++) {
    const g = w.map(v => lambda * v);
    for (const i of usable) {
      const z = Z[i].map(x => x.reduce((s, v, j) => s + v * w[j], 0));
      const mx = Math.max(...z);
      const e = z.map(v => Math.exp(v - mx));
      const sAll = e.reduce((a, b) => a + b, 0);
      const sPos = e.reduce((a, b, k) => a + (rows[i].pos[k] ? b : 0), 0);
      // d/dw [log sum_all - log sum_pos] = E_all[x] - E_pos[x]
      Z[i].forEach((x, k) => {
        const c = e[k] / sAll - (rows[i].pos[k] ? e[k] / sPos : 0);
        if (c !== 0) {
          x.forEach((v, j) => (g[j] += (c * v) / usable.length));
        }
      });
    }
    for (let j = 0; j < d; j++) {
      m1[j] = 0.9 * m1[j] + 0.1 * g[j];
      m2[j] = 0.999 * m2[j] + 0.001 * g[j] * g[j];
      w[j] -= (lr * (m1[j] / (1 - 0.9 ** ep))) / (Math.sqrt(m2[j] / (1 - 0.999 ** ep)) + 1e-8);
    }
  }
  return { kind: 'linear', target: 'policy: score of a step (softmax over the steps from a position), fitted to real play', names, mean, scale, weights: w, bias: 0, lambda, trainedOn: usable.length };
}

/** Index of the top-scoring candidate. */
export function bestCandidate(model: LinearModel, names: string[], x: number[][]): number {
  const p = new Predictor(model);
  let best = 0, bv = -Infinity;
  x.forEach((v, i) => {
    const s = p.predict(names, v);
    if (s > bv) {
      bv = s;
      best = i;
    }
  });
  return best;
}

/** The imitation pilot's line from `sim`: the top-scoring step, again and again, until the turn
 *  ends (at most `maxSteps` steps; then it passes). */
export function imitationLine(sim: Sim, model: LinearModel, seed = 1, maxSteps = 25): { line: string[]; end: Sim } {
  const mover = sim.state.activePlayer;
  let cur = sim;
  const line: string[] = [];
  for (let k = 0; k < maxSteps && !cur.finished && cur.state.activePlayer === mover; k++) {
    const { names, cands } = candidates(cur, { seed: seed + k });
    if (!cands.length) {
      break;
    }
    const i = bestCandidate(model, names, cands.map(c => c.x));
    line.push(cands[i].label);
    if (cands[i].child.terminal || cands[i].main === 'end turn') {
      if (cands[i].main !== 'end turn') {
        cur = cands[i].child.sim;
      }
      break;
    }
    cur = cands[i].child.sim;
  }
  return { line, end: cur };
}
