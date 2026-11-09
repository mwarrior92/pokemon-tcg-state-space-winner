// Can each card in a list be used for something, given the rest of the list? A rules check from the
// cards' costs and texts, used by the deck builder (a change may not add a card it cannot use, nor
// strand a card that was usable) and in the deck report next to how often each card was really used.
//
// Every text is read into conditions. A condition names a kind of card (a selector: "Tera Pokémon",
// "Basic Pokémon with 70 HP or less", "Benched N's Pokémon", "Pokémon with a Rule Box in play",
// "Pokémon Tools", "Supporter card") and says
//  - whose cards it is about: yours, your opponent's, or both ("(both yours and your opponent's)",
//    "each player who has ...");
//  - what it does with them: `enable` (the card works only if you have one: Area Zero Underdepths,
//    "if you have a Tera Pokémon in play", "for each of your Ancient Pokémon"), `copy` (uses their
//    attacks: N's Zoroark ex's Night Joker, Slowking's Seek Inspiration), `search` (finds them),
//    `target` (does something to them: Booster Energy Capsule, Sada), or `harm` (an effect on both
//    sides that hurts them: Nighttime Mine, Path to the Peak, Jamming Tower).
// Conditions about only the opponent's cards put no demand on your list.
//
// How conditions combine: every sentence (and every clause in it) must be met (Glass Trumpet: a Tera
// Pokémon in play, and a Benched Colorless Pokémon, and a Basic Energy card in the discard; Rosa's
// Encouragement: Basic Energy and a Stage 2). Phrases joined by "or", and a list of things to search
// for (Dawn: "a Basic Pokémon, a Stage 1 Pokémon, and a Stage 2 Pokémon"), are alternatives.
//
// The checks, both ways:
//  - forward: a card with helpful conditions needs cards in the list that meet them; a card with a harmful condition should hurt none of
//    your own cards. If what it hurts is a large part of your Pokémon (a third of the copies or
//    more: Gravity Mountain in a list of Stage 2 attackers) it is unusable; a minor piece (one
//    Meowth ex under your own Team Rocket's Watchtower, which 70 meta lists accept) is a side effect:
//    noted in the report, and the deck builder adds such cards less often. Pokémon that never get
//    into play (Slowking's deck-top targets with no evolution line) are not hurt.
//  - reverse: a Pokémon that cannot use its own attacks or abilities is still usable if another card
//    in the list uses it: copies its attacks (N's Zoroark ex with any N's Pokémon, Slowking with any
//    Pokémon without a Rule Box), or needs it in play (a Tera Pokémon for Area Zero Underdepths).
//    Being searched for or targeted by another card is not a use.
//
// Pokémon: usable if one of its attacks can be paid with the list's Energy (Colorless is paid by
// anything) and does damage or has a condition the list meets, or one of its abilities' conditions
// is met, or it is part of an evolution line in the list, named by another card, or used by another
// card (reverse). An evolution needs its pre-evolution (or Fossil), or for a Stage 2 its Basic and
// Rare Candy. Energy mentions ("attach a Fire Energy") need Energy of that type in the list. Basic
// Energy is always usable. For Special Energy, Energy types in its text are what it provides.
import { Card, CardTag, CardType, EnergyCard, PokemonCard, PowerType, Stage, SuperType, TrainerCard, TrainerType } from './engine';
import { engineCard, isBasicEnergy } from './decklist';
import { allCards, cardsNamed } from './cards';

const TYPE_WORD: Record<string, CardType> = {
  Grass: CardType.GRASS, Fire: CardType.FIRE, Water: CardType.WATER, Lightning: CardType.LIGHTNING,
  Psychic: CardType.PSYCHIC, Fighting: CardType.FIGHTING, Darkness: CardType.DARK, Metal: CardType.METAL,
  Dragon: CardType.DRAGON, Colorless: CardType.COLORLESS,
  G: CardType.GRASS, R: CardType.FIRE, W: CardType.WATER, L: CardType.LIGHTNING, P: CardType.PSYCHIC,
  F: CardType.FIGHTING, D: CardType.DARK, M: CardType.METAL, N: CardType.DRAGON, C: CardType.COLORLESS,
};
const TYPES = [CardType.GRASS, CardType.FIRE, CardType.WATER, CardType.LIGHTNING, CardType.PSYCHIC,
  CardType.FIGHTING, CardType.DARK, CardType.METAL];
