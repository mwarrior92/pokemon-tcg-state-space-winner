// [winner patch 014] Pawmot PFL 34 was missing (the engine's Pawmot FLO is a different card).
// Written from the printed card.
import { CardType, ConfirmPrompt, GameMessage, PokemonCard, Stage, State, StoreLike } from '../../../game';
import { Effect } from '../../../game/store/effects/effect';
import { WAS_ATTACK_USED, THIS_POKEMON_DOES_DAMAGE_TO_ITSELF } from '../../../game/store/prefabs/prefabs';
import { YOUR_OPPPONENTS_ACTIVE_POKEMON_IS_NOW_PARALYZED } from '../../../game/store/prefabs/attack-effects';

export class PawmotPFL extends PokemonCard {
  public stage: Stage = Stage.STAGE_2;
  public evolvesFrom = 'Pawmo';
  public cardType: CardType[] = [L];
  public hp: number = 140;
  public weakness = [{ type: F }];
  public retreat = [C];

  public attacks = [{
    name: 'Voltaic Fist',
    cost: [L, L],
    damage: 130,
    text: "You may have this Pokémon also do 60 damage to itself and make your opponent's Active Pokémon Paralyzed.",
  }];

  public regulationMark = 'I';
  public set: string = 'PFL';
  public setNumber: string = '34';
  public cardImage: string = 'assets/cardback.png';
  public name: string = 'Pawmot';
  public fullName: string = 'Pawmot PFL';

  public reduceEffect(store: StoreLike, state: State, effect: Effect): State {
    if (WAS_ATTACK_USED(effect, 0, this)) {
      return store.prompt(state, new ConfirmPrompt(effect.player.id, GameMessage.WANT_TO_USE_EFFECT_OF_ATTACK), yes => {
        if (yes) {
          THIS_POKEMON_DOES_DAMAGE_TO_ITSELF(store, state, effect, 60);
          YOUR_OPPPONENTS_ACTIVE_POKEMON_IS_NOW_PARALYZED(store, state, effect);
        }
      });
    }
    return state;
  }
}
