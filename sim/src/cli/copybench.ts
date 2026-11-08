// What a state copy consists of: objects by constructor, and copy time.
//   node dist/copybench.js
import { Card } from '../engine';
import { loadCards, metaDecks } from '../cards';
import { Rng } from '../rng';
import { generateState } from '../stategen';

loadCards();
const decks = metaDecks();
const rng = new Rng(5);
const g = generateState(decks[0].cards, decks[1].cards, rng);
const counts = new Map<string, number>();
const fieldCounts = new Map<string, number>();
const seen = new Set<any>();
const walk = (v: any, path: string, inCard: string) => {
  if (v === null || typeof v !== 'object' || seen.has(v)) {
    return;
  }
  seen.add(v);
  const name = Array.isArray(v) ? 'Array' : (v.constructor?.name ?? 'Object');
  const key = v instanceof Card ? 'Card' : name;
  counts.set(key, (counts.get(key) ?? 0) + 1);
  if (inCard) {
    fieldCounts.set(inCard, (fieldCounts.get(inCard) ?? 0) + 1);
  }
  for (const k of Object.keys(v)) {
    walk(v[k], path + '.' + k, v instanceof Card ? k : inCard);
  }
};
walk(g.sim.state, 'state', '');
console.log('objects reachable from a state:', seen.size);
console.log([...counts].sort((a, b) => b[1] - a[1]).slice(0, 20));
console.log('objects under card fields:', [...fieldCounts].sort((a, b) => b[1] - a[1]).slice(0, 20));
const t0 = performance.now();
const gc = (globalThis as any).gc as (() => void) | undefined;
let lap = performance.now();
for (let i = 0; i < Number(process.argv[2] ?? 300); i++) {
  g.sim.copy(new Rng(1));
  if (gc && (i + 1) % 2000 === 0) {
    gc();
    console.log(`  ${i + 1} copies: heap ${(process.memoryUsage().heapUsed / 1e6).toFixed(0)} MB, last 2000 at ${((performance.now() - lap) / 2000).toFixed(3)} ms`);
    lap = performance.now();
  }
}
console.log(`copy: ${((performance.now() - t0) / Number(process.argv[2] ?? 300)).toFixed(3)} ms`);
