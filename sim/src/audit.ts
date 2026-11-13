// Turn audit: what a pilot left undone at the end of its turn. Rules facts only (no play advice):
// each flag is a free resource the turn did not use, the kind of omission a human rarely makes.
// Rates per deck (cli/pilotaudit.ts) show where a pilot's play is weakest, and a pilot change can be
// measured on them much faster than on win rates.
//
//   attacked        the turn ended with an attack
//   idleAttack      no attack, although the Active could have attacked (the engine accepts it)
//   energyHeld      an Energy card left in hand with the turn's attachment unused
//   supporterHeld   a Supporter left in hand and none played (not on the first player's first turn)
//   stadiumHeld     a Stadium left in hand while no Stadium of the mover's is in play
//   basicHeld       a Basic Pokémon left in hand with a free Bench space
//   evolutionHeld   an Evolution left in hand that could have been played (the engine accepts it)
//   emptyBench      the turn ended with no Benched Pokémon
//   powerless       the turn ended with no Pokémon in play able to pay for any of its attacks
import { EnergyCard, PokemonCard, Stage, TrainerCard, TrainerType } from './engine';
import { energyGap } from './features';
import { Sim, legalMainOptions } from './sim';

export interface TurnAudit {
  attacked: boolean;
  idleAttack: boolean;
  energyHeld: boolean;
  supporterHeld: boolean;
  stadiumHeld: boolean;
  basicHeld: boolean;
  evolutionHeld: boolean;
  emptyBench: boolean;
  powerless: boolean;
  hand: number;
  energyInPlay: number;
}

export const AUDIT_FLAGS = ['attacked', 'idleAttack', 'energyHeld', 'supporterHeld', 'stadiumHeld', 'basicHeld', 'evolutionHeld', 'emptyBench', 'powerless'] as const;

/** `before`: the position at the start of the turn; `after`: the position after the pilot's line
 *  (the turn passed already if the line ended with an attack); `line`: the steps played. */
export function auditTurn(before: Sim, after: Sim, line: string[], mover: number): TurnAudit {
  const p = after.state.players[mover];
  const start = before.state.players[mover];
  const hand = p.hand.cards;
  const attacked = line.some(l => l.startsWith('attack '));
  const stillMine = !after.finished && after.state.activePlayer === mover;
  const legal = stillMine ? legalMainOptions(after) : [];
  // what the line did, by the cards that were in hand at the start or were found on the way
  const trainers = new Map<string, TrainerType>();
  for (const pl of [before.state.players[mover], p]) {
    for (const c of [...pl.hand.cards, ...pl.deck.cards, ...pl.discard.cards, ...pl.supporter.cards, ...pl.stadium.cards]) {
      if (c instanceof TrainerCard) {
        trainers.set(c.name, c.trainerType);
      }
    }
  }
  const played = line.map(l => /^play (.*?)(?: \| .*)?$/.exec(l)?.[1]).filter((x): x is string => !!x);
  const supporterPlayed = played.some(n => trainers.get(n) === TrainerType.SUPPORTER);
  const attachedByHand = line.some(l => l.startsWith('attach '));
  const firstTurn = before.state.turn <= 1;
  const inPlay = [p.active, ...p.bench].filter(l => l.cards.length);
  const myStadium = p.stadium.cards.length > 0;
  void start;
  return {
    attacked,
    idleAttack: !attacked && legal.some(o => o.kind === 'attack'),
    energyHeld: !attachedByHand && hand.some(c => c instanceof EnergyCard) && inPlay.length > 0,
    supporterHeld: !firstTurn && !supporterPlayed && hand.some(c => c instanceof TrainerCard && c.trainerType === TrainerType.SUPPORTER),
    stadiumHeld: !myStadium && hand.some(c => c instanceof TrainerCard && c.trainerType === TrainerType.STADIUM),
    basicHeld: p.bench.some(b => !b.cards.length) && hand.some(c => c instanceof PokemonCard && c.stage === Stage.BASIC),
    evolutionHeld: legal.some(o => o.kind === 'evolve'),
    emptyBench: !p.bench.some(b => b.cards.length),
    powerless: !inPlay.some(l => (l.getPokemonCard()?.attacks ?? []).some(a => energyGap(a.cost, l) === 0)),
    hand: hand.length,
    energyInPlay: inPlay.reduce((s, l) => s + l.energies.cards.length, 0),
  };
}
