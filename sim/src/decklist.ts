// Decklists as text (the Pokémon TCG Live export format), legality checks, and formatting.
//
//   Pokémon: 13
//   4 Dreepy TWM 128
//   ...
//   Energy: 8
//   5 Basic Psychic Energy SVE 5
//
// Lines are "<count> <name> [<set> <number>]"; section headers and "Total Cards" lines are ignored.
// A line without set and number resolves by name (Standard printings share text).
import { Card, CardTag, EnergyCard, EnergyType, PokemonCard, Stage, SuperType, TrainerCard } from './engine';
import { Deck, DeckEntry, allCards, buildDeck, loadCards, resolveEntry } from './cards';
import { standardPool } from './cardcheck';

export function parseDeckList(text: string): DeckEntry[] {
  const out: DeckEntry[] = [];
  for (const raw of text.split(/\r?\n/)) {
    const line = raw.trim();
    if (!line || /^(pok[eé]mon|trainer|energy|total cards)\b.*:/i.test(line) || line.startsWith('#')) {
      continue;
    }
    const full = /^(\d+)\s+(.+?)\s+([A-Za-z0-9]{2,5}(?:-[A-Za-z0-9]+)?)\s+(\d+[a-zA-Z]?)$/.exec(line);
    if (full) {
      out.push({ count: Number(full[1]), name: full[2], set: full[3], num: full[4] });
      continue;
    }
    const nameOnly = /^(\d+)\s+(.+)$/.exec(line);
    if (nameOnly) {
      out.push({ count: Number(nameOnly[1]), name: nameOnly[2] });
    }
  }
  return out;
}

let byFull: Map<string, Card> | undefined;
/** engine card by its full name (e.g. "Dragapult ex TWM") */
function engineCard(fullName: string): Card | undefined {
  loadCards();
  byFull = byFull ?? new Map(allCards().map(c => [c.fullName, c]));
  return byFull.get(fullName);
}

export const isBasicEnergy = (c: Card | undefined) => c instanceof EnergyCard && c.energyType === EnergyType.BASIC;

let pool: Set<string> | undefined;
/** engine cards that stand for a Standard-legal printing */
export function standardNames(): Set<string> {
  pool = pool ?? new Set(standardPool().keys());
  return pool;
}

export interface Legality {
  ok: boolean;
  problems: string[];
}

/** Rules of deck construction (Standard): exactly 60 cards, at most 4 of a name (basic Energy
 *  excepted), at most 1 ACE SPEC, at least one Basic Pokémon, every card Standard-legal and
 *  supported by the engine. */
export function checkLegal(deck: Deck, cardOf: (name: string) => Card | undefined): Legality {
  const problems: string[] = [];
  if (deck.missing.length) {
    problems.push(`not supported by the engine: ${deck.missing.map(m => `${m.name}${m.set ? ` ${m.set} ${m.num}` : ''}`).join(', ')}`);
  }
  if (deck.cards.length !== 60) {
    problems.push(`${deck.cards.length} cards (must be 60)`);
  }
  const byName = new Map<string, number>();
  let ace = 0, basics = 0;
  const legal = standardNames();
  const notStandard = new Set<string>();
  for (const n of deck.cards) {
    const c = cardOf(n);
    if (!c) {
      continue;
    }
    if (!isBasicEnergy(c)) {
      byName.set(c.name, (byName.get(c.name) ?? 0) + 1);
    }
    if (c.tags.includes(CardTag.ACE_SPEC)) {
      ace++;
    }
    if (c instanceof PokemonCard && c.stage === Stage.BASIC) {
      basics++;
    }
    if (!legal.has(c.fullName) && !isBasicEnergy(c)) {
      notStandard.add(c.fullName);
    }
  }
  for (const [n, k] of byName) {
    if (k > 4) {
      problems.push(`${k} copies of ${n} (at most 4)`);
    }
  }
  if (ace > 1) {
    problems.push(`${ace} ACE SPEC cards (at most 1)`);
  }
  if (!basics) {
    problems.push('no Basic Pokémon');
  }
  if (notStandard.size) {
    problems.push(`not Standard-legal (or no Standard printing known): ${[...notStandard].join(', ')}`);
  }
  return { ok: problems.length === 0, problems };
}

/** Deck from decklist text, with engine cards resolved. */
export function deckFromText(text: string, name = 'custom'): { deck: Deck; entries: DeckEntry[] } {
  const entries = parseDeckList(text);
  return { deck: buildDeck(name, name, entries), entries };
}

/** A deck (engine full names) as decklist entries, one line per distinct card. */
export function entriesOf(cards: string[]): DeckEntry[] {
  const counts = new Map<string, number>();
  cards.forEach(n => counts.set(n, (counts.get(n) ?? 0) + 1));
  return [...counts].map(([n, count]) => {
    const c = engineCard(n);
    return { name: c?.name ?? n, set: c ? String(c.set) : undefined, num: c ? String(c.setNumber) : undefined, count };
  });
}

/** Decklist text in the export format, grouped Pokémon / Trainer / Energy. */
export function formatDeckList(cards: string[]): string {
  const groups: Record<string, string[]> = { 'Pokémon': [], Trainer: [], Energy: [] };
  const totals: Record<string, number> = { 'Pokémon': 0, Trainer: 0, Energy: 0 };
  const counts = new Map<string, number>();
  cards.forEach(n => counts.set(n, (counts.get(n) ?? 0) + 1));
  const rows = [...counts].map(([n, k]) => ({ n, k, c: engineCard(n) }));
  rows.sort((a, b) => (b.k - a.k) || (a.c?.name ?? a.n).localeCompare(b.c?.name ?? b.n));
  for (const { n, k, c } of rows) {
    const g = c?.superType === SuperType.POKEMON ? 'Pokémon' : c?.superType === SuperType.ENERGY ? 'Energy' : 'Trainer';
    groups[g].push(`${k} ${c?.name ?? n}${c ? ` ${c.set} ${c.setNumber}` : ''}`);
    totals[g] += k;
  }
  return Object.entries(groups).map(([g, ls]) => `${g}: ${totals[g]}\n${ls.join('\n')}`).join('\n\n') + `\n\nTotal Cards: ${cards.length}\n`;
}

export { engineCard, resolveEntry };
void TrainerCard;