const TYPE_NAME: Partial<Record<CardType, string>> = {
  [CardType.GRASS]: 'Grass', [CardType.FIRE]: 'Fire', [CardType.WATER]: 'Water', [CardType.LIGHTNING]: 'Lightning',
  [CardType.PSYCHIC]: 'Psychic', [CardType.FIGHTING]: 'Fighting', [CardType.DARK]: 'Darkness', [CardType.METAL]: 'Metal',
};
const GROUP_TAG: Record<string, string> = {
  Tera: CardTag.POKEMON_TERA, Ancient: CardTag.ANCIENT, Future: CardTag.FUTURE, 'Single Strike': CardTag.SINGLE_STRIKE,
  'Rapid Strike': CardTag.RAPID_STRIKE, 'Fusion Strike': CardTag.FUSION_STRIKE,
};
const RULE_BOX = /^(ex|EX|GX|V|VMAX|VSTAR|V-UNION|Radiant|Prism Star|Break|Mega EX|Mega ex|Lv.X)$/;
const hasRuleBox = (c: Card) => c.tags.some(t => RULE_BOX.test(String(t)));

// --- reading texts ---------------------------------------------------------------------------------

export type Side = 'own' | 'opp' | 'both';
export type Role = 'enable' | 'copy' | 'search' | 'target' | 'harm';

export interface Sel {
  what: 'pokemon' | 'card' | 'supporter' | 'item' | 'tool' | 'stadium' | 'basic-energy' | 'special-energy';
  stage?: 'basic' | 'stage1' | 'stage2' | 'evolution';
  types?: CardType[];              // any of
  tags?: string[];                 // all of
  ruleBox?: boolean;               // must have (true) / must not have (false) a Rule Box
  maxHp?: number;
  owner?: string;                  // "N's"
  hasAbility?: boolean;            // only Pokémon with an Ability are affected ("have no Abilities")
  other?: boolean;                 // "your other ...": not the card itself
  inPlay?: boolean;                // about Pokémon in play (Benched, Active, "in play"), not in the deck or discard
  text: string;                    // what it says, for reasons
}
export interface Cond { sel: Sel; side: Side; role: Role; by?: string }
/** one thing a text needs: Energy of one of these types, or a card that fits a condition */
interface Item { energy?: CardType[]; cond?: Cond }
/** all clauses must be met; a clause is met by any of its items */
export interface Needs { clauses: Item[][]; conds: Cond[] }

const T = '(?:\\b(?:Grass|Fire|Water|Lightning|Psychic|Fighting|Darkness|Metal)\\b|\\[[GRWLPFDM]\\])';
const ENERGY_REQ = new RegExp(`(${T}(?:\\s*(?:,|or|and)\\s*${T})*)\\s+Energy`, 'g');

