// Where does a one-turn search spend its step budget? Runs the offense search on the states of a
// training run and attributes every generated child to the action that produced it.
//   node dist/searchwork.js [run=offense-r2] [n=30] [budget=3000]
import * as fs from 'fs';
import * as path from 'path';
import { REPO_ROOT, loadCards, metaDecks } from '../cards';
import { isEnergyCard, isPokemonCard, isTrainerCard } from '../rules';
import { Rng } from '../rng';
import { offenseSearch } from '../search';
import { generateState } from '../stategen';

loadCards();
const run = process.argv[2] ?? 'offense-r2';
const n = Number(process.argv[3] ?? 30);
const budget = Number(process.argv[4] ?? 3000);
const decks = metaDecks();
const labels = fs.readFileSync(path.join(REPO_ROOT, 'sim', 'runs', run, 'labels.jsonl'), 'utf8').split('\n').filter(Boolean).map(l => JSON.parse(l));
const seedBase = Math.floor(labels[0].seed / 1000);
// the run's job list: job k has seed seedBase*1000+k and decks from the run's pair rng (train.ts mkJobs)
const pairRng = new Rng(seedBase);
const jobs = new Map<number, { a: number; b: number }>();
for (let k = 0; k < 800; k++) {
  jobs.set(seedBase * 1000 + k, { a: pairRng.int(0, decks.length - 1), b: pairRng.int(0, decks.length - 1) });
}

/** action family: the option label up to the first prompt answer, slot positions removed */
function family(label: string): string {
  return label.split(' | ')[0]
    .replace(/ -> (active|bench\d) /, ' -> ')
    .replace(/\((active|bench\d) /, '(')
    .replace(/^evolve (active|bench\d) /, 'evolve ')
    .replace(/^retreat to bench\d.*/, 'retreat');
}

interface Tally { kids: number; known: number; uses: number }
const add = (m: Map<string, Tally>, k: string, kids: number, known: number, uses: number) => {
  const t = m.get(k) ?? { kids: 0, known: 0, uses: 0 };
  t.kids += kids;
  t.known += known;
  t.uses += uses;
  m.set(k, t);
};
const total = new Map<string, Tally>();
const kinds = new Map<string, Tally>();
const out: string[] = [];
let budgetHit = 0;
for (const r of labels.slice(0, n)) {
  const job = jobs.get(r.seed)!;
  const g = generateState(decks[job.a].cards, decks[job.b].cards, new Rng(r.seed));
  const per = new Map<string, Tally>();
  let lastParent = -1;
  let seenHere = new Set<string>();
  let parents = 0;
  const res = offenseSearch(g.sim, {
    budget, keepSims: 0,
    onChild: (c, known, depth) => {
      // a new parent starts when the depth changes or a family repeats... count uses per parent
      // via the parent's identity is not exposed; approximate one "use" per (parent, family) by
      // resetting when the child sequence restarts at main-option order
      void depth;
      const f = family(c.label);
      if (lastParent !== parents) {
        seenHere = new Set();
        lastParent = parents;
      }
      add(per, f, 1, known ? 1 : 0, seenHere.has(f) ? 0 : 1);
      seenHere.add(f);
      if (c.label === 'end turn') {
        parents++;     // "end turn" is the last option of every expansion
      }
    },
  });
  const me = g.sim.state.players[g.sim.state.activePlayer];
  const hand = me.hand.cards;
  const inPlay = [me.active, ...me.bench].filter(l => l.cards.length).length;
  const hit = !res.complete && res.expansions >= budget;
  budgetHit += hit ? 1 : 0;
  const top = [...per].sort((x, y) => y[1].kids - x[1].kids).slice(0, 4);
  out.push(`${res.complete ? 'complete' : hit ? 'BUDGET  ' : 'TIME    '} T${String(g.sim.state.turn).padStart(2)} hand ${String(hand.length).padStart(2)} (${hand.filter(isTrainerCard).length}T ${hand.filter(isPokemonCard).length}P ${hand.filter(isEnergyCard).length}E) inPlay ${inPlay} positions ${String(res.nodes.length).padStart(5)} ${(res.ms / 1000).toFixed(1).padStart(4)}s ${decks[job.a].archetype.padEnd(22)} top: ${top.map(([f, t]) => `${f} ${t.kids}`).join('; ')}`);
  for (const [f, t] of per) {
    add(total, f, t.kids, t.known, t.uses);
    add(kinds, f.split(' ')[0], t.kids, t.known, t.uses);
  }
}
console.log(out.join('\n'));
const sum = [...total.values()].reduce((s, t) => s + t.kids, 0);
console.log(`\n${budgetHit}/${n} searches stopped at the step budget. All generated children by kind of action ("known" = the child's position had already been reached another way):`);
[...kinds].sort((x, y) => y[1].kids - x[1].kids).forEach(([k, t]) =>
  console.log(`  ${k.padEnd(9)} ${(100 * t.kids / sum).toFixed(1).padStart(5)}%  ${(t.kids / Math.max(1, t.uses)).toFixed(1).padStart(5)} children per use  ${(100 * t.known / Math.max(1, t.kids)).toFixed(0).padStart(3)}% known`));
console.log(`\ntop actions:`);
[...total].sort((x, y) => y[1].kids - x[1].kids).slice(0, 25).forEach(([f, t]) =>
  console.log(`  ${(100 * t.kids / sum).toFixed(1).padStart(5)}%  ${(t.kids / Math.max(1, t.uses)).toFixed(1).padStart(5)} per use  ${(100 * t.known / Math.max(1, t.kids)).toFixed(0).padStart(3)}% known  ${f}`));
