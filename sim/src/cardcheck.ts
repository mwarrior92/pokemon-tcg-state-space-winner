// Card correctness checks, run by `npm test` and `node dist/cardcheck.js`.
//
// 1. Static: each Twinleaf card is compared with an independent copy of the printed card
//    (pokemon-tcg-data-standard/, keyed by set code + number): HP, stage, evolves-from, type,
//    weakness, resistance, retreat, attack names / costs / base damage, trainer kind.
// 2. Dynamic (smoke): the card is put into a prepared board and every attack, ability or the card
//    itself is used with random prompt answers. A card fails when the engine throws (a bug in the
//    card's code), when a prompt it raises has no valid answer, when cards are lost or duplicated,
//    or - for attacks whose text never mentions damage - when the damage dealt differs from print.
//
// New cards are covered automatically: anything in the Standard data or the meta decklists is
// checked. Known, accepted discrepancies live in sim/test/known-card-issues.json with a reason.
import * as fs from 'fs';
import * as path from 'path';
import { AttackAction, Card, CardType, EnergyCard, GameError, PlayCardAction, PlayerType, PokemonCard, SlotType, Stage, SuperType, TrainerCard, TrainerType, UseAbilityAction } from './engine';
import { REPO_ROOT, allCards, cardBySetNumber, cardsNamed, evolvesFromNames, loadCards, loadMetaLists, resolveEntry } from './cards';
import { checkInvariants } from './invariants';
import { ownedCards } from './rules';
import { Rng } from './rng';
import { buildScenario, PlayerSpec } from './scenario';
import { DeadEnd, randomChooser, resolvePrompts, Sim } from './sim';

import { PrintedCard, printedCards, TYPE_NAMES, baseDamage } from './printed';
export { PrintedCard, printedCards };

function sortedTypes(xs: CardType[]): string {
  return xs.slice().sort((a, b) => a - b).map(t => CardType[t]).join(',');
}

export interface StaticIssue {
  card: string;           // Twinleaf full name
  printed: string;        // dataset id
  field: string;
  twinleaf: string;
  expected: string;
}

/** Twinleaf card for a printed card: same set code + number, else the same name (reprint). */
export function twinleafFor(pc: PrintedCard): { card?: Card; how: string } {
  const exact = cardBySetNumber(pc.set, pc.number);
  if (exact && exact.name.toLowerCase() === pc.name.toLowerCase()) {
    return { card: exact, how: 'set+number' };
  }
  const r = resolveEntry({ name: pc.name, set: pc.set, num: pc.number, count: 1 });
  return { card: r.card, how: r.note ? `${r.how}: ${r.note}` : r.how };
}

