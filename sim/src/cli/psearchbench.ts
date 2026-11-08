// Parallel vs serial offense search on the same generated states: same answers? how much faster?
//   node dist/psearchbench.js [n=10] [budget=3000] [workers=auto] [seed=202]
import { loadCards, metaDecks } from '../cards';
import { ParallelSearch, serveSearch } from '../psearch';
import { autoWorkers, isMainThread } from '../pool';
import { Rng } from '../rng';
import { offenseSearch } from '../search';
import { generateState } from '../stategen';

loadCards();
const decks = metaDecks();
const factory = (spec: { seed: number; a: number; b: number }) =>
  generateState(decks[spec.a].cards, decks[spec.b].cards, new Rng(spec.seed)).sim;
serveSearch(factory);

async function main(): Promise<void> {
  const n = Number(process.argv[2] ?? 10);
  const budget = Number(process.argv[3] ?? 3000);
  const workers = process.argv[4] && process.argv[4] !== 'auto' ? Number(process.argv[4]) : autoWorkers();
  const seed = Number(process.argv[5] ?? 202);
  const ps = new ParallelSearch(__filename, factory, workers);
  const rng = new Rng(seed);
  let tS = 0, tP = 0, same = 0;
  for (let k = 0; k < n; k++) {
    const spec = { seed: seed * 1000 + k, a: rng.int(0, decks.length - 1), b: rng.int(0, decks.length - 1) };
    const s = offenseSearch(factory(spec), { budget, keepSims: 0 });
    const p = await ps.search(spec, { budget });
    tS += s.ms;
    tP += p.ms;
    same += s.value === p.value ? 1 : 0;
    console.log(`${String(k).padStart(3)} serial ${s.value} ${s.complete ? 'complete' : 'partial '} ${String(s.nodes.length).padStart(5)} pos ${(s.ms / 1000).toFixed(2)} s | parallel ${p.value} ${p.complete ? 'complete' : 'partial '} ${String(p.positions).padStart(5)} pos ${(p.ms / 1000).toFixed(2)} s, ${p.converged} converged, ${p.replays} replays${p.errors.length ? `, ${p.errors.length} errors: ${p.errors[0]}` : ''}`);
  }
  console.log(`\n${ps.size} workers: serial ${(tS / n / 1000).toFixed(2)} s/state, parallel ${(tP / n / 1000).toFixed(2)} s/state (x${(tS / Math.max(1, tP)).toFixed(1)}); same value on ${same}/${n}`);
  await ps.close();
}

if (isMainThread) {
  main().catch(e => {
    console.error(e);
    process.exitCode = 1;
  });
}
