// Board -> numbers. The feature vector is written from the point of view of `me` (normally the
// player to move): my slots first, then the opponent's. Features come in named groups with a cost
// class, so the reduction step (featsel.ts) can drop whole groups and move from exact, expensive
// engine probes toward cheap statistics:
//   cheap  - read straight off the board (HP, types, energy, costs, resources)
//   probe  - measured by playing the action in a throw-away copy of the game (exact damage an
//            attack does to each opposing Pokémon, damage an ability or a hand card can place)
// No feature encodes a judgement about what is good; they are facts about the position.
import {
  AttackAction, CardType, EnergyCard, PlayCardAction, Player, PlayerType, PokemonCard, PokemonCardList, SlotType,
  SpecialCondition, State, TrainerCard, TrainerType, UseAbilityAction,
} from './engine';
import { isEnergyCard, isPokemonCard, isTrainerCard, prizeValue, prizesLeft } from './rules';
import { Rng } from './rng';
import { makeCard } from './scenario';
import { DeadEnd, Sim, randomChooser, resolvePrompts } from './sim';
import { CardTag, Stage } from './engine';
import { resolveEntry } from './cards';

export const TYPES: CardType[] = [CardType.GRASS, CardType.FIRE, CardType.WATER, CardType.LIGHTNING, CardType.PSYCHIC,
  CardType.FIGHTING, CardType.DARK, CardType.METAL, CardType.FAIRY, CardType.DRAGON, CardType.COLORLESS];
const TYPE_KEYS = ['G', 'R', 'W', 'L', 'P', 'F', 'D', 'M', 'Y', 'N', 'C'];
const CONDITIONS = [SpecialCondition.POISONED, SpecialCondition.BURNED, SpecialCondition.ASLEEP, SpecialCondition.PARALYZED, SpecialCondition.CONFUSED];
export const SLOTS = 6;            // active + 5 bench, per side
export const ATTACKS = 2;          // attacks described per Pokémon (a third is rare in Standard)

export type Group = 'board' | 'types' | 'energy' | 'attacks' | 'resources' | 'turn' | 'reach' | 'probe-damage' | 'probe-ability' | 'probe-hand';
export const CHEAP_GROUPS: Group[] = ['board', 'types', 'energy', 'attacks', 'resources', 'turn', 'reach'];
export const PROBE_GROUPS: Group[] = ['probe-damage', 'probe-ability', 'probe-hand'];
export const ALL_GROUPS: Group[] = [...CHEAP_GROUPS, ...PROBE_GROUPS];

export interface FeatureVector {
  names: string[];
  groups: Group[];
  values: number[];
}

class Builder {
  names: string[] = [];
  groups: Group[] = [];
  values: number[] = [];
  constructor(private want: Set<Group>, private only?: Set<string>) {}
  on(g: Group): boolean {
    return this.want.has(g);
  }
  /** is this feature wanted (its group is on, and it is in `only` if that is given)? */
  need(g: Group, name: string): boolean {
    return this.want.has(g) && (!this.only || this.only.has(name));
  }
  add(g: Group, name: string, v: number): void {
    if (!this.need(g, name)) {
      return;
    }
    this.names.push(name);
    this.groups.push(g);
    this.values.push(Number.isFinite(v) ? v : 0);
  }
}

/** Bench order used by the vector: highest prize value, then most HP left, then name. Fixed so the
 *  same board always produces the same vector. */
export function orderedSlots(p: Player): PokemonCardList[] {
  const bench = p.bench.filter(b => b.cards.length > 0).sort((a, b) => {
    const pa = a.getPokemonCard()!, pb = b.getPokemonCard()!;
    return (prizeValue(pb) - prizeValue(pa)) || ((pb.hp - b.damage) - (pa.hp - a.damage)) || pa.fullName.localeCompare(pb.fullName);
  });
  const out: (PokemonCardList | undefined)[] = [p.active.cards.length ? p.active : undefined, ...bench];
  while (out.length < SLOTS) {
    out.push(undefined);
  }
  return out as PokemonCardList[];
}

function energyCounts(l: PokemonCardList): number[] {
  const n = TYPES.map(() => 0);
  for (const e of l.energies.cards) {
    const provides = (e as EnergyCard).provides ?? [CardType.COLORLESS];
    for (const t of provides) {
      const i = TYPES.indexOf(t);
      n[i >= 0 ? i : TYPES.length - 1]++;
    }
  }
  return n;
}

