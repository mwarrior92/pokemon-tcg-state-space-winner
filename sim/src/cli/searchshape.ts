// Shape of one offense search: positions per depth and what the root's children are.
//   node dist/searchshape.js [index=0] [budget=3000] [seed=202]
import { loadCards, metaDecks } from '../cards';
import { describeState } from '../describe';
import { Rng } from '../rng';
import { children, offenseSearch } from '../search';
import { prizesLeft } from '../rules';
import { generateState } from '../stategen';

loadCards();
const idx = Number(process.argv[2] ?? 0);
const budget = Number(process.argv[3] ?? 3000);
const seed = Number(process.argv[4] ?? 202);
const decks = metaDecks();
const rng = new Rng(seed);
let g = generateState(rng.pick(decks).cards, rng.pick(decks).cards, rng);
for (let k = 0; k < idx; k++) {
  g = generateState(rng.pick(decks).cards, rng.pick(decks).cards, rng);
}
console.log(describeState(g.sim.state));
const mover = g.sim.state.activePlayer;
const kids = children(g.sim, mover, prizesLeft(g.sim.state.players[mover]));
const byAction = new Map<string, number>();
for (const c of kids) {
  const a = c.label.split(' | ')[0];
  byAction.set(a, (byAction.get(a) ?? 0) + 1);
}
console.log(`\nroot: ${kids.length} children from ${byAction.size} actions`);
[...byAction].sort((a, b) => b[1] - a[1]).forEach(([a, n]) => console.log(`  ${String(n).padStart(3)}  ${a}`));
const r = offenseSearch(g.sim, { budget });
const depth = new Map<number, [number, number]>();
for (const n of r.nodes) {
  const d = depth.get(n.depth) ?? [0, 0];
  d[0]++;
  d[1] += n.expanded ? 1 : 0;
  depth.set(n.depth, d);
}
console.log(`\nsearch: ${r.nodes.length} positions, ${r.expansions} steps, complete ${r.complete}`);
[...depth].sort((a, b) => a[0] - b[0]).forEach(([d, [n, e]]) => console.log(`  depth ${d}: ${n} positions, ${e} expanded`));

// a deep expanded line and its children, to see what makes positions distinct
const deep = r.nodes.filter(n => n.expanded && n.depth === 3).slice(0, 2);
for (const n of deep) {
  console.log(`\nexpanded depth-3 position (${n.kids.length} children):`);
  const path: string[] = [];
  let cur: typeof n | undefined = n;
  while (cur && cur.depth > 0) {
    const parent = r.nodes.find(p => p.kids.some(k => k.node === cur));
    const lab = parent?.kids.find(k => k.node === cur)?.label ?? '?';
    path.unshift(lab);
    cur = parent;
  }
  console.log('  line: ' + path.join(' -> '));
  n.kids.slice(0, 40).forEach(k => console.log(`    ${k.terminal !== undefined ? 'T' + k.terminal : ' '} ${k.label}`));
}
