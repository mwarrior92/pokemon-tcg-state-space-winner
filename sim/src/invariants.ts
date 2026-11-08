// Board invariants: things that hold in every legal, settled state. Used by the state generator (as
// its validator), by the card tests, and by the search as a corruption guard.
import { evolvesFromNames } from './cards';
import { GamePhase, PokemonCard, Stage, State } from './engine';
import { inPlayLists, isEnergyCard, isPokemonCard, ownedCards, prizesLeft } from './rules';

export interface InvariantOptions {
  deckSize?: number;          // cards each player owns (60)
  settled?: boolean;          // no pending prompt, damage below HP, game not over
}

export function checkInvariants(state: State, opts: InvariantOptions = {}): string[] {
  const errs: string[] = [];
  const deckSize = opts.deckSize ?? 60;
  const owner = new Map<any, number>();

  state.players.forEach((p, i) => {
    const cards = ownedCards(state, i);
    if (cards.length !== deckSize) {
      errs.push(`P${i + 1} owns ${cards.length} cards, expected ${deckSize}`);
    }
    for (const c of cards) {
      if (owner.has(c)) {
        errs.push(`card ${c.fullName} is in two places (P${owner.get(c)! + 1} and P${i + 1})`);
      }
      owner.set(c, i);
    }
    if (p.prizes.some(l => l.cards.length > 1)) {
      errs.push(`P${i + 1} has a prize slot holding more than one card`);
    }
    if (prizesLeft(p) > 6) {
      errs.push(`P${i + 1} has ${prizesLeft(p)} prize cards`);
    }

    const lists = [p.active, ...p.bench];
    lists.forEach((l, k) => {
      if (l.cards.length === 0) {
        if (l.energies.cards.length || l.tools.length || l.damage) {
          errs.push(`P${i + 1} empty slot ${k} still has energy/tools/damage`);
        }
        return;
      }
      const where = `P${i + 1} ${k === 0 ? 'active' : 'bench' + (k - 1)}`;
      const mons = l.getPokemons();
      if (mons.length === 0) {
        errs.push(`${where} has cards but no Pokémon`);
        return;
      }
      for (const e of l.energies.cards) {
        if (!l.cards.includes(e)) {
          errs.push(`${where}: energy ${e.fullName} listed as attached but not in the card list`);
        }
      }
      for (const c of l.cards) {
        if (isEnergyCard(c) && !l.energies.cards.includes(c) && !mons.includes(c as any)) {
          errs.push(`${where}: energy ${c.fullName} in the stack but not attached as energy`);
        }
      }
      const top = mons[mons.length - 1] as PokemonCard;
      if (l.tools.length > Math.max(1, (top as any).maxTools ?? 1)) {
        errs.push(`${where}: ${l.tools.length} tools`);
      }
      if (l.damage < 0 || l.damage % 10 !== 0) {
        errs.push(`${where}: damage ${l.damage}`);
      }
      if (opts.settled && top.hp > 0 && l.damage >= top.hp + (l.hpBonus ?? 0)) {
        errs.push(`${where}: ${top.name} has ${l.damage} damage with ${top.hp} HP (should have been Knocked Out)`);
      }
      // each Pokémon in the stack evolves from the one below it (Rare Candy may skip Stage 1)
      for (let j = 1; j < mons.length; j++) {
        const below = mons[j - 1];
        const cur = mons[j] as PokemonCard;
        const ok = cur.evolvesFrom === below.name
          || ((cur as any).evolvesFromBase ?? []).includes(below.name)
          || (isPokemonCard(below) && rareCandySkip(cur, below));
        if (!ok) {
          errs.push(`${where}: ${cur.name} sits on ${below.name} but evolves from ${cur.evolvesFrom || '(nothing)'}`);
        }
      }
    });
    if (inPlayLists(p).length > 0 && p.active.cards.length === 0 && opts.settled) {
      errs.push(`P${i + 1} has Pokémon on the bench but no active Pokémon`);
    }
  });

  const stadiums = state.players.reduce((s, p) => s + p.stadium.cards.length, 0);
  if (stadiums > 1) {
    errs.push(`${stadiums} stadiums in play`);
  }

  if (opts.settled) {
    if (state.prompts.some(p => p.result === undefined)) {
      errs.push('a prompt is pending');
    }
    if (state.phase === GamePhase.FINISHED) {
      errs.push('game is over');
    } else {
      state.players.forEach((p, i) => {
        if (p.active.cards.length === 0) {
          errs.push(`P${i + 1} has no active Pokémon`);
        }
        if (prizesLeft(p) === 0) {
          errs.push(`P${i + 1} has no prizes left (should have won)`);
        }
      });
    }
  }
  return errs;
}

/** Stage 2 placed directly on its Basic (Rare Candy): the Basic must be what the Stage 2's
 *  Stage 1 evolves from. */
function rareCandySkip(cur: PokemonCard, below: PokemonCard): boolean {
  return cur.stage === Stage.STAGE_2 && below.stage === Stage.BASIC && evolvesFromNames(cur.evolvesFrom).has(below.name);
}
