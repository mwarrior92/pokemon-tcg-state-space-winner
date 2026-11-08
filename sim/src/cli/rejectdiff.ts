// What does the engine change before rejecting an action? (With its rollback off, patch 004, a
// rejected action can leave changes behind on the copy it was tried on.)
//   node dist/rejectdiff.js [n=40]
import { GameError } from '../engine';
import { loadCards, metaDecks } from '../cards';
import { Rng } from '../rng';
import { mainCandidates } from '../sim';
import { generateState } from '../stategen';

loadCards();
const n = Number(process.argv[2] ?? 40);
const decks = metaDecks();
const rng = new Rng(202);

function firstDiff(a: any, b: any, path: string, seen: Set<any>): string | undefined {
  if (a === b) {
    return undefined;
  }
  if (a === null || b === null || typeof a !== 'object' || typeof b !== 'object') {
    return `${path}: ${JSON.stringify(a)?.slice(0, 60)} -> ${JSON.stringify(b)?.slice(0, 60)}`;
  }
  if (seen.has(a)) {
    return undefined;
  }
  seen.add(a);
  if (Array.isArray(a)) {
    if (a.length !== b.length) {
      return `${path}.length: ${a.length} -> ${b.length}`;
    }
    for (let i = 0; i < a.length; i++) {
      const d = firstDiff(a[i], b[i], `${path}[${i}]`, seen);
      if (d) {
        return d;
      }
    }
    return undefined;
  }
  const keys = new Set([...Object.keys(a), ...Object.keys(b)]);
  for (const k of keys) {
    const d = firstDiff(a[k], b[k], `${path}.${k}`, seen);
    if (d) {
      return d;
    }
  }
  return undefined;
}

const tally = new Map<string, number>();
for (let k = 0; k < n; k++) {
  const g = generateState(rng.pick(decks).cards, rng.pick(decks).cards, rng).sim;
  for (const o of mainCandidates(g.state)) {
    const t = g.copy(new Rng(1));
    try {
      t.apply(o.action);
    } catch (e) {
      if (!(e instanceof GameError)) {
        continue;
      }
      const d = firstDiff(g.state, t.state, 'state', new Set());
      if (d) {
        const key = `${o.label.split(' ')[0]} | ${(e as Error).message} | ${d.replace(/\[\d+\]/g, '[i]').replace(/: .*/, '')}`;
        tally.set(key, (tally.get(key) ?? 0) + 1);
        if (tally.get(key) === 1) {
          console.log(`${o.label}: ${d}`);
        }
      }
    }
  }
}
console.log('\nchanges left by rejected actions:');
[...tally].sort((a, b) => b[1] - a[1]).forEach(([k, v]) => console.log(`  ${String(v).padStart(4)}  ${k}`));