export function staticCheck(card: Card, pc: PrintedCard): StaticIssue[] {
  const out: StaticIssue[] = [];
  const add = (field: string, tw: any, exp: any) => {
    if (String(tw) !== String(exp)) {
      out.push({ card: card.fullName, printed: pc.id, field, twinleaf: String(tw), expected: String(exp) });
    }
  };
  if (pc.supertype === 'Pokémon') {
    if (!(card instanceof PokemonCard)) {
      add('supertype', SuperType[card.superType], 'POKEMON');
      return out;
    }
    add('hp', card.hp, Number(pc.hp ?? 0));
    const stage = (pc.subtypes ?? []).includes('Stage 2') ? Stage.STAGE_2 : (pc.subtypes ?? []).includes('Stage 1') ? Stage.STAGE_1 : Stage.BASIC;
    add('stage', Stage[card.stage], Stage[stage]);
    if (pc.evolvesFrom) {
      add('evolvesFrom', card.evolvesFrom, pc.evolvesFrom);
    }
    if (pc.types?.length) {
      add('type', sortedTypes(card.cardType), sortedTypes(pc.types.map(t => TYPE_NAMES[t])));
    }
    add('weakness', sortedTypes(card.weakness.map(w => w.type)), sortedTypes((pc.weaknesses ?? []).map(w => TYPE_NAMES[w.type])));
    add('resistance', card.resistance.map(r => `${CardType[r.type]}${r.value}`).join(','),
      (pc.resistances ?? []).map(r => `${CardType[TYPE_NAMES[r.type]]}${r.value.replace(/[^\d-]/g, '')}`).join(','));
    add('retreat', card.retreat.length, (pc.retreatCost ?? []).length);
    const pa = pc.attacks ?? [];
    add('attack names', card.attacks.map(a => a.name).join(' | '), pa.map(a => a.name).join(' | '));
    pa.forEach((a, idx) => {
      // by name, else by position (translated names must not hide cost/damage differences)
      const ta = card.attacks.find(x => x.name.toLowerCase() === a.name.toLowerCase())
        ?? (card.attacks.length === pa.length ? card.attacks[idx] : undefined);
      if (!ta) {
        return;
      }
      add(`${a.name} cost`, sortedTypes(ta.cost), sortedTypes((a.cost ?? []).filter(t => t !== 'Free').map(t => TYPE_NAMES[t])));
      add(`${a.name} damage`, ta.damage, baseDamage(a.damage));
    });
    const abil = (pc.abilities ?? []).map(a => a.name);
    const tAbil = card.powers.map(p => p.name);
    add('abilities', tAbil.join(' | '), abil.join(' | '));
  } else if (pc.supertype === 'Trainer') {
    if (!(card instanceof TrainerCard)) {
      add('supertype', SuperType[card.superType], 'TRAINER');
      return out;
    }
    const sub = pc.subtypes ?? [];
    const kind = sub.includes('Supporter') ? TrainerType.SUPPORTER : sub.includes('Stadium') ? TrainerType.STADIUM
      : sub.includes('Pokémon Tool') ? TrainerType.TOOL : TrainerType.ITEM;
    add('trainer type', TrainerType[card.trainerType], TrainerType[kind]);
  } else if (pc.supertype === 'Energy') {
    if (!(card instanceof EnergyCard)) {
      add('supertype', SuperType[card.superType], 'ENERGY');
      return out;
    }
    const special = (pc.subtypes ?? []).includes('Special');
    add('energy kind', card.energyType === 1 ? 'SPECIAL' : 'BASIC', special ? 'SPECIAL' : 'BASIC');
  }
  return out;
}

// ---------- dynamic smoke test ----------

export interface SmokeResult {
  card: string;
  failures: string[];
  notes: string[];
  used: number;           // attacks / abilities / plays that the engine accepted
}

let filler: { pokemon: string; big: string } | undefined;

/** Plain Basic Pokémon used around the card under test: a big one with no Weakness or
 *  Resistance (the defender) and an ordinary one (bench, deck). Only cards without abilities. */
function fillers(): { pokemon: string; big: string } {
  if (filler) {
    return filler;
  }
  const basics = allCards().filter(c => c instanceof PokemonCard && c.stage === Stage.BASIC && c.powers.length === 0
    && c.weakness.length === 0 && c.resistance.length === 0 && c.attacks.length > 0 && !c.tags.length) as PokemonCard[];
  basics.sort((a, b) => b.hp - a.hp || a.fullName.localeCompare(b.fullName));
  const plain = allCards().filter(c => c instanceof PokemonCard && c.stage === Stage.BASIC && c.powers.length === 0
    && c.attacks.every(a => !a.text) && !c.tags.length && c.hp >= 60 && c.hp <= 100) as PokemonCard[];
  plain.sort((a, b) => a.fullName.localeCompare(b.fullName));
  filler = { big: basics[0].fullName, pokemon: plain[0].fullName };
  return filler;
}

const BASIC_ENERGY: Partial<Record<CardType, string>> = {
  [CardType.GRASS]: 'Grass Energy', [CardType.FIRE]: 'Fire Energy', [CardType.WATER]: 'Water Energy',
  [CardType.LIGHTNING]: 'Lightning Energy', [CardType.PSYCHIC]: 'Psychic Energy', [CardType.FIGHTING]: 'Fighting Energy',
  [CardType.DARK]: 'Darkness Energy', [CardType.METAL]: 'Metal Energy',
};

