// Sanity check for the reach features: does "a KO is reachable this turn" agree with the search?
//   node dist/reachdemo.js [n=60]
import { loadCards, metaDecks } from '../cards';
import { describeState } from '../describe';
import { features } from '../features';
import { Rng } from '../rng';
import { offenseSearch } from '../search';
import { generateState } from '../stategen';

loadCards();
const n = Number(process.argv[2] ?? 60);
const d = metaDecks();
const rng = new Rng(9);
const tab = { both: 0, reachOnly: 0, searchOnly: 0, neither: 0 };
const misses: string[] = [];
for (let k = 0; k < n; k++) {
  const g = generateState(rng.pick(d).cards, rng.pick(d).cards, rng);
  const fv = features(g.sim, g.sim.state.activePlayer, ['reach']);
  const get = (nm: string) => fv.values[fv.names.indexOf(nm)];
  const r = offenseSearch(g.sim, { budget: 1500 });
  const reach = get('me.reach.maxPrize') > 0;
  const found = r.value > 0;
  if (reach && found) tab.both++;
  else if (reach) tab.reachOnly++;
  else if (found) tab.searchOnly++;
  else tab.neither++;
  if (found && !reach && misses.length < 3) {
    misses.push(`${describeState(g.sim.state)}\n  search ${r.value}: ${r.line.join(' -> ').slice(0, 220)}\n  oneShort ${get('me.reach.oneShortMaxPrize')} potential ${get('me.reach.potentialMaxPrize')}`);
  }
}
console.log(tab);
console.log('\nsearch found prizes that reach missed:\n' + misses.join('\n\n'));
