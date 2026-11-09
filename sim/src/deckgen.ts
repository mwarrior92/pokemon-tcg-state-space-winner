// Deck generation from a seed card, and the changes the optimiser tries.
//
// Everything comes from the 512 meta decklists (no hand-written deck-building rules):
//   - if the seed card is played in meta lists, the start is the best-placed complete list of the
//     archetype that plays it most;
//   - otherwise the deck is built: the seed's evolution line in the counts meta lists use for
//     lines of that stage (Rare Candy for a Stage 2 as often as they do), basic Energy for the line's
//     attack costs in the usual amount, then the staples (cards played across many archetypes) in
//     their usual counts until 60 cards.
// The optimiser's changes swap one copy for a card from a pool (staples, cards played next to the
// deck's Pokémon in meta lists, the line's own cards, basic Energy of the line's types), move a
// copy between two cards of the deck, or trade a Trainer for an Energy. The seed's line keeps at
// least one copy of each stage.
import { Card, CardTag, CardType, EnergyCard, PokemonCard, Stage, SuperType } from './engine';
import { Deck, allCards, buildDeck, cardsNamed, loadCards, loadMetaLists, normName } from './cards';
import { checkLegal, engineCard, isBasicEnergy, standardNames } from './decklist';
import { Rng } from './rng';
import { cutWeight, fit, profile } from './synergy';

interface CardStat {
  lists: number;          // lists that include it
  copies: number[];       // copies in each list that includes it
  archetypes: Set<string>;
}

interface MetaStats {
  lists: { deck: string; rank: number; cards: string[]; id: string }[];
  byCard: Map<string, CardStat>;
  basicEnergyCount: number;     // median basic Energy in lists that play any
  lineCounts: Record<string, number[]>;   // "stage2" -> [basic, stage1, stage2, candy] medians, etc.
}

let stats: MetaStats | undefined;
const median = (xs: number[]) => {
  const s = xs.slice().sort((a, b) => a - b);
  return s.length ? s[Math.floor(s.length / 2)] : 0;
};

export function metaStats(): MetaStats {
  if (stats) {
    return stats;
  }
  loadCards();
  const lists: MetaStats['lists'] = [];
  const byCard = new Map<string, CardStat>();
  const energyCounts: number[] = [];
  const s2: number[][] = [], s1: number[][] = [];
  for (const l of loadMetaLists()) {
    const d = buildDeck(`${l.deck} #${l.list}`, l.deck, l.cards);
    if (d.missing.length || d.cards.length !== 60) {
      continue;
    }
    lists.push({ deck: l.deck, rank: l.rank, cards: d.cards, id: l.list });
    const counts = new Map<string, number>();
    d.cards.forEach(n => counts.set(n, (counts.get(n) ?? 0) + 1));
    for (const [n, k] of counts) {
      const st = byCard.get(n) ?? { lists: 0, copies: [], archetypes: new Set<string>() };
      st.lists++;
      st.copies.push(k);
      st.archetypes.add(l.deck);
      byCard.set(n, st);
    }
    const be = d.cards.filter(n => isBasicEnergy(engineCard(n))).length;
    if (be) {
      energyCounts.push(be);
    }
    // evolution line shapes: for each Stage 2 / Stage 1 played, the counts of its line
    const byName = new Map<string, number>();
    d.cards.forEach(n => {
      const c = engineCard(n);
      if (c) {
        byName.set(c.name, (byName.get(c.name) ?? 0) + 1);
      }
    });
    const candy = byName.get('Rare Candy') ?? 0;
    for (const [n] of counts) {
      const c = engineCard(n);
      if (!(c instanceof PokemonCard) || !c.evolvesFrom) {
        continue;
      }
      const mid = byName.get(c.evolvesFrom) ?? 0;
      if (c.stage === Stage.STAGE_2) {
        const midCard = cardsNamed(c.evolvesFrom).find(x => x instanceof PokemonCard) as PokemonCard | undefined;
        const base = midCard?.evolvesFrom ? byName.get(midCard.evolvesFrom) ?? 0 : 0;
        s2.push([base, mid, byName.get(c.name) ?? 0, candy]);
      } else if (c.stage === Stage.STAGE_1) {
        s1.push([mid, byName.get(c.name) ?? 0]);
      }
    }
  }
  const col = (rows: number[][], j: number) => median(rows.map(r => r[j]));
  stats = {
    lists, byCard,
    basicEnergyCount: median(energyCounts) || 8,
    lineCounts: {
      stage2: [col(s2, 0), col(s2, 1), col(s2, 2), col(s2, 3)].map(x => x || 1),
      stage1: [col(s1, 0), col(s1, 1)].map(x => x || 1),
    },
  };
  return stats;
}

