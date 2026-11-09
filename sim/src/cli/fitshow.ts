// Shows the deck builder's synergy weights for a list: the likeliest additions and cuts.
//   node dist/fitshow.js --list my-deck.txt   |   node dist/fitshow.js --seed "Archeops"
import * as fs from 'fs';
import * as path from 'path';
import { loadCards } from '../cards';
import { deckFromText, engineCard } from '../decklist';
import { candidatePool, seedDeck } from '../deckgen';
import { cutWeight, fit, profile } from '../synergy';

loadCards();
const arg = (n: string) => (process.argv.includes(`--${n}`) ? process.argv[process.argv.indexOf(`--${n}`) + 1] : '');
let cards: string[];
let pool: string[];
if (arg('seed')) {
  const sd = seedDeck(arg('seed'));
  cards = sd.cards;
  pool = sd.pool;
  console.log(sd.how);
  console.log([...new Set(cards)].map(n => `${cards.filter(x => x === n).length} ${engineCard(n)?.name}`).join(', '));
} else {
  cards = deckFromText(fs.readFileSync(path.resolve(arg('list')), 'utf8'), 'x').deck.cards;
  pool = candidatePool(cards);
}
const nm = (n: string) => engineCard(n)?.name ?? n;
const p = profile(cards);
const printings = new Map<string, number>();
new Set(pool).forEach(n => printings.set(nm(n), (printings.get(nm(n)) ?? 0) + 1));
const adds = [...new Set(pool)].filter(n => !cards.includes(n)).map(n => ({ n, w: fit(n, p) / printings.get(nm(n))! })).sort((a, b) => b.w - a.w);
const tot = adds.reduce((s, a) => s + a.w, 0);
const show = (xs: { n: string; w: number }[]) => xs.forEach(a => console.log(`  ${a.w.toFixed(2).padStart(6)}  ${(100 * a.w / tot).toFixed(1).padStart(4)}%  ${nm(a.n)}`));
console.log(`\nlikeliest additions (of ${adds.length} pool cards not in the deck):`);
show(adds.slice(0, 15));
console.log('least likely additions:');
show(adds.slice(-10));
const cuts = [...new Set(cards)].map(n => ({ n, w: cutWeight(n, cards) })).sort((a, b) => b.w - a.w);
console.log('\nlikeliest cuts:');
cuts.slice(0, 10).forEach(c => console.log(`  ${c.w.toFixed(2).padStart(6)}  ${nm(c.n)}`));
console.log('least likely cuts:');
cuts.slice(-6).forEach(c => console.log(`  ${c.w.toFixed(2).padStart(6)}  ${nm(c.n)}`));
