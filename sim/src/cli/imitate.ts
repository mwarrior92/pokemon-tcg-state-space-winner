// Learn a policy from real tournament play (match logs) and measure it on held-out matches.
//
//   node dist/imitate.js --name imit-v1                 # collect, cross-validate, fit, save
//   node dist/imitate.js --name imit-v1 --reuse         # reuse runs/imit-v1/decisions.jsonl
//   node dist/align.js --pilot imit:runs/imit-v1/policy.json --name align-imit-v1
//
// Collect: every match log in sim/data/matches is replayed (matchlog.ts); at each real state the
// turn search's candidate steps are described (imitate.ts) and the real choice marked. Scored states
// are the stated actions (inferred ones are left out, as in align.js).
// Cross-validation: one match (video) held out at a time; the share of held-out states where the
// top-scoring step is the real action or an interchangeable one, next to chance (picking a main
// action at random) and to the race pilot's first action on the same states (from an align run, if
// --compare runs/<align run> is given).
// Output in runs/<name>/: decisions.jsonl, policy.json (fitted on everything), report.md.
import * as fs from 'fs';
import * as path from 'path';
import { REPO_ROOT, loadCards } from '../cards';
import { Decision, TrainRow, candidates, fitPolicy, positives } from '../imitate';
import { Step, loadLogs, replayLog } from '../matchlog';
import { Predictor, saveModel } from '../model';

function arg(name: string, dflt: string): string {
  const i = process.argv.indexOf(`--${name}`);
  return i >= 0 ? process.argv[i + 1] : dflt;
}
const pct = (n: number, d: number) => (d ? `${Math.round((100 * n) / d)}%` : '-');

interface Row extends TrainRow {
  source: string;
  mains: string[];
  step: Step;
}

