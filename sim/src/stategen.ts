// Random, valid, mid-game board states between two decks.
//
// A state is a point at the start of the active player's turn, right after their draw: any turn
// from 2 on, any prize count that leaves the game unfinished, any board the rules allow. It is built
// by taking a real game set up by the engine (so players, cards and ids are genuine) and moving the
// same 120 card objects into new zones, which keeps every card accounted for. Rule constraints:
//   - evolved Pokémon only after the owner's first turn, along real evolution lines (Stage 2 on a
//     Basic only with a Rare Candy in the discard);
//   - prizes taken match the opponent's Knocked Out Pokémon in their discard (by prize value);
//   - attached Energy bounded by the owner's completed turns (one per turn, plus up to one extra per
//     turn for acceleration), tools at most one per Pokémon, damage below HP and only once the
//     opponent has had a turn;
//   - the deck holds no more than 60 - 7 opening - 6 prizes - turn draws, and at least one card.
// Nothing here prefers good or bad positions; choices are uniform within the rules, with the
// distributions documented next to each draw.
import { CardManager, CardList, Card, CheckHpEffect, EnergyCard, GamePhase, GameWinner, Player, PokemonCard, PokemonCardList, Stage, State, TrainerType } from './engine';
import { evolvesFromNames } from './cards';
import { checkInvariants } from './invariants';
import { isBasicPokemon, isEnergyCard, isPokemonCard, isTrainerCard, prizeValue } from './rules';
import { Rng } from './rng';
import { Sim, determinize, randomChooser, resolvePrompts } from './sim';

export interface GenOptions {
  /** inclusive range of the game turn number (turn 1 = first player's first turn) */
  turns?: [number, number];
  /** force the active player's index (0 or 1); random otherwise */
  active?: number;
}

export interface Generated {
  sim: Sim;
  info: {
    turn: number;
    active: number;
    prizesLeft: [number, number];
    inPlay: [number, number];
    hand: [number, number];
    deck: [number, number];
    discard: [number, number];
    attempts: number;
  };
}

// set-up games per deck pair, most recently used last; bounded, since a long run meets up to
// 37 x 37 pairs and each template is a full game
const templates = new Map<string, Sim>();
const MAX_TEMPLATES = 48;

function template(deckA: string[], deckB: string[]): Sim {
  const key = deckA.join('|') + '#' + deckB.join('|');
  let t = templates.get(key);
  if (t) {
    templates.delete(key);
  } else {
    const rng = new Rng(12345);
    t = Sim.newGame(deckA, deckB, rng);
    resolvePrompts(t, randomChooser(rng), rng);
    if (templates.size >= MAX_TEMPLATES) {
      templates.delete(templates.keys().next().value!);
    }
  }
  templates.set(key, t);
  return t;
}

/** A fresh Player with the same identity and the zone layout setup creates (6 prize slots,
 *  5 bench slots, public flags), all per-turn flags at their defaults. */
function freshPlayer(old: Player): Player {
  const p = new Player();
  p.id = old.id;
  p.name = old.name;
  p.deckId = old.deckId;
  p.prizes = [];
  for (let i = 0; i < 6; i++) {
    const l = new CardList();
    l.isSecret = true;
    p.prizes.push(l);
  }
  p.bench = [];
  for (let i = 0; i < 5; i++) {
    const b = new PokemonCardList();
    b.isPublic = true;
    p.bench.push(b);
  }
  p.active.isPublic = true;
  p.discard.isPublic = true;
  p.lostzone.isPublic = true;
  p.stadium.isPublic = true;
  p.supporter.isPublic = true;
  return p;
}

/** All cards a template player owns, detached from their zones. */
function collect(p: Player): Card[] {
  const out: Card[] = [];
  const take = (l: CardList) => {
    out.push(...l.cards);
    l.cards = [];
  };
  [p.deck, p.hand, p.discard, p.lostzone, p.stadium, p.supporter].forEach(take);
  p.prizes.forEach(take);
  for (const l of [p.active, ...p.bench]) {
    out.push(...l.cards);
    l.tools.forEach(t => {
      if (!out.includes(t)) {
        out.push(t);
      }
    });
  }
  return out;
}

class Pool {
  constructor(public cards: Card[], private rng: Rng) {}