function basicEnergy(t: CardType): string {
  const name = BASIC_ENERGY[t] ?? 'Water Energy';
  return resolveEntry({ name, count: 1 }).card!.fullName;
}

/** The Basic (and Stage 1) cards this Pokémon evolves from, Basic first. */
function lowerStages(c: PokemonCard): string[] | undefined {
  if (c.stage === Stage.BASIC) {
    return [];
  }
  const fromNames = [...evolvesFromNames(c.name)];
  for (const n of fromNames) {
    const below = cardsNamed(n).find(x => x instanceof PokemonCard && x.name !== c.name) as PokemonCard | undefined;
    if (below) {
      const rest = lowerStages(below);
      if (rest) {
        return [...rest, below.fullName];
      }
    }
  }
  return undefined;
}

function energyFor(c: PokemonCard): string[] {
  const need = new Map<CardType, number>();
  for (const a of c.attacks) {
    const m = new Map<CardType, number>();
    a.cost.forEach(t => m.set(t, (m.get(t) ?? 0) + 1));
    m.forEach((n, t) => need.set(t, Math.max(need.get(t) ?? 0, n)));
  }
  const out: string[] = [];
  need.forEach((n, t) => {
    for (let i = 0; i < n; i++) {
      out.push(basicEnergy(t === CardType.COLORLESS || t === CardType.ANY ? (c.cardType[0] ?? CardType.WATER) : t));
    }
  });
  out.push(basicEnergy(c.cardType[0] ?? CardType.WATER));   // one spare
  return out;
}

function richPlayer(active: PlayerSpec['active'], extraHand: string[]): PlayerSpec {
  const f = fillers();
  const w = basicEnergy(CardType.WATER);
  const g = basicEnergy(CardType.GRASS);
  return {
    active,
    bench: [{ card: f.pokemon, energy: [w] }, { card: f.pokemon, damage: 30 }],
    hand: [...extraHand, w, f.pokemon],
    deck: [f.pokemon, f.pokemon, w, g, w, g, f.big, w, f.pokemon, g, w, w, g, f.pokemon, w, g, w, w, g, w],
    discard: [w, g, f.pokemon, w],
  };
}

function conservation(sim: Sim): number[] {
  return [0, 1].map(i => ownedCards(sim.state, i).length);
}

function exercise(base: Sim, label: string, act: (s: Sim) => void, seeds: number, res: SmokeResult,
  after?: (before: Sim, s: Sim) => string | undefined): void {
  let accepted = false;
  for (let k = 0; k < seeds; k++) {
    const rng = new Rng(1000 + k);
    const s = base.copy(rng.fork());
    const before = conservation(s);
    try {
      act(s);
    } catch (e) {
      if (e instanceof GameError) {
        if (k === 0) {
          res.notes.push(`${label}: not usable here (${e.message})`);
        }
        return;
      }
      res.failures.push(`${label}: engine error ${String((e as Error)?.stack ?? e).split('\n').slice(0, 2).join(' | ')}`);
      return;
    }
    accepted = true;
    try {
      resolvePrompts(s, randomChooser(rng), rng);
    } catch (e) {
      if (e instanceof DeadEnd) {
        res.failures.push(`${label}: ${e.message}`);
      } else if (e instanceof GameError) {
        res.notes.push(`${label}: rejected after prompts (${e.message})`);
      } else {
        res.failures.push(`${label}: engine error during prompts ${String((e as Error)?.stack ?? e).split('\n').slice(0, 2).join(' | ')}`);
      }
      return;
    }
    const now = conservation(s);
    if (now[0] !== before[0] || now[1] !== before[1]) {
      res.failures.push(`${label}: card count changed ${before.join('/')} -> ${now.join('/')}`);
      return;
    }
    if (!s.finished) {
      const errs = checkInvariants(s.state, { deckSize: -1 }).filter(e => !/owns \d+ cards, expected/.test(e));
      if (errs.length) {
        res.failures.push(`${label}: ${errs.slice(0, 2).join('; ')}`);
        return;
      }
    }
    const msg = after?.(base, s);
    if (msg) {
      res.failures.push(`${label}: ${msg}`);
      return;
    }
  }
  if (accepted) {
    res.used++;
  }
}

