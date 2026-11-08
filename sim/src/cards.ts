// Card registry: loads every Twinleaf card once and maps decklist entries (set code + number, as
// Limitless / PTCGL print them) to Twinleaf card full names.
import * as fs from 'fs';
import * as path from 'path';
import { Card, CardManager, EnergyCard, PokemonCard, Sets, SuperType, EnergyType } from './engine';
import { engineSignature, printedFor, printedSignature } from './printed';

let loaded = false;
const all: Card[] = [];
const bySetNum = new Map<string, Card>();
const byName = new Map<string, Card[]>();

export function loadCards(): CardManager {
  const cm = CardManager.getInstance();
  if (loaded) {
    return cm;
  }
  for (const v of Object.values(Sets) as any[]) {
    if (!Array.isArray(v) || v.length === 0 || !(v[0] instanceof Card)) {
      continue;
    }
    for (const c of v as Card[]) {
      if (!cm.isCardDefined(c.fullName)) {
        cm.defineCard(c);
        all.push(c);
      }
      const key = `${String(c.set).toUpperCase()}|${normNum(c.setNumber)}`;
      if (!bySetNum.has(key)) {
        bySetNum.set(key, c);
      }
      const n = normName(c.name);
      const list = byName.get(n) ?? [];
      list.push(c);
      byName.set(n, list);
    }
  }
  loaded = true;
  return cm;
}

const SYMBOL: Record<string, string> = {
  G: 'grass', R: 'fire', W: 'water', L: 'lightning', P: 'psychic', F: 'fighting', D: 'darkness', M: 'metal', C: 'colorless', N: 'dragon', Y: 'fairy',
};

