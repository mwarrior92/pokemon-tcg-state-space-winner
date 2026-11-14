// The clock: how many of its own turns a player still needs to win, along the shortest path that is
// likely to work out.
//
// The prize race (planner.ts) looks one turn ahead on each side and adds tie-breaks for what is in
// play. Nothing in it says how far the win is, so a turn that brought the win no closer (a fourth
// engine piece with no Energy in play, Boss's Orders with no attack to follow) could look as good as
// one that did. The clock values a position by the win itself, kept coarse so it can run at every
// position of a turn search:
//
//   - A path is one attack of one Pokémon in play (or of an Evolution of it), used every turn from
//     the turn it is ready until the last Prize card is taken.
//   - Ready needs the Energy the attack still lacks (one attachment a turn, two with an Ability in
//     play that attaches Energy) and, for an Evolution,
//     the card. What is in play is certain; a card in hand is there when wanted with chance HELD; a
//     card still in the deck has shown up by turn t with the chance of seeing it among SEEN cards a
//     turn. The opponent's hand is not known: its hand and deck are one pool, and the cards in hand
//     count as that many cards seen. From these the path's expected ready turn.
//   - A path whose chance to be ready within two turns of its earliest turn is under MIN_P is not
//     followed at all.
//   - Hits: attacks needed to Knock Out the opponent's Pokémon in play, fewest attacks per prize
//     first, until the remaining Prize cards are taken (more like their average if they run out). An opponent with nothing on the Bench loses to the
//     first Knock Out unless it finds a Basic.
//   - The attacker lasts until the other side's best path has Knocked it Out; if that comes before
//     the last prize, the best path on another Pokémon takes over when it is ready (none: HORIZON).
//     A card in hand counts for one path only: the second path gets what the first leaves.
//
// Not modelled: Energy acceleration from Trainers, Rare Candy, gust cards, effects of attacks other
// than damage to the Active, the opponent's Energy for attacks that count both Active Pokémon's. The turn search plays those for real when they are within reach.
import { Card, EnergyCard, CardType, Player, PokemonCard, PokemonCardList, Stage } from './engine';
import { ACCEL_TEXT, SWITCH_TEXT, baseDamage, energyGap, estimateDamage } from './features';
import { prizeValue, prizesLeft } from './rules';
import { Sim } from './sim';
import { on } from './variant';

export const HORIZON = 8;   // turns looked ahead; a longer path counts as this long
const SEEN = 2.5;           // cards of its deck a player sees in a turn (the draw, search and draw cards)
const HELD = 0.9;           // chance a card in hand is still there when it is wanted (if not: a turn later)
const MIN_P = 0.3;          // paths less likely than this to be ready soon are not followed

interface PathOption {
  list: PokemonCardList;
  card: PokemonCard;        // the attacker (the Pokémon in play, or its Evolution)
  attack: string;
  base: number;             // damage before Weakness and Resistance
  ready: number;            // expected turn (1 = the player's next turn) the attack is first used
  hits: number;             // attacks needed to take every remaining Prize card
  turns: number;            // ready + hits - 1
  uses: Card[];             // the cards in hand it counts on
}

export interface Clock {
  turns: number;            // expected own turns to the win, 0 .. HORIZON + 4
  best?: PathOption;
  second?: PathOption;      // best path on another Pokémon
}

const SELF_ONLY = /to this Pok[ée]mon/i;
/** damage an attack adds for each Energy attached to its own Pokémon (0: it does not grow with Energy) */
const perEnergy = (text: string): number => {
  const m = /(\d+) (?:more )?damage (?:for each|times the (?:amount|number) of) (?:[^.]{0,30}?)Energy (?:cards? )?attached to (?:this Pok[ée]mon|both Active)/i.exec(text);
  return m ? Number(m[1]) : 0;
};

const withEnergy = (l: PokemonCardList, e: Card[]): PokemonCardList =>
  (e.length ? { energies: { cards: [...l.energies.cards, ...e] } } as unknown as PokemonCardList : l);

/** chance of at least `r` of `k` wanted cards among `n` cards seen from `size` (binomial, coarse) */
function seenBy(n: number, k: number, size: number, r = 1): number {
  if (r <= 0) {
    return 1;
  }
  if (k < r || size <= 0) {
    return 0;
  }
  const p = Math.min(1, k / size);
  if (r === 1) {
    return 1 - Math.pow(1 - p, n);
  }
  const m = Math.max(r, Math.round(n));
  let miss = 0, c = 1;
  for (let i = 0; i < r; i++) {
    miss += c * Math.pow(p, i) * Math.pow(1 - p, m - i);
    c = c * (m - i) / (i + 1);
  }
  return Math.max(0, 1 - miss);
}

