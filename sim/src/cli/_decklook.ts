import { loadCards, metaDecks, allCards } from '../cards';
loadCards();
const by = new Map(allCards().map(c => [c.fullName, c as any]));
for (const want of process.argv.slice(2)) {
  const d = metaDecks().find(x => x.archetype === want)!;
  console.log(`\n===== ${want}`);
  const n = new Map<string, number>();
  d.cards.forEach(c => n.set(c, (n.get(c) ?? 0) + 1));
  for (const [f, k] of n) {
    const c = by.get(f);
    let s = `${k}x ${f}`;
    if (c.attacks) {
      s += ` [${c.stage} hp${c.hp} retreat${c.retreat.length}${c.evolvesFrom ? ' from ' + c.evolvesFrom : ''}]`;
      for (const p of c.powers ?? []) s += `\n     POWER ${p.name}: ${p.text}`;
      for (const a of c.attacks) s += `\n     ATK ${a.name} [${a.cost.join(',')}] ${a.damage} ${a.text ?? ''}`;
    } else if (c.text) s += `: ${c.text}`;
    console.log(s);
  }
}
