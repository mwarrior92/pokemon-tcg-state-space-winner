// Generates random valid board states between meta decks: speed, distributions, rejection reasons,
// and a few sample boards.   node dist/genstates.js [n=2000] [seed=1] [samples=2]
import { loadCards, metaDecks } from '../cards';
import { describeState } from '../describe';
import { Rng } from '../rng';
import { generateState, lastRejections } from '../stategen';
import { legalMainOptions } from '../sim';

const n = Number(process.argv[2] ?? 2000);
const seed = Number(process.argv[3] ?? 1);
const samples = Number(process.argv[4] ?? 2);
loadCards();
const decks = metaDecks();
const rng = new Rng(seed);
const pairs = Array.from({ length: 12 }, () => [rng.pick(decks), rng.pick(decks)]);
// build the per-pair templates first so the timing below is generation only
pairs.forEach(([a, b]) => generateState(a.cards, b.cards, rng));
const t0 = process.hrtime.bigint();
const stats = { attempts: 0, turn: new Map<number, number>(), prizes: new Map<number, number>(), inPlay: new Map<number, number>() };
const gens = [];
for (let k = 0; k < n; k++) {
  const [a, b] = pairs[k % pairs.length];
  const g = generateState(a.cards, b.cards, rng);
  stats.attempts += g.info.attempts;
  stats.turn.set(g.info.turn, (stats.turn.get(g.info.turn) ?? 0) + 1);
  g.info.prizesLeft.forEach(x => stats.prizes.set(x, (stats.prizes.get(x) ?? 0) + 1));
  g.info.inPlay.forEach(x => stats.inPlay.set(x, (stats.inPlay.get(x) ?? 0) + 1));
  if (k < samples) {
    gens.push({ g, a: a.archetype, b: b.archetype });
  }
}
const us = Number(process.hrtime.bigint() - t0) / 1e3 / n;
console.log(`${n} states in ${(us * n / 1e6).toFixed(2)} s: ${us.toFixed(0)} us/state (${(1e6 / us).toFixed(0)}/s), ${(stats.attempts / n).toFixed(2)} attempts per state`);
const show = (m: Map<number, number>) => [...m.entries()].sort((x, y) => x[0] - y[0]).map(([k, v]) => `${k}:${v}`).join(' ');
console.log('turn      ', show(stats.turn));
console.log('prizes left', show(stats.prizes));
console.log('in play   ', show(stats.inPlay));
const rej = new Map<string, number>();
lastRejections.forEach(r => {
  const k = r.replace(/P\d/g, 'P#').replace(/\d+/g, '#').slice(0, 90);
  rej.set(k, (rej.get(k) ?? 0) + 1);
});
console.log('rejections:', [...rej.entries()].sort((x, y) => y[1] - x[1]).slice(0, 8));
// the engine must accept play from every generated state: legal options enumerate without errors
let checked = 0;
for (let k = 0; k < Math.min(n, 200); k++) {
  const [a, b] = pairs[k % pairs.length];
  const g = generateState(a.cards, b.cards, rng);
  legalMainOptions(g.sim);
  checked++;
}
console.log(`engine accepted ${checked} generated states (legal-move enumeration ran)`);
for (const { g, a, b } of gens) {
  console.log(`\n--- ${a} (P1) vs ${b} (P2)\n${describeState(g.sim.state)}`);
}
