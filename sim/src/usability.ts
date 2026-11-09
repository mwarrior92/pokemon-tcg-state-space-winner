// Can each card in a list be used for something, given the rest of the list? A rules check from the
// cards' costs and texts, used by the deck builder (a change may not add a card it cannot use, nor
// strand a card that was usable) and in the deck report next to how often each card was really used.
//
// A Pokémon is usable if it can pay for one of its attacks with the deck's Energy (Colorless costs
// are paid by anything), or has an ability whose text requirements the deck meets, or is what
// another Pokémon in the deck evolves from. An evolution needs its pre-evolution (or Fossil) in the
// deck. A Trainer or Special Energy is usable when its text requirements are met. Basic Energy is
// always usable (it pays Colorless costs).
//
// Text requirements: "<type> Energy" / "[X] Energy" needs Energy of that type in the deck, "<type>
// Pokémon" a Pokémon of that type, "Stage 2" a Stage 2 Pokémon, and a deck search needs something in
// the deck it can find ("search your deck for up to 2 Basic Pokémon with 70 HP or less" needs such a
// Basic; likewise Evolution / Stage 1 / typed / ex / no-Rule-Box Pokémon, Supporter, Item, Tool and
// Basic Energy cards), and a card for a group needs a member of it ("Tera Pokémon" for Area Zero
// Underdepths; Ancient, Future, Single / Rapid / Fusion Strike, Mega Evolution Pokémon ex, "your
// Pokémon ex / V"); mentions about the opponent's side are ignored. Group mentions in attacks are
// not counted (they are mostly damage bonuses; the attack still works). A text whose requirements are all unmet makes that effect unusable; meeting any one
// is enough (texts often offer alternatives).
import { Card, CardTag, CardType, EnergyCard, PokemonCard, Stage, SuperType, TrainerCard, TrainerType } from './engine';
import { engineCard, isBasicEnergy } from './decklist';
import { cardsNamed } from './cards';

const TYPE_WORD: Record<string, CardType> = {
  Grass: CardType.GRASS, Fire: CardType.FIRE, Water: CardType.WATER, Lightning: CardType.LIGHTNING,
  Psychic: CardType.PSYCHIC, Fighting: CardType.FIGHTING, Darkness: CardType.DARK, Metal: CardType.METAL,
  G: CardType.GRASS, R: CardType.FIRE, W: CardType.WATER, L: CardType.LIGHTNING, P: CardType.PSYCHIC,
  F: CardType.FIGHTING, D: CardType.DARK, M: CardType.METAL,
};
const TYPES = [CardType.GRASS, CardType.FIRE, CardType.WATER, CardType.LIGHTNING, CardType.PSYCHIC,
  CardType.FIGHTING, CardType.DARK, CardType.METAL];
const TYPE_NAME: Partial<Record<CardType, string>> = {
  [CardType.GRASS]: 'Grass', [CardType.FIRE]: 'Fire', [CardType.WATER]: 'Water', [CardType.LIGHTNING]: 'Lightning',
  [CardType.PSYCHIC]: 'Psychic', [CardType.FIGHTING]: 'Fighting', [CardType.DARK]: 'Darkness', [CardType.METAL]: 'Metal',
};
const T = '(?:\\b(?:Grass|Fire|Water|Lightning|Psychic|Fighting|Darkness|Metal)\\b|\\[[GRWLPFDM]\\])';
const REQ = new RegExp(`(${T}(?:\\s*(?:,|or|and)\\s*${T})*)\\s+(Energy|Pokémon)`, 'g');

interface Search {
  what: 'pokemon' | 'supporter' | 'item' | 'tool' | 'basic-energy';
  stage?: 'basic' | 'stage1' | 'stage2' | 'evolution';
  types?: CardType[];
  maxHp?: number;
  ex?: boolean;
  noRuleBox?: boolean;
  text: string;                    // as written, for the reason
}
interface Req { kind: 'energy' | 'pokemon' | 'stage2' | 'search' | 'tag'; types: CardType[]; search?: Search; tag?: { tag: string; pokemon: boolean; text: string } }

