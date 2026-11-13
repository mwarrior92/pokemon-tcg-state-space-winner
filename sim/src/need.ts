// Which cards a search looks at first.
//
// A card-choice prompt often has far more answers than a search can try ("search your deck for a
// card": about 25 different cards, 6 tried). The answers tried used to be a random sample, so the one
// card the board was waiting for was usually not among them: Festival Lead sat for six turns with
// three Dipplin, a Thwackey that finds any card each turn, and no Energy (runs/fl-investigate).
//
// cardNeed ranks cards by what the player's board can use right now, from rules facts only:
//   - an Evolution of a Pokémon in play, a Basic while the Bench has room;
//   - an Energy that pays part of an attack cost a Pokémon in play (or its Evolution in hand) still
//     lacks, more so when no such Energy is in hand;
//   - a Supporter or Stadium when the hand has none (a Stadium also when the player's is in play);
//   - less for every copy already in hand.
// It decides only the order in which answers are tried: the first few by need, the rest at random,
// and the search's own evaluation picks among them. Cards leaving the hand (discard costs, shuffling
// back) are tried in the opposite order: least needed first.
import { Card, CardType, ChooseCardsPrompt, EnergyCard, GameMessage, Player, PokemonCard, PokemonCardList, Stage, State, TrainerCard, TrainerType } from './engine';
import { energyGap } from './features';

function withEnergy(l: PokemonCardList, e: Card[]): PokemonCardList {
  return { energies: { cards: [...l.energies.cards, ...e] } } as unknown as PokemonCardList;
}

/** Does attaching `e` bring some attack of a Pokémon in play (or of its Evolution in hand) closer
 *  to payable, counting the Energy cards `held` as attached already? */
function paysSomething(p: Player, e: Card, held: Card[]): boolean {
  const evos = p.hand.cards.filter((c): c is PokemonCard => c instanceof PokemonCard && !!c.evolvesFrom);
  for (const l of [p.active, ...p.bench]) {
    const pc = l.getPokemonCard();
    if (!pc) {
      continue;
    }
    const attacks = [...pc.attacks, ...evos.filter(c => c.evolvesFrom === pc.name).flatMap(c => c.attacks)];
    for (const a of attacks) {
      if (energyGap(a.cost, withEnergy(l, [e])) < energyGap(a.cost, l) && energyGap(a.cost, withEnergy(l, held)) > 0) {
        return true;
      }
    }
  }
  return false;
}

/** How much `p`'s board can use `card` now (higher = tried first when searching for it). `inHand`:
 *  the card is one of the hand's (so one copy in hand is the card itself). */
export function cardNeed(state: State, p: Player, card: Card, inHand = false): number {
  const hand = p.hand.cards;
  const copies = hand.filter(c => c.name === card.name).length - (inHand ? 1 : 0);
  const dup = Math.pow(0.5, Math.max(0, copies));
  const inPlay = [p.active, ...p.bench].filter(l => l.cards.length);
  if (card instanceof PokemonCard) {
    if (card.stage === Stage.BASIC && !card.evolvesFrom) {
      const room = p.bench.some(b => !b.cards.length);
      return (room ? (inPlay.length <= 2 ? 3 : 2) : 0.3) * dup;
    }
    const targets = inPlay.filter(l => l.getPokemonCard()?.name === card.evolvesFrom).length;
    if (targets > 0) {
      return 3 * Math.pow(0.5, Math.max(0, copies - targets + 1));
    }
    // its pre-evolution is on the way (in hand), or it is the top of a line that is in play
    const below = hand.some(c => c.name === card.evolvesFrom) || inPlay.some(l => hand.some(c => c instanceof PokemonCard && c.evolvesFrom === l.getPokemonCard()?.name && c.name === card.evolvesFrom));
    const lineInPlay = card.stage === Stage.STAGE_2 && inPlay.some(l => (l.getPokemonCard() as any)?.name && hand.concat(p.deck.cards).some(c => c instanceof PokemonCard && c.name === card.evolvesFrom && c.evolvesFrom === l.getPokemonCard()!.name));
    return (below || lineInPlay ? 1.5 : 0.4) * dup;
  }
  if (card instanceof EnergyCard) {
    const held = hand.filter(c => c instanceof EnergyCard && c !== card);
    if (!paysSomething(p, card, [])) {
      return 0.5 * dup;
    }
    // useful at all; worth most when what is in hand does not already cover the same gap
    return paysSomething(p, card, held) ? 3 : 1.2 * dup;
  }
  if (card instanceof TrainerCard) {
    const sameKind = hand.filter(c => c instanceof TrainerCard && c.trainerType === card.trainerType && c !== card).length;
    if (card.trainerType === TrainerType.SUPPORTER) {
      return (sameKind === 0 ? 2 : 0.8) * dup;
    }
    if (card.trainerType === TrainerType.STADIUM) {
      const mine = p.stadium.cards[0];
      if (mine && mine.name === card.name) {
        return 0.2;
      }
      return (sameKind === 0 && !mine ? 2 : 0.8) * dup;
    }
    return (card.trainerType === TrainerType.TOOL ? 1 : 1.2) * dup;
  }
  return 1;
}

const LEAVING_HAND = new Set<string>([
  GameMessage.CHOOSE_CARD_TO_DISCARD, GameMessage.CHOOSE_CARD_TO_DECK, GameMessage.CHOOSE_CARD_TO_SHUFFLE, GameMessage.CHOOSE_CARDS_TO_RETURN_TO_PRIZES,
  GameMessage.CHOOSE_CARDS_TO_PUT_ON_TOP_OF_THE_DECK, GameMessage.CHOOSE_CARDS_TO_PUT_ON_BOTTOM_OF_THE_DECK, GameMessage.CHOOSE_CARD_TO_PUT_ON_BOTTOM,
  GameMessage.CHOOSE_ENERGIES_TO_DISCARD, GameMessage.CHOOSE_ENERGY_TO_DISCARD,
]);

/** Order the groups of interchangeable cards of a card-choice prompt (prompts.ts): the first
 *  `lead` by need (by least need for cards leaving the player's own hand), the rest as they came
 *  (shuffled). Prompts about another player's cards, or with nothing to rank, are left alone. */
export function orderByNeed(p: ChooseCardsPrompt, state: State, groups: number[][], lead: number): number[][] {
  const player = state.players.find(x => x.id === p.playerId);
  if (!player || groups.length <= 1 || p.message === GameMessage.CHOOSE_STARTING_POKEMONS) {
    return groups;
  }
  const cards = p.cards.cards;
  const own = p.cards === player.hand || p.cards === player.deck || p.cards === player.discard
    || cards.every(c => player.deck.cards.includes(c) || player.hand.cards.includes(c) || player.discard.cards.includes(c));
  if (!own) {
    return groups;
  }
  const fromHand = p.cards === player.hand;
  const leaving = fromHand && LEAVING_HAND.has(p.message);
  const scored = groups.map((g, i) => ({ g, i, need: cardNeed(state, player, cards[g[0]], fromHand) }));
  const ranked = scored.slice().sort((a, b) => (leaving ? a.need - b.need : b.need - a.need) || a.i - b.i);
  const head = ranked.slice(0, Math.max(1, lead));
  const taken = new Set(head.map(x => x.i));
  return [...head.map(x => x.g), ...scored.filter(x => !taken.has(x.i)).map(x => x.g)];
}

void CardType;