  take(c: Card): Card {
    const i = this.cards.indexOf(c);
    if (i === -1) {
      throw new Error(`card not in pool: ${c?.fullName} (pool ${this.cards.length})`);
    }
    this.cards.splice(i, 1);
    return c;
  }

  find(pred: (c: Card) => boolean): Card | undefined {
    const xs = this.cards.filter(pred);
    return xs.length ? this.rng.pick(xs) : undefined;
  }

  /** A full evolution line ending in `top` (Basic first), taking the cards from the pool, or
   *  undefined when the lower stages are not in the pool. `allowCandy`: a Stage 2 may sit directly
   *  on its Basic when a Rare Candy can be put in the discard. */
  line(top: PokemonCard, allowCandy: boolean, discard: Card[]): PokemonCard[] | undefined {
    if (top.stage === Stage.BASIC) {
      return [this.take(top) as PokemonCard];
    }
    if (top.stage !== Stage.STAGE_1 && top.stage !== Stage.STAGE_2) {
      return undefined;   // VMAX / VSTAR / restored etc. are not generated
    }
    const below = this.cards.filter(c => c !== top && isPokemonCard(c) && c.name !== top.name
      && (c.name === top.evolvesFrom || evolvesFromNames(top.name).has(c.name))) as PokemonCard[];
    if (below.length) {
      const sub = this.rng.pick(below);
      const rest = this.line(sub, false, discard);
      if (rest && !this.cards.includes(top)) {
        throw new Error(`line: ${top.fullName} vanished while building [${rest.map(r => r.fullName).join(', ')}] from ${sub.fullName}`);
      }
      if (rest) {
        return [...rest, this.take(top) as PokemonCard];
      }
    }
    if (top.stage === Stage.STAGE_2 && allowCandy) {
      const roots = evolvesFromNames(top.evolvesFrom);
      const basic = this.cards.find(c => isBasicPokemon(c) && roots.has(c.name)) as PokemonCard | undefined;
      const candy = this.cards.find(c => c.name === 'Rare Candy');
      if (basic && candy) {
        discard.push(this.take(candy));
        return [this.take(basic) as PokemonCard, this.take(top) as PokemonCard];
      }
    }
    return undefined;
  }
}

/** Uniform integer in [lo, hi] but biased toward the low end (geometric-ish), for counts that are
 *  usually small (damage counters, attached energy, extra discards). */
function lowBiased(rng: Rng, lo: number, hi: number): number {
  if (hi <= lo) {
    return lo;
  }
  const u = rng.next();
  return lo + Math.floor((hi - lo + 1) * u * u);
}

export function generateState(deckA: string[], deckB: string[], rng: Rng, opts: GenOptions = {}): Generated {
  for (let attempt = 1; attempt <= 50; attempt++) {
    const g = tryGenerate(deckA, deckB, rng, opts);
    if (g) {
      g.info.attempts = attempt;
      return g;
    }
  }
  throw new Error('generateState: no valid state in 50 attempts');
}

export let lastRejections: string[] = [];

