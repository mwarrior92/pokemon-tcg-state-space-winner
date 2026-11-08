// Time the offense policy alone (one thread, nothing else running) with a run's chosen model.
//   node dist/policybench.js [run=offense-r2] [n=10] [seed=500] [searchBudget: 0 = greedy]
import * as path from 'path';
import { REPO_ROOT, loadCards, metaDecks } from '../cards';
import { loadModel } from '../model';
import { groupsFor, playOffense, playOffenseSearch } from '../policy';
import { offenseSearch, stateHash } from '../search';
import { sameState } from '../clone';
import { Sim } from '../sim';
import { Rng } from '../rng';
import { generateState } from '../stategen';

loadCards();
const run = process.argv[2] ?? 'offense-r2';
const n = Number(process.argv[3] ?? 10);
const seed = Number(process.argv[4] ?? 500);
const sb = Number(process.argv[5] ?? 0);
let teacher = 0, got = 0, atLeast = 0, mutated = 0;
void stateHash; void Sim;
const model = loadModel(path.join(REPO_ROOT, 'sim', 'runs', run, 'model.json'));
const decks = metaDecks();
const rng = new Rng(seed);
let ms = 0, steps = 0, worst = 0;
console.log(`model: ${model.names.length} features, groups ${[...new Set(groupsFor(model))].join(', ')}`);
for (let k = 0; k < n; k++) {
  const g = generateState(rng.pick(decks).cards, rng.pick(decks).cards, rng);
  const before = g.sim.copy();
  const p = sb ? playOffenseSearch(g.sim, model, { budget: sb }) : playOffense(g.sim, model);
  if (!sameState(before.state, g.sim.state)) {
    mutated++;
  }
  const t = process.env.NO_TEACHER ? { value: 0 } as any : offenseSearch(g.sim, { budget: 3000, keepSims: 0 });
  teacher += t.value;
  got += p.prizes;
  atLeast += p.prizes >= t.value ? 1 : 0;
  ms += p.ms;
  steps += p.steps.length;
  worst = Math.max(worst, p.ms);
  console.log(`${String(k).padStart(3)} ${(p.ms / 1000).toFixed(2)} s, ${p.steps.length} steps, prizes ${p.prizes} (teacher ${t.value})`);
}
console.log(`\n${sb ? `search policy, budget ${sb}` : 'greedy policy'}: ${(got / n).toFixed(2)} prizes/turn vs teacher ${(teacher / n).toFixed(2)}; at least as good on ${atLeast}/${n}; policy changed its input position on ${mutated}; mean ${(ms / n / 1000).toFixed(2)} s/turn (${(ms / Math.max(1, steps)).toFixed(0)} ms/step), worst ${(worst / 1000).toFixed(2)} s`);
