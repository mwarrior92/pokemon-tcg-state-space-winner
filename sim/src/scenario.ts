// Hand-specified board positions (for card tests and debugging), built straight into a Sim.
import { Card, CardList, CardManager, EnergyCard, GamePhase, GameSettings, Player, PokemonCard, PokemonCardList, State } from './engine';
import { loadCards } from './cards';
import { Rng } from './rng';
import { Sim } from './sim';

export interface SlotSpec {
  card: string;              // Twinleaf full name of the top Pokémon
  under?: string[];          // lower stages, Basic first
  energy?: string[];
  tools?: string[];
  damage?: number;
}

export interface PlayerSpec {
  active: SlotSpec;
  bench?: SlotSpec[];
  hand?: string[];
  deck?: string[];
  discard?: string[];
  prizes?: string[];         // face-down prize cards (default: 6 copies of `filler`)
}

export interface ScenarioSpec {
  p1: PlayerSpec;
  p2: PlayerSpec;
  turn?: number;             // default 5 (both players past their first turn)
  active?: number;           // default 0 (P1 to move)
  filler?: string;           // card used for default prizes
}

let nextId = 100000;

export function makeCard(fullName: string): Card {
  const c = CardManager.getInstance().getCardByName(fullName);
  if (!c) {
    throw new Error(`unknown card "${fullName}"`);
  }
  c.id = nextId++;
  return c;
}

export function emptyPlayer(id: number, name: string): Player {
  const p = new Player();
  p.id = id;
  p.name = name;
  for (let i = 0; i < 6; i++) {
    const l = new CardList();
    l.isSecret = true;
    p.prizes.push(l);
  }
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

function fillSlot(l: PokemonCardList, s: SlotSpec, playedTurn: number): void {
  for (const n of [...(s.under ?? []), s.card]) {
    l.cards.push(makeCard(n));
  }
  const top = l.cards[l.cards.length - 1] as PokemonCard;
  l.hp = top.hp;
  for (const e of s.energy ?? []) {
    const c = makeCard(e) as EnergyCard;
    l.cards.push(c);
    l.energies.cards.push(c);
  }
  for (const t of s.tools ?? []) {
    l.tools.push(makeCard(t));
  }
  l.damage = s.damage ?? 0;
  l.pokemonPlayedTurn = playedTurn;
}

export function buildScenario(spec: ScenarioSpec, rng: Rng): Sim {
  loadCards();
  const state = new State();
  const gs = new GameSettings();
  state.gameSettings = gs;
  state.rules = gs.rules;
  state.turn = spec.turn ?? 5;
  state.activePlayer = spec.active ?? 0;
  state.phase = GamePhase.PLAYER_TURN;
  const filler = spec.filler ?? 'Water Energy SVE';
  [spec.p1, spec.p2].forEach((ps, i) => {
    const p = emptyPlayer(i + 1, i === 0 ? 'A' : 'B');
    p.canEvolve = true;
    fillSlot(p.active, ps.active, 1);
    (ps.bench ?? []).forEach((b, k) => fillSlot(p.bench[k], b, 1));
    (ps.hand ?? []).forEach(n => p.hand.cards.push(makeCard(n)));
    (ps.deck ?? []).forEach(n => p.deck.cards.push(makeCard(n)));
    (ps.discard ?? []).forEach(n => p.discard.cards.push(makeCard(n)));
    const prizes = ps.prizes ?? Array(6).fill(filler);
    prizes.forEach((n, k) => p.prizes[k].cards.push(makeCard(n)));
    state.players.push(p);
  });
  return new Sim(state, rng);
}