function tryGenerate(deckA: string[], deckB: string[], rng: Rng, opts: GenOptions): Generated | undefined {
  const sim = template(deckA, deckB).copy(rng.fork());
  const st: State = sim.state;
  const [tLo, tHi] = opts.turns ?? [2, 20];
  // turn: uniform over the range - every stage of the game is equally interesting for training
  const turn = rng.int(Math.max(2, tLo), Math.max(2, tHi));
  const active = opts.active ?? rng.int(0, 1);
  const first = turn % 2 === 1 ? active : 1 - active;
  const started = [0, 1].map(i => (i === first ? Math.ceil(turn / 2) : Math.floor(turn / 2)));
  // completed turns: the active player is at the start of a turn that has not happened yet
  const done = [0, 1].map(i => started[i] - (i === active ? 1 : 0));
  // turns on which a player could have attacked (the first player cannot attack on turn 1)
  const attackTurns = [0, 1].map(i => done[i] - (i === first && done[i] > 0 ? 1 : 0));

  const old = st.players;
  const pools = old.map(p => new Pool(collect(p), rng));
  const players = old.map(freshPlayer);

  // prizes taken by each player: 0..min(5, 3 per attacking turn), uniform
  const taken = [0, 1].map(i => rng.int(0, Math.min(5, 3 * Math.max(0, attackTurns[i]))));
  const discards: Card[][] = [[], []];

  // Knocked Out Pokémon: player q's discard holds lines worth exactly what the opponent has taken
  for (let q = 0; q < 2; q++) {
    let need = taken[1 - q];
    let guard = 0;
    while (need > 0 && guard++ < 40) {
      const tops = pools[q].cards.filter(c => isPokemonCard(c) && prizeValue(c as PokemonCard) <= need) as PokemonCard[];
      if (!tops.length) {
        break;
      }
      const top = rng.pick(tops);
      const line = pools[q].line(top, true, discards[q]);
      if (!line) {
        continue;
      }
      discards[q].push(...line);
      // energy it had attached went to the discard with it
      for (let e = lowBiased(rng, 0, 3); e > 0; e--) {
        const en = pools[q].find(isEnergyCard);
        if (en) {
          discards[q].push(pools[q].take(en));
        }
      }
      need -= prizeValue(top);
    }
    if (need !== 0) {
      taken[1 - q] -= need;   // could not build an exact match: fewer prizes taken
    }
  }

  for (let i = 0; i < 2; i++) {
    const p = players[i];
    const pool = pools[i];
    const canEvolve = done[i] >= 1;   // evolution is possible from the owner's 2nd turn
    // Pokémon in play: active + 0..5 benched, uniform count
    const want = 1 + rng.int(0, 5);
    const slots: PokemonCard[][] = [];
    for (let k = 0; k < want; k++) {
      const cands = pool.cards.filter(c => isPokemonCard(c) && (c.stage === Stage.BASIC
        || (canEvolve && (c.stage === Stage.STAGE_1 || c.stage === Stage.STAGE_2)))) as PokemonCard[];
      // the active spot must be filled; a candidate that fails to form a line is just skipped
      for (let tries = 0; tries < 8 && cands.length; tries++) {
        const top = rng.pick(cands);
        const line = pool.line(top, canEvolve, discards[i]);
        if (line) {
          slots.push(line);
          break;
        }
      }
    }
    if (!slots.length) {
      lastRejections.push('no Pokémon to put in play');
      return undefined;
    }
    // energy budget: completed turns (1 attachment each) + up to that many again from acceleration
    let energyBudget = done[i] === 0 ? 0 : rng.int(0, 2 * done[i]);
    const opponentHadTurn = done[1 - i] >= 1;
    slots.forEach((line, k) => {
      const l = k === 0 ? p.active : p.bench[k - 1];
      l.cards.push(...line);
      const top = line[line.length - 1];
      l.hp = top.hp;
      // played on one of the owner's earlier turns (game turn numbers of that player's turns)
      // (0 = placed during setup, before any turn)
      const ownTurnNumbers = done[i] === 0 ? [0] : Array.from({ length: done[i] }, (_, j) => (i === first ? 1 + 2 * j : 2 + 2 * j));
      l.pokemonPlayedTurn = rng.pick(ownTurnNumbers);
      const nE = Math.min(energyBudget, lowBiased(rng, 0, 4));
      for (let e = 0; e < nE; e++) {
        const en = pool.find(isEnergyCard) as EnergyCard | undefined;
        if (!en) {
          break;
        }
        pool.take(en);
        l.cards.push(en);
        l.energies.cards.push(en);
        energyBudget--;
      }
      if (done[i] >= 1 && rng.chance(0.25)) {
        const tool = pool.find(c => isTrainerCard(c) && c.trainerType === TrainerType.TOOL);
        if (tool) {
          l.tools.push(pool.take(tool));
        }
      }
      if (opponentHadTurn && top.hp > 10) {
        // damage counters: none half the time, else uniform below HP
        l.damage = rng.chance(0.5) ? 0 : 10 * rng.int(1, top.hp / 10 - 1);
      }
    });

    // prize cards still face down (set aside before anything else is drawn from the pool)
    const left = 6 - taken[i];
    if (pool.cards.length < left + 2) {
      lastRejections.push(`P${i + 1}: not enough cards left for prizes, hand and deck`);
      return undefined;
    }
    for (let k = 0; k < left; k++) {
      p.prizes[k].cards.push(pool.take(rng.pick(pool.cards)));
    }

    // discard: the KO'd lines, Supporters (at most one per completed turn) and other used cards,
    // always leaving at least 2 cards for hand and deck
    const disc = discards[i];
    const room = () => Math.max(0, pool.cards.length - 2);
    const supporters = pool.cards.filter(c => isTrainerCard(c) && c.trainerType === TrainerType.SUPPORTER);
    rng.sample(supporters, Math.min(room(), lowBiased(rng, 0, done[i]))).forEach(c => disc.push(pool.take(c)));
    const other = pool.cards.filter(c => !(isTrainerCard(c) && c.trainerType === TrainerType.SUPPORTER));
    rng.sample(other, Math.min(room(), lowBiased(rng, 0, 4 * done[i]))).forEach(c => disc.push(pool.take(c)));
    p.discard.cards.push(...disc);
  }

  // stadium: none 60%, else one from either player's remaining cards
  if (rng.chance(0.4)) {
    const owners = [0, 1].filter(i => pools[i].cards.some(c => isTrainerCard(c) && c.trainerType === TrainerType.STADIUM));
    if (owners.length) {
      const o = rng.pick(owners);
      const sc = pools[o].find(c => isTrainerCard(c) && c.trainerType === TrainerType.STADIUM)!;
      players[o].stadium.cards.push(pools[o].take(sc));
    }
  }

  // hand and deck from what is left. Deck limit: 60 - 7 opening - 6 prizes set aside - turn draws
  // (the first player skips the draw on turn 1).
  for (let i = 0; i < 2; i++) {
    const p = players[i];
    const pool = pools[i];
    const draws = started[i] - (i === first ? 1 : 0);
    const maxDeck = 60 - 7 - 6 - draws;
    rng.shuffle(pool.cards);
    // hand: uniform 1..10 for the player to move (they just drew), 0..10 for the other
    let hand = rng.int(i === active ? 1 : 0, 10);
    hand = Math.max(hand, pool.cards.length - maxDeck);
    if (pool.cards.length - hand < 1) {
      hand = pool.cards.length - 1;
    }
    if (hand < (i === active ? 1 : 0)) {
      lastRejections.push(`P${i + 1}: no card left for the hand`);
      return undefined;
    }
    p.hand.cards.push(...pool.cards.splice(0, hand));
    p.deck.cards.push(...pool.cards.splice(0));
  }

  st.players = players;
  st.turn = turn;
  st.activePlayer = active;
  st.phase = GamePhase.PLAYER_TURN;
  st.winner = GameWinner.NONE;
  st.prompts = [];
  st.logs = [];
  st.lastAttack = null;
  st.playerLastAttack = {};
  st.skipOpponentTurn = false;
  players.forEach(p => {
    p.canEvolve = turn > 2;
  });

  const errs = checkInvariants(st, { settled: true });
  if (errs.length) {
    lastRejections.push(...errs);
    return undefined;
  }
  // the engine caches HP modifiers (tools, stadiums, abilities) in hpBonus and refreshes them on
  // every HP check; a fresh state must start with them computed, as after any engine step
  for (const p of players) {
    for (const l of [p.active, ...p.bench]) {
      if (l.cards.length) {
        sim.store.reduceEffect(st, new CheckHpEffect(p, l));
        // damage was drawn against printed HP; an HP-lowering effect can leave it at or above the
        // effective HP (the Pokémon would already be Knocked Out): keep it below
        const hp = l.getPokemonCard()!.hp + (l.hpBonus ?? 0);
        if (hp <= 0) {
          lastRejections.push(`${l.getPokemonCard()!.name}: effective HP ${hp}`);
          return undefined;
        }
        if (l.damage >= hp) {
          l.damage = Math.floor((hp - 1) / 10) * 10;
        }
      }
    }
  }
  // fixed hidden information for the turn being tested (see Sim.chanceSeed)
  const chanceSeed = rng.int(0, 0x7fffffff);
  if (!process.env.RANDOM_SHUFFLES) {
    determinize(sim, chanceSeed);
  }
  return {
    sim,
    info: {
      turn,
      active,
      prizesLeft: [6 - taken[0], 6 - taken[1]] as [number, number],
      inPlay: players.map(p => [p.active, ...p.bench].filter(l => l.cards.length).length) as [number, number],
      hand: players.map(p => p.hand.cards.length) as [number, number],
      deck: players.map(p => p.deck.cards.length) as [number, number],
      discard: players.map(p => p.discard.cards.length) as [number, number],
      attempts: 0,
    },
  };
}

export { CardManager };
