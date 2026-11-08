// Card correctness report.   node dist/cardcheck.js [--all] [--card "Full Name"] [--seeds 3]
//   default: every card in the meta decklists; --all: every card in the Standard card data.
import * as fs from 'fs';
import * as path from 'path';
import { REPO_ROOT, loadCards, loadMetaLists } from '../cards';
import { isKnownSmoke, isKnownStatic, loadKnownIssues, metaCardNames, printedCards, smokeTest, staticCheck, twinleafFor, StaticIssue, SmokeResult } from '../cardcheck';

const args = process.argv.slice(2);
const all = args.includes('--all');
const one = args.includes('--card') ? args[args.indexOf('--card') + 1] : undefined;
const seeds = args.includes('--seeds') ? Number(args[args.indexOf('--seeds') + 1]) : 3;

loadCards();
const known = loadKnownIssues();
const printed = printedCards();
const metaNames = new Set(metaCardNames());

// pick the card pool: every Standard printing (--all), one card, or the decklist printings
const pool = new Map<string, typeof printed[number] | undefined>();
const missing: string[] = [];
const metaPrintings = new Set<string>();
for (const l of loadMetaLists()) {
  for (const e of l.cards) {
    metaPrintings.add(`${String(e.set).toUpperCase()}|${String(e.num).replace(/^0+/, '')}`);
  }
}
for (const pc of printed) {
  if (!all && !one && !metaPrintings.has(`${pc.set.toUpperCase()}|${String(pc.number).replace(/^0+/, '')}`)) {
    continue;
  }
  const tw = twinleafFor(pc);
  if (!tw.card) {
    missing.push(`${pc.name} ${pc.set} ${pc.number}`);
    continue;
  }
  if (one ? tw.card.fullName === one : true) {
    if (!pool.has(tw.card.fullName) || tw.how === 'set+number') {
      pool.set(tw.card.fullName, pc);
    }
  }
}
if (!all && !one) {
  metaNames.forEach(n => {
    if (!pool.has(n)) {
      pool.set(n, undefined);   // basic energy etc. without a dataset entry
    }
  });
}

const t0 = Date.now();
const staticIssues: StaticIssue[] = [];
const smoke: SmokeResult[] = [];
for (const [name, pc] of pool) {
  if (pc) {
    staticIssues.push(...staticCheck(require('../cards').allCards().find((c: any) => c.fullName === name), pc));
  }
  smoke.push(smokeTest(name, pc, seeds));
}
const newStatic = staticIssues.filter(i => !isKnownStatic(known, i));
const newSmoke = smoke.flatMap(r => r.failures.filter(f => !isKnownSmoke(known, r.card, f)).map(f => `${r.card}: ${f}`));

console.log(`${pool.size} cards checked in ${((Date.now() - t0) / 1000).toFixed(1)} s (${all ? 'all Standard data' : one ? one : 'meta decklists'})`);
if (all) {
  console.log(`printed Standard cards with no engine implementation: ${missing.length}`);
  missing.slice(0, 20).forEach(m => console.log('  ' + m));
}
console.log(`static mismatches with printed data: ${staticIssues.length} (${newStatic.length} not in known-card-issues.json)`);
newStatic.slice(0, 60).forEach(i => console.log(`  ${i.card} [${i.printed}] ${i.field}: engine "${i.twinleaf}" vs printed "${i.expected}"`));
console.log(`smoke failures: ${smoke.reduce((s, r) => s + r.failures.length, 0)} (${newSmoke.length} not in known-card-issues.json)`);
newSmoke.slice(0, 60).forEach(f => console.log('  ' + f));
const unused = smoke.filter(r => r.used === 0);
console.log(`cards whose attacks/abilities/play were never accepted in the test board: ${unused.length}`);
unused.slice(0, 25).forEach(r => console.log(`  ${r.card}: ${r.notes.slice(0, 2).join('; ')}`));

const outDir = path.join(REPO_ROOT, 'sim', 'reports');
fs.mkdirSync(outDir, { recursive: true });
fs.writeFileSync(path.join(outDir, all ? 'cardcheck-all.json' : 'cardcheck-meta.json'),
  JSON.stringify({ when: new Date().toISOString(), staticIssues, smoke, missing }, null, 1));
process.exitCode = newStatic.length + newSmoke.length > 0 ? 1 : 0;
