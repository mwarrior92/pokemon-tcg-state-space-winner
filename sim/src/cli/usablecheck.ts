// Cards a list cannot use (usability.ts), and usable cards that also hurt the list's own cards.
//   node dist/usablecheck.js --list my-deck.txt     one list
//   node dist/usablecheck.js --meta                 every meta list (false-alarm check: real lists use all their cards)
//   node dist/usablecheck.js --conds                how every Standard Trainer / Special Energy text is read (audit)
import * as fs from 'fs';
import * as path from 'path';
import { allCards, loadCards, loadMetaLists, resolveEntry } from '../cards';
import { deckFromText, engineCard } from '../decklist';
import { sideEffects, textNeeds, unusableCards } from '../usability';
import { EnergyCard, TrainerCard } from '../engine';

loadCards();
const arg = (n: string) => (process.argv.includes(`--${n}`) ? process.argv[process.argv.indexOf(`--${n}`) + 1] : '');
if (process.argv.includes('--conds')) {
  const seen = new Set<string>();
  for (const c of allCards()) {
    if (!(c instanceof TrainerCard || c instanceof EnergyCard) || seen.has(c.name)) {
      continue;
    }
    seen.add(c.name);
    const n = textNeeds((c as any).text ?? '');
    if (n.conds.length) {
      console.log(`${c.name}: ${n.conds.map(k => `${k.role}${k.side === 'both' ? ' (both)' : ''} ${k.sel.text}`).join('; ')}`);
    }
  }
} else if (process.argv.includes('--meta')) {
  const flagged = new Map<string, number>(), side = new Map<string, number>();
  let lists = 0, withAny = 0;
  const bump = (m: Map<string, number>, k: string) => m.set(k, (m.get(k) ?? 0) + 1);
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
    u.forEach(x => bump(flagged, `${engineCard(x.card)?.name}: ${x.reason}`));
    // counts differ per list; group by card and what it hurts
    sideEffects(cards).forEach(x => bump(side, `${engineCard(x.card)?.name}: ${x.note.replace(/: \d+ of \d+ (?:Pokémon|cards)\)$/, ')')}`));
  }
  const show = (m: Map<string, number>) => [...m].sort((a, b) => b[1] - a[1]).slice(0, 40).forEach(([k, v]) => console.log(`  ${String(v).padStart(4)}  ${k}`));
  console.log(`${lists} meta lists; ${withAny} with a card flagged unusable`);
  show(flagged);
  console.log('accepted side effects (usable, noted in reports):');
  show(side);
} else {
  const cards = deckFromText(fs.readFileSync(path.resolve(arg('list')), 'utf8'), 'x').deck.cards;
  const u = unusableCards(cards);
  console.log(u.length ? u.map(x => `${engineCard(x.card)?.name}: ${x.reason}`).join('\n') : 'every card can be used');
  sideEffects(cards).forEach(x => console.log(`${engineCard(x.card)?.name}: ${x.note} (usable)`));
}