let ownersRe: string | undefined;
/** "N's", "Team Rocket's", ...: the owners that name Pokémon in the card pool */
function owners(): string {
  if (ownersRe === undefined) {
    const set = new Set<string>();
    for (const c of allCards()) {
      const m = /^((?:Team )?[A-Z][\w.-]*'s) /.exec(c.name);
      if (m && c instanceof PokemonCard) {
        set.add(m[1].replace(/[.]/g, '\\.'));
      }
    }
    ownersRe = [...set].sort((a, b) => b.length - a.length).join('|') || 'NO_OWNER';
  }
  return ownersRe;
}

let phraseRe: RegExp | undefined;
function phrase(): RegExp {
  if (!phraseRe) {
    const mod = `(?:Basic|Stage 1|Stage 2|Evolution|Evolved|Benched|Active|other|Mega Evolution|Mega|Tera|Ancient|Future|Single Strike|Rapid Strike|Fusion Strike|Grass|Fire|Water|Lightning|Psychic|Fighting|Darkness|Metal|Colorless|Dragon|\\[[GRWLPFDMCN]\\]|${owners()})`;
    const head = `Pok[eé]mon Tools?|Pok[eé]mon|Supporter(?: cards?)?|Item(?: cards?)?|Stadium(?: cards?)?|Basic Energy(?: cards?)?|Special Energy(?: cards?)?|cards?`;
    const suffix = `(?:\\s+(?:with a Rule Box|that (?:doesn't|does not|don't|do not) have a Rule Box|that has an Ability|with an Ability|with \\d+ HP or less))*`;
    phraseRe = new RegExp(`(?<![\\w'\\]-])((?:${mod}\\s+){0,4})(${head})((?:\\s+(?:ex|V)\\b)?)(${suffix})`, 'g');
  }
  phraseRe.lastIndex = 0;
  return phraseRe;
}

const BOTH_MARK = ' [both sides]';
const EITHER_MARK = ' [either side]';    // you choose whose: puts no demand on your list
const HARM = /(?:\bgets? -\d+ HP|\bhas -\d+ HP|\b(?:have no Abilities|has no Abilities|have no effect|has no effect|costs? (?:\[\w\]|\w+) more|can't|cannot|do(?:es)? \d+ less damage|damage counters on|is now (?:Asleep|Burned|Confused|Paralyzed|Poisoned)|discard))/i;

/** a selector from a matched phrase, or undefined if it covers every card of its kind */
function selector(mods: string, head: string, suffix1: string, suffix2: string): Sel | undefined {
  const words = mods.trim();
  const sel: Sel = { what: 'pokemon', text: '' };
  if (/^Pok[eé]mon Tool/.test(head)) sel.what = 'tool';
  else if (/^Supporter/.test(head)) sel.what = 'supporter';
  else if (/^Item/.test(head)) sel.what = 'item';
  else if (/^Stadium/.test(head)) sel.what = 'stadium';
  else if (/^Basic Energy/.test(head)) sel.what = 'basic-energy';
  else if (/^Special Energy/.test(head)) sel.what = 'special-energy';
  else if (/^card/.test(head)) sel.what = 'card';
  const stage = /\b(Basic|Stage 1|Stage 2|Evolution|Evolved)\b/.exec(words)?.[1];
  if (stage) {
    sel.stage = ({ Basic: 'basic', 'Stage 1': 'stage1', 'Stage 2': 'stage2', Evolution: 'evolution', Evolved: 'evolution' } as const)[stage as 'Basic'];
    if (sel.what === 'card') {
      sel.what = 'pokemon';          // "a Stage 2 card"
    }
  }
  const types = [...words.matchAll(/\b(Grass|Fire|Water|Lightning|Psychic|Fighting|Darkness|Metal|Colorless|Dragon)\b|\[([GRWLPFDMCN])\]/g)]
    .map(m => TYPE_WORD[m[1] ?? m[2]]).filter(t => t !== undefined);
  if (types.length) sel.types = types;
  const tags: string[] = [];
  for (const [w, tag] of Object.entries(GROUP_TAG)) {
    if (new RegExp(`\\b${w}\\b`).test(words)) tags.push(tag);
  }
  const mega = /\bMega\b/.test(words);
  if (/\bex\b/.test(suffix1)) tags.push(...(mega ? [CardTag.POKEMON_SV_MEGA, CardTag.POKEMON_ex] : [CardTag.POKEMON_ex]));
  else if (mega) tags.push(CardTag.POKEMON_SV_MEGA);
  if (/\bV\b/.test(suffix1)) tags.push(CardTag.POKEMON_V);
  if (tags.length) sel.tags = tags;
  const owner = new RegExp(`(?:^|\\s)(${owners()})(?:\\s|$)`).exec(words)?.[1];
  if (owner) sel.owner = owner;
  if (/with a Rule Box/.test(suffix2)) sel.ruleBox = true;
  if (/(?:have|has) a Rule Box/.test(suffix2) && !/with a Rule Box/.test(suffix2)) sel.ruleBox = false;
  if (/Ability/.test(suffix2)) sel.hasAbility = true;
  const hp = /with (\d+) HP or less/.exec(suffix2)?.[1];
  if (hp) sel.maxHp = Number(hp);
  if (/\bother\b/.test(words)) sel.other = true;
  if (/\b(?:Benched|Active)\b/.test(words)) sel.inPlay = true;
  // "cards" alone, "Pokémon" alone, "Benched Pokémon": every card of its kind, no demand
  const specific = sel.stage || sel.types || sel.tags || sel.owner || sel.ruleBox !== undefined || sel.maxHp !== undefined || sel.hasAbility;
  if (!specific && (sel.what === 'pokemon' || sel.what === 'card')) {
    return undefined;
  }
  const shown = words.replace(/\b(Benched|Active|other)\s*/g, '').trim();
  const noun = head.replace(/ cards?$/, ' card').replace(/^cards?$/, 'card').replace(/Tools$/, 'Tool').replace(/^Pokemon/, 'Pokémon');
  const named = shown.replace(/\[([GRWLPFDMCN])\]/g, (_, l: string) => ({ N: 'Dragon', C: 'Colorless' } as Record<string, string>)[l] ?? TYPE_NAME[TYPE_WORD[l]] ?? l);
  sel.text = `${named ? named + ' ' : ''}${noun}${suffix1}${suffix2}`.replace(/\s+/g, ' ').trim();
  return sel;
}

/** whose cards a phrase at `i` in a sentence is about */
function sideOf(sentence: string, i: number, end: number): Side {
  const before = sentence.slice(0, i), after = sentence.slice(end);
  if (/opponent'?s?\s+(?:\S+\s+){0,4}$/i.test(before) || /\byour opponent\b(?![^,;]*\byour\b)[^,;]*$/i.test(before)) {
    return 'opp';
  }
  // "a Pokémon Tool ... from 1 of your opponent's Pokémon", "... attached to your opponent's Pokémon",
  // "for each Supporter card you find there" (in the opponent's hand)
  if (/^[^,;]*?\b(?:from|attached to|on) (?:1 of |each of |all of |any of )?your opponent's/i.test(after) || /^[^,;.]*\byou find there\b/i.test(after) || sentence.includes(EITHER_MARK)) {
    return 'opp';
  }
  if (sentence.includes(BOTH_MARK) || /\b(?:each player|both players|either player)\b/i.test(before)) {
    return 'both';
  }
  return 'own';
}

function roleOf(sentence: string, i: number, end: number, side: Side): Role {
  const before = sentence.slice(0, i), after = sentence.slice(end);
  if (side === 'both' && HARM.test(sentence) && !/\bmay\b/i.test(sentence)) {
    return 'harm';
  }
  if (/choose 1 of (?:its|their|\w+'s) attacks|attacks? and use it|use it as this attack|can use (?:any )?(?:of )?the attacks/i.test(sentence)) {
    return 'copy';
  }
  if (/search your (?:deck|discard pile) for[^,;]*$/i.test(before) || /^\s*(?:or [^,;]*?)?(?:from|in) your (?:deck|discard pile)/i.test(after)) {
    return 'search';
  }
  if (/\b(?:if (?:you have|1 of your|any of your)|only if you have|each player who has|for each of your|for each|as long as you have)\b[^,;]*$/i.test(before)) {
    return 'enable';
  }
  return 'target';
}

const needsCache = new Map<string, Needs>();
/** what a text asks of your list: Energy mentions and conditions on kinds of cards */
export function textNeeds(text: string): Needs {
  const hit = needsCache.get(text);
  if (hit) {
    return hit;
  }
  const out: Needs = { clauses: [], conds: [] };
  // reminder text in parentheses is not rules, except who an effect applies to
  const clean = text
    .replace(/\(both yours and your opponent's\)/gi, BOTH_MARK)
    .replace(/\((?:either )?yours or your opponent's[^()]*\)/gi, EITHER_MARK)
    .replace(/\([^()]*\)/g, ' ');
  let m: RegExpExecArray | null;
  for (const sentence of clean.split(/(?<=[.!?])\s+/)) {
    // the sentence's items in order: Energy mentions and conditions, with where they are
    const items: { at: number; end: number; item: Item; search: boolean }[] = [];
    ENERGY_REQ.lastIndex = 0;
    while ((m = ENERGY_REQ.exec(sentence))) {
      const before = sentence.slice(Math.max(0, m.index - 40), m.index);
      if (/opponent'?s?\s+(?:\S+\s+){0,3}$/i.test(before) || /your opponent\b[^.]*$/i.test(before)) {
        continue;
      }
      const energy = [...m[1].matchAll(new RegExp(T, 'g'))].map(x => TYPE_WORD[x[0].replace(/[[\]]/g, '')]).filter(t => t !== undefined);
      items.push({ at: m.index, end: m.index + m[0].length, item: { energy }, search: /search your deck for[^,;]*$/i.test(sentence.slice(0, m.index)) });
    }
    const re = phrase();
    while ((m = re.exec(sentence))) {
      let sel = selector(m[1], m[2], m[3], m[4]);
      if (!sel) {
        // "a Pokémon" in a search or recovery is an alternative any Pokémon meets
        if (/^Pok[eé]mon$/.test(m[2]) && !m[3] && !m[4] && roleOf(sentence, m.index, m.index + m[0].length, 'own') === 'search') {
          sel = { what: 'pokemon', text: 'Pokémon' };
        } else {
          continue;
        }
      }
      const side = sideOf(sentence, m.index, m.index + m[0].length);
      if (/^\s*in play\b/.test(sentence.slice(m.index + m[0].length))) {
        sel.inPlay = true;
      }
      if (side === 'opp') {
        continue;
      }
      const role = roleOf(sentence, m.index, m.index + m[0].length, side);
      if (role === 'harm' && /no Abilities/i.test(sentence)) {
        sel.hasAbility = true;       // only Pokémon with an Ability lose something
      }
      const cond: Cond = { sel, side, role };
      out.conds.push(cond);
      if (role !== 'harm') {
        items.push({ at: m.index, end: m.index + m[0].length, item: { cond }, search: role === 'search' });
      }
    }
    // alternatives: joined by "or", or both things to search for; otherwise each is needed
    items.sort((a, b) => a.at - b.at);
    let clause: Item[] = [];
    items.forEach((x, i) => {
      const prev = items[i - 1];
      const between = prev ? sentence.slice(prev.end, x.at) : '';
      // "search your deck for a Basic Pokémon, a Stage 1 Pokémon, and a Stage 2 Pokémon": the list goes on
      if (prev?.search && !x.search && /^\s*(?:cards?\s*)?,?\s*(?:and\/or|and|or)?\s*(?:an?|any|up to \w+|\d+)?\s*$/.test(between)) {
        x.search = true;
        if (x.item.cond) {
          x.item.cond.role = 'search';
        }
      }
      if (prev && !(/\bor\b/.test(between) || (prev.search && x.search))) {
        out.clauses.push(clause);
        clause = [];
      }
      clause.push(x.item);
    });
    if (clause.length) {
      out.clauses.push(clause);
    }
  }
  needsCache.set(text, out);
  return out;
}

// --- the list ------------------------------------------------------------------------------------

export interface DeckFacts {
  names: Set<string>;
  energy: Set<CardType>;           // Energy types the list's Energy cards provide
  anyEnergy: boolean;              // some Energy provides every type
  evolvesFrom: Set<string>;        // names something in the list evolves from
  texts: string;                   // every text in the list (for cards that name other cards)
  cards: Card[];                   // the distinct cards
  users: Cond[];                   // conditions that use a Pokémon (copy its attacks, need it in play), with `by`
  counts: Map<string, number>;     // copies of each card
  total: number;                   // cards in the list
  pokemon: number;                 // Pokémon copies
}

/** share of your own Pokémon a harmful card may hit and still be usable (above: unusable) */
export const HARM_LIMIT = 1 / 3;

/** every text on a card: its own, its attacks', its abilities' */
function textsOf(c: Card): string[] {
  const out = [(c as any).text ?? ''];
  if (c instanceof PokemonCard) {
    c.attacks.forEach(a => out.push(a.text ?? ''));
    c.powers.forEach(p => out.push(p.text ?? ''));
  }
  return out.filter(Boolean);
}

export function deckFacts(cards: string[]): DeckFacts {
  const f: DeckFacts = { names: new Set(), energy: new Set(), anyEnergy: false, evolvesFrom: new Set(), texts: '', cards: [], users: [], counts: new Map(), total: 0, pokemon: 0 };
  for (const n of cards) {
    const c = engineCard(n);
    if (c) {
      f.counts.set(c.fullName, (f.counts.get(c.fullName) ?? 0) + 1);
      f.total++;
      if (c instanceof PokemonCard && c.superType === SuperType.POKEMON) {
        f.pokemon++;
      }
    }
  }
  const texts: string[] = [];
  const cs = [...new Set(cards)].map(n => engineCard(n)).filter((c): c is Card => !!c);
  for (const c of cs) {
    f.names.add(c.name);
    if (c instanceof EnergyCard) {
      c.provides.forEach(t => (t === CardType.ANY ? (f.anyEnergy = true) : f.energy.add(t)));
      if (!isBasicEnergy(c)) {
        // Special Energy often says what it provides only in its text (Team Rocket's, Prism, Legacy)
        const text = (c as any).text ?? '';
        if (/every type of Energy/i.test(text)) {
          f.anyEnergy = true;
        }
        textNeeds(text).clauses.flat().forEach(x => x.energy?.forEach(t => f.energy.add(t)));
      }
    }
    for (const t of textsOf(c)) {
      texts.push(t);
      textNeeds(t).conds.filter(k => (k.role === 'copy' || k.role === 'enable') && k.sel.what === 'pokemon')
        .forEach(k => f.users.push({ ...k, by: c.fullName }));
    }
    if (c instanceof PokemonCard && c.evolvesFrom) {
      f.evolvesFrom.add(c.evolvesFrom);
    }
  }
  f.texts = texts.join('\n');
  f.cards = cs;
  return f;
}

/** does card `c` fit selector `s`? */
export function matches(s: Sel, c: Card): boolean {
  switch (s.what) {
    case 'supporter': case 'item': case 'tool': case 'stadium': {
      const t = { supporter: TrainerType.SUPPORTER, item: TrainerType.ITEM, tool: TrainerType.TOOL, stadium: TrainerType.STADIUM }[s.what];
      return c instanceof TrainerCard && c.trainerType === t && (!s.tags || s.tags.every(g => c.tags.some(x => String(x) === g)));
    }
    case 'basic-energy':
      return isBasicEnergy(c);
    case 'special-energy':
      return c instanceof EnergyCard && !isBasicEnergy(c);
    case 'card':
      return !!s.tags && s.tags.every(g => c.tags.some(x => String(x) === g));
  }
  if (!(c instanceof PokemonCard) || c.superType !== SuperType.POKEMON) {
    return false;                    // Fossils are Items in the deck, not Pokémon
  }
  if (s.stage === 'basic' && c.stage !== Stage.BASIC) return false;
  if (s.stage === 'stage1' && c.stage !== Stage.STAGE_1) return false;
  if (s.stage === 'stage2' && c.stage !== Stage.STAGE_2) return false;
  if (s.stage === 'evolution' && c.stage === Stage.BASIC) return false;
  if (s.types && !s.types.some(t => c.cardType.includes(t))) return false;
  if (s.tags && !s.tags.every(g => c.tags.some(x => String(x) === g))) return false;
  if (s.ruleBox !== undefined && hasRuleBox(c) !== s.ruleBox) return false;
  if (s.maxHp !== undefined && c.hp > s.maxHp) return false;
  if (s.owner && !c.name.startsWith(s.owner + ' ')) return false;
  if (s.hasAbility && !c.powers.some(p => p.powerType === PowerType.ABILITY)) return false;
  return true;
}

const article = (x: string) => `${/^[AEIOU8]/.test(x) ? 'an' : 'a'} ${x}`;
const sayCond = (k: Cond) => k.role === 'search' ? `${article(k.sel.text)} to search for` : article(k.sel.text);

/** what of these needs the list does not meet; undefined if all are met */
function unmet(n: Needs, f: DeckFacts, self?: Card): string | undefined {
  const energyOk = (ts: CardType[]) => f.anyEnergy || ts.some(t => f.energy.has(t));
  // a card can meet its own condition ("if you have a Tera Pokémon in play"), but not "your other ..."
  // and not a search for itself (it is already in hand or play)
  const condOk = (k: Cond) => f.cards.some(c => (c !== self || (!k.sel.other && k.role !== 'search')) && matches(k.sel, c));
  const ok = (x: Item) => x.energy ? energyOk(x.energy) : condOk(x.cond!);
  const say = (x: Item) => x.energy ? `${x.energy.map(t => TYPE_NAME[t]).join(' or ')} Energy` : sayCond(x.cond!);
  const missing = n.clauses.filter(cl => cl.length && !cl.some(ok)).map(cl => [...new Set(cl.map(say))].join(' / '));
  return missing.length ? [...new Set(missing)].join(' and ') : undefined;
}

/** can this Pokémon get into play in this list (its line, or Rare Candy for a Stage 2)? */
function playable(c: PokemonCard, f: DeckFacts): boolean {
  if (!c.evolvesFrom || f.names.has(c.evolvesFrom)) {
    return true;
  }
  const basic = c.stage === Stage.STAGE_2 ? cardsNamed(c.evolvesFrom).map(x => (x as PokemonCard).evolvesFrom).find(Boolean) : undefined;
  return !!(basic && f.names.has(basic) && f.names.has('Rare Candy'));
}

/** the worst harmful condition of a text on the list's own cards: what it hurts and how much of the list */
function hurts(n: Needs, f: DeckFacts): { text: string; share: number } | undefined {
  let worst: { text: string; share: number } | undefined;
  for (const k of n.conds.filter(x => x.role === 'harm')) {
    const hit = f.cards.filter(c => matches(k.sel, c) && (!(c instanceof PokemonCard) || playable(c, f)));
    if (!hit.length) {
      continue;
    }
    const copies = hit.reduce((a, c) => a + (f.counts.get(c.fullName) ?? 1), 0);
    // Pokémon: share of the list's Pokémon; other cards (Tools, Special Energy): against a quarter of the list
    const share = k.sel.what === 'pokemon' ? copies / Math.max(1, f.pokemon) : Math.min(1, copies / Math.max(1, f.total / 4));
    const names = [...new Set(hit.map(c => c.name))];
    const text = `your own ${k.sel.text} (${names.slice(0, 3).join(', ')}${names.length > 3 ? ', ...' : ''}: ${copies} of ${k.sel.what === 'pokemon' ? `${f.pokemon} Pokémon` : `${f.total} cards`})`;
    if (!worst || share > worst.share) {
      worst = { text, share };
    }
  }
  return worst;
}

/** a usable card's harm to the list's own cards, when it is small enough to accept ("also hurts ...") */
export function sideEffect(n: string, f: DeckFacts): string | undefined {
  const c = engineCard(n);
  if (!(c instanceof TrainerCard || (c instanceof EnergyCard && !isBasicEnergy(c)))) {
    return undefined;
  }
  const h = hurts(textNeeds((c as any).text ?? ''), f);
  return h && h.share < HARM_LIMIT ? `also hurts ${h.text}` : undefined;
}

/** every card in the list with an accepted side effect on the list's own cards */
export function sideEffects(cards: string[]): { card: string; note: string }[] {
  const f = deckFacts(cards);
  return [...new Set(cards)].map(n => ({ card: n, note: sideEffect(n, f) })).filter((x): x is { card: string; note: string } => !!x.note);
}

/** does a card other than `c` name it in its text? */
function namedElsewhere(c: PokemonCard, f: DeckFacts): boolean {
  const own = [...c.attacks.map(a => a.text ?? ''), ...c.powers.map(p => p.text ?? '')].join('\n');
  const count = (x: string) => x.split(c.name).length - 1;
  return count(f.texts) > count(own);
}

/** the card in the list that uses this Pokémon (copies its attacks or needs it in play), if any */
function usedBy(c: PokemonCard, f: DeckFacts): string | undefined {
  return f.users.find(k => k.by !== c.fullName && matches(k.sel, c) && (k.role !== 'copy' || c.attacks.length > 0))?.by;
}

/** why card `n` cannot be used in a list with these facts, or undefined if it can */
export function whyUnusable(n: string, f: DeckFacts): string | undefined {
  const c = engineCard(n);
  if (!c || isBasicEnergy(c)) {
    return undefined;
  }
  if (c instanceof PokemonCard) {
    const user = usedBy(c, f);
    if (c.attacks.length && f.users.some(k => k.by !== c.fullName && k.role === 'copy' && !k.sel.inPlay && matches(k.sel, c))) {
      return undefined;              // its attacks are used from the deck or discard (Slowking)
    }
    if (c.evolvesFrom && !f.names.has(c.evolvesFrom)) {
      // a Stage 2 straight from its Basic with Rare Candy
      const basic = c.stage === Stage.STAGE_2 ? cardsNamed(c.evolvesFrom).map(x => (x as PokemonCard).evolvesFrom).find(Boolean) : undefined;
      if (!(basic && f.names.has(basic) && f.names.has('Rare Candy'))) {
        return `nothing to evolve it from (needs ${c.evolvesFrom})`;
      }
    }
    if (f.evolvesFrom.has(c.name) || namedElsewhere(c, f) || user) {
      return undefined;              // part of a line, named by another card, or used by one
    }
    const payable = (cost: CardType[]) => cost.every(t => t === CardType.COLORLESS || !TYPES.includes(t) || f.anyEnergy || f.energy.has(t));
    // an attack that does damage works whatever its text adds ("does 30 more if you have a Tera
    // Pokémon"); one that does not needs its text to work
    const attackOk = c.attacks.some(a => payable(a.cost) && (a.damage > 0 || !unmet(textNeeds(a.text ?? ''), f, c)));
    const abilityOk = c.powers.some(p => !unmet(textNeeds(p.text ?? ''), f, c));
    if (attackOk || abilityOk) {
      return undefined;
    }
    const why: string[] = [];
    if (c.attacks.length) {
      const need = [...new Set(c.attacks.flatMap(a => a.cost.filter(t => TYPES.includes(t) && !f.anyEnergy && !f.energy.has(t))))].map(t => TYPE_NAME[t]);
      const textNeed = c.attacks.map(a => unmet(textNeeds(a.text ?? ''), f, c)).filter(Boolean).join(' / ');
      why.push(need.length ? `no attack the deck's Energy can pay (needs ${need.join(' or ')} Energy)` : `its attacks need ${textNeed || 'cards the deck does not have'}`);
    }
    c.powers.forEach(p => why.push(`${p.name} needs ${unmet(textNeeds(p.text ?? ''), f, c)}`));
    return why.join('; ') || 'no attack or ability';
  }
  if (c instanceof TrainerCard || c instanceof EnergyCard) {
    const needs = textNeeds((c as any).text ?? '');
    const harm = hurts(needs, f);
    if (harm && harm.share >= HARM_LIMIT) {
      return `hurts ${harm.text}`;
    }
    // for Special Energy, Energy types in its text are what it provides, not requirements
    const u = unmet(c instanceof EnergyCard ? { ...needs, clauses: needs.clauses.map(cl => cl.filter(x => !x.energy)) } : needs, f, c);
    return u ? `needs ${u}` : undefined;
  }
  return undefined;
}

/** every card in the list that cannot be used, with the reason */
export function unusableCards(cards: string[]): { card: string; reason: string }[] {
  const f = deckFacts(cards);
  return [...new Set(cards)].map(n => ({ card: n, reason: whyUnusable(n, f) })).filter((x): x is { card: string; reason: string } => !!x.reason);
}
