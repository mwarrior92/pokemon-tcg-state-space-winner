// Offense-search cost per state: time, positions, state copies, memory held by the search result.
//   node --expose-gc dist/searchbench.js [n=12] [budget=3000] [seed=202] [keepSims]
import { loadCards, metaDecks } from '../cards';
import { Rng } from '../rng';
import { offenseSearch } from '../search';
import { Sim } from '../sim';
import { generateState } from '../stategen';

loadCards();
const n = Number(process.argv[2] ?? 12);
const budget = Number(process.argv[3] ?? 3000);
const seed = Number(process.argv[4] ?? 202);
const keep = process.argv[5] === undefined ? undefined : Number(process.argv[5]);   // keepSims
const decks = metaDecks();
const rng = new Rng(seed);
const gc = (globalThis as any).gc as (() => void) | undefined;
const heap = () => {
  gc?.();
  return process.memoryUsage().heapUsed / 1e6;
};
let copies = 0;
let peak = 0;
const realCopy = Sim.prototype.copy;
Sim.prototype.copy = function (this: Sim, r?: Rng) {
  copies++;
  if (copies % 100 === 0) {
    peak = Math.max(peak, process.memoryUsage().heapUsed / 1e6);
  }
  return realCopy.call(this, r);
};
let ms = 0, worst = 0, complete = 0, prizes = 0, positions = 0;
for (let k = 0; k < n; k++) {
  const a = rng.pick(decks), b = rng.pick(decks);
  const g = generateState(a.cards, b.cards, rng);
  const h0 = heap();
  copies = 0;
  peak = 0;
  const r = offenseSearch(g.sim, { budget, keepSims: keep });
  const h1 = heap();
  ms += r.ms;
  worst = Math.max(worst, r.ms);
  complete += r.complete ? 1 : 0;
  prizes += r.value;
  positions += r.nodes.length;
  console.log(`${String(k).padStart(3)} T${String(g.info.turn).padStart(2)} prizes ${r.value} ${r.complete ? 'complete' : 'partial '} ${String(r.expansions).padStart(5)} steps ${String(r.nodes.length).padStart(5)} nodes ${String(copies).padStart(6)} copies ${(r.ms / 1000).toFixed(2)} s  held ${(h1 - h0).toFixed(0)} MB, peak heap ${peak.toFixed(0)} MB (${(peak - h0).toFixed(0)} over start)`);
}
console.log(`\ncomplete ${complete}/${n}, mean prizes ${(prizes / n).toFixed(2)}, mean positions ${(positions / n).toFixed(0)}; mean ${(ms / n / 1000).toFixed(2)} s/state, worst ${(worst / 1000).toFixed(2)} s, heap now ${heap().toFixed(0)} MB`);
