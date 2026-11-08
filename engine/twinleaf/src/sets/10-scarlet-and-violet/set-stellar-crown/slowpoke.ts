import { PokemonCard, Stage, CardType, State, StoreLike, ChooseCardsPrompt, GameMessage, SuperType } from '../../../game';
import { Effect } from '../../../game/store/effects/effect';
import { MOVE_CARDS, WAS_ATTACK_USED } from '../../../game/store/prefabs/prefabs';

export class Slowpoke extends PokemonCard {

  public regulationMark = 'H';
  public stage: Stage = Stage.BASIC;
  public cardType: CardType[] = [P];
  public hp: number = 80;
  public weakness = [{ type: D }];
  public resistance = [{ type: F, value: -30 }];
  public retreat = [C, C];

  public attacks = [
    {
      name: 'Dangle Tail',
      cost: [C],
      damage: 0,
      text: 'Put a Pokémon from your discard pile into your hand.'
    },
    {
      name: 'Tackle',
      cost: [P, C],
      damage: 30,
      text: ''
    }
  ];

  public set: string = 'SCR';
  public cardImage: string = 'assets/cardback.png';
  public setNumber: string = '57';
  public name: string = 'Slowpoke';
  public fullName: string = 'Slowpoke SCR';

  public reduceEffect(store: StoreLike, state: State, effect: Effect): State {

    if (WAS_ATTACK_USED(effect, 0, this)) {
      const player = effect.player;

      // [winner patch 008] upstream required any card in the discard (not a Pokémon) and then
      // moved the chosen card from a temporary list, leaving it in the discard as well. With no
      // Pokémon in the discard the attack is legal and does nothing.
      const hasCardInDiscard = player.discard.cards.some(c => {
        return c.superType === SuperType.POKEMON;
      });
      if (!hasCardInDiscard) {
        return state;
      }

      return store.prompt(state, [
        new ChooseCardsPrompt(
          player,
          GameMessage.CHOOSE_CARD_TO_HAND,
          player.discard,
          { superType: SuperType.POKEMON },
          { min: 1, max: 1, allowCancel: false }
        )], selected => {
          MOVE_CARDS(store, state, player.discard, player.hand, { cards: selected || [] });
        });
    }

    return state;
  }
}