/** Energy cards still needed to pay `cost` with what is attached (basic arithmetic: typed costs
 *  first, colorless from the rest; ANY-providing cards fill any gap). */
export function energyGap(cost: CardType[], l: PokemonCardList): number {
  const have = energyCounts(l);
  let any = 0;
  for (const e of l.energies.cards) {
    if (((e as EnergyCard).provides ?? []).includes(CardType.ANY)) {
      any++;
    }
  }
  let missing = 0;
  let spare = have.reduce((s, x) => s + x, 0) + any;
  const typed = new Map<number, number>();
  let colorless = 0;
  for (const t of cost) {
    if (t === CardType.COLORLESS) {
      colorless++;
    } else {
      typed.set(t, (typed.get(t) ?? 0) + 1);
    }
  }
  typed.forEach((need, t) => {
    const i = TYPES.indexOf(t);
    const got = i >= 0 ? have[i] : 0;
    const use = Math.min(need, got);
    spare -= use;
    let rest = need - use;
    const fromAny = Math.min(rest, any);
    any -= fromAny;
    spare -= fromAny;
    rest -= fromAny;
    missing += rest;
  });
  missing += Math.max(0, colorless - Math.max(0, spare));
  return missing;
}

function isTag(c: PokemonCard, t: CardTag): number {
  return c.tags.includes(t) ? 1 : 0;
}

// ---------------------------------------------------------------- probes

export interface ProbeOptions {
  seeds?: number;     // prompt answer samples per probe (max is kept)
  /** compute only these features (by name); engine probes run only for features in it. A model
   *  passes its own names, so play time pays only for what the model uses. */
  only?: Set<string>;
}

function slotKey(l: PokemonCardList, p: Player): number {
  return l === p.active ? 0 : 1 + p.bench.indexOf(l);
}

/** Put the Pokémon in `slot` (index in active/bench numbering) into the Active Spot of a copy. */
function swapToActive(p: Player, idx: number): void {
  if (idx === 0) {
    return;
  }
  const b = p.bench[idx - 1];
  p.bench[idx - 1] = p.active;
  p.active = b;
}

function basicEnergyFor(t: CardType): string {
  const names: Partial<Record<CardType, string>> = {
    [CardType.GRASS]: 'Grass Energy', [CardType.FIRE]: 'Fire Energy', [CardType.WATER]: 'Water Energy', [CardType.LIGHTNING]: 'Lightning Energy',
    [CardType.PSYCHIC]: 'Psychic Energy', [CardType.FIGHTING]: 'Fighting Energy', [CardType.DARK]: 'Darkness Energy', [CardType.METAL]: 'Metal Energy',
  };
  return resolveEntry({ name: names[t] ?? 'Water Energy', count: 1 }).card!.fullName;
}

/** Damage (capped at HP left, KO = full HP left) that `side`'s Pokémon at slot `a` does to each
 *  of the opponent's slots with attack `name`, measured in the engine. `topUp` attaches whatever
 *  energy the cost still needs (the "potential" version); otherwise only attached energy counts. */
