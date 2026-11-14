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
import { on } from './variant';

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

/** How well `p`'s own Energy cards (deck, hand, discard pile and in play; the player knows the list)
 *  can pay `cost`: 1 if they pay it three times over, 0.75 twice, 0.5 once, 0.15 not even once. A
 *  deck of many types holds attacks it can hardly ever pay for (Basic Box: Chien-Pao's needs two of
 *  its one Water Energy, Latias ex's two of its three Psychic); Energy and searches spent on those
 *  are spent on nothing. */
export function costSupply(p: Player, cost: CardType[]): number {
  if (!cost.length || !on('supply')) {
    return 1;
  }
  const all: Card[] = [];
  for (const list of [p.deck.cards, p.hand.cards, p.discard.cards, ...[p.active, ...p.bench].map(l => l.energies.cards)]) {
    for (const c of list) {
      if (c instanceof EnergyCard) {
        all.push(c);
      }
    }
  }
  const pool = { energies: { cards: all } } as unknown as PokemonCardList;
  const pays = (k: number) => energyGap(Array.from({ length: k }, () => cost).flat(), pool) === 0;
  return pays(3) ? 1 : pays(2) ? 0.75 : pays(1) ? 0.5 : 0.15;
}

/** How much Energy `e` on `p`'s Pokémon `l` brings an attack nearer, counting `extra` as attached to
 *  it already: for the attack it helps most, the attack's weight (its printed damage; attacks that
 *  print little count as a modest one) over 1 + the Energy still missing afterwards. An attack of
 *  its Evolution in hand counts a little less, one the deck's Energy can hardly pay less (costSupply), a damaged Pokémon less (its Energy goes with it), the
 *  Active a little more. 0 if the Energy pays for nothing there. */
export function attachNeed(p: Player, l: PokemonCardList, e: Card, extra: Card[] = []): number {
  const pc = l.getPokemonCard();
  if (!pc) {
    return 0;
  }
  const before = withEnergy(l, extra), after = withEnergy(l, [...extra, e]);
  const evos = p.hand.cards.filter((c): c is PokemonCard => c instanceof PokemonCard && c.evolvesFrom === pc.name);
  let best = 0;
  const consider = (attacks: PokemonCard['attacks'], k: number) => {
    for (const a of attacks) {
      const left = energyGap(a.cost, after);
      if (left < energyGap(a.cost, before)) {
        best = Math.max(best, k * costSupply(p, a.cost) * Math.min(3, Math.max(0.6, a.damage / 100)) / (1 + left));
      }
    }
  };
  consider(pc.attacks, 1);
  evos.forEach(c => consider(c.attacks, 0.7));
  const hp = pc.hp + (l.hpBonus ?? 0);
  return best * (0.4 + 0.6 * Math.max(0, hp - l.damage) / Math.max(1, hp)) * (l === p.active ? 1.1 : 1);
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
      // among Basics, those with an attack the deck's Energy can pay for come first
      const fit = card.attacks.reduce((m, a) => Math.max(m, costSupply(p, a.cost) * Math.min(1, Math.max(0.3, a.damage / 150))), 0);
      return (room ? (inPlay.length <= 2 ? 3 : 2) : 0.3) * dup * (0.6 + 0.4 * fit);
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