function main(): void {
  loadCards();
  const name = arg('name', 'imit-v1');
  const dir = path.join(REPO_ROOT, 'sim', 'runs', name);
  fs.mkdirSync(dir, { recursive: true });
  const logs = loadLogs(path.resolve(REPO_ROOT, arg('logs', 'sim/data/matches')));
  const dataFile = path.join(dir, 'decisions.jsonl');
  let names: string[] = [];
  const rows: Row[] = [];
  if (process.argv.includes('--reuse') && fs.existsSync(dataFile)) {
    for (const l of fs.readFileSync(dataFile, 'utf8').split('\n').filter(Boolean)) {
      const r = JSON.parse(l);
      names = r.names;
      rows.push(r.row);
    }
  } else {
    const out: string[] = [];
    for (const { id, log } of logs) {
      const t0 = Date.now();
      const got = new Map<number, Decision>();
      let res;
      try {
        res = replayLog(log, id, (s, key) => {
          const c = candidates(s, { seed: key });
          got.set(key, { game: id, key, names: c.names, cands: c.cands.map(x => ({ label: x.label, main: x.main, x: x.x })) });
          return ['end turn'];
        }, 1);
      } catch (e) {
        console.log(`${id}: skipped (${(e as Error).message})`);
        continue;
      }
      let n = 0;
      for (const st of res.steps) {
        const d = got.get(1000 + st.turn * 37 + st.k);
        if (!d || st.inferred || !d.cands.length) {
          continue;
        }
        names = d.names;
        const pos = positives(d.cands, st.real, st.realFull, st.admissible);
        const row: Row = { game: id, source: log.source, x: d.cands.map(c => c.x), pos, mains: d.cands.map(c => c.main), step: { ...st, board: '' } };
        rows.push(row);
        out.push(JSON.stringify({ names, row }));
        n++;
      }
      console.log(`${id}: ${n} states (${((Date.now() - t0) / 1000).toFixed(0)} s)`);
    }
    fs.writeFileSync(dataFile, out.join('\n') + '\n');
  }
  const usable = rows.filter(r => r.pos.some(Boolean));
  console.log(`${rows.length} states, ${usable.length} with the real action among the candidates, ${new Set(rows.map(r => r.source)).size} matches`);

  // top-1: the best candidate's main action is admissible
  const hit = (model: ReturnType<typeof fitPolicy>, r: Row) => {
    const p = new Predictor(model);
    let best = 0, bv = -Infinity;
    r.x.forEach((x, i) => {
      const s = p.predict(names, x);
      if (s > bv) {
        bv = s;
        best = i;
      }
    });
    return { main: r.step.admissible.includes(r.mains[best]), full: r.pos[best] && r.mains[best] === r.step.real };
  };
  const chance = (r: Row) => {
    const mains = [...new Set(r.mains)];
    return mains.filter(m => r.step.admissible.includes(m)).length / mains.length;
  };
  const sources = [...new Set(usable.map(r => r.source))];
  // cross-validation folds: whole matches (videos), dealt into --folds groups
  const nFolds = Math.min(Number(arg('folds', '5')), sources.length);
  const foldOf = new Map(sources.slice().sort().map((s, i) => [s, i % nFolds]));
  const lambdas = arg('lambdas', '0.1,1,3').split(',').map(Number);
  const cv: { lambda: number; main: number; full: number }[] = [];
  for (const lambda of lambdas) {
    let m = 0, f = 0;
    for (let k = 0; k < nFolds; k++) {
      const model = fitPolicy(names, usable.filter(r => foldOf.get(r.source) !== k), { lambda });
      for (const r of usable.filter(r => foldOf.get(r.source) === k)) {
        const h = hit(model, r);
        m += h.main ? 1 : 0;
        f += h.full ? 1 : 0;
      }
    }
    cv.push({ lambda, main: m / usable.length, full: f / usable.length });
    console.log(`lambda ${lambda}: held-out top-1 ${pct(m, usable.length)} (with the real choices ${pct(f, usable.length)})`);
  }
  const best = cv.reduce((a, b) => (b.main > a.main ? b : a));
  const model = fitPolicy(names, usable, { lambda: best.lambda });
  model.metrics = { heldOutTop1: best.main, heldOutFull: best.full, states: usable.length, matches: sources.length };
  saveModel(model, path.join(dir, 'policy.json'));

  // the race pilot on the same states, from an align run
  let raceLine = '';
  const cmp = arg('compare', '');
  if (cmp) {
    const f = path.resolve(REPO_ROOT, 'sim', cmp, 'steps.jsonl');
    if (fs.existsSync(f)) {
      const al: Step[] = fs.readFileSync(f, 'utf8').split('\n').filter(Boolean).map(l => JSON.parse(l));
      const key = (s: Step) => `${s.game}|${s.turn}|${s.k}`;
      const want = new Set(usable.map(r => key(r.step)));
      const same = al.filter(s => want.has(key(s)));
      raceLine = `| ${cmp} (first action of its planned line) | ${same.length} | ${pct(same.filter(s => s.aligned).length, same.length)} |`;
    }
  }
  const L = [`# Imitation policy: ${name}`, '',
    `${usable.length} real states (stated actions) from ${sources.length} matches (${logs.length} game logs). Each state's candidates are the turn search's steps (action + prompt answers); the policy scores them by the change in the mover's features, the kind of action and Trainer, and prizes taken.`, '',
    '| | states | top choice is the real action (or interchangeable) |', '|---|---|---|',
    `| policy, held out by match (${nFolds} folds, λ ${best.lambda}) | ${usable.length} | **${pct(Math.round(best.main * usable.length), usable.length)}** (same prompt answers too: ${pct(Math.round(best.full * usable.length), usable.length)}) |`,
    `| chance (a random main action) | ${usable.length} | ${pct(Math.round(usable.reduce((s, r) => s + chance(r), 0)), usable.length)} |`];
  if (raceLine) {
    L.push(raceLine);
  }
  L.push('', `Cross-validation over λ: ${cv.map(c => `${c.lambda}: ${pct(Math.round(c.main * usable.length), usable.length)}`).join(', ')}.`, '',
    '## Largest weights (standardized)', '');
  model.names.map((n, i) => ({ n, w: model.weights[i] })).sort((a, b) => Math.abs(b.w) - Math.abs(a.w)).slice(0, 25)
    .forEach(x => L.push(`- ${x.w >= 0 ? '+' : ''}${x.w.toFixed(2)} ${x.n}`));
  fs.writeFileSync(path.join(dir, 'report.md'), L.join('\n') + '\n');
  console.log(`policy: ${path.join(dir, 'policy.json')}\nreport: ${path.join(dir, 'report.md')}`);
}

main();
