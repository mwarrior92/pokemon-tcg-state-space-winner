// Training round for the offensive or defensive turn player.
//
//   node dist/train.js offense [--states 400] [--eval 60] [--budget 3000] [--workers auto] [--run name] [--seed n] [--data dir,...]
//   (a run is resumable: rerun the same command and finished states are skipped)
//   node dist/train.js defense [...]
//
// One round:
//   1. label     generated states (stategen) -> exhaustive search -> positions with exact values
//                offense: prizes the mover can still take this turn from that position
//                defense: prizes the opponent takes on their next turn after we end ours there
//   2. fit       linear value model on all features, validated on held-out states
//   3. reduce    feature reduction: refit on cheaper feature sets and keep the cheapest one whose
//                validation error is within tolerance of the full model
//   4. evaluate  play fresh generated states with the fast policy and compare with the search
//   5. log       every evaluated turn to battles.jsonl, plus review-packet.md with aggregates and
//                the worst decisions, for the AI review step (see sim/REVIEW.md)
// Everything is written under sim/runs/<run>/.
import * as fs from 'fs';
import * as path from 'path';
import { REPO_ROOT, loadCards, metaDecks } from '../cards';
import { describeState } from '../describe';
import { ALL_GROUPS, CHEAP_GROUPS, Group, PROBE_GROUPS, features } from '../features';
import { LinearModel, fitRidge, importance, loadModel, mse, saveModel, selectColumns } from '../model';
import { passTurn, playDefense, playOffense, playOffenseSearch } from '../policy';
import { autoWorkers, isMainThread, runPool, serveJobs } from '../pool';
import { prizesLeft } from '../rules';
import { Rng } from '../rng';
import { offenseSearch } from '../search';
import { Sim } from '../sim';
import { generateState } from '../stategen';

type Objective = 'offense' | 'defense';

interface LabelJob { kind: 'label'; objective: Objective; seed: number; a: number; b: number; budget: number; perState: number; oppBudget: number }
interface Row { x: number[]; y: number; state: number; depth: number }
interface LabelResult { names: string[]; groups: Group[]; rows: Row[]; root: { value: number; complete: boolean; line: string[]; ms: number; turn: number }; heapMb?: number; seed?: number }
interface EvalJob { kind: 'eval'; objective: Objective; seed: number; a: number; b: number; budget: number; modelFile: string; oppBudget: number; policyBudget: number }

// ---------------------------------------------------------------- worker side

function stateFor(seed: number, a: number, b: number) {
  const decks = metaDecks();
  const rng = new Rng(seed);
  const g = generateState(decks[a].cards, decks[b].cards, rng);
  return { g, da: decks[a], db: decks[b] };
}

/** Prizes the player now to move can take this turn (exhaustive search). */
function oppPrizes(afterPass: Sim, budget: number): { value: number; complete: boolean } {
  const r = offenseSearch(afterPass, { budget });
  return { value: r.value, complete: r.complete };
}

function label(job: LabelJob): LabelResult {
  const { g } = stateFor(job.seed, job.a, job.b);
  const mover = g.sim.state.activePlayer;
  // positions to learn from: the root plus a uniform sample of the expanded positions (defense: of
  // all positions). Incomplete ones carry a lower bound (review offense-r1: complete-only labels
  // kept 393 of 1000 states and over-represented simple boards). Only the sampled positions keep
  // their state in memory.
  const r = offenseSearch(g.sim, {
    budget: job.budget, keepSims: job.perState - 1, sampleFrom: job.objective === 'defense' ? 'all' : 'expanded', sampleSeed: job.seed * 7 + 1,
  });
  const rows: Row[] = [];
  let names: string[] = [];
  let groups: Group[] = [];
  for (const n of r.sample) {
    let y: number;
    let at = n.sim!;
    if (job.objective === 'offense') {
      y = n.value;   // exact if the subtree was searched completely, else a lower bound
    } else {
      const after = passTurn(n.sim!, job.seed + n.depth);
      if (!after) {
        continue;
      }
      const o = oppPrizes(after, job.oppBudget);
      if (!o.complete && o.value === 0) {
        continue;    // unknown: the opponent's turn was not searched far enough
      }
      y = o.value;
      at = after;    // features of the position the opponent faces, from our side
    }
    const fv = features(at, mover, ALL_GROUPS);
    names = fv.names;
    groups = fv.groups;
    rows.push({ x: fv.values, y, state: job.seed, depth: n.depth });
  }
  return { names, groups, rows, root: { value: r.value, complete: r.complete, line: r.line, ms: r.ms, turn: g.info.turn }, heapMb: heapMb() };
}

