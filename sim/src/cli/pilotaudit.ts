// Pilot audit: what does a pilot leave undone, deck by deck? (audit.ts)
//
//   node dist/pilotaudit.js --pilot race --name audit-race                       all pairings of the top 10 decks, 2 games each
//   node dist/pilotaudit.js --pilot race --focus "Festival Lead" --games 6       one deck against the other nine
//   node dist/pilotaudit.js --compare audit-race,audit-new [--focus "Festival Lead"]
//   node dist/pilotaudit.js --pilot race --versus inplay --name vs-inplay        the pilot against itself with a part off
//
// --versus <parts> (variant.ts): every game is played twice with the same seed, once with each deck
// in the hands of the pilot as it is ("new") against the pilot with those parts off ("old"). The
// report gives the new pilot's share of the decided games and both pilots' audit rates.
//
// Every turn of every game is checked for free resources left unused (an attack not made, an Energy
// or Supporter kept in hand, a Stadium not played, ...). The rates per deck go to
// runs/<name>/report.md; games with every turn's line go to runs/<name>/games.jsonl. The same
// --seeds give the same games (set-up and draws) to every pilot, so two pilots can be compared on a
// few dozen games: the rates move far less between runs than win rates do.
import * as fs from 'fs';
import * as path from 'path';
import { AUDIT_FLAGS, TurnAudit } from '../audit';
import { REPO_ROOT, loadCards, metaDecks } from '../cards';
import { GameRec, GameSpec, playGame } from '../playgame';
import { autoWorkers, isMainThread, runPool, serveJobs } from '../pool';

serveJobs((spec: GameSpec) => {
  loadCards();
  return playGame(spec);
});

function arg(name: string, dflt: string): string {
  const i = process.argv.indexOf(`--${name}`);
  return i >= 0 ? process.argv[i + 1] : dflt;
}

interface Row { variant?: string; deck: string; opp: string; won: boolean; decided: boolean; turns: { n: number; took: number; audit?: TurnAudit; line?: string[] }[] }

const pct = (x: number) => `${(100 * x).toFixed(0)}%`;

function summarize(rows: Row[]): Map<string, Record<string, number>> {
  const out = new Map<string, Record<string, number>>();
  for (const deck of [...new Set(rows.map(r => r.deck))]) {
    const mine = rows.filter(r => r.deck === deck);
    const turns = mine.flatMap(r => r.turns).filter(t => t.audit);
    const s: Record<string, number> = {
      games: mine.length,
      win: mine.filter(r => r.won).length / Math.max(1, mine.filter(r => r.decided).length),
      turns: turns.length / Math.max(1, mine.length),
      prizesPerTurn: turns.reduce((a, t) => a + t.took, 0) / Math.max(1, turns.length),
      hand: turns.reduce((a, t) => a + t.audit!.hand, 0) / Math.max(1, turns.length),
      energyInPlay: turns.reduce((a, t) => a + t.audit!.energyInPlay, 0) / Math.max(1, turns.length),
    };
    // the first turn in which the deck attacked (own turns; games without an attack count as their length)
    s.firstAttack = mine.reduce((a, r) => {
      const i = r.turns.findIndex(t => t.audit?.attacked);
      return a + (i < 0 ? r.turns.length : i + 1);
    }, 0) / Math.max(1, mine.length);
    for (const f of AUDIT_FLAGS) {
      s[f] = turns.filter(t => t.audit![f]).length / Math.max(1, turns.length);
    }
    out.set(deck, s);
  }
  return out;
}

const COLS: [string, string, (v: number) => string][] = [
  ['games', 'games', v => String(v)], ['win', 'win', pct], ['turns', 'own turns', v => v.toFixed(1)], ['prizesPerTurn', 'prizes / turn', v => v.toFixed(2)],
  ['firstAttack', 'first attack (own turn)', v => v.toFixed(1)], ['attacked', 'attacked', pct], ['idleAttack', 'attack not made', pct],
  ['powerless', 'no attack payable', pct], ['energyHeld', 'Energy held', pct], ['supporterHeld', 'Supporter held', pct], ['stadiumHeld', 'Stadium held', pct],
  ['basicHeld', 'Basic held', pct], ['evolutionHeld', 'Evolution held', pct], ['emptyBench', 'empty Bench', pct], ['hand', 'hand at end', v => v.toFixed(1)],
  ['energyInPlay', 'Energy in play', v => v.toFixed(1)],
];

function table(s: Map<string, Record<string, number>>): string[] {
  const L = [`| deck | ${COLS.map(c => c[1]).join(' | ')} |`, `|---|${COLS.map(() => '---|').join('')}`];
  for (const [deck, v] of [...s].sort((a, b) => a[1].win - b[1].win)) {
    L.push(`| ${deck} | ${COLS.map(c => c[2](v[c[0]])).join(' | ')} |`);
  }
  return L;
}

