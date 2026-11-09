// The local game archive (sim/data/archive/, see src/archive.ts).
//   node dist/archive.js stats
//   node dist/archive.js audit [--pilot race] [--n 6] [--kind deck-final] [--run "<run name>"] [--out file.md]
// audit: picks games won by the side playing --pilot (comebacks and different decks first), replays
// them with the board logged and writes a review packet (default sim/reviews/audit-<date>.md), so the
// play of a model can be checked by hand (or by an AI review) before it is adopted.
import * as fs from 'fs';
import * as path from 'path';
import { REPO_ROOT, loadCards } from '../cards';
import { ArchiveRec, expand, isFresh, readArchive } from '../archive';
import { GameSpec, playGame } from '../playgame';

loadCards();
const cmd = process.argv[2] ?? 'stats';
const arg = (n: string, d = '') => (process.argv.includes(`--${n}`) ? process.argv[process.argv.indexOf(`--${n}`) + 1] : d);

const tally = (m: Map<string, number>, k: string) => m.set(k, (m.get(k) ?? 0) + 1);
const show = (title: string, m: Map<string, number>) => {
  console.log(`${title}:`);
  [...m].sort((a, b) => b[1] - a[1]).slice(0, 15).forEach(([k, v]) => console.log(`  ${String(v).padStart(7)}  ${k}`));
};

if (cmd === 'stats') {
  let games = 0, fresh = 0, positions = 0, decided = 0;
  const kinds = new Map<string, number>(), pilots = new Map<string, number>(), commits = new Map<string, number>(), decks = new Map<string, number>();
  for (const r of readArchive()) {
    games++;
    fresh += isFresh(r) ? 1 : 0;
    decided += r.game.winner === 0 || r.game.winner === 1 ? 1 : 0;
    positions += r.game.turns.filter(t => t.x).length;
    tally(kinds, r.kind);
    tally(pilots, [...new Set(r.game.seats)].join(' vs '));
    tally(commits, r.commit);
    r.game.decks.forEach(d => tally(decks, d));
  }
  console.log(`${games} games (${decided} decided), ${fresh} played with the current card rules; ${positions} positions with feature vectors`);
  show('by kind', kinds);
  show('by pilot', pilots);
  show('by commit', commits);
  console.log(`${decks.size} different deck names; most played:`);
  [...decks].sort((a, b) => b[1] - a[1]).slice(0, 10).forEach(([k, v]) => console.log(`  ${String(v).padStart(7)}  ${k}`));
} else if (cmd === 'audit') {
  const pilot = arg('pilot', '');
  const n = Number(arg('n', '6'));
  const kind = arg('kind', '');
  const run = arg('run', '');
  // candidate games: decided, fresh, won by the side playing the pilot
  const cands: { r: ArchiveRec; w: number; comeback: number }[] = [];
  for (const r of readArchive({ fresh: true })) {
    const g = r.game;
    if ((kind && r.kind !== kind) || (run && r.run !== run) || !(g.winner === 0 || g.winner === 1)) {
      continue;
    }
    if (pilot && !g.seats[g.winner].includes(pilot)) {
      continue;
    }
    // how far behind on prizes the winner was at some point (comebacks are the interesting wins)
    const behind = Math.max(0, ...g.turns.map(t => t.prizes[g.winner] - t.prizes[1 - g.winner]));
    cands.push({ r, w: g.winner, comeback: behind });
  }
  // comebacks first, then one game per winning deck before repeating a deck
  cands.sort((a, b) => b.comeback - a.comeback || b.r.game.turns.length - a.r.game.turns.length);
  const picked: typeof cands = [];
  const seenDeck = new Set<string>();
  for (const pass of [0, 1]) {
    for (const c of cands) {
      const d = c.r.game.decks[c.w];
      if (picked.length < n && !picked.includes(c) && (pass === 1 || !seenDeck.has(d))) {
        picked.push(c);
        seenDeck.add(d);
      }
    }
  }
  console.log(`${cands.length} games won by ${pilot || 'any pilot'}; replaying ${picked.length}`);
  const L: string[] = [`# Play audit: games won by ${pilot || 'any pilot'}`, '',
    'For each game: the winner, how far behind it was at worst, then every turn with the board before it and the moves played. Check that the winning side\'s plays are sensible (sequencing, targets, resource use, not leaving itself open) and note anything that only worked because the opponent erred.', ''];
  picked.forEach((c, i) => {
    const r = c.r;
    const spec: GameSpec = { ...r.spec, decks: [expand(r.decks[0]), expand(r.decks[1])], names: r.game.decks, log: 'board' } as GameSpec;
    const t0 = Date.now();
    const g = playGame(spec);
    const same = g.winner === r.game.winner && g.turns.length === r.game.turns.length;
    console.log(`  game ${i + 1}: ${r.game.decks.join(' vs ')} (${((Date.now() - t0) / 1000).toFixed(0)} s)${same ? '' : ' - replay diverged'}`);
    L.push(`## Game ${i + 1}: ${g.decks[0]} (P1, ${g.seats[0]}) vs ${g.decks[1]} (P2, ${g.seats[1]})`, '');
    L.push(`- Archived result: ${r.game.decks[r.game.winner]} won by ${r.game.reason}, ${r.game.turns.length} turns; worst prize deficit of the winner: ${c.comeback}. Run "${r.run}" (${r.kind}), seed ${r.spec.seed}, commit ${r.commit}.`);
    if (!same) {
      L.push(`- **Replay diverged** (planners stop at wall-clock limits): this replay ${g.winner === 0 || g.winner === 1 ? `was won by ${g.decks[g.winner]}` : 'was not decided'} by ${g.reason} in ${g.turns.length} turns. Review it as its own game.`);
    }
    L.push('');
    g.turns.forEach(t => {
      L.push(`### Turn ${t.turn}: P${t.mover + 1} ${g.decks[t.mover]} to move (prizes left P1 ${t.prizes[0]}, P2 ${t.prizes[1]}; ${t.cat})`, '');
      if (t.board) {
        L.push('```', t.board.trimEnd(), '```');
      }
      L.push(`Moves (${t.policy}): ${(t.line ?? []).join(' -> ') || '(none)'}${t.took ? ` - took ${t.took} prize${t.took > 1 ? 's' : ''}` : ''}`, '');
    });
  });
  const out = arg('out', path.join(REPO_ROOT, 'sim', 'reviews', `audit-${new Date().toISOString().slice(0, 10)}${pilot ? `-${pilot.replace(/[^a-z0-9]+/gi, '-')}` : ''}.md`));
  fs.mkdirSync(path.dirname(out), { recursive: true });
  fs.writeFileSync(out, L.join('\n') + '\n');
  console.log(`packet: ${out}`);
} else {
  console.error('usage: archive.js stats | audit [--pilot p] [--n 6] [--kind k] [--run r] [--out file]');
  process.exitCode = 1;
}
