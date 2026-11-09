// Cards a list cannot use (usability.ts).
//   node dist/usablecheck.js --list my-deck.txt     one list
//   node dist/usablecheck.js --meta                 every meta list (false-alarm check: real lists use all their cards)
import * as fs from 'fs';
import * as path from 'path';
import { loadCards, loadMetaLists, resolveEntry } from '../cards';
import { deckFromText, engineCard } from '../decklist';
import { unusableCards } from '../usability';

loadCards();
const arg = (n: string) => (process.argv.includes(`--${n}`) ? process.argv[process.argv.indexOf(`--${n}`) + 1] : '');
if (process.argv.includes('--meta')) {
  const flagged = new Map<string, { lists: number; reason: string }>();
  let lists = 0, withAny = 0;
  for (const l of loadMetaLists()) {
    const cards = l.cards.flatMap(e => {
      const c = resolveEntry(e).card;
      return c ? Array(Number(e.count) || 1).fill(c.fullName) : [];
    });
    lists++;
    const u = unusableCards(cards);
    if (u.length) {
      withAny++;
    }
    u.forEach(x => {
      const k = `${engineCard(x.card)?.name}: ${x.reason}`;
      const v = flagged.get(k) ?? { lists: 0, reason: x.reason };
      v.lists++;
      flagged.set(k, v);
    });
  }
  console.log(`${lists} meta lists; ${withAny} with a card flagged unusable`);
  [...flagged].sort((a, b) => b[1].lists - a[1].lists).slice(0, 40).forEach(([k, v]) => console.log(`  ${String(v.lists).padStart(4)}  ${k}`));
} else {
  const cards = deckFromText(fs.readFileSync(path.resolve(arg('list')), 'utf8'), 'x').deck.cards;
  const u = unusableCards(cards);
  console.log(u.length ? u.map(x => `${engineCard(x.card)?.name}: ${x.reason}`).join('\n') : 'every card can be used');
}
