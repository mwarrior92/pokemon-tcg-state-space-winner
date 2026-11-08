// Runs the offense search on generated states: prizes found, completeness, time.
//   node dist/oracle.js [n=10] [budget=1500] [seed=1]
import { loadCards, metaDecks } from '../cards';
import { describeState } from '../describe';
import { Rng } from '../rng';
import { offenseSearch } from '../search';
import { generateState } from '../stategen';
loadCards();
const n = Number(process.argv[2] ?? 10);
const budget = Number(process.argv[3] ?? 1500);
const seed = Number(process.argv[4] ?? 1);
const decks = metaDecks();
const rng = new Rng(seed);
let tot = 0, comp = 0, ms = 0, nodes = 0;
const hist = new Map<number, number>();
for (let k = 0; k < n; k++) {
  const a = rng.pick(decks), b = rng.pick(decks);
  const g = generateState(a.cards, b.cards, rng);
  const r = offenseSearch(g.sim, { budget });
  tot += r.value; comp += r.complete ? 1 : 0; ms += r.ms; nodes += r.nodes.length;
  hist.set(r.value, (hist.get(r.value) ?? 0) + 1);
  console.log(`${String(k).padStart(3)} ${a.archetype.padEnd(22)} vs ${b.archetype.padEnd(22)} T${g.info.turn} prizes ${r.value} ${r.complete ? 'complete' : 'partial '} ${String(r.expansions).padStart(5)} steps ${String(r.nodes.length).padStart(4)} nodes ${(r.ms / 1000).toFixed(1)}s  ${r.line.join(' -> ').slice(0, 150)}`);
  if (k === 0) console.log(describeState(g.sim.state));
}
console.log(`\nmean prizes ${(tot / n).toFixed(2)}, complete ${comp}/${n}, ${(ms / n / 1000).toFixed(2)} s/state, ${(nodes / n).toFixed(0)} nodes/state, distribution ${[...hist.entries()].sort().map(([k, v]) => k + ':' + v).join(' ')}`);
