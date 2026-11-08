// Small rule facts used by the generator, invariants and features. Rules only - no play advice.
import { Card, CardList, CardTag, EnergyCard, Player, PokemonCard, PokemonCardList, Stage, State, SuperType, TrainerCard } from './engine';

/** Prize cards a Knock Out of this (top) Pokémon is worth, as the engine computes it. */
export function prizeValue(card: PokemonCard | undefined): number {
  if (!card) {
    return 1;
  }
  const t = card.tags;
  let n = 1;
  if (t.includes(CardTag.POKEMON_EX) || t.includes(CardTag.POKEMON_V) || t.includes(CardTag.POKEMON_VSTAR)
    || t.includes(CardTag.POKEMON_ex) || t.includes(CardTag.POKEMON_GX)) {
    n += 1;
  }
  if (t.includes(CardTag.POKEMON_SV_MEGA) || t.includes(CardTag.TAG_TEAM) || t.includes(CardTag.DUAL_LEGEND)) {
    n += 1;
  }
  if (t.includes(CardTag.POKEMON_VMAX) || t.includes(CardTag.POKEMON_VUNION)) {
    n += 2;
  }
  return n;
}

/** Index (0/1) of the player who took the first turn of the game, given who is active on `turn`. */
export function firstPlayer(state: State): number {
  return state.turn % 2 === 1 ? state.activePlayer : 1 - state.activePlayer;
}

/** Turns player `i` has started so far (the current turn counts for the active player). */
export function turnsStarted(state: State, i: number): number {
  return i === firstPlayer(state) ? Math.ceil(state.turn / 2) : Math.floor(state.turn / 2);
}

export function isPokemonCard(c: Card): c is PokemonCard {
  return c.superType === SuperType.POKEMON;
}

export function isEnergyCard(c: Card): c is EnergyCard {
  return c.superType === SuperType.ENERGY;
}

export function isTrainerCard(c: Card): c is TrainerCard {
  return c.superType === SuperType.TRAINER;
}

export function isBasicPokemon(c: Card): c is PokemonCard {
  return isPokemonCard(c) && c.stage === Stage.BASIC;
}

export function inPlayLists(p: Player): PokemonCardList[] {
  return [p.active, ...p.bench].filter(l => l.cards.length > 0);
}

export function prizesLeft(p: Player): number {
  return p.prizes.reduce((s, l) => s + l.cards.length, 0);
}

/** Every card a player owns, wherever it is (deck, hand, discard, lost zone, prizes, in play,
 *  attached tools, played-supporter zone, their stadium, cards stored under other cards). */
export function ownedCards(state: State, i: number): Card[] {
  const p = state.players[i];
  const out: Card[] = [];
  const addList = (l: CardList | undefined) => l?.cards.forEach(c => out.push(c));
  addList(p.deck);
  addList(p.hand);
  addList(p.discard);
  addList(p.lostzone);
  addList(p.stadium);
  addList(p.supporter);
  p.prizes.forEach(addList);
  for (const l of [p.active, ...p.bench]) {
    addList(l);
    (l.tools ?? []).forEach(c => {
      if (!l.cards.includes(c)) {
        out.push(c);
      }
    });
  }
  return out;
}
