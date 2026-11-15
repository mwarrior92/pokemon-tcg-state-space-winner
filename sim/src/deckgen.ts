// Deck generation from a seed card, and the changes the optimiser tries.
//
// Everything comes from the 512 meta decklists (no hand-written deck-building rules):
//   - if the seed card is played in meta lists, the start is the best-placed complete list of the
//     archetype that plays it most;
//   - otherwise the deck is built: the seed's evolution line in the counts meta lists use for
//     lines of that stage (Rare Candy for a Stage 2 as often as they do), basic Energy for the line's
//     attack costs in the usual amount, then the staples (cards played across many archetypes) in
//     their usual counts until 60 cards.
// Random starts (randomStarts): several starting decks around the same seed that share nothing but
// the seed's line and its Energy: every other card is drawn uniformly from all Standard cards and
// kept if the rules check (usability.ts) says the deck can use it. Each start is the root of its
// own family in the search (cli/deckbuilder.ts).
// The optimiser's changes swap one copy for a card from a pool (staples, cards played next to the
// deck's Pokémon in meta lists, the line's own cards, basic Energy of the line's types), move a
// copy between two cards of the deck, or trade a Trainer for an Energy. The seed's line keeps at
// least one copy of each stage.
import { Card, CardTag, CardType, EnergyCard, PokemonCard, Stage, SuperType } from './engine';
import { Deck, allCards, buildDeck, cardsNamed, loadCards, loadMetaLists, normName } from './cards';
import { checkLegal, engineCard, isBasicEnergy, standardNames } from './decklist';
import { ISSUE_TEXT, Issue, remedies } from './diagnose';
import { Rng } from './rng';
import { cutWeight, fit, profile } from './synergy';
import { deckFacts, sideEffect, unusableCards, whyUnusable } from './usability';

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
  // (a Basic is where the line starts, whatever its data says: the engine's Meltan SCR "evolves from Meltan")
  for (let guard = 0; guard < 3 && cur instanceof PokemonCard && cur.evolvesFrom && cur.stage !== Stage.BASIC; guard++) {
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

/** The seed's line in the counts meta lists use for lines of its stage (Rare Candy for a Stage 2). */
function lineKit(seed: Card, line: Card[], s: MetaStats): [Card | undefined, number][] {
  const stage = (seed as PokemonCard).stage;
  if (stage === Stage.STAGE_2 && line.length === 3) {
    const [b, m, t, candy] = s.lineCounts.stage2;
    return [[line[0], b], [line[1], m], [line[2], t], [printingOf('Rare Candy'), candy]];
  }
  if (stage === Stage.STAGE_1 && line.length === 2) {
    const [b, t] = s.lineCounts.stage1;
    return [[line[0], b], [line[1], t]];
  }
  return line.map(c => [c, c === seed ? 4 : 3]);
}

/** basic Energy types the line's attacks cost, with how often each appears */
function lineEnergy(line: Card[]): Map<CardType, number> {
  const need = new Map<CardType, number>();
  line.forEach(c => (c as PokemonCard).attacks?.forEach(a => a.cost.forEach(t => {
    if (ENERGY_NAME[t]) {
      need.set(t, (need.get(t) ?? 0) + 1);
    }
  })));
  return need;
}

export interface SeedDeck {
  cards: string[];
  core: Map<string, number>;     // card -> minimum copies the optimiser keeps
  how: string;
  pool: string[];
  /** random starts: the basic Energy types the seed's line pays with; the search adds no others */
  energyTypes?: CardType[];
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
 *  deck's own cards, basic Energy of the types its attacks need.
 *  `energyTypes` (random starts): the only basic Energy types allowed in the pool. Without it every
 *  Pokémon in the list brings the Energy of its attack costs in, and so does every meta list that
 *  shares a Pokémon with it: a random partner then pulls the deck towards three or four types. */
export function candidatePool(cards: string[], energyTypes?: CardType[]): string[] {
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
  const allowed = energyTypes?.length ? new Set(energyTypes.map(t => basicEnergy(t)?.name)) : undefined;
  return [...pool].filter(n => {
    const c = engineCard(n);
    return isBasicEnergy(c) ? !allowed || allowed.has(c!.name) : standardNames().has(n);
  });
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
  lineKit(seed, line, s).forEach(([c, k]) => add(c, k));
  // Energy for the line's attack costs
  const need = lineEnergy(line);
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
    // skip staples this deck could not use (e.g. Teal Mask Ogerpon ex without Grass Energy)
    if (whyUnusable(st.card, deckFacts([...cards, ...energies.filter(([e]) => e).map(([e]) => e!.fullName), st.card]))) {
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
  // repair: a staple chosen early can end up unusable in the finished list (Buddy-Buddy Poffin with
  // no Basic of 70 HP or less); take such cards out (never the seed's line) and refill
  const lineNames = new Set(line.map(c => c.fullName));
  const removed = new Set<string>();
  for (let guard = 0; guard < 5; guard++) {
    const bad = unusableCards(cards).filter(u => !lineNames.has(u.card));
    if (!bad.length) {
      break;
    }
    bad.forEach(u => removed.add(u.card));
    for (let i = cards.length - 1; i >= 0; i--) {
      if (bad.some(u => u.card === cards[i])) {
        cards.splice(i, 1);
      }
    }
    // top up with the most common usable staple if short
    for (const st of staples(3)) {
      if (cards.length >= 60) {
        break;
      }
      const c = engineCard(st.card);
      if (c && !removed.has(st.card) && !c.tags.includes(CardTag.ACE_SPEC) && !whyUnusable(st.card, deckFacts([...cards, st.card]))) {
        add(c, 60 - cards.length);
      }
    }
  }
  // top up with the most common staple if short
  for (const st of staples(3)) {
    if (cards.length >= 60) {
      break;
    }
    const c = engineCard(st.card);
    if (c && !c.tags.includes(CardTag.ACE_SPEC) && !whyUnusable(st.card, deckFacts([...cards, st.card]))) {
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

/** `n` starting decks around the seed card that are as different as 60-card decks around one card
 *  can be: each has the seed's line in its usual counts and basic Energy for the line's attack costs
 *  (a random amount); every other card is drawn uniformly at random from all Standard cards - any
 *  card the rules check says the deck can use, in a random number of copies, a Pokémon with the rest
 *  of its line. No card outside the seed's line, Rare Candy and basic Energy is in two of the decks.
 *  Nothing here looks at what the meta plays: most of these decks are weak, and the search is what
 *  finds the good ones.
 *  `shaped` (the default): two of three Standard cards are Pokémon, so a draw from all cards alike
 *  gives 40 Pokémon and half a dozen Trainers. Shaped, each start first draws how many other Pokémon
 *  cards it takes (8 to 20); the rest are Trainers and Special Energy. Within each kind every card
 *  is as likely as any other. */
export function randomStarts(seedQuery: string, n: number, rng: Rng, shaped = true): SeedDeck[] {
  const s = metaStats();
  const seed = findSeed(seedQuery);
  const line = lineOf(seed);
  const core = new Map<string, number>();
  line.forEach(c => core.set(c.fullName, 1));
  core.set(seed.fullName, 2);
  const kit = lineKit(seed, line, s).filter((x): x is [Card, number] => !!x[0]);
  const need = lineEnergy(line);
  const needTotal = [...need.values()].reduce((x, y) => x + y, 0);
  const everything = [...standardNames()].filter(nm => engineCard(nm) && !isBasicEnergy(engineCard(nm))).sort();
  const pokemon = everything.filter(nm => engineCard(nm) instanceof PokemonCard), others = everything.filter(nm => !(engineCard(nm) instanceof PokemonCard));
  const shared = new Set(kit.map(([c]) => c.name));     // card names every start has
  const taken = new Set<string>();                      // card names another start has
  const out: SeedDeck[] = [];
  for (let d = 0; d < n; d++) {
    const cards: string[] = [];
    kit.forEach(([c, k]) => {
      for (let i = 0; i < k; i++) {
        cards.push(c.fullName);
      }
    });
    // Energy first, so the rules check knows what the deck can pay for
    const energyCount = needTotal ? rng.int(6, 14) : 0;
    need.forEach((k, t) => {
      const e = basicEnergy(t);
      for (let i = 0; e && i < Math.max(1, Math.round(energyCount * k / needTotal)); i++) {
        cards.push(e.fullName);
      }
    });
    const picked: string[] = [];                        // what the draw added, by card name
    const has = (name: string) => cards.some(x => engineCard(x)?.name === name);
    const free = (name: string) => !shared.has(name) && !taken.has(name) && !has(name);
    const budget = rng.int(8, 20);
    let drawnPokemon = 0;
    const draw = (): void => {
      const c = engineCard(rng.pick(!shaped ? everything : drawnPokemon < budget && rng.chance(0.5) ? pokemon : others))!;
      // a Pokémon comes with the stages below it, each in the same number of copies
      const group = (c instanceof PokemonCard ? lineOf(c) : [c]).filter((g, i, a) => a.findIndex(x => x.name === g.name) === i);
      if (!group.every(g => free(g.name)) || (c instanceof PokemonCard && c.evolvesFrom && group.length < 2)) {
        return;
      }
      const aceSpec = c.tags.includes(CardTag.ACE_SPEC);
      if (aceSpec && cards.some(x => engineCard(x)?.tags.includes(CardTag.ACE_SPEC))) {
        return;
      }
      const room = Math.min(60 - cards.length, shaped && c instanceof PokemonCard ? budget - drawnPokemon : 60);
      const k = Math.min(aceSpec ? 1 : rng.int(1, group.length > 1 ? 3 : 4), Math.floor(room / group.length));
      if (k < 1) {
        return;
      }
      const added = group.flatMap(g => Array.from({ length: k }, () => g.fullName));
      const facts = deckFacts([...cards, ...added]);
      if (group.some(g => whyUnusable(g.fullName, facts))) {
        return;
      }
      cards.push(...added);
      picked.push(c.name);
      drawnPokemon += c instanceof PokemonCard ? added.length : 0;
    };
    // fill, then take out what the finished list cannot use after all (never the seed's line) and fill again
    const kitNames = new Set(kit.map(([c]) => c.fullName));
    for (let round = 0; round < 6; round++) {
      for (let guard = 0; cards.length < 60 && guard < 4000; guard++) {
        draw();
      }
      const bad = new Set(unusableCards(cards).filter(u => !kitNames.has(u.card)).map(u => u.card));
      if (!bad.size) {
        break;
      }
      for (let i = cards.length - 1; i >= 0; i--) {
        if (bad.has(cards[i])) {
          drawnPokemon -= engineCard(cards[i]) instanceof PokemonCard ? 1 : 0;
          cards.splice(i, 1);
        }
      }
    }
    // a few cards short after all that: basic Energy
    const spare = basicEnergy([...need.keys()][0] ?? CardType.GRASS);
    while (cards.length < 60 && spare) {
      cards.push(spare.fullName);
    }
    cards.forEach(x => {
      const c = engineCard(x);
      if (c && !shared.has(c.name) && !isBasicEnergy(c)) {
        taken.add(c.name);
      }
    });
    const kept = picked.filter(has);
    out.push({
      cards, core,
      how: `random start ${d + 1}: ${line.map(c => c.name).join(' -> ')} with ${cards.filter(x => isBasicEnergy(engineCard(x))).length} basic Energy and ${kept.length} cards drawn at random from all of Standard (${kept.join(', ')})`,
      pool: candidatePool(cards, [...need.keys()]),
      energyTypes: [...need.keys()],
      alternatives: [],
    });
  }
  return out;
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
  const baseBad = unusableCards(cards).length;
  for (let tries = 0; tries < 50; tries++) {
    let next = cards.slice();
    const steps: string[] = [];
    const added: string[] = [];
    const k = rng.chance(0.6) ? 1 : 2;
    for (let i = 0; i < k; i++) {
      const removable = [...new Set(next)].filter(n => {
        const have = next.filter(x => x === n).length;
        return have > (core.get(n) ?? 0);
      });
      if (!removable.length) {
        break;
      }
      // cards the list cannot use are by far the likeliest cuts
      const nextFacts = deckFacts(next);
      const out = pickWeighted(rng, removable, n => cutWeight(n, next) * (whyUnusable(n, nextFacts) ? 20 : 1))!;
      const kind = rng.int(0, 2);
      const after = next.slice();
      after.splice(after.indexOf(out), 1);
      const prof = profile(after);
      const facts = deckFacts(after);
      // cards the deck could not use get almost no weight (and are rejected below); cards that would
      // also hurt some of its own cards (Team Rocket's Watchtower with a Meowth ex) are tried less often
      const byFit = (n: string) => fit(n, prof) / (printings.get(nameOf(n)) ?? 1) * (whyUnusable(n, facts) ? 0.02 : sideEffect(n, facts) ? 0.3 : 1);
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
      added.push(inn);
      steps.push(`-1 ${engineCard(out)?.name ?? out}, +1 ${engineCard(inn)?.name ?? inn}`);
    }
    if (!steps.length) {
      continue;
    }
    const d: Deck = { id: 'x', archetype: 'x', cards: next, missing: [] };
    // every card must stay usable: no unusable card added, none stranded (e.g. its Energy cut)
    const bad = unusableCards(next);
    if (bad.length > baseBad || bad.some(b => added.includes(b.card))) {
      continue;
    }
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

/** A big change for a rough list (a random start): one whole group leaves the deck - a partner
 *  Pokémon with the rest of its line, or every copy of one Trainer or Special Energy - and cards from
 *  the pool take its place, each in the number of copies meta lists play (a Pokémon with its line).
 *  A family can leave its thirty random cards in a few such steps; one copy at a time it cannot.
 *  The group that leaves is more likely one that fits the rest badly or cannot be used; the cards
 *  that come in are picked by fit, as in `mutate`. The seed's line (`core`) is never touched. */
export function swapGroup(cards: string[], pool: string[], core: Map<string, number>, rng: Rng): Change | undefined {
  const s = metaStats();
  const nameOf = (n: string) => engineCard(n)?.name ?? n;
  const coreNames = new Set([...core.keys()].map(nameOf));
  const printings = new Map<string, number>();
  new Set(pool).forEach(n => printings.set(nameOf(n), (printings.get(nameOf(n)) ?? 0) + 1));
  const baseBad = unusableCards(cards).length;
  const facts0 = deckFacts(cards);
  // the groups, as sets of card names
  const distinct = [...new Set(cards)];
  const pokes = distinct.map(n => engineCard(n)).filter((c): c is PokemonCard => c instanceof PokemonCard);
  const below = new Set(pokes.filter(c => c.stage !== Stage.BASIC).map(c => c.evolvesFrom).filter(Boolean));
  const tops = pokes.filter(c => !below.has(c.name));
  const lines = tops.map(c => new Set(lineOf(c).map(x => x.name)));
  const groups: Set<string>[] = [];
  lines.forEach((ln, i) => {
    // not the seed's line, and not a stage another line of the deck also stands on
    const own = new Set([...ln].filter(nm => !coreNames.has(nm) && !lines.some((o, j) => j !== i && o.has(nm))));
    if (own.size && !coreNames.has(tops[i].name)) {
      groups.push(own);
    }
  });
  distinct.forEach(n => {
    const c = engineCard(n);
    if (c && !(c instanceof PokemonCard) && !isBasicEnergy(c) && !coreNames.has(c.name) && !groups.some(g => g.has(c.name))) {
      groups.push(new Set([c.name]));
    }
  });
  if (!groups.length) {
    return undefined;
  }
  const groupWeight = (g: Set<string>) => {
    const mine = distinct.filter(n => g.has(nameOf(n)));
    const w = mine.reduce((x, n) => x + cutWeight(n, cards), 0) / Math.max(1, mine.length);
    // by size as well: a four-card group is four times as likely to go as a single copy, which is
    // no bigger a step than a one-card change
    const size = cards.filter(n => g.has(nameOf(n))).length;
    return w * size * (mine.some(n => whyUnusable(n, facts0)) ? 20 : 1);
  };
  const weights = new Map(groups.map(g => [g, groupWeight(g)]));
  for (let tries = 0; tries < 20; tries++) {
    const out = pickWeighted(rng, groups, g => weights.get(g)!)!;
    const next = cards.filter(n => !out.has(nameOf(n)));
    const gone = cards.length - next.length;
    const prof = profile(next);
    const facts = deckFacts(next);
    const cands = [...new Set(pool)].filter(n => !out.has(nameOf(n)) && (isBasicEnergy(engineCard(n)) || !next.some(x => nameOf(x) === nameOf(n))));
    const w = new Map(cands.map(n => [n, fit(n, prof) / (printings.get(nameOf(n)) ?? 1) * (whyUnusable(n, facts) ? 0.02 : sideEffect(n, facts) ? 0.3 : 1)]));
    const added: string[] = [];
    const steps: string[] = [];
    for (let guard = 0; next.length < cards.length && guard < 200; guard++) {
      const inn = pickWeighted(rng, cands, n => w.get(n)!);
      const c = inn && engineCard(inn);
      if (!inn || !c) {
        continue;
      }
      const room = cards.length - next.length;
      if (isBasicEnergy(c)) {
        next.push(inn);
        added.push(inn);
        steps.push(`+1 ${c.name}`);
        continue;
      }
      if (next.some(x => nameOf(x) === c.name) || (c.tags.includes(CardTag.ACE_SPEC) && next.some(x => engineCard(x)?.tags.includes(CardTag.ACE_SPEC)))) {
        continue;
      }
      // a Pokémon comes with the stages below it that the deck does not have yet
      const line = (c instanceof PokemonCard ? lineOf(c) : [c]).filter((g, i, a) => a.findIndex(x => x.name === g.name) === i);
      const group = line.filter(g => g === c || !next.some(x => nameOf(x) === g.name));
      if (line.some(g => out.has(g.name)) || (c instanceof PokemonCard && c.stage !== Stage.BASIC && line.length < 2)) {
        continue;
      }
      const usual = c.tags.includes(CardTag.ACE_SPEC) ? 1 : median(s.byCard.get(inn)?.copies ?? [1]) || 1;
      const k = Math.min(usual, 4, Math.floor(room / group.length));
      if (k < 1) {
        continue;
      }
      group.forEach(g => {
        for (let i = 0; i < k; i++) {
          next.push(g.fullName);
          added.push(g.fullName);
        }
        steps.push(`+${k} ${g.name}`);
      });
    }
    if (next.length !== cards.length) {
      continue;
    }
    const bad = unusableCards(next);
    if (bad.length > baseBad || bad.some(b => added.includes(b.card))) {
      continue;
    }
    if (checkLegal({ id: 'x', archetype: 'x', cards: next, missing: [] }, engineCard).ok) {
      return { cards: next.slice().sort(), what: `out ${[...out].join(', ')} (${gone} cards); in ${steps.join(', ')}` };
    }
  }
  return undefined;
}

/** A change aimed at a flag from the deck's games (diagnose.ts): a card from the pool that answers
 *  it comes in (basic Energy for "no Energy to attach", a switch card for "the Active was stuck",
 *  a card that draws for "dead hand", ...), in up to the number of copies meta lists play, and as
 *  many copies leave of the cards the deck used least. `used`: by card name, the share of the deck's
 *  games the card was used in; without it the cut goes by fit alone. Cards that answer the flag
 *  themselves are not cut for it, nor is the seed's line below `core`. */
export function fixIssue(cards: string[], pool: string[], core: Map<string, number>, rng: Rng, issue: Issue, used?: Map<string, number>): Change | undefined {
  const s = metaStats();
  const nameOf = (n: string) => engineCard(n)?.name ?? n;
  const count = (list: string[], name: string) => list.filter(x => nameOf(x) === name).length;
  const baseBad = unusableCards(cards).length;
  const prof = profile(cards);
  const facts = deckFacts(cards);
  const printings = new Map<string, number>();
  new Set(pool).forEach(n => printings.set(nameOf(n), (printings.get(nameOf(n)) ?? 0) + 1));
  const cands = [...new Set(pool)].filter(n => {
    const c = engineCard(n);
    return !!c && remedies(issue, c) && (isBasicEnergy(c) || count(cards, c.name) < 4)
      && !(c.tags.includes(CardTag.ACE_SPEC) && cards.some(x => engineCard(x)?.tags.includes(CardTag.ACE_SPEC)))
      // a Pokémon that needs a line below it is a job for the other changes
      && !(c instanceof PokemonCard && c.stage !== Stage.BASIC);
  });
  if (!cands.length) {
    return undefined;
  }
  const w = new Map(cands.map(n => [n, fit(n, prof) / (printings.get(nameOf(n)) ?? 1) * (whyUnusable(n, deckFacts([...cards, n])) ? 0.02 : sideEffect(n, facts) ? 0.3 : 1)]));
  for (let tries = 0; tries < 30; tries++) {
    const inn = pickWeighted(rng, cands, n => w.get(n)!)!;
    const c = engineCard(inn)!;
    const usual = isBasicEnergy(c) ? rng.int(1, 3) : c.tags.includes(CardTag.ACE_SPEC) ? 1 : median(s.byCard.get(inn)?.copies ?? [rng.int(1, 3)]) || 1;
    const k = Math.max(1, Math.min(usual, isBasicEnergy(c) ? 3 : 4 - count(cards, c.name)));
    const next = cards.slice();
    const cut: string[] = [];
    for (let i = 0; i < k; i++) {
      const removable = [...new Set(next)].filter(n => {
        const e = engineCard(n);
        return next.filter(x => x === n).length > (core.get(n) ?? 0) && !(e && remedies(issue, e)) && nameOf(n) !== c.name;
      });
      if (!removable.length) {
        break;
      }
      const nf = deckFacts(next);
      // little used in the deck's own games: the likeliest cut (a card never used counts four times
      // one used in every game); cards the list cannot use before any other
      const out = pickWeighted(rng, removable, n => cutWeight(n, next) * (whyUnusable(n, nf) ? 20 : 1) * (used ? 1 + 3 * (1 - (used.get(nameOf(n)) ?? 0)) : 1))!;
      next.splice(next.indexOf(out), 1);
      cut.push(nameOf(out));
    }
    if (!cut.length) {
      continue;
    }
    cut.forEach(() => next.push(inn));
    const bad = unusableCards(next);
    if (bad.length > baseBad || bad.some(b => b.card === inn)) {
      continue;
    }
    if (checkLegal({ id: 'x', archetype: 'x', cards: next, missing: [] }, engineCard).ok) {
      const tally = new Map<string, number>();
      cut.forEach(n => tally.set(n, (tally.get(n) ?? 0) + 1));
      return { cards: next.slice().sort(), what: `for "${ISSUE_TEXT[issue]}": ${[...tally].map(([n, x]) => `-${x} ${n}`).join(', ')}, +${cut.length} ${c.name}` };
    }
  }
  return undefined;
}

void normName;