export function normName(s: string): string {
  // engine names sometimes use energy symbols ("Growing [G] Energy" = "Growing Grass Energy")
  return s.replace(/\[([GRWLPFDMCNY])\]/g, (_, t) => SYMBOL[t]).toLowerCase()
    .replace(/[’`]/g, "'").replace(/é/g, 'e').replace(/\s+/g, ' ').trim();
}

function normNum(n: string | number | undefined): string {
  return String(n ?? '').replace(/^0+/, '').toLowerCase();
}

const BASIC_ENERGY: Record<string, string> = {
  grass: 'Grass Energy', fire: 'Fire Energy', water: 'Water Energy', lightning: 'Lightning Energy',
  psychic: 'Psychic Energy', fighting: 'Fighting Energy', darkness: 'Darkness Energy', metal: 'Metal Energy',
};

export interface DeckEntry {
  name: string;
  set?: string;
  num?: string;
  count: number;
}

export interface ResolvedEntry {
  entry: DeckEntry;
  card?: Card;
  how: 'set+number' | 'same-stats' | 'name' | 'name-unverified' | 'basic-energy' | 'missing';
  note?: string;
}

/** Twinleaf card for one decklist line: exact printing first, then same-name card (reprints share
 *  text in Standard), then basic energy by type. */
export function resolveEntry(e: DeckEntry): ResolvedEntry {
  loadCards();
  if (e.set && e.num) {
    const c = bySetNum.get(`${e.set.toUpperCase()}|${normNum(e.num)}`);
    if (c && normName(c.name) === normName(e.name)) {
      return { entry: e, card: c, how: 'set+number' };
    }
  }
  const n = normName(e.name);
  const m = n.match(/^(?:basic )?(grass|fire|water|lightning|psychic|fighting|darkness|metal) energy$/);
  if (m) {
    const cands = (byName.get(normName(BASIC_ENERGY[m[1]])) ?? [])
      .filter(c => c instanceof EnergyCard && c.energyType === EnergyType.BASIC);
    // prefer a Scarlet & Violet / Mega Evolution era printing
    const pick = cands.find(c => /^(SVE|MEE)$/i.test(String(c.set))) ?? cands[0];
    if (pick) {
      return { entry: e, card: pick, how: 'basic-energy' };
    }
  }
  const same = (byName.get(n) ?? []).slice()
    .sort((a, b) => String((b as any).regulationMark ?? '').localeCompare(String((a as any).regulationMark ?? '')));
  if (!same.length) {
    return { entry: e, how: 'missing' };
  }
  // Different cards can share a name (Chi-Yu TWM is Fire, Chi-Yu PBL is Dark). For Pokémon, a
  // same-name engine card stands in for the printing only if its rules-relevant stats match the
  // printed card. Trainers and Energy with the same name are the same card.
  const pc = printedFor(e.set, e.num);
  if (pc && pc.supertype === 'Pokémon') {
    const want = printedSignature(pc);
    const match = same.find(c => c instanceof PokemonCard && engineSignature(c) === want);
    if (match) {
      return { entry: e, card: match, how: 'same-stats' };
    }
    return { entry: e, how: 'missing', note: `no engine card matches ${e.name} ${e.set} ${e.num} (${want}); same-name cards: ${same.map(c => c.fullName).join(', ')}` };
  }
  return { entry: e, card: same[0], how: pc ? 'name' : 'name-unverified' };
}

export interface Deck {
  id: string;
  archetype: string;
  cards: string[];          // 60 Twinleaf full names
  missing: DeckEntry[];
}

export function buildDeck(id: string, archetype: string, entries: DeckEntry[]): Deck {
  const cards: string[] = [];
  const missing: DeckEntry[] = [];
  for (const e of entries) {
    const r = resolveEntry(e);
    if (!r.card) {
      missing.push(e);
      continue;
    }
    for (let i = 0; i < e.count; i++) {
      cards.push(r.card.fullName);
    }
  }
  return { id, archetype, cards, missing };
}

const REPO = path.resolve(__dirname, '..', '..');

export interface MetaList {
  tournament: string;
  event: string;
  rank: number;
  deck: string;
  list: string;
  cards: DeckEntry[];
}

export function loadMetaLists(file = path.join(REPO, 'meta', 'decklists_2026-09-19_to_10-31.json')): MetaList[] {
  return JSON.parse(fs.readFileSync(file, 'utf8'));
}

/** Best-placing complete list per archetype (no missing cards), in meta-share order. */
export function metaDecks(limit = 1000): Deck[] {
  const lists = loadMetaLists();
  const share = new Map<string, number>();
  lists.forEach(l => share.set(l.deck, (share.get(l.deck) ?? 0) + 1));
  const best = new Map<string, Deck>();
  for (const l of lists.slice().sort((a, b) => a.rank - b.rank)) {
    if (best.has(l.deck)) {
      continue;
    }
    const d = buildDeck(`${l.deck} #${l.list}`, l.deck, l.cards);
    if (d.missing.length === 0 && d.cards.length === 60) {
      best.set(l.deck, d);
    }
  }
  return [...best.values()].sort((a, b) => (share.get(b.archetype)! - share.get(a.archetype)!)).slice(0, limit);
}

export function isPokemon(c: Card): c is PokemonCard {
  return c.superType === SuperType.POKEMON;
}

/** Names that a card called `name` evolves from (over all printings with that name). */
export function evolvesFromNames(name: string): Set<string> {
  loadCards();
  const out = new Set<string>();
  for (const c of byName.get(normName(name)) ?? []) {
    const pc = c as PokemonCard;
    if (pc.evolvesFrom) {
      out.add(pc.evolvesFrom);
    }
    ((pc as any).evolvesFromBase ?? []).forEach((n: string) => out.add(n));
  }
  // old LV.X cards "evolve" from a Pokémon with their own name; that is never a lower stage
  out.delete(name);
  return out;
}

/** Every distinct card definition (prototype objects - copy with CardManager before use). */
export function allCards(): Card[] {
  loadCards();
  return all;
}

export function cardsNamed(name: string): Card[] {
  loadCards();
  return byName.get(normName(name)) ?? [];
}

export function cardBySetNumber(set: string, num: string): Card | undefined {
  loadCards();
  return bySetNum.get(`${set.toUpperCase()}|${normNum(num)}`);
}

export const REPO_ROOT = REPO;