function probeAttack(sim: Sim, side: number, a: number, d: number, name: string, topUp: boolean, seeds: number): number[] | undefined {
  let best: number[] | undefined;
  for (let k = 0; k < seeds; k++) {
    const c = sim.copy(new Rng(7 + k));
    const st = c.state;
    const me = st.players[side];
    const op = st.players[1 - side];
    swapToActive(me, a);
    swapToActive(op, d);
    st.activePlayer = side;
    if (st.turn < 3) {
      st.turn = 3;   // first-turn attack ban is a timing rule, not a property of the board
    }
    me.active.specialConditions = [];
    const atk = me.active.getPokemonCard()!.attacks.find(x => x.name === name);
    if (!atk) {
      return undefined;
    }
    if (topUp) {
      const gapTypes: CardType[] = [];
      // add one energy of each missing typed symbol, colorless as the Pokémon's own type
      const tmp = me.active;
      let guard = 0;
      while (energyGap(atk.cost, tmp) > 0 && guard++ < 8) {
        const typed = atk.cost.find(t => t !== CardType.COLORLESS && energyGap([t], tmp) > 0);
        const t = typed ?? (me.active.getPokemonCard()!.cardType[0] ?? CardType.WATER);
        gapTypes.push(t);
        const e = makeCard(basicEnergyFor(t));
        tmp.cards.push(e);
        tmp.energies.cards.push(e);
      }
    }
    const opSlots = [op.active, ...op.bench];
    const before = opSlots.map(l => ({ l, hpLeft: l.cards.length ? (l.getPokemonCard()!.hp + (l.hpBonus ?? 0) - l.damage) : 0, dmg: l.damage }));
    try {
      c.apply(new AttackAction(me.id, name));
      resolvePrompts(c, randomChooser(new Rng(100 + k)), new Rng(200 + k));
    } catch (e) {
      if (k === 0 && !(e instanceof DeadEnd)) {
        return undefined;   // not usable (or engine refused): no measurement
      }
      continue;
    }
    const out = before.map(b => {
      if (b.hpLeft <= 0) {
        return 0;
      }
      if (b.l.cards.length === 0) {
        return b.hpLeft;   // knocked out
      }
      return Math.min(b.hpLeft, Math.max(0, b.l.damage - b.dmg));
    });
    // undo the swap numbering: report in original slot order of the defender side
    const ordered = out.slice();
    if (d !== 0) {
      [ordered[0], ordered[d]] = [ordered[d], ordered[0]];
    }
    best = best ? best.map((x, i) => Math.max(x, ordered[i])) : ordered;
  }
  return best;
}

/** Damage counters an ability can place on the opponent's board right now (0 when it cannot be
 *  used or places none). */
function probeAbility(sim: Sim, side: number, a: number, power: string, seeds: number): number {
  let best = 0;
  for (let k = 0; k < seeds; k++) {
    const c = sim.copy(new Rng(11 + k));
    const st = c.state;
    if (st.activePlayer !== side) {
      return 0;   // only the player to move can use abilities now
    }
    const me = st.players[side];
    const op = st.players[1 - side];
    const target = a === 0 ? { player: PlayerType.BOTTOM_PLAYER, slot: SlotType.ACTIVE, index: 0 }
      : { player: PlayerType.BOTTOM_PLAYER, slot: SlotType.BENCH, index: a - 1 };
    const before = [op.active, ...op.bench].reduce((s, l) => s + l.damage, 0);
    const prizes = prizesLeft(me);
    try {
      c.apply(new UseAbilityAction(me.id, power, target));
      resolvePrompts(c, randomChooser(new Rng(300 + k)), new Rng(400 + k));
    } catch {
      continue;
    }
    const placed = [op.active, ...op.bench].reduce((s, l) => s + l.damage, 0) - before + 100 * (prizes - prizesLeft(me));
    best = Math.max(best, placed);
  }
  return best;
}

/** Best damage a single card in hand places on the opponent's board when played now. */
function probeHand(sim: Sim, side: number, seeds: number): { damage: number; prizes: number } {
  const st = sim.state;
  if (st.activePlayer !== side) {
    return { damage: 0, prizes: 0 };
  }
  const me = st.players[side];
  let best = { damage: 0, prizes: 0 };
  const seen = new Set<string>();
  me.hand.cards.forEach((card, hi) => {
    if (!(isTrainerCard(card)) || card.trainerType === TrainerType.TOOL || card.trainerType === TrainerType.STADIUM || seen.has(card.fullName)) {
      return;
    }
    seen.add(card.fullName);
    for (let k = 0; k < seeds; k++) {
      const c = sim.copy(new Rng(21 + k));
      const op = c.state.players[1 - side];
      const before = [op.active, ...op.bench].reduce((s, l) => s + l.damage, 0);
      const prizes = prizesLeft(c.state.players[side]);
      try {
        c.apply(new PlayCardAction(me.id, hi, { player: PlayerType.BOTTOM_PLAYER, slot: SlotType.ACTIVE, index: 0 }));
        resolvePrompts(c, randomChooser(new Rng(500 + k)), new Rng(600 + k));
      } catch {
        continue;
      }
      const dmg = [op.active, ...op.bench].reduce((s, l) => s + l.damage, 0) - before;
      const pz = prizes - prizesLeft(c.state.players[side]);
      if (dmg > best.damage || pz > best.prizes) {
        best = { damage: Math.max(best.damage, dmg), prizes: Math.max(best.prizes, pz) };
      }
    }
  });
  return best;
}