/** what `side` can count on: `hand` (known cards; empty for a hidden hand) and the pool the rest
 *  comes from, of which `seen0` cards are in the hidden hand already */
function sources(p: Player, known: boolean): { hand: Card[]; pool: Card[]; seen0: number } {
  return known ? { hand: p.hand.cards, pool: p.deck.cards, seen0: 0 } : { hand: [], pool: [...p.hand.cards, ...p.deck.cards], seen0: p.hand.cards.length };
}

const hpLeft = (l: PokemonCardList, pc: PokemonCard): number => Math.max(10, pc.hp + (l.hpBonus ?? 0) - l.damage);

/** Every path of `side` likely enough to follow, with its ready turn (hits are filled in by clock). */
function paths(s: Sim, side: number, known: boolean, spent: Card[] = []): PathOption[] {
  const p = s.state.players[side];
  const src = sources(p, known);
  // (cards in hand another path counts on are not there for this one)
  const hand = src.hand.filter(c => !spent.includes(c)), { pool, seen0 } = src;
  const seen = (t: number) => seen0 + SEEN * t;
  const out: PathOption[] = [];
  // Energy attachments a turn: two with an Ability in play that attaches Energy, else one. An Ability
  // that attaches "to this Pokémon" (Teal Dance) counts for its own Pokémon only: counted for all, it
  // made Tapu Bulu's four-Energy attack look two turns away and took Teal Mask Ogerpon ex out of the
  // Active Spot on the first turn.
  const accel = (l: PokemonCardList) => (l.getPokemonCard()?.powers ?? []).filter(pw => ACCEL_TEXT.test(pw.text ?? ''));
  const accelAny = [p.active, ...p.bench].some(l => accel(l).some(pw => !SELF_ONLY.test(pw.text ?? '')));
  const perTurnOf = (l: PokemonCardList) => (accelAny || accel(l).length ? 2 : 1);
  // Bench position ('benchpos', variant.ts): a Benched attacker has to get to the Active Spot, so the
  // Energy the Active still lacks for its Retreat Cost counts as attachments the path needs, taken from
  // the hand's Energy the attack does not use or drawn (none with a switch card in hand). Without it
  // every Energy went to the Benched attacker and none to an Active that could not retreat: Teal Mask
  // Ogerpon ex and Yveltal stood ready on the Bench for turns (first attack 0.8 of a turn later for
  // Hydrapple, 0.65 for N's Zoroark; runs/vs-clock4*).
  const apc = p.active.getPokemonCard();
  const switchHeld = hand.some(c => !(c instanceof PokemonCard) && !(c instanceof EnergyCard) && SWITCH_TEXT.test((c as { text?: string }).text ?? ''));
  const stuck = on('benchpos') && apc && !switchHeld ? energyGap(apc.retreat, p.active) : 0;
  const evoNames = (from: string): PokemonCard[] => {
    const byName = new Map<string, PokemonCard>();
    for (const c of [...hand, ...pool]) {
      if (c instanceof PokemonCard && c.evolvesFrom === from && !byName.has(c.name)) {
        byName.set(c.name, c);
      }
    }
    return [...byName.values()];
  };
  // chance the card named is at hand by turn t
  const cardBy = (name: string) => {
    const inHand = hand.find(c => c.name === name);
    if (inHand) {
      return { held: [inHand], by: () => 1 };
    }
    const k = pool.filter(c => c.name === name).length;
    return { held: [] as Card[], by: (t: number) => seenBy(seen(t), k, pool.length) };
  };
  for (const l of [p.active, ...p.bench]) {
    const pc = l.getPokemonCard();
    if (!pc) {
      continue;
    }
    // the Pokémon as it is, its Evolutions (from the next turn) and theirs (a turn later)
    const forms: { card: PokemonCard; from: number; held: Card[]; have: (t: number) => number }[] = [{ card: pc, from: 1, held: [], have: () => 1 }];
    for (const e1 of evoNames(pc.name)) {
      const h1 = cardBy(e1.name);
      forms.push({ card: e1, from: 1, held: h1.held, have: h1.by });
      if (e1.stage === Stage.STAGE_1) {
        for (const e2 of evoNames(e1.name)) {
          const h2 = cardBy(e2.name);
          forms.push({ card: e2, from: 2, held: [...h1.held, ...h2.held], have: t => h1.by(t - 1) * h2.by(t) });
        }
      }
    }
    for (const f of forms) {
      for (const a of f.card.attacks) {
        const perTurn = perTurnOf(l);
        // an attack that does more for each Energy attached counts with the Energy it will have: its
        // cost paid and one more turn's attachments (measured now, with one Energy or none, Myriad
        // Leaf Shower needed 7.5 attacks to win and was never the path)
        const now = l.energies.cards.length, then = Math.max(now, a.cost.length) + perTurn;
        const inc = perEnergy(a.text ?? '');
        const printed = (a as { damageCalculation?: string }).damageCalculation === 'x' ? 0 : a.damage;
        const base = f.card === pc ? baseDamage(s, side, l, a) + inc * (then - now) : (inc ? printed + inc * then : a.damage);
        if (!(base > 0)) {
          continue;
        }
        // Energy: what is attached, then what the hand holds, then what has to be drawn
        const gap = energyGap(a.cost, l);
        const held: Card[] = [];
        for (const c of hand) {
          if (held.length < gap && c instanceof EnergyCard && energyGap(a.cost, withEnergy(l, [...held, c])) < energyGap(a.cost, withEnergy(l, held))) {
            held.push(c);
          }
        }
        const fromHand = withEnergy(l, held);
        const lack = energyGap(a.cost, fromHand);
        const k = lack > 0 ? pool.filter(c => c instanceof EnergyCard && energyGap(a.cost, withEnergy(fromHand, [c])) < lack).length : 0;
        const away = l === p.active ? 0 : stuck;
        const first = Math.max(1, Math.ceil((gap + away) / perTurn), f.from);
        const spare = away ? hand.filter(c => c instanceof EnergyCard && !held.includes(c)).slice(0, away) : [];
        const outLack = away - spare.length, anyEnergy = outLack > 0 ? pool.filter(c => c instanceof EnergyCard).length : 0;
        const energy = (t: number) => (lack > 0 ? seenBy(seen(t), k, pool.length, lack) : 1) * (outLack > 0 ? seenBy(seen(t), anyEnergy, pool.length, outLack) : 1);
        const at = (t: number) => (t < first ? 0 : f.have(t) * energy(t));
        if (at(first + 2) < MIN_P) {
          continue;
        }
        // expected turn = sum over t of the chance it is not ready by t
        // (each card it needs from the hand may be gone by then: a turn's delay with chance 1 - HELD)
        let ready = (1 - HELD) * (f.held.length + held.length + spare.length), sofar = 0;
        for (let t = 0; t < HORIZON; t++) {
          sofar = Math.max(sofar, at(t));
          ready += 1 - sofar;
        }
        out.push({ list: l, card: f.card, attack: a.name, base, ready, hits: 0, turns: 0, uses: [...f.held, ...held] });
      }
    }
  }
  return out;
}

