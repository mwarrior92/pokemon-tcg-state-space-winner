// How each meta decklist maps onto engine cards.   node dist/decks.js
import { buildDeck, loadMetaLists, metaDecks, resolveEntry } from '../cards';
const lists = loadMetaLists();
const how = new Map<string, number>();
const missing = new Map<string, { n: number; note: string }>();
let complete = 0;
for (const l of lists) {
  let ok = true;
  for (const e of l.cards) {
    const r = resolveEntry(e);
    how.set(r.how, (how.get(r.how) ?? 0) + e.count);
    if (!r.card) {
      ok = false;
      const k = `${e.name} ${e.set} ${e.num}`;
      missing.set(k, { n: (missing.get(k)?.n ?? 0) + 1, note: r.note ?? '' });
    }
  }
  complete += ok ? 1 : 0;
}
console.log(`${lists.length} lists, ${complete} fully playable in the engine`);
console.log('card entries by match type:', Object.fromEntries(how));
console.log('missing printings (lists affected):');
[...missing.entries()].sort((a, b) => b[1].n - a[1].n).forEach(([k, v]) => console.log(`  ${String(v.n).padStart(4)}  ${k}${v.note ? '  - ' + v.note.replace(/^no engine card matches [^(]*/, '') : ''}`));
const archetypes = new Set(lists.map(l => l.deck));
const playable = metaDecks();
console.log(`archetypes: ${archetypes.size}, with at least one fully playable list: ${playable.length}`);
console.log('not playable:', [...archetypes].filter(a => !playable.some(d => d.archetype === a)).join(', '));