// ---------------------------------------------------------------- reach (review offense-r1)
//
// Can a Knock Out be put together this turn? For every attacker (a Pokémon in play, or an
// evolution in hand that can evolve one now) x attack x opposing target:
//   damage   - the probe's exact number when probes ran, else printed damage x Weakness - Resistance
//   energy   - cost gap after this turn's one attachment (if an Energy is in hand and none attached)
//   active   - the attacker is Active, or can get there (affordable retreat, or a switch card in hand)
//   target   - the target is Active, or a gust card ("switch in 1 of your opponent's Benched
//              Pokémon") is in hand
// The opponent's side uses public information only: their hand is unknown, so they are assumed to
// have one attachment (if they hold any card) and no switch or gust card.
const GUST_TEXT = /switch in 1 of your opponent's benched pok[eé]mon to the active spot/i;
const SWITCH_TEXT = /switch your active pok[eé]mon with 1 of your benched pok[eé]mon/i;
// energy acceleration: a card or ability that attaches Energy (beyond the one attachment per turn)
const ACCEL_TEXT = /attach (up to )?(an?|\d+|any amount of) .{0,60}energy/i;
// retreat helpers: tools / items / stadiums that change Retreat Cost
const RETREAT_TEXT = /retreat cost/i;
// abilities that put damage counters on the opponent's Pokémon
const COUNTER_TEXT = /(put|move) .{0,40}damage counters? .{0,60}(opponent|their)/i;

function cardText(c: any): string {
  return [c.text, ...(c.attacks ?? []).map((a: any) => a.text), ...(c.powers ?? []).map((p: any) => p.text)].filter(Boolean).join(' ');
}

export function estimateDamage(attacker: PokemonCard, base: number, defender: PokemonCard | undefined): number {
  if (!defender || base <= 0) {
    return Math.max(0, base);
  }
  let d = base;
  if (defender.weakness.some(w => attacker.cardType.includes(w.type))) {
    d *= 2;
  }
  const r = defender.resistance.find(x => attacker.cardType.includes(x.type));
  if (r) {
    d += r.value;   // value is negative (e.g. -30)
  }
  return Math.max(0, d);
}

interface ReachSummary {
  maxPrize: number; count: number; oneShortMaxPrize: number; oneShortCount: number; potentialMaxPrize: number;
  perTarget: number[]; perTargetOneShort: number[]; bestDamageToActive: number;
}

