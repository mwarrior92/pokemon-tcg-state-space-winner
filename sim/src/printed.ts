// Independent copy of the printed Standard cards (pokemon-tcg-data-standard/, keyed by the set
// codes decklists use). Used to check engine cards and to pick the right engine card when a
// decklist names a printing the engine does not have.
import * as fs from 'fs';
import * as path from 'path';
import { CardType } from './engine';

const REPO = path.resolve(__dirname, '..', '..');


export interface PrintedCard {
  id: string;
  name: string;
  supertype: string;
  subtypes?: string[];
  hp?: string;
  types?: string[];
  evolvesFrom?: string;
  attacks?: { name: string; cost?: string[]; damage?: string; text?: string }[];
  abilities?: { name: string; text: string }[];
  weaknesses?: { type: string; value: string }[];
  resistances?: { type: string; value: string }[];
  retreatCost?: string[];
  number: string;
  set: string;               // ptcgo code, filled in on load
  regulationMark?: string;
  rules?: string[];
}

let printed: PrintedCard[] | undefined;

export function printedCards(): PrintedCard[] {
  if (printed) {
    return printed;
  }
  const dir = path.join(REPO, 'pokemon-tcg-data-standard');
  const sets: { id: string; ptcgoCode?: string }[] = JSON.parse(fs.readFileSync(path.join(dir, 'sets.json'), 'utf8'));
  const code = new Map(sets.map(s => [s.id, s.ptcgoCode ?? s.id]));
  printed = [];
  for (const f of fs.readdirSync(path.join(dir, 'cards'))) {
    const setId = f.replace(/\.json$/, '');
    for (const c of JSON.parse(fs.readFileSync(path.join(dir, 'cards', f), 'utf8'))) {
      printed.push({ ...c, set: code.get(setId) ?? setId });
    }
  }
  return printed;
}

export const TYPE_NAMES: Record<string, CardType> = {
  Grass: CardType.GRASS, Fire: CardType.FIRE, Water: CardType.WATER, Lightning: CardType.LIGHTNING,
  Psychic: CardType.PSYCHIC, Fighting: CardType.FIGHTING, Darkness: CardType.DARK, Metal: CardType.METAL,
  Colorless: CardType.COLORLESS, Fairy: CardType.FAIRY, Dragon: CardType.DRAGON,
};

export function baseDamage(s: string | undefined): number {
  const m = String(s ?? '').match(/\d+/);
  return m ? Number(m[0]) : 0;
}


const bySetNum = new Map<string, PrintedCard>();

export function printedFor(set: string | undefined, num: string | undefined): PrintedCard | undefined {
  if (!set || !num) {
    return undefined;
  }
  if (!bySetNum.size) {
    printedCards().forEach(pc => bySetNum.set(`${pc.set.toUpperCase()}|${String(pc.number).replace(/^0+/, '')}`, pc));
  }
  return bySetNum.get(`${set.toUpperCase()}|${String(num).replace(/^0+/, '')}`);
}

/** Gameplay signature of a printed Pokémon: what the rules use, not names (names differ between
 *  translations). */
export function printedSignature(pc: PrintedCard): string {
  const types = (pc.types ?? []).map(t => TYPE_NAMES[t]).sort((a, b) => a - b).join(',');
  const weak = (pc.weaknesses ?? []).map(w => TYPE_NAMES[w.type]).sort((a, b) => a - b).join(',');
  const atk = (pc.attacks ?? []).map(a => `${(a.cost ?? []).filter(t => t !== 'Free').map(t => TYPE_NAMES[t]).sort((x, y) => x - y).join('')}:${baseDamage(a.damage)}`).join('|');
  return `hp${pc.hp ?? 0} t${types} w${weak} r${(pc.retreatCost ?? []).length} a${atk}`;
}

export function engineSignature(c: any): string {
  const types = (c.cardType ?? []).slice().sort((a: number, b: number) => a - b).join(',');
  const weak = (c.weakness ?? []).map((w: any) => w.type).sort((a: number, b: number) => a - b).join(',');
  const atk = (c.attacks ?? []).map((a: any) => `${a.cost.slice().sort((x: number, y: number) => x - y).join('')}:${a.damage}`).join('|');
  return `hp${c.hp ?? 0} t${types} w${weak} r${(c.retreat ?? []).length} a${atk}`;
}
