// Feature vector size and cost on generated states.   node dist/featbench.js [n=30]
import { loadCards, metaDecks } from '../cards';
import { ALL_GROUPS, CHEAP_GROUPS, features } from '../features';
import { Rng } from '../rng';
import { generateState } from '../stategen';
import { describeState } from '../describe';
loadCards();
const n = Number(process.argv[2] ?? 30);
const decks = metaDecks();
const rng = new Rng(3);
const states = Array.from({ length: n }, (_, k) => generateState(decks[k % decks.length].cards, decks[(k * 5 + 1) % decks.length].cards, rng).sim);
for (const [label, groups] of [['cheap', CHEAP_GROUPS], ['all (with probes)', ALL_GROUPS]] as const) {
  const t0 = process.hrtime.bigint();
  let fv;
  for (const s of states) fv = features(s, s.state.activePlayer, groups as any);
  const ms = Number(process.hrtime.bigint() - t0) / 1e6 / n;
  console.log(`${label.padEnd(20)} ${fv!.values.length} features, ${ms.toFixed(1)} ms/state`);
}
const s = states[0];
const fv = features(s, s.state.activePlayer);
console.log(describeState(s.state));
const show = fv.names.map((nm, i) => [nm, fv.values[i]] as const).filter(([nm, v]) => v !== 0 && /s0\.a\d\.(dmgTo|koTo|nowTo)|incoming|koThreat|abilityDamage|handDamage|handPrizes|s0\.a0\.gap|s0\.hpLeft/.test(nm));
console.log(show.map(([a, b]) => `${a}=${b}`).join('  '));