// group mentions: "Tera Pokémon", "Ancient cards", "Rapid Strike Supporter", "Mega Evolution Pokémon ex", "your Benched Pokémon ex"
const TAG_WORD = /\b(Tera|Ancient|Future|Single Strike|Rapid Strike|Fusion Strike)\s+(Pok[eé]mon|cards?|Supporter|Item)\b/g;
const TAG_MEGA = /\bMega (?:Evolution )?Pok[eé]mon ex\b/g;
const TAG_RULE = /\byour\s+(?:(?:other|Active|Benched|Basic)\s+){0,2}Pok[eé]mon (ex|V)\b/g;
const TAG_OF: Record<string, string> = {
  Tera: CardTag.POKEMON_TERA, Ancient: CardTag.ANCIENT, Future: CardTag.FUTURE, 'Single Strike': CardTag.SINGLE_STRIKE,
  'Rapid Strike': CardTag.RAPID_STRIKE, 'Fusion Strike': CardTag.FUSION_STRIKE, ex: CardTag.POKEMON_ex, V: CardTag.POKEMON_V,
};
const NEGATED = /\b(?:isn't|is not|aren't|not|doesn't|don't|except|other than|non-)\s*(?:a |an |any )?$/i;

const SEARCH_POKEMON = /search your deck for (?:up to \w+ |an? |any number of )?((?:(Basic|Stage 1|Stage 2|Evolution) )?(?:(\[[GRWLPFDMC]\]|Grass|Fire|Water|Lightning|Psychic|Fighting|Darkness|Metal|Colorless) )?Pok[eé]mon( ex)?( that doesn't have a Rule Box)?(?: with (\d+) HP or less)?)/gi;
const SEARCH_OTHER = /search your deck for (?:up to \w+ |an? |any number of )?(Supporter|Item|Pokémon Tool|Basic Energy) cards?/gi;
const RULE_BOX = /^(ex|EX|GX|V|VMAX|VSTAR|V-UNION|Radiant|Prism Star|Break|Mega EX|Mega ex|Lv.X)$/;

const reqCache = new Map<string, Req[]>();
/** requirements a text puts on your own deck */
export function textNeeds(text: string): Req[] {
  const hit = reqCache.get(text);
  if (hit) {
    return hit;
  }
  const out: Req[] = [];
  let m: RegExpExecArray | null;
  REQ.lastIndex = 0;
  while ((m = REQ.exec(text))) {
    const before = text.slice(Math.max(0, m.index - 40), m.index);
    if (/opponent'?s?\s+(?:\w+\s+){0,3}$/i.test(before) || /your opponent\b[^.]*$/i.test(before)) {
      continue;                      // about the opponent's side
    }
    const types = [...m[1].matchAll(new RegExp(T, 'g'))].map(x => TYPE_WORD[x[0].replace(/[[\]]/g, '')]).filter(t => t !== undefined);
    out.push({ kind: m[2] === 'Energy' ? 'energy' : 'pokemon', types });
  }
  if (/\bStage 2\b/.test(text) && !/\bStage 1\b/.test(text) && !/opponent/i.test(text)) {   // Rare Candy, not Dawn
    out.push({ kind: 'stage2', types: [] });
  }
  // group mentions: something in the deck must belong to the group
  const tagAt = (i: number, tag: string, pokemon: boolean, said: string) => {
    const before = text.slice(Math.max(0, i - 40), i);
    if (/opponent'?s?\s+(?:\w+\s+){0,3}$/i.test(before) || /your opponent\b[^.]*$/i.test(before) || NEGATED.test(before)) {
      return;
    }
    // "each Tera Pokémon in play (both yours and your opponent's)": aimed at either side, no need
    if (/both yours and your opponent's/i.test(text.slice(i).split('.')[0])) {
      return;
    }
    out.push({ kind: 'tag', types: [], tag: { tag, pokemon, text: said } });
  };
  for (const tm of text.matchAll(TAG_WORD)) {
    tagAt(tm.index!, TAG_OF[tm[1]], /^Pok/.test(tm[2]), `${tm[1]} ${/^Pok/.test(tm[2]) ? 'Pokémon' : 'card'}`);
  }
  for (const tm of text.matchAll(TAG_MEGA)) {
    tagAt(tm.index!, CardTag.POKEMON_SV_MEGA, true, 'Mega Evolution Pokémon ex');
  }
  for (const tm of text.matchAll(TAG_RULE)) {
    tagAt(tm.index!, TAG_OF[tm[1]], true, `Pokémon ${tm[1]}`);
  }
  // deck searches: something in the deck must match
  for (const sm of text.matchAll(SEARCH_POKEMON)) {
    const st = sm[2] ? ({ Basic: 'basic', 'Stage 1': 'stage1', 'Stage 2': 'stage2', Evolution: 'evolution' } as const)[sm[2] as 'Basic'] : undefined;
    const tw = sm[3]?.replace(/[[\]]/g, '');
    const t = tw === 'C' || tw === 'Colorless' ? CardType.COLORLESS : tw ? TYPE_WORD[tw] : undefined;
    out.push({ kind: 'search', types: [], search: { what: 'pokemon', stage: st, types: t !== undefined ? [t] : undefined, maxHp: sm[6] ? Number(sm[6]) : undefined, ex: !!sm[4], noRuleBox: !!sm[5], text: sm[1] } });
  }
  for (const sm of text.matchAll(SEARCH_OTHER)) {
    const what = ({ Supporter: 'supporter', Item: 'item', 'Pokémon Tool': 'tool', 'Basic Energy': 'basic-energy' } as const)[sm[1] as 'Item'];
    out.push({ kind: 'search', types: [], search: { what, text: `${sm[1]} card` } });
  }
  reqCache.set(text, out);
  return out;
}

export interface DeckFacts {
  names: Set<string>;
  energy: Set<CardType>;           // Energy types the deck's Energy cards provide
  anyEnergy: boolean;              // some Energy provides every type
  pokeTypes: Set<CardType>;
  evolvesFrom: Set<string>;        // names something in the deck evolves from
  stage2: boolean;                 // a Stage 2 whose line can be played
  texts: string;                   // every text in the deck (for cards that name other cards)
  cards: Card[];                   // the distinct cards
}

export function deckFacts(cards: string[]): DeckFacts {
  const f: DeckFacts = { names: new Set(), energy: new Set(), anyEnergy: false, pokeTypes: new Set(), evolvesFrom: new Set(), stage2: false, texts: '', cards: [] };
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
        textNeeds(text).filter(r => r.kind === 'energy').forEach(r => r.types.forEach(t => f.energy.add(t)));
      }
    }
    texts.push((c as any).text ?? '');
    if (c instanceof PokemonCard) {
      c.attacks.forEach(a => texts.push(a.text ?? ''));
      c.powers.forEach(p => texts.push(p.text ?? ''));
    }
    if (c instanceof PokemonCard) {
      c.cardType.forEach(t => f.pokeTypes.add(t));
      if (c.evolvesFrom) {
        f.evolvesFrom.add(c.evolvesFrom);
      }
    }
  }
  f.texts = texts.join('\n');
  f.cards = cs;
  f.stage2 = cs.some(c => c instanceof PokemonCard && c.stage === Stage.STAGE_2);
  return f;
}