export interface BattleLog {
  objective: Objective;
  seed: number;
  decks: [string, string];
  board: string;
  oracle: { value: number; complete: boolean; line: string[] };
  policy: { value: number; line: string[]; steps: any[]; ms: number };
  baseline?: { passNow: number };
  greedy?: { value: number; line: string[]; ms: number };
  gap: number;
  heapMb?: number;
}

function evaluate(job: EvalJob): BattleLog {
  const { g, da, db } = stateFor(job.seed, job.a, job.b);
  const model = loadModel(job.modelFile);
  const board = describeState(g.sim.state);
  if (job.objective === 'offense') {
    const r = offenseSearch(g.sim, { budget: job.budget, keepSims: 0 });
    // the policy is the search policy (review offense-r2); the greedy one is kept for comparison
    const greedy = playOffense(g.sim, model);
    const p = playOffenseSearch(g.sim, model, { budget: job.policyBudget });
    // reference = the best of search and policies (an incomplete search is not an upper bound)
    const ref = Math.max(r.value, p.prizes, greedy.prizes);
    return {
      objective: 'offense', seed: job.seed, decks: [da.archetype, db.archetype], board,
      oracle: { value: r.value, complete: r.complete, line: r.line },
      policy: { value: p.prizes, line: p.line, steps: p.steps, ms: p.ms },
      greedy: { value: greedy.prizes, line: greedy.line, ms: greedy.ms },
      gap: ref - p.prizes, heapMb: heapMb(),
    };
  }
  // defense: opponent's best next turn after our policy's turn, vs. after simply passing, vs. the
  // best end position among a sample of our searched positions (an approximate optimum)
  const p = playDefense(g.sim, model, job.seed);
  const after = p.afterTurn;
  const policyValue = after ? oppPrizes(after, job.oppBudget).value : 0;
  const passed = passTurn(g.sim, job.seed);
  const passNow = passed ? oppPrizes(passed, job.oppBudget).value : 0;
  const r = offenseSearch(g.sim, { budget: Math.min(job.budget, 400), keepSims: 12, sampleFrom: 'all', sampleSeed: job.seed });
  let best = Math.min(policyValue, passNow);
  let bestLine: string[] = ['(end turn immediately)'];
  for (const n of r.sample.slice(1)) {
    const a = passTurn(n.sim!, job.seed + 3);
    if (!a) {
      continue;
    }
    const v = oppPrizes(a, job.oppBudget).value;
    if (v < best) {
      best = v;
      bestLine = [`(a searched position at depth ${n.depth}; key ${n.key.slice(0, 40)}...)`];
    }
  }
  return {
    objective: 'defense', seed: job.seed, decks: [da.archetype, db.archetype], board,
    oracle: { value: best, complete: false, line: bestLine },
    policy: { value: policyValue, line: p.line, steps: p.steps, ms: p.ms },
    baseline: { passNow },
    gap: policyValue - best, heapMb: heapMb(),
  };
}

/** this worker's live JS heap, MB (reported with every result so the main thread can log it) */
function heapMb(): number {
  return Math.round(process.memoryUsage().heapUsed / 1e6);
}

serveJobs((job: LabelJob | EvalJob) => {
  loadCards();
  return job.kind === 'label' ? { ...label(job), seed: job.seed } : evaluate(job);
});

// ---------------------------------------------------------------- main side

function arg(name: string, dflt: string): string {
  const i = process.argv.indexOf(`--${name}`);
  return i >= 0 ? process.argv[i + 1] : dflt;
}

function readJsonl<T>(file: string): T[] {
  if (!fs.existsSync(file)) {
    return [];
  }
  return fs.readFileSync(file, 'utf8').split('\n').filter(l => l.trim()).flatMap(l => {
    try {
      return [JSON.parse(l) as T];
    } catch {
      return [];     // a line cut off by an interruption
    }
  });
}

/** Progress line every `every` results: count, elapsed, time for the last window (so a slowdown
 *  shows), mean job time inside a worker, and the largest worker heap seen in the window. */
