// The card sets the simulator loads: the Scarlet & Violet and Mega Evolution eras (a superset of
// current Standard), instead of the engine's full index of every era since Base Set. Loading all
// 15k cards cost every worker ~180 MB of heap (card objects plus the code of ~10k card files) for
// cards no Standard deck can play. Generated from engine/twinleaf/src/sets/index.ts.
export * from '../../engine/twinleaf/src/sets/10-scarlet-and-violet/set-scarlet-and-violet';
export * from '../../engine/twinleaf/src/sets/10-scarlet-and-violet/set-scarlet-and-violet-energy';
export * from '../../engine/twinleaf/src/sets/10-scarlet-and-violet/set-scarlet-and-violet-promos';
export * from '../../engine/twinleaf/src/sets/10-scarlet-and-violet/set-paldea-evolved';
export * from '../../engine/twinleaf/src/sets/10-scarlet-and-violet/set-obsidian-flames';
export * from '../../engine/twinleaf/src/sets/10-scarlet-and-violet/set-pokemon-151';
export * from '../../engine/twinleaf/src/sets/10-scarlet-and-violet/set-paradox-rift';
export * from '../../engine/twinleaf/src/sets/10-scarlet-and-violet/set-paldean-fates';
export * from '../../engine/twinleaf/src/sets/10-scarlet-and-violet/set-temporal-forces';
export * from '../../engine/twinleaf/src/sets/10-scarlet-and-violet/set-twilight-masquerade';
export * from '../../engine/twinleaf/src/sets/10-scarlet-and-violet/set-shrouded-fable';
export * from '../../engine/twinleaf/src/sets/10-scarlet-and-violet/set-stellar-crown';
export * from '../../engine/twinleaf/src/sets/10-scarlet-and-violet/set-surging-sparks';
export * from '../../engine/twinleaf/src/sets/10-scarlet-and-violet/set-prismatic-evolution';
export * from '../../engine/twinleaf/src/sets/10-scarlet-and-violet/set-journey-together';
export * from '../../engine/twinleaf/src/sets/10-scarlet-and-violet/set-destined-rivals';
export * from '../../engine/twinleaf/src/sets/10-scarlet-and-violet/set-black-bolt-white-flare';
export * from '../../engine/twinleaf/src/sets/11-mega-evolution/set-mega-evolution-promos';
export * from '../../engine/twinleaf/src/sets/11-mega-evolution/set-mega-evolution';
export * from '../../engine/twinleaf/src/sets/11-mega-evolution/set-mega-evolution-energy';
export * from '../../engine/twinleaf/src/sets/11-mega-evolution/set-phantasmal-flames';
export * from '../../engine/twinleaf/src/sets/11-mega-evolution/set-ascended-heroes';
export * from '../../engine/twinleaf/src/sets/11-mega-evolution/set-perfect-order';
export * from '../../engine/twinleaf/src/sets/11-mega-evolution/set-chaos-rising';
export * from '../../engine/twinleaf/src/sets/11-mega-evolution/set-delta-reign';
export * from '../../engine/twinleaf/src/sets/11-mega-evolution/set-pitch-black';
export * from '../../engine/twinleaf/src/sets/11-mega-evolution/set-30th-celebration';
export * from '../../engine/twinleaf/src/sets/11-mega-evolution/set-mega-x-mega-parade';
export * from '../../engine/twinleaf/src/sets/11-mega-evolution/set-aura-seeker';

// Standard-legal printings whose only engine definition lives in an older era's folder (reprints;
// found by comparing the Standard card manifest with and without the older eras). Loaded one card
// file each instead of their whole sets.
import { Bronzor as Bronzor_R0 } from '../../engine/twinleaf/src/sets/09-sword-and-shield/set-astral-radiance/bronzor';
import { Caterpie as Caterpie_R1 } from '../../engine/twinleaf/src/sets/08-sun-and-moon/set-burning-shadows/caterpie';
import { Drilbur as Drilbur_R2 } from '../../engine/twinleaf/src/sets/08-sun-and-moon/set-cosmic-eclipse/drilbur';
import { Eldegoss2 as Eldegoss2_R3 } from '../../engine/twinleaf/src/sets/set-shining-fates/eldegoss-2';
import { Escavalier as Escavalier_R4 } from '../../engine/twinleaf/src/sets/09-sword-and-shield/set-brilliant-stars/escavalier';
import { Fletchling as Fletchling_R5 } from '../../engine/twinleaf/src/sets/08-sun-and-moon/set-unified-minds/fletchling';
import { Fomantis as Fomantis_R6 } from '../../engine/twinleaf/src/sets/09-sword-and-shield/set-battle-styles/fomantis';
import { Gossifleur2 as Gossifleur2_R7 } from '../../engine/twinleaf/src/sets/set-shining-fates/gossifleur-2';
import { Kecleon as Kecleon_R8 } from '../../engine/twinleaf/src/sets/08-sun-and-moon/set-celestial-storm/kecleon';
import { Litwick as Litwick_R9 } from '../../engine/twinleaf/src/sets/09-sword-and-shield/set-lost-origin/litwick';
import { PokemonCenterLadyCPA as PokemonCenterLadyCPA_R10 } from '../../engine/twinleaf/src/sets/09-sword-and-shield/set-champions-path/other-prints';
import { Remoraid as Remoraid_R11 } from '../../engine/twinleaf/src/sets/09-sword-and-shield/set-battle-styles/remoraid';
import { Ribombee as Ribombee_R12 } from '../../engine/twinleaf/src/sets/09-sword-and-shield/set-evolving-skies/ribombee';
import { Sewaddle as Sewaddle_R13 } from '../../engine/twinleaf/src/sets/08-sun-and-moon/set-unified-minds/sewaddle';
import { Shinx as Shinx_R14 } from '../../engine/twinleaf/src/sets/07-x-and-y/set-flashfire/shinx';
import { Spearow as Spearow_R15 } from '../../engine/twinleaf/src/sets/07-x-and-y/set-phantom-forces/spearow';
import { Swablu as Swablu_R16 } from '../../engine/twinleaf/src/sets/08-sun-and-moon/set-crimson-invasion/swablu';
import { Vanillite as Vanillite_R17 } from '../../engine/twinleaf/src/sets/06-black-and-white/set-next-destinies/vanillite';
import { WoolooSHF as WoolooSHF_R18 } from '../../engine/twinleaf/src/sets/set-shining-fates/other-prints';

export const reprintsFromOlderSets = [
  new Bronzor_R0(),
  new Caterpie_R1(),
  new Drilbur_R2(),
  new Eldegoss2_R3(),
  new Escavalier_R4(),
  new Fletchling_R5(),
  new Fomantis_R6(),
  new Gossifleur2_R7(),
  new Kecleon_R8(),
  new Litwick_R9(),
  new PokemonCenterLadyCPA_R10(),
  new Remoraid_R11(),
  new Ribombee_R12(),
  new Sewaddle_R13(),
  new Shinx_R14(),
  new Spearow_R15(),
  new Swablu_R16(),
  new Vanillite_R17(),
  new WoolooSHF_R18(),
];
