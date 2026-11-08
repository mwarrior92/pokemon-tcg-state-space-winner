// Human-readable board text, for battle logs and reviews.
import { CardType, EnergyCard, PokemonCardList, State } from './engine';
import { prizesLeft } from './rules';

const TYPE: Record<number, string> = {};
for (const [k, v] of Object.entries(CardType)) {
  if (typeof v === 'number') {
    TYPE[v] = k[0] + k.slice(1).toLowerCase();
  }
}

export function typeName(t: CardType): string {
  return TYPE[t] ?? String(t);
}

function energyShort(l: PokemonCardList): string {
  const counts = new Map<string, number>();
  for (const e of l.energies.cards) {
    const k = (e as EnergyCard).energyType === 1 ? e.name.replace(/ Energy$/, '') : typeName((e as EnergyCard).provides?.[0] ?? CardType.COLORLESS)[0];
    counts.set(k, (counts.get(k) ?? 0) + 1);
  }
  return [...counts.entries()].map(([k, n]) => (n > 1 ? `${n}${k}` : k)).join(' ') || '-';
}

export function describeSlot(l: PokemonCardList): string {
  const top = l.getPokemonCard();
  if (!top) {
    return '(empty)';
  }
  const hp = top.hp + (l.hpBonus ?? 0);
  const below = l.getPokemons().slice(0, -1).map(c => c.name);
  const cond = l.specialConditions.length ? ` [${l.specialConditions.join(',')}]` : '';
  const tool = l.tools.length ? ` +${l.tools.map(t => t.name).join('+')}` : '';
  return `${top.name}${below.length ? ` (on ${below.join('<')})` : ''} ${hp - l.damage}/${hp} E:${energyShort(l)}${tool}${cond}`;
}

export function describeState(state: State, perspective?: number): string {
  const lines: string[] = [];
  lines.push(`Turn ${state.turn}, P${state.activePlayer + 1} to move`);
  const stadium = state.players.map(p => p.stadium.cards[0]?.name).find(Boolean);
  if (stadium) {
    lines.push(`Stadium: ${stadium}`);
  }
  state.players.forEach((p, i) => {
    const hidden = perspective !== undefined && perspective !== i;
    lines.push(`P${i + 1}${i === state.activePlayer ? ' (to move)' : ''}: prizes ${prizesLeft(p)}  deck ${p.deck.cards.length}  discard ${p.discard.cards.length}  hand ${p.hand.cards.length}`);
    lines.push(`  Active: ${describeSlot(p.active)}`);
    p.bench.forEach((b, k) => {
      if (b.cards.length) {
        lines.push(`  Bench${k}: ${describeSlot(b)}`);
      }
    });
    if (!hidden) {
      lines.push(`  Hand: ${p.hand.cards.map(c => c.name).join(', ') || '-'}`);
    }
  });
  return lines.join('\n');
}
