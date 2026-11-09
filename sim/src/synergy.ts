// How well a card fits a deck, as a weight for the deck builder's random changes: cards that fit
// are added more often and cards that fit worst are cut more often. Nothing is ruled out.
//
// fit(card, deck) = meta co-occurrence x Energy fit x evolution links x basic-Energy demand
//  - co-occurrence: in the meta decklists, how much more often the card is played next to the deck's
//    cards than chance would give (smoothed lift, averaged over the deck's cards that the meta plays;
//    1 when there is nothing to go on, e.g. new or off-meta cards).
//  - Energy fit: the share of a Pokémon's attacks the deck's basic Energy types (plus Colorless) can
//    pay; a Pokémon with an ability counts as at least half playable (support Pokémon).
//  - evolution links: a Pokémon that evolves from, or into, one of the deck's Pokémon is boosted; an
//    evolution with nothing to evolve from is heavily discounted, as is Rare Candy without a Stage 2.
//  - basic Energy: an Energy type that no attack in the deck uses is discounted.
import { CardType, PokemonCard, Stage } from './engine';
import { engineCard, isBasicEnergy } from './decklist';
import { loadMetaLists, resolveEntry } from './cards';

interface CoStats { n: number; count: Map<string, number>; pair: Map<string, number> }
let co: CoStats | undefined;

/** card-name co-occurrence over the meta decklists (printings merged) */
function coStats(): CoStats {
  if (co) {
    return co;
  }
  const count = new Map<string, number>();
  const pair = new Map<string, number>();
  let n = 0;
  for (const l of loadMetaLists()) {
    const names = [...new Set(l.cards.map(e => resolveEntry(e).card?.name).filter((x): x is string => !!x))].sort();
    if (!names.length) {
      continue;
    }
    n++;
    for (let i = 0; i < names.length; i++) {
      count.set(names[i], (count.get(names[i]) ?? 0) + 1);
      for (let j = i + 1; j < names.length; j++) {
        const k = `${names[i]}|${names[j]}`;
        pair.set(k, (pair.get(k) ?? 0) + 1);
      }
    }
  }
  co = { n, count, pair };
  return co;
}

/** smoothed lift of two card names in the meta lists; undefined if either is rarely played */
export function lift(a: string, b: string): number | undefined {
  const s = coStats();
  const na = s.count.get(a) ?? 0, nb = s.count.get(b) ?? 0;
  if (na < 3 || nb < 3 || a === b) {
    return undefined;
  }
  const nab = s.pair.get(a < b ? `${a}|${b}` : `${b}|${a}`) ?? 0;
  return (nab + 1) / (na * nb / s.n + 1);
}

const ENERGY_TYPES = [CardType.GRASS, CardType.FIRE, CardType.WATER, CardType.LIGHTNING, CardType.PSYCHIC,
  CardType.FIGHTING, CardType.DARK, CardType.METAL];

export interface DeckProfile {
  names: Set<string>;
  energy: Set<CardType>;        // basic Energy types in the deck
  needs: Set<CardType>;         // Energy types the deck's attacks ask for
  pokeNames: Set<string>;
  evolvesFrom: Set<string>;     // names the deck's Pokémon evolve from
  hasStage2: boolean;
}

export function profile(cards: string[]): DeckProfile {
  const p: DeckProfile = { names: new Set(), energy: new Set(), needs: new Set(), pokeNames: new Set(), evolvesFrom: new Set(), hasStage2: false };
  for (const n of new Set(cards)) {
    const c = engineCard(n);
    if (!c) {
      continue;
    }
    p.names.add(c.name);
    if (isBasicEnergy(c)) {
      (c as any).provides?.forEach((t: CardType) => p.energy.add(t));
    }
    if (c instanceof PokemonCard) {
      p.pokeNames.add(c.name);
      if (c.evolvesFrom) {
        p.evolvesFrom.add(c.evolvesFrom);
      }
      if (c.stage === Stage.STAGE_2) {
        p.hasStage2 = true;
      }
      c.attacks.forEach(a => a.cost.forEach(t => ENERGY_TYPES.includes(t) && p.needs.add(t)));
    }
  }
  return p;
}

/** how well card `n` fits a deck with profile `p` (about 1 = neutral; 0.02 to 6) */
export function fit(n: string, p: DeckProfile): number {
  const c = engineCard(n);
  if (!c) {
    return 1;
  }
  // meta co-occurrence with the deck's other cards
  const lifts = [...p.names].filter(m => m !== c.name).map(m => lift(c.name, m)).filter((x): x is number => x !== undefined);
  let w = lifts.length ? Math.exp(lifts.reduce((s, x) => s + Math.log(x), 0) / lifts.length) : 1;
  w = Math.min(5, Math.max(0.2, w));
  if (isBasicEnergy(c)) {
    const t: CardType | undefined = (c as any).provides?.[0];
    // judged by what the deck's attacks use, not by co-occurrence
    return t !== undefined && p.needs.has(t) ? 1.5 : t !== undefined && p.energy.has(t) ? 0.7 : 0.15;
  }
  if (c instanceof PokemonCard) {
    // Energy fit (soft)
    if (c.attacks.length) {
      const payable = c.attacks.filter(a => a.cost.every(t => !ENERGY_TYPES.includes(t) || p.energy.has(t))).length / c.attacks.length;
      const f = c.powers.length ? Math.max(0.5, payable) : payable;
      w *= 0.25 + 0.75 * f;
    }
    // evolution links
    if (c.evolvesFrom && !p.names.has(c.evolvesFrom)) {      // names: Fossils are Trainers
      w *= 0.1;                      // nothing to evolve it from (yet)
    } else if (c.evolvesFrom) {
      w *= 2;
    }
    if (p.evolvesFrom.has(c.name)) {
      w *= 2;                        // a piece of one of the deck's lines
    }
  } else if (c.name === 'Rare Candy' && !p.hasStage2) {
    w *= 0.1;
  }
  return Math.min(6, w);
}

/** a card's weight for being cut: how badly it fits the rest of the deck */
export function cutWeight(n: string, cards: string[]): number {
  const rest = cards.slice();
  rest.splice(rest.indexOf(n), 1);
  // judged against the rest of the deck, so the last Basic of a line the deck still plays counts
  // as a good fit (the line evolves from it)
  return 1 / Math.sqrt(fit(n, profile(rest)));
}