export function smokeTest(fullName: string, pc?: PrintedCard, seeds = 3): SmokeResult {
  loadCards();
  const res: SmokeResult = { card: fullName, failures: [], notes: [], used: 0 };
  const proto = allCards().find(c => c.fullName === fullName);
  if (!proto) {
    res.failures.push('not defined in the engine');
    return res;
  }
  const f = fillers();
  const opp: PlayerSpec = richPlayer({ card: f.big, energy: [basicEnergy(CardType.WATER)] }, []);

  if (proto instanceof PokemonCard) {
    const under = lowerStages(proto);
    if (under === undefined) {
      res.notes.push('evolution line not found in the engine; tested as if Basic');
    }
    const me = richPlayer({ card: fullName, under: under ?? [], energy: energyFor(proto) }, [fullName]);
    const base = buildScenario({ p1: me, p2: opp }, new Rng(7));
    for (const a of proto.attacks) {
      const pa = pc?.attacks?.find(x => x.name.toLowerCase() === a.name.toLowerCase());
      // "plain" attacks: the printed number is all that happens to the defender. Anything that
      // copies attacks, flips coins, places counters or inflicts a damaging Special Condition, or
      // can "do nothing", is excluded from the exact-damage check (still smoke tested).
      const plain = pa !== undefined && !/damage|coin|counter|attack|poison|burn|nothing|heads|tails/i.test(pa.text ?? '')
        && !/[+×x-]/.test(pa.damage ?? '');
      exercise(base, `attack ${a.name}`, s => s.apply(new AttackAction(1, a.name)), seeds, res, plain ? (b, s) => {
        const dealt = s.state.players[1].active.damage - b.state.players[1].active.damage;
        const expected = baseDamage(pa!.damage);
        // the defender has no Weakness/Resistance and enough HP; a KO ends the check
        return s.state.players[1].active.getPokemonCard()?.fullName === f.big && dealt !== expected
          ? `dealt ${dealt} damage, card says ${expected}` : undefined;
      } : undefined);
    }
    for (const pw of proto.powers) {
      exercise(base, `ability ${pw.name} (active)`, s => s.apply(new UseAbilityAction(1, pw.name, { player: PlayerType.BOTTOM_PLAYER, slot: SlotType.ACTIVE, index: 0 })), seeds, res);
    }
    // play it from hand (bench it, or evolve onto a matching Pokémon in play)
    exercise(base, 'play from hand', s => {
      const hi = s.state.players[0].hand.cards.findIndex(c => c.fullName === fullName);
      const target = proto.stage === Stage.BASIC ? { player: PlayerType.BOTTOM_PLAYER, slot: SlotType.BENCH, index: 2 }
        : { player: PlayerType.BOTTOM_PLAYER, slot: SlotType.ACTIVE, index: 0 };
      s.apply(new PlayCardAction(1, hi, target));
    }, seeds, res);
  } else if (proto instanceof TrainerCard) {
    const me = richPlayer({ card: f.pokemon, energy: [basicEnergy(CardType.WATER)], damage: 20 }, [fullName, fullName]);
    const base = buildScenario({ p1: me, p2: opp }, new Rng(7));
    const targets = proto.trainerType === TrainerType.TOOL
      ? [{ player: PlayerType.BOTTOM_PLAYER, slot: SlotType.ACTIVE, index: 0 }, { player: PlayerType.BOTTOM_PLAYER, slot: SlotType.BENCH, index: 0 }]
      : [{ player: PlayerType.BOTTOM_PLAYER, slot: SlotType.ACTIVE, index: 0 }];
    targets.forEach((t, k) => exercise(base, `play${k ? ' (bench target)' : ''}`, s => {
      const hi = s.state.players[0].hand.cards.findIndex(c => c.fullName === fullName);
      s.apply(new PlayCardAction(1, hi, t));
    }, seeds, res));
  } else if (proto instanceof EnergyCard) {
    if (!proto.provides?.length && proto.energyType === 0) {
      res.failures.push('basic energy provides nothing');
    }
    const me = richPlayer({ card: f.pokemon }, [fullName]);
    const base = buildScenario({ p1: me, p2: opp }, new Rng(7));
    exercise(base, 'attach', s => {
      const hi = s.state.players[0].hand.cards.findIndex(c => c.fullName === fullName);
      s.apply(new PlayCardAction(1, hi, { player: PlayerType.BOTTOM_PLAYER, slot: SlotType.ACTIVE, index: 0 }));
    }, seeds, res);
  }
  return res;
}