/** attacks `o` needs to take the `prizes` its player has left */
function hitsToWin(s: Sim, o: PathOption, defender: number, prizes: number, defenderKnown: boolean): number {
  const d = s.state.players[defender];
  const need = (l: PokemonCardList): { hits: number; prize: number } | undefined => {
    const pc = l.getPokemonCard();
    if (!pc) {
      return undefined;
    }
    const dmg = estimateDamage(o.card, o.base, pc);
    return { hits: dmg > 0 ? Math.min(HORIZON, Math.ceil(hpLeft(l, pc) / dmg)) : HORIZON, prize: prizeValue(pc) };
  };
  const act = need(d.active);
  if (!act) {
    return 1;
  }
  const bench = d.bench.map(need).filter((x): x is { hits: number; prize: number } => !!x);
  // the Pokémon in play, fewest attacks per prize first, whichever is Active now (so moving one into
  // the Active Spot changes nothing unless the attack follows); past those, more like their average
  const all = [act, ...bench].sort((x, y) => x.hits / x.prize - y.hits / y.prize);
  const mean = { hits: all.reduce((x, b) => x + b.hits, 0) / all.length, prize: all.reduce((x, b) => x + b.prize, 0) / all.length };
  let full = 0, left = prizes;
  for (const t of all) {
    if (left <= 0) {
      break;
    }
    full += t.hits;
    left -= t.prize;
  }
  if (left > 0) {
    full += Math.ceil(left / mean.prize - 1e-9) * mean.hits;
  }
  if (bench.length) {
    return full;
  }
  // nothing on the Bench: the first Knock Out wins unless a Basic comes down first
  const isBasic = (c: Card) => c instanceof PokemonCard && c.stage === Stage.BASIC;
  const finds = defenderKnown
    ? (d.hand.cards.some(isBasic) ? 0.95 : seenBy(SEEN, d.deck.cards.filter(isBasic).length, d.deck.cards.length))
    : seenBy(d.hand.cards.length + SEEN, [...d.hand.cards, ...d.deck.cards].filter(isBasic).length, d.hand.cards.length + d.deck.cards.length);
  return finds * full + (1 - finds) * act.hits;
}

