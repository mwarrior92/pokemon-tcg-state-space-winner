// Fit the win-probability model on a playout run (needs --vectors) and report how well it predicts
// held-out games, against a baseline that only knows the prize counts.
//   node dist/fitvalue.js [run=playout-v0] [--with otherRun,...] [--out dir]
// Writes <out>/value-model.json and <out>/value-report.md (out defaults to runs/<run>). Games from
// the --with runs are added (they must have the same feature names).
import * as fs from 'fs';
import * as path from 'path';
import { REPO_ROOT } from '../cards';
import { importance, saveModel } from '../model';
import { WinModel, auc, fitLogistic, logLoss } from '../value';

const run = process.argv[2] ?? 'playout-v0';
const argOf = (n: string) => {
  const i = process.argv.indexOf(`--${n}`);
  return i >= 0 ? process.argv[i + 1] : undefined;
};
const runsDir = path.join(REPO_ROOT, 'sim', 'runs');
const runs = [run, ...(argOf('with') ?? '').split(',').filter(Boolean)];
const dir = path.join(runsDir, argOf('out') ?? run);
fs.mkdirSync(dir, { recursive: true });
const names: string[] = JSON.parse(fs.readFileSync(path.join(runsDir, run, 'feature-names.json'), 'utf8'));
const games: any[] = [];
for (const r of runs) {
  const nm: string[] = JSON.parse(fs.readFileSync(path.join(runsDir, r, 'feature-names.json'), 'utf8'));
  if (nm.join('|') !== names.join('|')) {
    throw new Error(`${r}: different feature names`);
  }
  games.push(...fs.readFileSync(path.join(runsDir, r, 'games.jsonl'), 'utf8').split('\n').filter(Boolean).map(l => JSON.parse(l)));
}
const rows: { x: number[]; y: number; g: number }[] = [];
games.forEach((g: any, gi: number) => {
  if (g.winner !== 0 && g.winner !== 1) {
    return;
  }
  for (const t of g.turns) {
    if (t.x) {
      rows.push({ x: t.x, y: g.winner === t.mover ? 1 : 0, g: gi });
    }
  }
});
const tr = rows.filter(r => r.g % 5 !== 0), va = rows.filter(r => r.g % 5 === 0);
const L: string[] = [];
const log = (s: string) => {
  console.log(s);
  L.push(s);
};
log(`# Win-probability model from ${runs.join(', ')}`);
log('');
log(`${rows.length} turn-start positions from ${new Set(rows.map(r => r.g)).size} decided games; ${tr.length} train, ${va.length} validation (by game).`);
log('');
const evaluate = (label: string, cols: number[]) => {
  const pick = (r: { x: number[] }) => cols.map(j => r.x[j]);
  const nm = cols.map(j => names[j]);
  let best: { m: any; ll: number; lambda: number } | undefined;
  for (const lambda of [1, 10, 100, 1000]) {
    const m = fitLogistic(tr.map(pick), tr.map(r => r.y), nm, lambda, 300, 'P(side to move wins)');
    const wm = new WinModel(m);
    const p = va.map(r => wm.prob(nm, pick(r)));
    const ll = logLoss(p, va.map(r => r.y));
    if (!best || ll < best.ll) {
      best = { m, ll, lambda };
    }
  }
  const wm = new WinModel(best!.m);
  const p = va.map(r => wm.prob(nm, pick(r)));
  const y = va.map(r => r.y);
  const acc = p.filter((pi, i) => (pi > 0.5 ? 1 : 0) === y[i]).length / p.length;
  log(`| ${label} | ${cols.length} | ${best!.ll.toFixed(3)} | ${auc(p, y).toFixed(3)} | ${(100 * acc).toFixed(1)}% | ${best!.lambda} |`);
  best!.m.metrics = { ...(best!.m.metrics ?? {}), valLogLoss: best!.ll };
  return best!.m;
};
const base = 1 - va.reduce((s, r) => s + r.y, 0) / va.length;
log(`Predicting 50% everywhere: log loss 0.693. Share of validation positions whose mover lost: ${(100 * base).toFixed(0)}%.`);
log('');
log('| model | features | log loss | AUC | accuracy | lambda |');
log('|---|---|---|---|---|---|');
const prizeCols = ['me.prizes', 'op.prizes'].map(n => names.indexOf(n)).filter(j => j >= 0);
evaluate('prize counts only', prizeCols);
const reachCols = names.map((n, j) => (/^(me|op)\.(prizes|reach\.|benchCount|hand|deck)/.test(n) ? j : -1)).filter(j => j >= 0);
const compact = evaluate('prizes + reach + bench/hand/deck', reachCols);
const all = names.map((_, j) => j);
const fullModel = evaluate('all cheap features', all);
// keep the one that predicts held-out games best
const full = (compact.metrics!.valLogLoss <= fullModel.metrics!.valLogLoss) ? compact : fullModel;
saveModel(full, path.join(dir, 'value-model.json'));
log('');
log(`saved: ${full === compact ? 'prizes + reach + bench/hand/deck' : 'all cheap features'} (lower validation log loss)`);
log('');
log('Largest weights of the saved model (standardized):');
importance(full).slice(0, 25).forEach(x => log(`- ${x.weight >= 0 ? '+' : ''}${x.weight.toFixed(3)} \`${x.name}\``));
fs.writeFileSync(path.join(dir, 'value-report.md'), L.join('\n') + '\n');