/** Cards played across many archetypes, most common first. */
let evolvedFrom: Set<string> | undefined;
/** A staple Pokémon must stand alone: a Basic that nothing in the meta evolves from (support
 *  Pokémon such as Fezandipiti ex). Evolution lines are other decks' attackers, not staples. */
function standalone(n: string): boolean {
  const c = engineCard(n);
  if (!(c instanceof PokemonCard)) {
    return true;
  }
  if (!evolvedFrom) {
    evolvedFrom = new Set();
    for (const [m] of metaStats().byCard) {
      const e = engineCard(m);
      if (e instanceof PokemonCard && e.evolvesFrom) {
        evolvedFrom.add(e.evolvesFrom);
      }
    }
  }
  return c.stage === Stage.BASIC && !c.evolvesFrom && !evolvedFrom.has(c.name);
}

export function staples(minArchetypes = 3): { card: string; rate: number; copies: number }[] {
  const s = metaStats();
  return [...s.byCard].filter(([n, st]) => st.archetypes.size >= minArchetypes && !isBasicEnergy(engineCard(n)) && standalone(n))
    .map(([card, st]) => ({ card, rate: st.lists / s.lists.length, copies: median(st.copies) }))
    .sort((a, b) => b.rate - a.rate);
}

const legalPrintings = (name: string) => cardsNamed(name).filter(c => standardNames().has(c.fullName));

/** the printing of a name to use: the one meta lists play most, else any Standard one */
function printingOf(name: string): Card | undefined {
  const s = metaStats();
  const cands = legalPrintings(name);
  return cands.sort((a, b) => (s.byCard.get(b.fullName)?.lists ?? 0) - (s.byCard.get(a.fullName)?.lists ?? 0))[0];
}

/** The seed card's evolution line, Basic first (engine cards). */
export function lineOf(seed: Card): Card[] {
  const out: Card[] = [seed];
  let cur = seed as PokemonCard;
  for (let guard = 0; guard < 3 && cur instanceof PokemonCard && cur.evolvesFrom; guard++) {
    const prev = printingOf(cur.evolvesFrom);
    if (!prev) {
      break;
    }
    out.unshift(prev);
    cur = prev as PokemonCard;
  }
  return out;
}

const ENERGY_NAME: Partial<Record<CardType, string>> = {
  [CardType.GRASS]: 'Grass Energy', [CardType.FIRE]: 'Fire Energy', [CardType.WATER]: 'Water Energy',
  [CardType.LIGHTNING]: 'Lightning Energy', [CardType.PSYCHIC]: 'Psychic Energy', [CardType.FIGHTING]: 'Fighting Energy',
  [CardType.DARK]: 'Darkness Energy', [CardType.METAL]: 'Metal Energy',
};

function basicEnergy(t: CardType): Card | undefined {
  const name = ENERGY_NAME[t];
  return name ? cardsNamed(name).find(c => c instanceof EnergyCard && isBasicEnergy(c)) : undefined;
}

export interface SeedDeck {
  cards: string[];
  core: Map<string, number>;     // card -> minimum copies the optimiser keeps
  how: string;
  pool: string[];
  /** other meta lists that play the seed (other archetypes first), as extra starting points */
  alternatives: { cards: string[]; what: string }[];
}

/** Find the seed card by name (case-insensitive; a set code and number may follow). */
export function findSeed(query: string): Card {
  loadCards();
  const q = query.trim();
  const exact = allCards().filter(c => c.fullName.toLowerCase() === q.toLowerCase() && standardNames().has(c.fullName));
  if (exact.length) {
    return exact[0];
  }
  const byName = legalPrintings(q);
  if (byName.length) {
    return printingOf(q) ?? byName[0];
  }
  const near = allCards().filter(c => standardNames().has(c.fullName) && c.name.toLowerCase().includes(q.toLowerCase())).map(c => c.name);
  throw new Error(`no Standard card named "${q}"${near.length ? `; did you mean: ${[...new Set(near)].slice(0, 8).join(', ')}` : ''}`);
}

/** Cards the optimiser may add: staples, cards played next to the deck's Pokémon in meta lists, the
 *  deck's own cards, basic Energy of the types its attacks need. */