function progressLogger(log: (s: string) => void, what: string, total: number, t0: number, every = 50) {
  let done = 0;
  let lastT = t0;
  let maxHeap = 0;
  let jobMs = 0;
  return (heap: number, ms: number) => {
    done++;
    maxHeap = Math.max(maxHeap, heap);
    jobMs += ms;
    if (done % every === 0 || done === total) {
      const now = Date.now();
      const n = done % every === 0 ? every : done % every;
      log(`  ${what} ${done}/${total} (${((now - t0) / 1000).toFixed(0)} s; last ${n} in ${((now - lastT) / 1000).toFixed(0)} s, ${(jobMs / n / 1000).toFixed(1)} s/job in a worker; max worker heap ${maxHeap} MB)`);
      lastT = now;
      maxHeap = 0;
      jobMs = 0;
    }
  };
}

function cost(groups: Group[]): string {
  return groups.some(g => PROBE_GROUPS.includes(g)) ? 'probe' : 'cheap';
}

async function main(): Promise<void> {
  const objective = (process.argv[2] ?? 'offense') as Objective;
  const nStates = Number(arg('states', '400'));
  const nEval = Number(arg('eval', '60'));
  const budget = Number(arg('budget', '3000'));
  const oppBudget = Number(arg('opp-budget', '600'));
  const policyBudget = Number(arg('policy-budget', '100'));
  // default: as many workers as cores and free memory allow (round 2 swapped with 18 workers)
  const workers = arg('workers', 'auto') === 'auto' ? autoWorkers() : Number(arg('workers', '0'));
  const perState = Number(arg('per-state', '10'));
  const run = arg('run', `${objective}-${new Date().toISOString().replace(/[:.]/g, '-').slice(0, 19)}`);
  const reuse = arg('data', '').split(',').filter(Boolean);
  const dir = path.join(REPO_ROOT, 'sim', 'runs', run);
  fs.mkdirSync(dir, { recursive: true });
  loadCards();
  const decks = metaDecks();
  const script = __filename;
  // default seed from the run name, so rerunning the same command resumes the same states
  const seedBase = Number(arg('seed', String([...run].reduce((h, ch) => (h * 31 + ch.charCodeAt(0)) % 999983, 7))));
  const pairRng = new Rng(seedBase);
  const mkJobs = (n: number, offset: number) => Array.from({ length: n }, (_, k) => ({
    seed: seedBase * 1000 + offset + k, a: pairRng.int(0, decks.length - 1), b: pairRng.int(0, decks.length - 1),
  }));
  const log = (s: string) => {
    console.log(s);
    fs.appendFileSync(path.join(dir, 'log.txt'), s + '\n');
  };
  log(`# ${objective} round "${run}": ${nStates} states to label, ${nEval} to evaluate, search budget ${budget}, ${workers} workers`);

  // 1. label
  const t0 = Date.now();
  let names: string[] = [];
  let groups: Group[] = [];
  let rows: Row[] = [];
  const roots: LabelResult['root'][] = [];
  for (const r of reuse) {
    const d = JSON.parse(fs.readFileSync(path.join(REPO_ROOT, 'sim', 'runs', r, 'data.json'), 'utf8'));
    names = d.names;
    groups = d.groups;
    rows.push(...d.rows);
    log(`reused ${d.rows.length} labelled positions from ${r}`);
  }
  // every labelled state is appended to labels.jsonl as it arrives; a rerun with the same --run
  // and --seed skips the states already there (resume after an interruption)
  const allLabelJobs: LabelJob[] = mkJobs(nStates, 0).map(j => ({ kind: 'label', objective, budget, perState, oppBudget, ...j }));
  const labelFile = path.join(dir, 'labels.jsonl');
  const labelled: LabelResult[] = readJsonl<LabelResult>(labelFile);
  const doneSeeds = new Set(labelled.map(r => r.seed));
  const labelJobs = allLabelJobs.filter(j => !doneSeeds.has(j.seed));
  if (labelled.length) {
    log(`resuming: ${labelled.length} states already labelled in ${labelFile}, ${labelJobs.length} to go`);
  }
  const progress = progressLogger(log, 'labelled', labelJobs.length, t0);
  await runPool<LabelJob, LabelResult>(script, labelJobs, {
    workers,
    onResult: r => {
      fs.appendFileSync(labelFile, JSON.stringify(r) + '\n');
      labelled.push(r);
      progress(r.heapMb ?? 0, r.root.ms);
    },
  });
  for (const r of labelled) {
    if (!r || !r.rows.length) {
      continue;
    }
    if (!names.length) {
      names = r.names;
      groups = r.groups;
    }
    if (r.names.length !== names.length) {
      continue;   // feature list changed between runs; skip mismatched rows
    }
    rows.push(...r.rows);
    roots.push(r.root);
  }
  fs.writeFileSync(path.join(dir, 'data.json'), JSON.stringify({ names, groups, rows }));
  const complete = roots.filter(r => r.complete).length;
  log(`labelled ${rows.length} positions from ${roots.length} states in ${((Date.now() - t0) / 1000).toFixed(0)} s; searches complete ${complete}/${roots.length}; mean root value ${(roots.reduce((s, r) => s + r.value, 0) / Math.max(1, roots.length)).toFixed(2)}`);
  const yDist = new Map<number, number>();
  rows.forEach(r => yDist.set(r.y, (yDist.get(r.y) ?? 0) + 1));
  log(`target distribution: ${[...yDist.entries()].sort((a, b) => a[0] - b[0]).map(([k, v]) => `${k}:${v}`).join(' ')}`);

  // 2. fit, validated on held-out *states* (positions from one state never straddle the split)
  const stateIds = [...new Set(rows.map(r => r.state))];
  const valSet = new Set(stateIds.filter((_, i) => i % 5 === 0));
  const tr = rows.filter(r => !valSet.has(r.state));
  const va = rows.filter(r => valSet.has(r.state));
  const Xtr = tr.map(r => r.x), ytr = tr.map(r => r.y), Xva = va.map(r => r.x), yva = va.map(r => r.y);
  const baseMse = (() => {
    const m = ytr.reduce((s, v) => s + v, 0) / Math.max(1, ytr.length);
    return yva.reduce((s, v) => s + (v - m) ** 2, 0) / Math.max(1, yva.length);
  })();
  const target = objective === 'offense' ? 'prizes the mover can still take this turn' : "prizes the opponent takes on their next turn";
  const fitSet = (label: string, keep: (n: string, i: number) => boolean): { label: string; model: LinearModel; val: number; n: number; groups: Group[] } => {
    const a = selectColumns(names, Xtr, keep);
    const b = selectColumns(names, Xva, keep);
    let bestM: LinearModel | undefined;
    let bestV = Infinity;
    for (const lambda of [1, 10, 100, 1000, 10000]) {
      const m = fitRidge(a.X, ytr, a.names, lambda, target);
      const v = mse(m, b.X, yva);
      if (v < bestV) {
        bestV = v;
        bestM = m;
      }
    }
    const gs = [...new Set(a.names.map(n => groups[names.indexOf(n)]))];
    bestM!.groups = a.names.map(n => groups[names.indexOf(n)]);
    bestM!.metrics = { valMse: bestV, baselineMse: baseMse, r2: 1 - bestV / baseMse, train: tr.length, val: va.length };
    return { label, model: bestM!, val: bestV, n: a.names.length, groups: gs };
  };
  const full = fitSet('all features', () => true);
  log(`fit: all ${full.n} features: validation MSE ${full.val.toFixed(3)} (predicting the mean: ${baseMse.toFixed(3)}, R² ${(1 - full.val / baseMse).toFixed(3)})`);

  // 3. feature reduction: cheaper sets, then the top features by importance within the cheapest
  const imp = importance(full.model);
  const candidates = [
    full,
    fitSet('cheap groups only (no engine probes)', (_n, i) => CHEAP_GROUPS.includes(groups[i])),
    ...PROBE_GROUPS.map(pg => fitSet(`all but ${pg}`, (_n, i) => groups[i] !== pg)),
    fitSet('cheap + probe-damage', (_n, i) => CHEAP_GROUPS.includes(groups[i]) || groups[i] === 'probe-damage'),
    ...[200, 100, 50, 25].map(k => {
      const top = new Set(imp.slice(0, k).map(x => x.name));
      return fitSet(`top ${k} features by importance`, n => top.has(n));
    }),
    // the same restricted to cheap features (no engine probes at play time)
    ...[200, 100, 50].map(k => {
      const top = new Set(imp.filter(x => CHEAP_GROUPS.includes(groups[names.indexOf(x.name)])).slice(0, k).map(x => x.name));
      return fitSet(`top ${k} cheap features by importance`, n => top.has(n));
    }),
    fitSet('reach + board + resources only', (_n, i) => ['reach', 'board', 'resources', 'turn'].includes(groups[i])),
  ];
  const tol = 1.05;
  log('\nfeature reduction (validation MSE; lower is better):');
  for (const c of candidates) {
    log(`  ${c.label.padEnd(40)} ${String(c.n).padStart(5)} features  [${cost(c.groups)}]  MSE ${c.val.toFixed(3)}  R² ${(1 - c.val / baseMse).toFixed(3)}`);
  }
  // pick (review offense-r1): the best cheap set, unless a probe set beats it by more than 10%;
  // within a cost class, the smallest set within tolerance of that class's best
  const cheapSets = candidates.filter(c => cost(c.groups) === 'cheap');
  const probeSets = candidates.filter(c => cost(c.groups) !== 'cheap');
  const bestOf = (xs: typeof candidates) => {
    const m = Math.min(...xs.map(c => c.val));
    return xs.filter(c => c.val <= m * tol).sort((a, b) => a.n - b.n)[0];
  };
  const bestCheap = cheapSets.length ? bestOf(cheapSets) : undefined;
  const bestProbe = probeSets.length ? bestOf(probeSets) : undefined;
  const chosen = !bestCheap ? (bestProbe ?? full) : (bestProbe && bestProbe.val < bestCheap.val * 0.9 ? bestProbe : bestCheap);
  log(`chosen: "${chosen.label}" (${chosen.n} features, ${cost(chosen.groups)})`);
  const modelFile = path.join(dir, 'model.json');
  saveModel(chosen.model, modelFile);
  saveModel(full.model, path.join(dir, 'model-full.json'));
  log('\ntop features of the full model (weight on a standardized scale):');
  imp.slice(0, 25).forEach(x => log(`  ${x.weight >= 0 ? '+' : '-'}${x.abs.toFixed(3)}  ${x.name}`));

  // 4. evaluate on fresh states
  const t1 = Date.now();
  // evaluated turns are appended to battles.jsonl as they finish (resumable like the labels; a
  // resumed round refits the same model from the same labels, so earlier battles stay comparable)
  const allEvalJobs: EvalJob[] = mkJobs(nEval, 500000).map(j => ({ kind: 'eval', objective, budget, oppBudget, modelFile, policyBudget, ...j }));
  const battleFile = path.join(dir, 'battles.jsonl');
  const battles = readJsonl<BattleLog>(battleFile);
  const doneEval = new Set(battles.map(b => b.seed));
  const evalJobs = allEvalJobs.filter(j => !doneEval.has(j.seed));
  if (battles.length) {
    log(`resuming: ${battles.length} turns already evaluated, ${evalJobs.length} to go`);
  }
  const evalProgress = progressLogger(log, 'evaluated', evalJobs.length, t1, 10);
  await runPool<EvalJob, BattleLog>(script, evalJobs, {
    workers,
    onResult: b => {
      fs.appendFileSync(battleFile, JSON.stringify(b) + '\n');
      battles.push(b);
      evalProgress(b.heapMb ?? 0, b.policy.ms);
    },
  });
  const mean = (f: (b: BattleLog) => number) => battles.reduce((s, b) => s + f(b), 0) / Math.max(1, battles.length);
  log(`\nevaluation on ${battles.length} fresh states (${((Date.now() - t1) / 1000).toFixed(0)} s):`);
  if (objective === 'offense') {
    log(`  search found ${mean(b => b.oracle.value).toFixed(2)} prizes/turn, policy took ${mean(b => b.policy.value).toFixed(2)}; policy at least as good as the search on ${battles.filter(b => b.policy.value >= b.oracle.value).length}/${battles.length}; policy beat the search on ${battles.filter(b => b.policy.value > b.oracle.value).length}; mean gap to the best ${mean(b => b.gap).toFixed(2)}; policy ${(mean(b => b.policy.ms) / 1000).toFixed(2)} s/turn (search policy, budget ${policyBudget})`);
    log(`  greedy policy (round-2 style): ${mean(b => b.greedy?.value ?? 0).toFixed(2)} prizes/turn, at least as good as the search on ${battles.filter(b => (b.greedy?.value ?? 0) >= b.oracle.value).length}/${battles.length}, ${(mean(b => b.greedy?.ms ?? 0) / 1000).toFixed(2)} s/turn`);
  } else {
    log(`  opponent's next-turn prizes: after policy ${mean(b => b.policy.value).toFixed(2)}, after passing at once ${mean(b => b.baseline!.passNow).toFixed(2)}, best sampled ${mean(b => b.oracle.value).toFixed(2)}; policy ${(mean(b => b.policy.ms) / 1000).toFixed(2)} s/turn`);
  }
  writePacket(dir, objective, battles, candidates.map(c => ({ label: c.label, n: c.n, cost: cost(c.groups), val: c.val })), chosen.label, imp.slice(0, 40), baseMse);
  log(`\nreview packet: ${path.join(dir, 'review-packet.md')}`);
}

