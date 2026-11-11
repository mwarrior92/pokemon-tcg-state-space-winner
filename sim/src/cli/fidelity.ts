// Pilot fidelity: do the simulator's matchups look like real ones?
//
//   node dist/fidelity.js --pilot race --decks 10 --games 12 --name fidelity-race
//   node dist/fidelity.js --pilot plan2:runs/value-v2/value-model.json --name fidelity-plan2
//
// The top `--decks` archetypes of the meta decklists (best-placed complete list each) play every
// other one `--games` times (seats alternate), both sides piloted by `--pilot`. Each matchup's sim
// win rate is compared with the real one from the Limitless matchup tables
// (meta/matchups_*.json, all rounds of 8 events, thousands of games per common pairing).
//
// The scores, in runs/<name>/report.md:
//  - correlation of sim and real matchup win rates (1 = same order and spacing; 0 = unrelated);
//  - mean absolute error, next to the error that sampling noise alone would give with this many
//    games (a pilot cannot score below that floor; more games lower it);
//  - lopsidedness: mean |win rate - 50%| in the sim and in reality (a weak pilot exaggerates
//    matchups: whoever's plan it executes better wins most games);
//  - each deck's average win rate against the others, sim vs real, and the rank correlation;
//  - how games end (prizes, deck out, no Pokémon, turn limit), game length, first-player win rate.
// Games go to runs/<name>/games.jsonl as they finish (rerunning the same command resumes) and to
// the local game archive (kind 'fidelity').
import * as fs from 'fs';
import * as path from 'path';
import { REPO_ROOT, loadCards, metaDecks } from '../cards';
import { archiveGames } from '../archive';
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

interface Job { a: number; b: number; k: number; spec: GameSpec }
interface Done { a: string; b: string; k: number; seed: number; winner: number; first?: number; reason: string; turns: number; ms: number; seats: [string, string] }

const pct = (x: number) => `${(100 * x).toFixed(0)}%`;
const mean = (xs: number[]) => xs.reduce((s, x) => s + x, 0) / Math.max(1, xs.length);
function pearson(x: number[], y: number[]): number {
  const mx = mean(x), my = mean(y);
  let sxy = 0, sxx = 0, syy = 0;
  x.forEach((v, i) => {
    sxy += (v - mx) * (y[i] - my);
    sxx += (v - mx) ** 2;
    syy += (y[i] - my) ** 2;
  });
  return sxx && syy ? sxy / Math.sqrt(sxx * syy) : 0;
}
const ranks = (x: number[]) => {
  const order = x.map((v, i) => ({ v, i })).sort((p, q) => p.v - q.v);
  const r = Array(x.length).fill(0);
  order.forEach((o, k) => (r[o.i] = k));
  return r;
};
const spearman = (x: number[], y: number[]) => pearson(ranks(x), ranks(y));