export function candidatePool(cards: string[]): string[] {
  const s = metaStats();
  const mine = new Set(cards);
  const pokes = new Set(cards.filter(n => engineCard(n) instanceof PokemonCard).map(n => engineCard(n)!.name));
  const pool = new Set<string>(cards);
  staples(2).slice(0, 80).forEach(x => pool.add(x.card));
  const generic = new Set(staples(4).map(x => x.card));
  for (const l of s.lists) {
    const shared = l.cards.filter(n => pokes.has(engineCard(n)?.name ?? '') && !generic.has(n));
    if (shared.length) {
      l.cards.forEach(n => pool.add(n));
    }
  }
  for (const n of mine) {
    const c = engineCard(n);
    if (c instanceof PokemonCard) {
      c.attacks.forEach(a => a.cost.forEach(t => {
        const e = basicEnergy(t);
        if (e) {
          pool.add(e.fullName);
        }
      }));
    }
  }
  return [...pool].filter(n => standardNames().has(n) || isBasicEnergy(engineCard(n)));
}

export function seedDeck(seedQuery: string): SeedDeck {
  const s = metaStats();
  const seed = findSeed(seedQuery);
  const line = lineOf(seed);
  const core = new Map<string, number>();
  line.forEach(c => core.set(c.fullName, 1));
  core.set(seed.fullName, 2);
  // 1. the seed is played in meta lists: start from the best-placed list of the archetype that plays it most
  const withSeed = s.lists.filter(l => l.cards.some(n => engineCard(n)?.name === seed.name));
  if (withSeed.length >= 2) {
    const arche = new Map<string, number>();
    withSeed.forEach(l => arche.set(l.deck, (arche.get(l.deck) ?? 0) + 1));
    const top = [...arche].sort((a, b) => b[1] - a[1])[0][0];
    const best = withSeed.filter(l => l.deck === top).sort((a, b) => a.rank - b.rank)[0];
    // other starting points: the best list of each other archetype, then the next lists of any
    const others = withSeed.filter(l => l !== best).sort((a, b) => a.rank - b.rank);
    const seenDeck = new Set([top]);
    const alt = [...others.filter(l => !seenDeck.has(l.deck) && seenDeck.add(l.deck)), ...others]
      .filter((l, i, a) => a.indexOf(l) === i);
    return {
      cards: best.cards.slice(), core,
      how: `${seed.name} is played in ${withSeed.length} meta lists; starting from the best-placed ${top} list (#${best.id}, placed ${best.rank}) that plays it`,
      pool: candidatePool(best.cards),
      alternatives: alt.map(l => ({ cards: l.cards.slice(), what: `meta list #${l.id} (${l.deck}, placed ${l.rank})` })),
    };
  }
  // 2. build it
  const cards: string[] = [];
  const add = (c: Card | undefined, k: number) => {
    if (!c) {
      return;
    }
    const have = cards.filter(n => engineCard(n)?.name === c.name).length;
    const room = isBasicEnergy(c) ? k : Math.max(0, Math.min(k, 4 - have));
    for (let i = 0; i < room && cards.length < 60; i++) {
      cards.push(c.fullName);
    }
  };
  const stage = (seed as PokemonCard).stage;
  if (stage === Stage.STAGE_2 && line.length === 3) {
    const [b, m, t, candy] = s.lineCounts.stage2;
    add(line[0], b);
    add(line[1], m);
    add(line[2], t);
    add(printingOf('Rare Candy'), candy);
  } else if (stage === Stage.STAGE_1 && line.length === 2) {
    const [b, t] = s.lineCounts.stage1;
    add(line[0], b);
    add(line[1], t);
  } else {
    line.forEach(c => add(c, c === seed ? 4 : 3));
  }
  // Energy for the line's attack costs
  const need = new Map<CardType, number>();
  line.forEach(c => (c as PokemonCard).attacks?.forEach(a => a.cost.forEach(t => {
    if (ENERGY_NAME[t]) {
      need.set(t, (need.get(t) ?? 0) + 1);
    }
  })));
  const total = [...need.values()].reduce((x, y) => x + y, 0);
  const energyCount = total ? s.basicEnergyCount : 0;
  const energies: [Card | undefined, number][] = [...need].map(([t, k]) => [basicEnergy(t), Math.max(1, Math.round(energyCount * k / total))]);
  // staples until 60, leaving room for the Energy
  const roomForEnergy = energies.reduce((x, [, k]) => x + k, 0);
  let ace = 0;
  // staples by how often the meta plays them, Pokémon also by how well they fit the line and its Energy
  const lineProfile = profile([...line.map(c => c.fullName), ...energies.filter(([c]) => c).map(([c]) => c!.fullName)]);
  const ranked = staples(3).map(st => {
    const c = engineCard(st.card);
    return { st, w: st.rate * (c instanceof PokemonCard ? Math.min(1, fit(st.card, lineProfile)) : 1) };
  }).sort((a, b) => b.w - a.w).map(x => x.st);
  for (const st of ranked) {
    if (cards.length >= 60 - roomForEnergy) {
      break;
    }
    const c = engineCard(st.card);
    if (!c || cards.some(n => engineCard(n)?.name === c.name)) {
      continue;
    }
    if (c.tags.includes(CardTag.ACE_SPEC)) {
      if (ace) {
        continue;
      }
      ace++;
    }
    add(c, Math.min(st.copies, 60 - roomForEnergy - cards.length));
  }
  energies.forEach(([c, k]) => add(c, k));
  // top up with the most common staple if short
  for (const st of staples(3)) {
    if (cards.length >= 60) {
      break;
    }
    const c = engineCard(st.card);
    if (c && !c.tags.includes(CardTag.ACE_SPEC)) {
      add(c, 60 - cards.length);
    }
  }
  return {
    cards: cards.slice(0, 60), core,
    how: `${seed.name} is not played in the meta lists; built from its line (${line.map(c => c.name).join(' -> ')}) in the usual counts for its stage, ${energyCount} basic Energy for its attack costs, and the most common staples`,
    pool: candidatePool(cards),
    alternatives: [],
  };
}