/** can a deck search find this card? */
function found(s: Search, c: Card): boolean {
  if (s.what === 'supporter' || s.what === 'item' || s.what === 'tool') {
    const t = { supporter: TrainerType.SUPPORTER, item: TrainerType.ITEM, tool: TrainerType.TOOL }[s.what];
    return c instanceof TrainerCard && c.trainerType === t;
  }
  if (s.what === 'basic-energy') {
    return isBasicEnergy(c);
  }
  if (!(c instanceof PokemonCard) || c.superType !== SuperType.POKEMON) {
    return false;                    // Fossils are Items in the deck, not Pokémon
  }
  if (s.stage === 'basic' && c.stage !== Stage.BASIC) return false;
  if (s.stage === 'stage1' && c.stage !== Stage.STAGE_1) return false;
  if (s.stage === 'stage2' && c.stage !== Stage.STAGE_2) return false;
  if (s.stage === 'evolution' && c.stage === Stage.BASIC) return false;
  if (s.types && !s.types.some(t => c.cardType.includes(t))) return false;
  if (s.maxHp !== undefined && c.hp > s.maxHp) return false;
  if (s.ex && !c.tags.includes(CardTag.POKEMON_ex)) return false;
  if (s.noRuleBox && c.tags.some(t => RULE_BOX.test(String(t)))) return false;
  return true;
}

function unmet(reqs: Req[], f: DeckFacts, self?: Card): string | undefined {
  if (!reqs.length) {
    return undefined;
  }
  const ok = (r: Req) => r.kind === 'search' ? f.cards.some(c => c !== self && found(r.search!, c))
    : r.kind === 'tag' ? f.cards.some(c => c !== self && (!r.tag!.pokemon || c instanceof PokemonCard) && c.tags.some(t => String(t) === r.tag!.tag))
    : r.kind === 'stage2' ? f.stage2
    : r.kind === 'energy' ? f.anyEnergy || r.types.some(t => f.energy.has(t))
      : r.types.some(t => f.pokeTypes.has(t));
  if (reqs.some(ok)) {
    return undefined;
  }
  const say = (r: Req) => r.kind === 'tag' ? `${/^[AEIOU]/.test(r.tag!.text) ? 'an' : 'a'} ${r.tag!.text}` : r.kind === 'search' ? `a ${r.search!.text} to search for` : r.kind === 'stage2' ? 'a Stage 2 Pokémon' : `${r.types.map(t => TYPE_NAME[t]).join(' or ')} ${r.kind === 'energy' ? 'Energy' : 'Pokémon'}`;
  return [...new Set(reqs.map(say))].join(' / ');
}

