// Time the offense policy alone (one thread, nothing else running) with a run's chosen model.
//   node dist/policybench.js [run=offense-r2] [n=10] [seed=500]
import * as path from 'path';
import { REPO_ROOT, loadCards, metaDecks } from '../cards';
import { loadModel } from '../model';
import { groupsFor, playOffense } from '../policy';
import { Rng } from '../rng';
import { generateState } from '../stategen';

loadCards();
const run = process.argv[2] ?? 'offense-r2';
const n = Number(process.argv[3] ?? 10);
const seed = Number(process.argv[4] ?? 500);
const model = loadModel(path.join(REPO_ROOT, 'sim', 'runs', run, 'model.json'));
const decks = metaDecks();
const rng = new Rng(seed);
let ms = 0, steps = 0, worst = 0;
console.log(`model: ${model.names.length} features, groups ${[...new Set(groupsFor(model))].join(', ')}`);
for (let k = 0; k < n; k++) {
  const g = generateState(rng.pick(decks).cards, rng.pick(decks).cards, rng);
  const p = playOffense(g.sim, model);
  ms += p.ms;
  steps += p.steps.length;
  worst = Math.max(worst, p.ms);
  console.log(`${String(k).padStart(3)} ${(p.ms / 1000).toFixed(2)} s, ${p.steps.length} steps, prizes ${p.prizes}`);
}
console.log(`\nmean ${(ms / n / 1000).toFixed(2)} s/turn (${(ms / Math.max(1, steps)).toFixed(0)} ms/step), worst ${(worst / 1000).toFixed(2)} s`);
