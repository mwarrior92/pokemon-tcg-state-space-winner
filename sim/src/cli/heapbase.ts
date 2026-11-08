// What a worker's baseline heap consists of: engine load, card database, decklists, a template game.
//   node --expose-gc dist/heapbase.js
export {};   // module scope (its gc constant must not clash with other CLI files)
const gc = (globalThis as any).gc as () => void;
const mb = () => {
  gc();
  return (process.memoryUsage().heapUsed / 1e6).toFixed(0);
};
console.log(`start: ${mb()} MB`);
// eslint-disable-next-line @typescript-eslint/no-var-requires
const cards = require('../cards') as typeof import('../cards');
console.log(`after loading the bundle (engine modules, every set's card objects): ${mb()} MB`);
cards.loadCards();
console.log(`after loadCards(): ${mb()} MB`);
const decks = cards.metaDecks();
console.log(`after metaDecks() (${decks.length} decks): ${mb()} MB`);
// eslint-disable-next-line @typescript-eslint/no-var-requires
const { generateState } = require('../stategen') as typeof import('../stategen');
// eslint-disable-next-line @typescript-eslint/no-var-requires
const { Rng } = require('../rng') as typeof import('../rng');
const g = generateState(decks[0].cards, decks[1].cards, new Rng(1));
console.log(`after one generated state (+ its template): ${mb()} MB`);
void g;
// eslint-disable-next-line @typescript-eslint/no-var-requires
const engine = require('../engine') as any;
const cm = engine.CardManager.getInstance();
const all = cm.getAllCards?.() ?? [];
console.log(`engine card database: ${all.length} cards`);
