// Records the current card fingerprints (sim/test/card-manifest.json) so `npm test` can tell which
// cards are new or changed, and adds translated-name differences of meta cards to the known-issues
// file. Gameplay differences are never auto-accepted: fix the card or add an entry by hand with a
// reason.   node dist/cardbaseline.js
import * as fs from 'fs';
import { allCards, loadCards } from '../cards';
import { cardFingerprint, loadKnownIssues, manifestPath, staticCheck, standardPool } from '../cardcheck';
import * as path from 'path';
import { REPO_ROOT } from '../cards';

loadCards();
const pool = standardPool();
const manifest: Record<string, string> = {};
const byName = new Map(allCards().map(c => [c.fullName, c]));
for (const name of [...pool.keys()].sort()) {
  manifest[name] = cardFingerprint(byName.get(name)!);
}
fs.writeFileSync(manifestPath(), JSON.stringify(manifest, null, 1));
console.log(`manifest: ${Object.keys(manifest).length} Standard cards`);

const known = loadKnownIssues();
let added = 0;
for (const [name, pc] of pool) {
  for (const i of staticCheck(byName.get(name)!, pc)) {
    if (/names$|^abilities$/.test(i.field) && !known.static[`${i.card}|${i.field}`]) {
      known.static[`${i.card}|${i.field}`] = `translated name: engine "${i.twinleaf}", printed "${i.expected}" (cosmetic)`;
      added++;
    }
  }
}
fs.writeFileSync(path.join(REPO_ROOT, 'sim', 'test', 'known-card-issues.json'), JSON.stringify(known, null, 1));
console.log(`known-card-issues.json: ${added} translated-name entries added`);