function reachFor(st: State, side: number, mine: PokemonCardList[], theirs: PokemonCardList[], knowHand: boolean,
  potential: number[][][] | undefined): ReachSummary {
  const p = st.players[side];
  const hand = knowHand ? p.hand.cards : [];
  const gust = hand.some(c => isTrainerCard(c) && GUST_TEXT.test(cardText(c)));
  const sw = hand.some(c => isTrainerCard(c) && SWITCH_TEXT.test(cardText(c)));
  const attachOk = knowHand ? (hand.some(isEnergyCard) && p.energyPlayedTurn !== st.turn) : p.hand.cards.length > 0;
  // extra attachments from trainers in hand and abilities in play (review offense-r1 follow-up)
  const accel = Math.min(3, hand.filter(c => isTrainerCard(c) && ACCEL_TEXT.test(cardText(c))).length
    + mine.filter(l => l?.getPokemonCard()?.powers.some(pw => ACCEL_TEXT.test(pw.text ?? ''))).length);
  const retreatHelp = hand.some(c => isTrainerCard(c) && RETREAT_TEXT.test(cardText(c)));
  const active = mine[0];
  const canRetreat = !!active && p.retreatedTurn !== st.turn && active.getPokemonCard() !== undefined
    && (energyGap(active.getPokemonCard()!.retreat, active) === 0 || retreatHelp);
  const out: ReachSummary = { maxPrize: 0, count: 0, oneShortMaxPrize: 0, oneShortCount: 0, potentialMaxPrize: 0,
    perTarget: theirs.map(() => 0), perTargetOneShort: theirs.map(() => 0), bestDamageToActive: 0 };
  // attackers: in play, plus evolutions in hand onto a Pokémon that can evolve now
  const attackers: { slot: number; card: PokemonCard; list: PokemonCardList }[] = [];
  mine.forEach((l, a) => {
    const pc = l?.getPokemonCard();
    if (pc) {
      attackers.push({ slot: a, card: pc, list: l });
      if (knowHand && st.turn > 2 && l.pokemonPlayedTurn < st.turn) {
        for (const c of hand) {
          if (isPokemonCard(c) && c.evolvesFrom === pc.name) {
            attackers.push({ slot: a, card: c, list: l });
          }
        }
      }
    }
  });
  for (const at of attackers) {
    const isActive = at.slot === 0;
    const activeOk = isActive || canRetreat || sw;
    at.card.attacks.forEach((atk, j) => {
      const gap = Math.max(0, energyGap(atk.cost, at.list) - (attachOk ? 1 : 0) - accel);
      theirs.forEach((dl, d) => {
        const dpc = dl?.getPokemonCard();
        if (!dpc) {
          return;
        }
        const hpLeft = dpc.hp + (dl.hpBonus ?? 0) - dl.damage;
        const probed = at.card === at.list.getPokemonCard() ? potential?.[at.slot]?.[j]?.[d] : undefined;
        const dmg = probed ?? estimateDamage(at.card, atk.damage, dpc);
        if (d === 0 && isActive && gap === 0) {
          out.bestDamageToActive = Math.max(out.bestDamageToActive, dmg);
        }
        if (dmg < hpLeft) {
          return;
        }
        const prize = prizeValue(dpc);
        out.potentialMaxPrize = Math.max(out.potentialMaxPrize, prize);
        const missing = (gap > 0 ? 1 : 0) + (activeOk ? 0 : 1) + (d === 0 || gust ? 0 : 1);
        if (missing === 0) {
          out.maxPrize = Math.max(out.maxPrize, prize);
          out.count++;
          out.perTarget[d] = 1;
        } else if (missing === 1) {
          out.oneShortMaxPrize = Math.max(out.oneShortMaxPrize, prize);
          out.oneShortCount++;
          out.perTargetOneShort[d] = 1;
        }
      });
    });
  }
  return out;
}

// ---------------------------------------------------------------- the vector

