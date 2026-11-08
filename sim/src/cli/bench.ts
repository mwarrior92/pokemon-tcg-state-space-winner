import { loadCards, metaDecks } from '../cards';
import { deepCopy } from '../clone';
import { Rng } from '../rng';
import { Sim, legalMainOptions, mainCandidates, randomChooser, resolvePrompts, runStep } from '../sim';
loadCards();
const d = metaDecks();
const rng = new Rng(5);
let sim = Sim.newGame(d[0].cards, d[1].cards, rng.fork());
resolvePrompts(sim, randomChooser(rng), rng);
for (let i = 0; i < 40 && !sim.finished; i++) {
  const o = rng.pick(legalMainOptions(sim));
  sim = runStep(sim, o, randomChooser(rng), rng).sim ?? sim;
}
let objs = 0; const seen = new Set<any>();
(function walk(v: any) { if (v === null || typeof v !== 'object' || seen.has(v)) return; seen.add(v); objs++; for (const k in v) if (Object.prototype.hasOwnProperty.call(v, k)) walk(v[k]); })(sim.state);
console.log('turn', sim.state.turn, 'objects', objs, 'prompts', sim.state.prompts.length);
const time = (label: string, n: number, f: () => void) => { const t = process.hrtime.bigint(); for (let i = 0; i < n; i++) f(); console.log(label.padEnd(30), (Number(process.hrtime.bigint() - t) / 1e3 / n).toFixed(1), 'us'); };
time('deepCopy(state)', 500, () => deepCopy(sim.state));
time('legalMainOptions', 30, () => legalMainOptions(sim));
const opts = legalMainOptions(sim);
time('runStep (random legal)', 30, () => runStep(sim, rng.pick(opts), randomChooser(rng), rng));
console.log('candidates', mainCandidates(sim.state).length, 'legal', opts.length);
if (process.argv[2] === 'loop') { for (let i = 0; i < 300; i++) legalMainOptions(sim); }