async function main(): Promise<void> {
  loadCards();
  const pilot = arg('pilot', 'race');
  const nDecks = Number(arg('decks', '10'));
  const perPair = Number(arg('games', '12'));
  const workers = arg('workers', 'auto') === 'auto' ? autoWorkers() : Number(arg('workers', '0'));
  const name = arg('name', `fidelity-${pilot.replace(/^(plan2?):.*?([^/\\]+?)(?:\.json)?$/, '$1-$2').replace(/[^a-z0-9-]+/gi, '-')}`);
  const offense = path.join(REPO_ROOT, 'sim', arg('offense', 'runs/offense-r3b/model.json'));
  const defense = path.join(REPO_ROOT, 'sim', arg('defense', 'runs/defense-r1/model.json'));
  const pilotSpec = pilot.startsWith('plan') ? pilot.replace(/^(plan2?):(.*)$/, (_m, k, f) => `${k}:${path.join(REPO_ROOT, 'sim', f)}`) : pilot;
  const realFile = path.join(REPO_ROOT, 'meta', arg('real', 'matchups_2026-09-19_to_10-31.json'));
  const real: Record<string, Record<string, [number, number, number]>> = JSON.parse(fs.readFileSync(realFile, 'utf8')).total;

  const decks = metaDecks().filter(d => real[d.archetype]).slice(0, nDecks);
  const dir = path.join(REPO_ROOT, 'sim', 'runs', name);
  fs.mkdirSync(dir, { recursive: true });
  const gamesFile = path.join(dir, 'games.jsonl');
  const done: Done[] = fs.existsSync(gamesFile) ? fs.readFileSync(gamesFile, 'utf8').split('\n').filter(Boolean).map(l => JSON.parse(l)) : [];
  const have = new Set(done.map(d => `${d.a}|${d.b}|${d.k}`));

  const jobs: Job[] = [];
  for (let a = 0; a < decks.length; a++) {
    for (let b = a + 1; b < decks.length; b++) {
      for (let k = 0; k < perPair; k++) {
        if (have.has(`${decks[a].archetype}|${decks[b].archetype}|${k}`)) {
          continue;
        }
        const seat = k % 2;                  // deck a moves as player 1 in even games
        const seed = 500000 + a * 10000 + b * 100 + k;
        const pair: [string[], string[]] = seat === 0 ? [decks[a].cards, decks[b].cards] : [decks[b].cards, decks[a].cards];
        const names: [string, string] = seat === 0 ? [decks[a].archetype, decks[b].archetype] : [decks[b].archetype, decks[a].archetype];
        jobs.push({
          a, b, k, spec: {
            seed, decks: pair, names, start: 'full', offense, defense, budget: 100, maxTurns: 120,
            seats: [pilotSpec, pilotSpec], vectors: true,
          },
        });
      }
    }
  }
  const pairs = decks.length * (decks.length - 1) / 2;
  console.log(`# ${name}: pilot ${pilot}, ${decks.length} decks (${pairs} matchups x ${perPair} games), ${done.length} done, ${jobs.length} to play, ${workers} workers`);
  console.log(`  decks: ${decks.map(d => d.archetype).join(', ')}`);

  if (jobs.length) {
    const t0 = Date.now();
    let n = 0;
    const batch: { g: GameRec; spec: GameSpec }[] = [];
    await runPool<GameSpec, GameRec>(__filename, jobs.map(j => j.spec), {
      workers,
      onResult: (g: GameRec, i: number) => {
        n++;
        if (g) {
          const j = jobs[i];
          // winner from deck a's side: names[0] is deck a when seat 0
          const aSeat = j.spec.names[0] === decks[j.a].archetype ? 0 : 1;
          const rec: Done = {
            a: decks[j.a].archetype, b: decks[j.b].archetype, k: j.k, seed: j.spec.seed,
            winner: g.winner === 2 || g.winner < 0 ? g.winner : g.winner === aSeat ? 0 : 1,
            first: g.first === undefined ? undefined : g.first === aSeat ? 0 : 1,
            reason: g.reason, turns: g.turns.length, ms: g.ms, seats: j.spec.seats,
          };
          done.push(rec);
          fs.appendFileSync(gamesFile, JSON.stringify(rec) + '\n');
          batch.push({ g, spec: j.spec });
          if (batch.length >= 20) {
            archiveGames(batch.map(x => x.g), batch.map(x => x.spec), 'fidelity', name);
            batch.length = 0;
          }
        }
        if (n % 20 === 0 || n === jobs.length) {
          const s = (Date.now() - t0) / 1000;
          console.log(`    ${n}/${jobs.length} games (${s.toFixed(0)} s, about ${((jobs.length - n) * s / n / 60).toFixed(0)} min left)`);
        }
      },
    });
    if (batch.length) {
      archiveGames(batch.map(x => x.g), batch.map(x => x.spec), 'fidelity', name);
    }
  }
  fs.writeFileSync(path.join(dir, 'report.md'), report(name, pilot, decks.map(d => d.archetype), done, real, realFile));
  console.log(`report: ${path.join(dir, 'report.md')}`);
}