export function features(sim: Sim, me: number, groups: Group[] = ALL_GROUPS, opts: ProbeOptions = {}): FeatureVector {
  const st: State = sim.state;
  const b = new Builder(new Set(groups), opts.only);
  const seeds = opts.seeds ?? 1;
  const sides = [me, 1 - me];
  const ordered = sides.map(i => orderedSlots(st.players[i]));

  // probe tables, computed on first use (each engine probe runs at most once per vector):
  // potential(s, a, j, d) = damage side s's slot a does with attack j to opposing slot d, with the
  // energy it still needs topped up; nowToActive(s, a, j) = the same, Active vs Active, with what
  // is attached now (only on the side to move)
  const potMemo = new Map<number, number>();
  const potential = (s: number, a: number, j: number, d: number): number => {
    const k = ((s * SLOTS + a) * ATTACKS + j) * SLOTS + d;
    let v = potMemo.get(k);
    if (v === undefined) {
      v = 0;
      const side = sides[s];
      const l = ordered[s][a], dl = ordered[1 - s][d];
      const atk = l?.getPokemonCard()?.attacks[j];
      if (l && dl && atk && j < ATTACKS) {
        const didx = slotKey(dl, st.players[1 - side]);
        v = probeAttack(sim, side, slotKey(l, st.players[side]), didx, atk.name, true, seeds)?.[didx] ?? 0;
      }
      potMemo.set(k, v);
    }
    return v;
  };
  const nowToActive = (s: number, a: number, j: number): number => {
    const side = sides[s];
    const l = ordered[s][a], dl = ordered[1 - s][0];
    const atk = l?.getPokemonCard()?.attacks[j];
    if (!l || !dl || !atk || side !== st.activePlayer || slotKey(l, st.players[side]) !== 0 || slotKey(dl, st.players[1 - side]) !== 0
      || energyGap(atk.cost, l) !== 0) {
      return 0;
    }
    return probeAttack(sim, side, 0, 0, atk.name, false, seeds)?.[0] ?? 0;
  };

  sides.forEach((side, s) => {
    const p = st.players[side];
    const tag = s === 0 ? 'me' : 'op';
    ordered[s].forEach((l, a) => {
      const pre = `${tag}.s${a}`;
      const pc = l?.getPokemonCard();
      const hpMax = pc ? pc.hp + (l.hpBonus ?? 0) : 0;
      const hpLeft = pc ? hpMax - l.damage : 0;
      b.add('board', `${pre}.present`, pc ? 1 : 0);
      b.add('board', `${pre}.hpMax`, hpMax);
      b.add('board', `${pre}.hpLeft`, hpLeft);
      b.add('board', `${pre}.damage`, pc ? l.damage : 0);
      b.add('board', `${pre}.prizeValue`, pc ? prizeValue(pc) : 0);
      b.add('board', `${pre}.stage`, pc ? (pc.stage === Stage.STAGE_2 ? 2 : pc.stage === Stage.STAGE_1 ? 1 : 0) : 0);
      b.add('board', `${pre}.ex`, pc ? isTag(pc, CardTag.POKEMON_ex) : 0);
      b.add('board', `${pre}.mega`, pc ? isTag(pc, CardTag.POKEMON_SV_MEGA) : 0);
      b.add('board', `${pre}.hasAbility`, pc ? (pc.powers.length ? 1 : 0) : 0);
      b.add('board', `${pre}.tool`, pc ? l.tools.length : 0);
      b.add('board', `${pre}.retreatCost`, pc ? pc.retreat.length : 0);
      b.add('board', `${pre}.retreatGap`, pc ? Math.max(0, pc.retreat.length - l.energies.cards.length) : 0);
      if (a === 0) {
        CONDITIONS.forEach((c, k) => b.add('board', `${pre}.cond${k}`, pc && l.specialConditions.includes(c) ? 1 : 0));
      }
      if (b.on('types')) {
        TYPES.forEach((t, k) => b.add('types', `${pre}.type${TYPE_KEYS[k]}`, pc && pc.cardType.includes(t) ? 1 : 0));
        TYPES.forEach((t, k) => b.add('types', `${pre}.weak${TYPE_KEYS[k]}`, pc && pc.weakness.some(w => w.type === t) ? 1 : 0));
        TYPES.forEach((t, k) => b.add('types', `${pre}.resist${TYPE_KEYS[k]}`, pc && pc.resistance.some(r => r.type === t) ? 1 : 0));
      }
      if (b.on('energy')) {
        const ec = pc ? energyCounts(l) : TYPES.map(() => 0);
        b.add('energy', `${pre}.energy`, pc ? l.energies.cards.length : 0);
        ec.forEach((n, k) => b.add('energy', `${pre}.energy${TYPE_KEYS[k]}`, n));
      }
      for (let j = 0; j < ATTACKS; j++) {
        const atk = pc?.attacks[j];
        b.add('attacks', `${pre}.a${j}.present`, atk ? 1 : 0);
        b.add('attacks', `${pre}.a${j}.cost`, atk ? atk.cost.length : 0);
        b.add('attacks', `${pre}.a${j}.gap`, atk ? energyGap(atk.cost, l) : 0);
        b.add('attacks', `${pre}.a${j}.baseDamage`, atk ? atk.damage : 0);
        if (b.on('probe-damage')) {
          for (let d = 0; d < SLOTS; d++) {
            const dmgName = `${pre}.a${j}.dmgTo${d}`, koName = `${pre}.a${j}.koTo${d}`;
            if (!b.need('probe-damage', dmgName) && !b.need('probe-damage', koName)) {
              continue;
            }
            const pot = potential(s, a, j, d);
            const dl = ordered[1 - s][d];
            const dpc = dl?.getPokemonCard();
            const hpD = dpc ? dpc.hp + (dl.hpBonus ?? 0) - dl.damage : 0;
            b.add('probe-damage', dmgName, pot);
            b.add('probe-damage', koName, hpD > 0 && pot >= hpD ? 1 : 0);
          }
          if (b.need('probe-damage', `${pre}.a${j}.nowToActive`)) {
            b.add('probe-damage', `${pre}.a${j}.nowToActive`, nowToActive(s, a, j));
          }
        }
      }
      if (b.need('probe-damage', `${pre}.incoming`) || b.need('probe-damage', `${pre}.koThreat`)) {
        // incoming: the most any opposing Pokémon could do to this one, and whether that is a KO
        let incoming = 0;
        for (let oa = 0; oa < SLOTS && pc; oa++) {
          for (let j = 0; j < ATTACKS; j++) {
            incoming = Math.max(incoming, potential(1 - s, oa, j, a));
          }
        }
        b.add('probe-damage', `${pre}.incoming`, incoming);
        b.add('probe-damage', `${pre}.koThreat`, pc && incoming >= hpLeft ? 1 : 0);
      }
      if (b.need('probe-ability', `${pre}.abilityDamage`)) {
        const pw = pc?.powers.find(x => x.useWhenInPlay !== false);
        b.add('probe-ability', `${pre}.abilityDamage`, pc && pw ? probeAbility(sim, side, slotKey(l, p), pw.name, seeds) : 0);
      }
    });

    // resources
    const hand = p.hand.cards;
    const deck = p.deck.cards;
    const disc = p.discard.cards;
    const inPlayNames = new Set([p.active, ...p.bench].flatMap(l => l.getPokemons().map(c => c.name)));
    b.add('resources', `${tag}.prizes`, prizesLeft(p));
    b.add('resources', `${tag}.hand`, hand.length);
    b.add('resources', `${tag}.deck`, deck.length);
    b.add('resources', `${tag}.discard`, disc.length);
    b.add('resources', `${tag}.discardPokemon`, disc.filter(isPokemonCard).length);
    b.add('resources', `${tag}.discardEnergy`, disc.filter(isEnergyCard).length);
    b.add('resources', `${tag}.discardTrainer`, disc.filter(isTrainerCard).length);
    b.add('resources', `${tag}.lostzone`, p.lostzone.cards.length);
    b.add('resources', `${tag}.benchCount`, p.bench.filter(x => x.cards.length).length);
    b.add('resources', `${tag}.benchSpace`, p.bench.filter(x => !x.cards.length).length);
    b.add('resources', `${tag}.stadium`, p.stadium.cards.length);
    if (s === 0) {
      // own hidden zones are known to the player (hand contents, deck contents but not order)
      b.add('resources', 'me.handPokemon', hand.filter(isPokemonCard).length);
      b.add('resources', 'me.handBasic', hand.filter(c => isPokemonCard(c) && c.stage === Stage.BASIC).length);
      b.add('resources', 'me.handEvolution', hand.filter(c => isPokemonCard(c) && c.stage !== Stage.BASIC).length);
      b.add('resources', 'me.handEvolvesInPlay', hand.filter(c => isPokemonCard(c) && !!c.evolvesFrom && inPlayNames.has(c.evolvesFrom)).length);
      b.add('resources', 'me.handEnergy', hand.filter(isEnergyCard).length);
      b.add('resources', 'me.handSupporter', hand.filter(c => isTrainerCard(c) && c.trainerType === TrainerType.SUPPORTER).length);
      b.add('resources', 'me.handItem', hand.filter(c => isTrainerCard(c) && c.trainerType === TrainerType.ITEM).length);
      b.add('resources', 'me.handTool', hand.filter(c => isTrainerCard(c) && c.trainerType === TrainerType.TOOL).length);
      b.add('resources', 'me.handStadium', hand.filter(c => isTrainerCard(c) && c.trainerType === TrainerType.STADIUM).length);
      b.add('resources', 'me.deckPokemon', deck.filter(isPokemonCard).length);
      b.add('resources', 'me.deckBasic', deck.filter(c => isPokemonCard(c) && c.stage === Stage.BASIC).length);
      b.add('resources', 'me.deckEnergy', deck.filter(isEnergyCard).length);
      b.add('resources', 'me.altPokemon', [...hand, ...deck].filter(c => isPokemonCard(c) && !inPlayNames.has(c.name)).length);
      TYPES.forEach((t, k) => b.add('energy', `me.handEnergy${TYPE_KEYS[k]}`, hand.filter(c => isEnergyCard(c) && ((c as EnergyCard).provides ?? []).includes(t)).length));
    }
  });

  if (b.need('probe-hand', 'me.handDamage') || b.need('probe-hand', 'me.handPrizes')) {
    const h = probeHand(sim, me, seeds);
    b.add('probe-hand', 'me.handDamage', h.damage);
    b.add('probe-hand', 'me.handPrizes', h.prizes);
  }

  if (b.on('reach')) {
    sides.forEach((side, s) => {
      const tag = s === 0 ? 'me' : 'op';
      // always the analytic damage estimate (not the probes): the reach group must mean the same
      // with or without the probe groups, or a "cheap" model would be trained on probe-based values
      // and played with estimated ones
      const r = reachFor(st, side, ordered[s], ordered[1 - s], s === 0, undefined);
      b.add('reach', `${tag}.reach.maxPrize`, r.maxPrize);
      b.add('reach', `${tag}.reach.count`, r.count);
      b.add('reach', `${tag}.reach.oneShortMaxPrize`, r.oneShortMaxPrize);
      b.add('reach', `${tag}.reach.oneShortCount`, r.oneShortCount);
      b.add('reach', `${tag}.reach.potentialMaxPrize`, r.potentialMaxPrize);
      b.add('reach', `${tag}.reach.bestDamageToActive`, r.bestDamageToActive);
      r.perTarget.forEach((v, d) => b.add('reach', `${tag}.reach.ko${d}`, v));
      r.perTargetOneShort.forEach((v, d) => b.add('reach', `${tag}.reach.oneShort${d}`, v));
    });
    const hand = st.players[me].hand.cards;
    const mineInPlay = [st.players[me].active, ...st.players[me].bench].filter(l => l.cards.length);
    b.add('reach', 'me.accelSources', hand.filter(c => isTrainerCard(c) && ACCEL_TEXT.test(cardText(c))).length
      + mineInPlay.filter(l => l.getPokemonCard()?.powers.some(pw => ACCEL_TEXT.test(pw.text ?? ''))).length);
    b.add('reach', 'me.retreatHelpInHand', hand.some(c => isTrainerCard(c) && RETREAT_TEXT.test(cardText(c))) ? 1 : 0);
    // damage-counter abilities in play or in hand (benchable now), and the weakest opposing Pokémon
    const counterAbil = [...mineInPlay.map(l => l.getPokemonCard()), ...hand.filter(isPokemonCard)]
      .filter(pc => pc && (pc as PokemonCard).powers.some(pw => COUNTER_TEXT.test(pw.text ?? ''))).length;
    b.add('reach', 'me.counterAbilities', counterAbil);
    const opLists = [st.players[1 - me].active, ...st.players[1 - me].bench].filter(l => l.cards.length);
    const minHp = Math.min(999, ...opLists.map(l => l.getPokemonCard()!.hp + (l.hpBonus ?? 0) - l.damage));
    b.add('reach', 'op.minHpLeft', minHp === 999 ? 0 : minHp);
    b.add('reach', 'op.minHpLeftPrize', opLists.filter(l => l.getPokemonCard()!.hp + (l.hpBonus ?? 0) - l.damage === minHp).reduce((m, l) => Math.max(m, prizeValue(l.getPokemonCard())), 0));
    b.add('reach', 'me.gustInHand', hand.some(c => isTrainerCard(c) && GUST_TEXT.test(cardText(c))) ? 1 : 0);
    b.add('reach', 'me.switchInHand', hand.some(c => isTrainerCard(c) && SWITCH_TEXT.test(cardText(c))) ? 1 : 0);
  }

  const P = st.players[me];
  b.add('turn', 'turn', st.turn);
  b.add('turn', 'myTurn', st.activePlayer === me ? 1 : 0);
  b.add('turn', 'energyAttached', P.energyPlayedTurn === st.turn ? 1 : 0);
  b.add('turn', 'supporterPlayed', P.supporter.cards.length ? 1 : 0);
  b.add('turn', 'retreated', P.retreatedTurn === st.turn ? 1 : 0);
  b.add('turn', 'stadiumMine', st.players[me].stadium.cards.length ? 1 : 0);
  b.add('turn', 'stadiumTheirs', st.players[1 - me].stadium.cards.length ? 1 : 0);
  return { names: b.names, groups: b.groups, values: b.values };
}

void TrainerCard;