/** The clocks of both players in a position where it is `toMove`'s turn (or about to be). `me`'s
 *  hand is known, the other's is not. Returns [clock of player 0, clock of player 1]. */
export function clocks(s: Sim, me: number, toMove: number): [Clock, Clock] {
  const rate = (side: number, spent: Card[] = []) => {
    const prizes = prizesLeft(s.state.players[side]);
    const opts = paths(s, side, side === me, spent);
    for (const o of opts) {
      o.hits = hitsToWin(s, o, 1 - side, prizes, 1 - side === me);
      o.turns = o.ready + o.hits - 1;
    }
    opts.sort((a, b) => a.turns - b.turns);
    return opts;
  };
  const raw = [0, 1].map(side => rate(side));
  const out = [0, 1].map((side): Clock => {
    if (prizesLeft(s.state.players[side]) === 0) {
      return { turns: 0 };
    }
    const best = raw[side][0];
    if (!best) {
      return { turns: HORIZON + 4 };
    }
    const second = (best.uses.length ? rate(side, best.uses) : raw[side]).find(o => o.list !== best.list);
    // how many attacks the attacker makes before the other side's best path Knocks it Out
    const foe = raw[1 - side][0];
    let attacks = Infinity;
    if (foe) {
      const hp = best.card === best.list.getPokemonCard() ? hpLeft(best.list, best.card) : Math.max(10, best.card.hp - best.list.damage);
      const dmg = estimateDamage(foe.card, foe.base, best.card);
      if (dmg > 0) {
        // the foe's k-th hit lands on its turn foe.ready + k - 1; the player to move takes each turn first
        const dies = foe.ready + Math.ceil(hp / dmg) - 1;
        attacks = Math.max(0, dies - best.ready + (side === toMove ? 1 : 0));
      }
    }
    let turns = best.turns;
    if (attacks < best.hits) {
      const r2 = second ? second.ready : HORIZON;
      turns = Math.max(best.ready + attacks, r2) + (best.hits - attacks) - 1;
    }
    return { turns: Math.min(HORIZON + 4, turns), best, second };
  });
  return out as [Clock, Clock];
}

/** `me`'s turns to its win along its best path alone: no opponent, no Knock Out of the attacker. */
export function ownClock(s: Sim, me: number): number {
  const prizes = prizesLeft(s.state.players[me]);
  if (prizes === 0) {
    return 0;
  }
  let best = HORIZON + 4;
  for (const o of paths(s, me, true)) {
    best = Math.min(best, o.ready + hitsToWin(s, o, 1 - me, prizes, false) - 1);
  }
  return best;
}

// SIM_CLOCK_MODE=race: both players' clocks with the attacker's Knock Out (clocks). Measured at 52%
// and 54% of 180 games against the pilot without the clock (runs/vs-clock, vs-clock2), with later
// first attacks: the opponent's clock and the Knock Out step moved by a whole turn for a gust card
// or a Tool. The default counts the mover's own path only.
const RACE = process.env.SIM_CLOCK_MODE === 'race';

/** `me`'s standing on the clock, in turns (higher is better): minus its own turns to the win, or
 *  in race mode the opponent's turns less `me`'s. */
export function clockLead(s: Sim, me: number): number {
  if (!RACE) {
    return -ownClock(s, me);
  }
  const c = clocks(s, me, s.state.activePlayer);
  return c[1 - me].turns - c[me].turns;
}

export function describeClock(c: Clock): string {
  const o = (x?: PathOption) => (x ? `${x.card.name} ${x.attack} ready ${x.ready.toFixed(1)} hits ${x.hits.toFixed(1)}` : 'none');
  return `${c.turns.toFixed(1)} turns (${o(c.best)}; then ${o(c.second)})`;
}

void CardType;