function writePacket(dir: string, objective: Objective, battles: BattleLog[], sets: { label: string; n: number; cost: string; val: number }[],
  chosen: string, imp: { name: string; weight: number }[], baseMse: number): void {
  const L: string[] = [];
  const mean = (f: (b: BattleLog) => number) => battles.reduce((s, b) => s + f(b), 0) / Math.max(1, battles.length);
  L.push(`# Review packet: ${objective}`);
  L.push('');
  L.push(`${battles.length} evaluated turns. Read the worst decisions below, decide what the policy is getting wrong and why, and write the reasoning and the changes to make in sim/reviews/ (see sim/REVIEW.md).`);
  L.push('');
  if (objective === 'offense') {
    L.push(`- search (teacher): ${mean(b => b.oracle.value).toFixed(2)} prizes/turn; policy: ${mean(b => b.policy.value).toFixed(2)}; policy matched the search on ${battles.filter(b => b.gap <= 0).length}/${battles.length}`);
  } else {
    L.push(`- opponent's next-turn prizes after the policy's turn: ${mean(b => b.policy.value).toFixed(2)}; after passing at once: ${mean(b => b.baseline!.passNow).toFixed(2)}; best of a sample of positions: ${mean(b => b.oracle.value).toFixed(2)}`);
  }
  L.push('');
  L.push('## Feature sets (validation MSE; predicting the mean gives ' + baseMse.toFixed(3) + ')');
  L.push('');
  L.push('| set | features | cost | MSE |');
  L.push('|---|---|---|---|');
  sets.forEach(s => L.push(`| ${s.label}${s.label === chosen ? ' **(chosen)**' : ''} | ${s.n} | ${s.cost} | ${s.val.toFixed(3)} |`));
  L.push('');
  L.push('## Largest weights (full model)');
  L.push('');
  imp.forEach(x => L.push(`- ${x.weight >= 0 ? '+' : ''}${x.weight.toFixed(3)} \`${x.name}\``));
  L.push('');
  L.push('## Worst decisions');
  const worst = battles.slice().sort((a, b) => b.gap - a.gap).filter(b => b.gap > 0).slice(0, 12);
  if (!worst.length) {
    L.push('');
    L.push('(none: the policy matched the reference on every turn)');
  }
  for (const b of worst) {
    L.push('');
    L.push(`### ${b.decks[0]} vs ${b.decks[1]} (seed ${b.seed}) - gap ${b.gap}`);
    L.push('');
    L.push('```');
    L.push(b.board);
    L.push('```');
    L.push(`- reference (${b.objective === 'offense' ? 'search' : 'best sampled'}): ${b.oracle.value} - ${b.oracle.line.join(' -> ')}`);
    L.push(`- policy: ${b.policy.value} - ${b.policy.line.join(' -> ')}`);
    for (const s of b.policy.steps) {
      L.push(`  - chose \`${s.chosen}\` (${s.exact ? 'exact' : 'predicted'} ${Number(s.value).toFixed(2)}); others: ${s.alternatives.map((a: any) => `\`${a.label}\` ${Number(a.value).toFixed(2)}`).join(', ')}`);
    }
  }
  fs.writeFileSync(path.join(dir, 'review-packet.md'), L.join('\n') + '\n');
}

if (isMainThread) {
  main().catch(e => {
    console.error(e);
    process.exitCode = 1;
  });
}

void prizesLeft;
void PROBE_GROUPS;