const loadRows = (run: string): Row[] => fs.readFileSync(path.join(REPO_ROOT, 'sim', 'runs', run, 'games.jsonl'), 'utf8').split('\n').filter(Boolean).flatMap(l => JSON.parse(l).rows as Row[]);

async function main(): Promise<void> {
  const cmp = arg('compare', '');
  const focus = arg('focus', '');
  if (cmp) {
    // the runs side by side: one deck (--focus) or all decks pooled
    const runs = cmp.split(',').map(r => ({ r, rows: r.split('+').flatMap(loadRows) }));
    const sums = runs.map(x => {
      const rows = focus ? x.rows.filter(r => r.deck === focus) : x.rows.map(r => ({ ...r, deck: 'all decks' }));
      return summarize(rows).get(focus || 'all decks') ?? {};
    });
    console.log(`${focus || 'All decks'}:\n`);
    console.log(`| | ${runs.map(x => x.r).join(' | ')} |\n|---|${runs.map(() => '---|').join('')}`);
    for (const c of COLS) {
      console.log(`| ${c[1]} | ${sums.map(s => (s[c[0]] === undefined ? '-' : c[2](s[c[0]]))).join(' | ')} |`);
    }
    return;
  }
  loadCards();
  const pilot = arg('pilot', 'race');
  const nDecks = Number(arg('decks', '10'));
  const perPair = Number(arg('games', '2'));
  const workers = arg('workers', 'auto') === 'auto' ? autoWorkers() : Number(arg('workers', '0'));
  const name = arg('name', `audit-${pilot.replace(/[^a-z0-9-]+/gi, '-')}`);
  const offense = path.join(REPO_ROOT, 'sim', arg('offense', 'runs/offense-r3b/model.json'));
  const defense = path.join(REPO_ROOT, 'sim', arg('defense', 'runs/defense-r1/model.json'));
  const pilotSpec = /^(plan2?|imit|imitrace|\w+):.+\.json$/.test(pilot) ? pilot.replace(/^(\w+):(.*)$/, (_m, k, f) => `${k}:${path.resolve(REPO_ROOT, 'sim', f)}`) : pilot;
  const real = JSON.parse(fs.readFileSync(path.join(REPO_ROOT, 'meta', 'matchups_2026-09-19_to_10-31.json'), 'utf8')).total;
  const decks = metaDecks().filter(d => real[d.archetype]).slice(0, nDecks);
  const seedBase = 700000 + 1000000 * Number(arg('seeds', '0'));
  const dir = path.join(REPO_ROOT, 'sim', 'runs', name);
  fs.mkdirSync(dir, { recursive: true });
  // --replay "deck a|deck b|k": one game of the run again, with the board before every turn
  const rp = arg('replay', '');
  if (rp) {
    const [ra, rb, rk] = rp.split('|');
    const a = decks.findIndex(d => d.archetype === ra), b = decks.findIndex(d => d.archetype === rb), k = Number(rk);
    const x = k % 2 === 0 ? [a, b] : [b, a];
    const spec: GameSpec = {
      seed: seedBase + a * 10000 + b * 100 + k, decks: [decks[x[0]].cards, decks[x[1]].cards], names: [decks[x[0]].archetype, decks[x[1]].archetype],
      start: 'full', offense, defense, budget: 100, maxTurns: 120, seats: [pilotSpec, pilotSpec], log: 'board', audit: true,
    };
    const g = playGame(spec);
    const L = [`# Replay: ${spec.names[0]} (P1) vs ${spec.names[1]} (P2), seed ${spec.seed}, pilot ${pilot}`, '',
      `Result: ${g.winner === 0 || g.winner === 1 ? `${g.decks[g.winner]} won` : 'undecided'} by ${g.reason} in ${g.turns.length} turns; P${(g.first ?? 0) + 1} went first.`, ''];
    for (const t of g.turns) {
      const flags = t.audit ? AUDIT_FLAGS.filter(f => f !== 'attacked' && t.audit![f]) : [];
      L.push(`### Turn ${t.turn}: P${t.mover + 1} ${g.decks[t.mover]} (prizes left P1 ${t.prizes[0]}, P2 ${t.prizes[1]})`, '', '```', (t.board ?? '').trimEnd(), '```',
        `Moves: ${(t.line ?? []).join(' -> ') || '(none)'}${t.took ? ` - took ${t.took}` : ''}`, ...(flags.length ? [`Left undone: ${flags.join(', ')}`] : []), '');
    }
    const out = path.join(dir, `replay-${[ra, rb, rk].join('-').replace(/[^a-z0-9-]+/gi, '_')}.md`);
    fs.writeFileSync(out, L.join('\n') + '\n');
    console.log(`${g.decks[g.winner] ?? 'nobody'} won by ${g.reason} in ${g.turns.length} turns: ${out}`);
    return;
  }
  const versus = arg('versus', '');
  const oldSpec = `${pilotSpec}@${versus}`;
  const gamesFile = path.join(dir, 'games.jsonl');
  const done: { key: string; rows: Row[] }[] = fs.existsSync(gamesFile) ? fs.readFileSync(gamesFile, 'utf8').split('\n').filter(Boolean).map(l => JSON.parse(l)) : [];
  const have = new Set(done.map(d => d.key));
  const jobs: { key: string; spec: GameSpec }[] = [];
  for (let a = 0; a < decks.length; a++) {
    for (let b = a + 1; b < decks.length; b++) {
      if (focus && decks[a].archetype !== focus && decks[b].archetype !== focus) {
        continue;
      }
      for (let k = 0; k < perPair; k++) {
        const x = k % 2 === 0 ? [a, b] : [b, a];
        // versus: the game twice, the new pilot in either seat
        for (const side of versus ? [0, 1] : [-1]) {
          const key = `${decks[a].archetype}|${decks[b].archetype}|${k}${side < 0 ? '' : `|new${side}`}`;
          if (have.has(key)) {
            continue;
          }
          const seats: [string, string] = side < 0 ? [pilotSpec, pilotSpec] : side === 0 ? [pilotSpec, oldSpec] : [oldSpec, pilotSpec];
          jobs.push({
            key, spec: {
              seed: seedBase + a * 10000 + b * 100 + k, decks: [decks[x[0]].cards, decks[x[1]].cards], names: [decks[x[0]].archetype, decks[x[1]].archetype],
              start: 'full', offense, defense, budget: 100, maxTurns: 120, seats, log: 'lines', audit: true,
            },
          });
        }
      }
    }
  }
  console.log(`# ${name}: pilot ${pilot}, ${jobs.length} games to play (${done.length} done), ${workers} workers`);
  if (jobs.length) {
    const t0 = Date.now();
    let n = 0;
    await runPool<GameSpec, GameRec>(__filename, jobs.map(j => j.spec), {
      workers,
      onResult: (g: GameRec, i: number) => {
        n++;
        if (g) {
          const rows: Row[] = [0, 1].map(seat => ({
            variant: versus ? (jobs[i].spec.seats[seat] === oldSpec ? 'old' : 'new') : undefined,
            deck: g.decks[seat], opp: g.decks[1 - seat], won: g.winner === seat, decided: g.winner === 0 || g.winner === 1,
            turns: g.turns.filter(t => t.mover === seat).map(t => ({ n: t.turn, took: t.took, audit: t.audit, line: t.line })),
          }));
          const rec = { key: jobs[i].key, seed: jobs[i].spec.seed, winner: g.winner, reason: g.reason, rows };
          done.push(rec);
          fs.appendFileSync(gamesFile, JSON.stringify(rec) + '\n');
        }
        if (n % 10 === 0 || n === jobs.length) {
          console.log(`    ${n}/${jobs.length} games (${((Date.now() - t0) / 1000).toFixed(0)} s)`);
        }
      },
    });
  }
  const rows = done.flatMap(d => d.rows);
  const L = [`# Pilot audit: ${name}`, '', `Pilot \`${pilot}\`, ${done.length} games${focus ? ` (every game has ${focus})` : ''}. Rates are shares of the deck's own turns; see \`src/audit.ts\` for what each column counts.`, '',
    ...table(summarize(rows)), '', '## All decks together', '', ...table(summarize(rows.map(r => ({ ...r, deck: 'all decks' }))))];
  if (versus) {
    // the new pilot's share of the decided games, with a 95% interval (normal approximation), and
    // how many same-seed pairs of games went 2-0, 1-1 and 0-2 for it
    const mine = rows.filter(r => r.variant === 'new' && r.decided);
    const w = mine.filter(r => r.won).length, n = mine.length, sh = w / Math.max(1, n), se = Math.sqrt(sh * (1 - sh) / Math.max(1, n));
    const pairs = new Map<string, number[]>();
    for (const d of done) {
      const r = d.rows.find(x => x.variant === 'new');
      if (r?.decided) {
        const pk = d.key.replace(/\|new\d$/, '');
        pairs.set(pk, [...(pairs.get(pk) ?? []), r.won ? 1 : 0]);
      }
    }
    const full = [...pairs.values()].filter(v => v.length === 2).map(v => v[0] + v[1]);
    L.push('', `## New against old (parts off: ${versus})`, '', `New won ${w} of ${n} decided games: ${pct(sh)} (95% interval ${pct(Math.max(0, sh - 1.96 * se))} to ${pct(Math.min(1, sh + 1.96 * se))}).`,
      `Pairs of games on the same seed: new won both in ${full.filter(x => x === 2).length}, one each in ${full.filter(x => x === 1).length}, none in ${full.filter(x => x === 0).length}.`, '',
      ...table(summarize(rows.map(r => ({ ...r, deck: r.variant ?? '?' })))));
  }
  fs.writeFileSync(path.join(dir, 'report.md'), L.join('\n') + '\n');
  console.log(L.slice(4).join('\n'));
}

if (isMainThread) {
  main().catch(e => {
    console.error(e);
    process.exitCode = 1;
  });
}