function report(name: string, pilot: string, names: string[], done: Done[], real: Record<string, Record<string, [number, number, number]>>, realFile: string): string {
  const L: string[] = [];
  const realWr = (a: string, b: string) => {
    const r = real[a]?.[b];
    if (!r) {
      return undefined;
    }
    const g = r[0] + r[1] + r[2];
    return g ? { wr: (r[0] + r[2] / 2) / g, n: g } : undefined;
  };
  const decided = done.filter(d => d.winner === 0 || d.winner === 1 || d.winner === 2);
  const simWr = (a: string, b: string) => {
    const gs = decided.filter(d => (d.a === a && d.b === b) || (d.a === b && d.b === a));
    if (!gs.length) {
      return undefined;
    }
    const pts = gs.reduce((s, d) => s + (d.winner === 2 ? 0.5 : (d.a === a) === (d.winner === 0) ? 1 : 0), 0);
    return { wr: pts / gs.length, n: gs.length };
  };
  const rows: { a: string; b: string; sim: number; real: number; n: number; realN: number }[] = [];
  for (let i = 0; i < names.length; i++) {
    for (let j = i + 1; j < names.length; j++) {
      const s = simWr(names[i], names[j]), r = realWr(names[i], names[j]);
      if (s && r) {
        rows.push({ a: names[i], b: names[j], sim: s.wr, real: r.wr, n: s.n, realN: r.n });
      }
    }
  }
  const corr = pearson(rows.map(r => r.sim), rows.map(r => r.real));
  const mae = mean(rows.map(r => Math.abs(r.sim - r.real)));
  // expected |error| from sampling alone: E|N(0, s)| = s * sqrt(2/pi), s^2 = p(1-p)/n (sim) + p(1-p)/N (real)
  const noise = mean(rows.map(r => Math.sqrt(r.real * (1 - r.real) / r.n + r.real * (1 - r.real) / r.realN) * Math.sqrt(2 / Math.PI)));
  const lopSim = mean(rows.map(r => Math.abs(r.sim - 0.5))), lopReal = mean(rows.map(r => Math.abs(r.real - 0.5)));
  // the sim's lopsidedness includes noise too: E|sim - 0.5| is at least about the noise level
  const deckRows = names.map(nm => {
    const mine = rows.filter(r => r.a === nm || r.b === nm);
    const side = (r: typeof rows[0], x: number) => (r.a === nm ? x : 1 - x);
    return { nm, sim: mean(mine.map(r => side(r, r.sim))), real: mean(mine.map(r => side(r, r.real))), n: mine.reduce((t, r) => t + r.n, 0) };
  });
  const deckMae = mean(deckRows.map(d => Math.abs(d.sim - d.real)));
  const deckNoise = mean(deckRows.map(d => Math.sqrt(d.real * (1 - d.real) / Math.max(1, d.n)) * Math.sqrt(2 / Math.PI)));
  const rankCorr = spearman(deckRows.map(d => d.sim), deckRows.map(d => d.real));

  L.push(`# Pilot fidelity: ${name}`);
  L.push('');
  L.push(`Pilot \`${pilot}\`. ${names.length} meta decks (best-placed complete list of each archetype), every pairing played ${Math.round(mean(rows.map(r => r.n)))} times with seats alternating: ${done.length} games. Real matchups: ${path.basename(realFile)} (Limitless, all rounds).`);
  L.push('');
  L.push('## Scores');
  L.push('');
  L.push('| score | value | what it means |');
  L.push('|---|---|---|');
  L.push(`| correlation, sim vs real matchup win rates | **${corr.toFixed(2)}** | 1 = same order and spacing, 0 = unrelated |`);
  L.push(`| mean absolute error | **${pct(mae)}** | sampling noise alone would give about ${pct(noise)} |`);
  L.push(`| lopsidedness (mean distance from 50%) | sim ${pct(lopSim)}, real ${pct(lopReal)} | a weak pilot exaggerates matchups; noise adds about ${pct(noise)} to the sim figure |`);
  L.push(`| rank correlation of deck win rates | **${rankCorr.toFixed(2)}** | do the decks come out in the real order? |`);
  L.push(`| deck win rate error (mean absolute, each deck against all the others) | **${pct(deckMae)}** | the steadiest score: sampling noise alone would give about ${pct(deckNoise)} |`);
  L.push('');
  L.push('## Decks: average win rate against the others');
  L.push('');
  L.push('| deck | sim | real | difference |');
  L.push('|---|---|---|---|');
  deckRows.slice().sort((p, q) => (q.sim - q.real) - (p.sim - p.real)).forEach(d => L.push(`| ${d.nm} | ${pct(d.sim)} | ${pct(d.real)} | ${d.sim >= d.real ? '+' : ''}${(100 * (d.sim - d.real)).toFixed(0)} |`));
  L.push('');
  L.push('Sorted from most overrated by the simulator to most underrated.');
  L.push('');
  L.push('## Matchups, largest disagreement first');
  L.push('');
  L.push('| deck A | deck B | A wins: sim | A wins: real | sim games | real games |');
  L.push('|---|---|---|---|---|---|');
  rows.slice().sort((p, q) => Math.abs(q.sim - q.real) - Math.abs(p.sim - p.real)).forEach(r => L.push(`| ${r.a} | ${r.b} | ${pct(r.sim)} | ${pct(r.real)} | ${r.n} | ${r.realN} |`));
  L.push('');
  L.push('## How games went');
  L.push('');
  const reasons = new Map<string, number>();
  done.forEach(d => reasons.set(d.reason || 'unknown', (reasons.get(d.reason || 'unknown') ?? 0) + 1));
  L.push(`- Endings: ${[...reasons].sort((p, q) => q[1] - p[1]).map(([k, v]) => `${k} ${v} (${pct(v / done.length)})`).join(', ')}.`);
  L.push(`- Mean length ${mean(done.map(d => d.turns)).toFixed(1)} turns; ${(mean(done.map(d => d.ms)) / 1000).toFixed(0)} s per game in a worker.`);
  const withFirst = decided.filter(d => d.first !== undefined && d.winner !== 2);
  if (withFirst.length) {
    L.push(`- The player who went first won ${pct(withFirst.filter(d => d.first === d.winner).length / withFirst.length)} of ${withFirst.length} decided games.`);
  }
  L.push('');
  L.push('## Reading this');
  L.push('');
  L.push('- Real matchups mix pilots of every level and list variants; the sim plays one list per archetype with one pilot on both sides. A perfect pilot would still not match exactly, but its errors should be close to the noise floor and its lopsidedness close to the real figure.');
  L.push('- Decks far above the line (overrated) are ones the pilot plays well relative to their opponents; decks far below are where its play is worst. Audit those games first (`node dist/archive.js audit --kind fidelity --run ' + name + '`).');
  return L.join('\n') + '\n';
}

if (isMainThread) {
  main().catch(e => {
    console.error(e);
    process.exitCode = 1;
  });
}