/** does a card other than `c` name it in its text? */
function namedElsewhere(c: PokemonCard, f: DeckFacts): boolean {
  const own = [...c.attacks.map(a => a.text ?? ''), ...c.powers.map(p => p.text ?? '')].join('\n');
  const count = (x: string) => x.split(c.name).length - 1;
  return count(f.texts) > count(own);
}

/** why card `n` cannot be used in a deck with these facts, or undefined if it can */
export function whyUnusable(n: string, f: DeckFacts): string | undefined {
  const c = engineCard(n);
  if (!c || isBasicEnergy(c)) {
    return undefined;
  }
  if (c instanceof PokemonCard) {
    // a deck that uses the attacks of Pokémon from its deck or discard (Slowking's Seek Inspiration:
    // "choose 1 of its attacks and use it") can use any Pokémon without a Rule Box for its attacks
    const ruleBox = c.tags.some(t => /^(EX|GX|V|VMAX|VSTAR|V-UNION|Radiant|Prism Star|Break|Mega EX|Mega ex|Lv.X)$/i.test(String(t)));
    if (/choose 1 of its attacks and use it/i.test(f.texts) && !ruleBox && c.attacks.length) {
      return undefined;
    }
    if (c.evolvesFrom && !f.names.has(c.evolvesFrom)) {
      // a Stage 2 straight from its Basic with Rare Candy
      const basic = c.stage === Stage.STAGE_2 ? cardsNamed(c.evolvesFrom).map(x => (x as PokemonCard).evolvesFrom).find(Boolean) : undefined;
      if (!(basic && f.names.has(basic) && f.names.has('Rare Candy'))) {
        return `nothing to evolve it from (needs ${c.evolvesFrom})`;
      }
    }
    if (f.evolvesFrom.has(c.name)) {
      return undefined;              // part of a line in the deck
    }
    // another card uses it by name, or as one of a group ("N's Pokémon" for N's Zoroark ex's Night Joker)
    const owner = /^(.+?'s) /.exec(c.name)?.[1];
    if ((owner && f.texts.includes(`${owner} Pokémon`)) || namedElsewhere(c, f)) {
      return undefined;
    }
    const payable = (cost: CardType[]) => cost.every(t => t === CardType.COLORLESS || !TYPES.includes(t) || f.anyEnergy || f.energy.has(t));
    const attackOk = c.attacks.some(a => payable(a.cost) && !unmet(textNeeds(a.text ?? '').filter(r => r.kind !== 'tag'), f));
    const abilityOk = c.powers.some(p => !unmet(textNeeds(p.text ?? ''), f));
    if (attackOk || abilityOk) {
      return undefined;
    }
    const why: string[] = [];
    if (c.attacks.length) {
      const need = [...new Set(c.attacks.flatMap(a => a.cost.filter(t => TYPES.includes(t) && !f.energy.has(t))))].map(t => TYPE_NAME[t]);
      why.push(need.length ? `no attack the deck's Energy can pay (needs ${need.join(' or ')} Energy)` : 'its attacks need cards the deck does not have');
    }
    c.powers.forEach(p => why.push(`${p.name} needs ${unmet(textNeeds(p.text ?? ''), f)}`));
    return why.join('; ') || 'no attack or ability';
  }
  if (c instanceof TrainerCard || c instanceof EnergyCard) {
    // for Special Energy, Energy types in its text are what it provides, not requirements
    const reqs = textNeeds((c as any).text ?? '').filter(r => !(c instanceof EnergyCard && r.kind === 'energy'));
    const u = unmet(reqs, f, c);
    return u ? `needs ${u}` : undefined;
  }
  return undefined;
}

/** every card in the list that cannot be used, with the reason */
export function unusableCards(cards: string[]): { card: string; reason: string }[] {
  const f = deckFacts(cards);
  return [...new Set(cards)].map(n => ({ card: n, reason: whyUnusable(n, f) })).filter((x): x is { card: string; reason: string } => !!x.reason);
}