// ---------- card pools ----------

/** Twinleaf full names of every card in the meta decklists. */
export function metaCardNames(): string[] {
  const s = new Set<string>();
  for (const l of loadMetaLists()) {
    for (const e of l.cards) {
      const r = resolveEntry(e);
      if (r.card) {
        s.add(r.card.fullName);
      }
    }
  }
  return [...s].sort();
}

export interface KnownIssues {
  static: Record<string, string>;     // "<fullName>|<field>" -> reason
  smoke: Record<string, string>;      // "<fullName>|<label prefix>" -> reason
}

export function loadKnownIssues(): KnownIssues {
  const f = path.join(REPO_ROOT, 'sim', 'test', 'known-card-issues.json');
  if (!fs.existsSync(f)) {
    return { static: {}, smoke: {} };
  }
  return JSON.parse(fs.readFileSync(f, 'utf8'));
}

export function isKnownStatic(k: KnownIssues, i: StaticIssue): boolean {
  return k.static[`${i.card}|${i.field}`] !== undefined || k.static[`${i.card}|*`] !== undefined;
}

export function isKnownSmoke(k: KnownIssues, card: string, failure: string): boolean {
  return Object.keys(k.smoke).some(key => {
    const [c, prefix] = key.split('|');
    return c === card && failure.startsWith(prefix);
  });
}

// ---------- new / changed card detection ----------

import { createHash } from 'crypto';

/** Fingerprint of a card's rules: printed fields plus the code of its effects. Changes when a
 *  card is added, edited upstream, or patched here. */
export function cardFingerprint(c: Card): string {
  const fields: any = {};
  for (const k of Object.keys(c).sort()) {
    const v = (c as any)[k];
    if (typeof v !== 'function' && k !== 'id' && k !== 'cardImage' && k !== 'marker') {
      fields[k] = v;
    }
  }
  // the bundler suffixes colliding identifiers with numbers (MOVE_CARDS2, Pawmo3) differently in each
  // bundle; strip those so the fingerprint only changes when the card's code does
  const norm = (f: any) => String(f ?? '').replace(/\b([A-Za-z_$][A-Za-z_$]*?)\d+\b/g, '$1');
  const code = [norm((c as any).reduceEffect), ...((c as any).powers ?? []).map((p: any) => norm(p.effect))].join('\n');
  return createHash('sha1').update(JSON.stringify(fields, (_k, v) => typeof v === 'function' ? norm(v) : v) + code).digest('hex').slice(0, 16);
}

export function manifestPath(): string {
  return path.join(REPO_ROOT, 'sim', 'test', 'card-manifest.json');
}

export function loadManifest(): Record<string, string> {
  return fs.existsSync(manifestPath()) ? JSON.parse(fs.readFileSync(manifestPath(), 'utf8')) : {};
}

/** Every engine card that stands for a printed Standard card, with that printing. */
export function standardPool(): Map<string, PrintedCard> {
  const pool = new Map<string, PrintedCard>();
  for (const pc of printedCards()) {
    const tw = twinleafFor(pc);
    if (tw.card && (!pool.has(tw.card.fullName) || tw.how === 'set+number')) {
      pool.set(tw.card.fullName, pc);
    }
  }
  return pool;
}