export interface Change {
  cards: string[];
  what: string;
}

/** weighted random pick (weights >= 0) */
function pickWeighted<T>(rng: Rng, xs: T[], w: (x: T) => number): T | undefined {
  const ws = xs.map(w);
  const tot = ws.reduce((a, b) => a + b, 0);
  if (!xs.length || !(tot > 0)) {
    return xs.length ? rng.pick(xs) : undefined;
  }
  let r = rng.next() * tot;
  for (let i = 0; i < xs.length; i++) {
    r -= ws[i];
    if (r <= 0) {
      return xs[i];
    }
  }
  return xs[xs.length - 1];
}

/** A random legal change of 1-2 steps; undefined if none was found. The card cut is more likely
 *  one that fits the rest of the deck badly, the card added one that fits it well (synergy.ts). */
export function mutate(cards: string[], pool: string[], core: Map<string, number>, rng: Rng): Change | undefined {
  const nameOf = (n: string) => engineCard(n)?.name ?? n;
  const printings = new Map<string, number>();
  new Set(pool).forEach(n => printings.set(nameOf(n), (printings.get(nameOf(n)) ?? 0) + 1));
  for (let tries = 0; tries < 50; tries++) {
    let next = cards.slice();
    const steps: string[] = [];
    const k = rng.chance(0.6) ? 1 : 2;
    for (let i = 0; i < k; i++) {
      const removable = [...new Set(next)].filter(n => {
        const have = next.filter(x => x === n).length;
        return have > (core.get(n) ?? 0);
      });
      if (!removable.length) {
        break;
      }
      const out = pickWeighted(rng, removable, n => cutWeight(n, next))!;
      const kind = rng.int(0, 2);
      const after = next.slice();
      after.splice(after.indexOf(out), 1);
      const prof = profile(after);
      // a name's weight is shared by its printings, so a card with three printings is not tripled
      const byFit = (n: string) => fit(n, prof) / (printings.get(nameOf(n)) ?? 1);
      let inn: string | undefined;
      if (kind === 0) {
        inn = pickWeighted(rng, pool, byFit);                // a card from the pool
      } else if (kind === 1) {
        inn = pickWeighted(rng, [...new Set(next)].filter(n => n !== out), byFit);   // one more of a card already in
      } else {
        // Energy <-> Trainer
        const outCard = engineCard(out);
        inn = isBasicEnergy(outCard) ? pickWeighted(rng, pool.filter(n => engineCard(n)?.superType === SuperType.TRAINER), byFit)
          : pickWeighted(rng, pool.filter(n => isBasicEnergy(engineCard(n))), byFit);
      }
      if (!inn || inn === out) {
        continue;
      }
      next.splice(next.indexOf(out), 1);
      next.push(inn);
      steps.push(`-1 ${engineCard(out)?.name ?? out}, +1 ${engineCard(inn)?.name ?? inn}`);
    }
    if (!steps.length) {
      continue;
    }
    const d: Deck = { id: 'x', archetype: 'x', cards: next, missing: [] };
    if (checkLegal(d, engineCard).ok) {
      next = next.slice().sort();
      return { cards: next, what: steps.join('; ') };
    }
  }
  return undefined;
}

/** k changes in a row (a bigger jump, for spreading out a starting population) */
export function mutateN(cards: string[], pool: string[], core: Map<string, number>, rng: Rng, k: number): Change | undefined {
  let cur: Change | undefined;
  for (let i = 0; i < k; i++) {
    const next = mutate(cur?.cards ?? cards, pool, core, rng);
    if (next) {
      cur = { cards: next.cards, what: cur ? `${cur.what}; ${next.what}` : next.what };
    }
  }
  return cur;
}

void normName;
