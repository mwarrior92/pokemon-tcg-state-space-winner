// Play generated states to the end of the game and measure, per state category, how often the
// side to move goes on to win - overall and per deck - plus how categories lead to one another.
//
//   node dist/playout.js --games 200 --offense runs/offense-r3/model.json --defense runs/defense-r1/model.json [--run name]
//     [--workers auto] [--budget 100] [--max-turns 80] [--seed n] [--vectors]
//     [--A v0|race|race2|plan:<value-model.json>|plan2:<value-model.json>] [--B ...]   (head to head; seats swap every game)
//
// Turn policy (both sides, v0): the offense search policy; if it finds no prize this turn, the
// defense policy instead (set up so the opponent's next turn takes as few prizes as possible).
// Writes runs/<run>/games.jsonl (one game per line: decks, every turn's category for the side to
// move, prizes left, the winner) and runs/<run>/categories.md (win rates and transitions).
// Resumable like train.ts: finished games are skipped on a rerun.
import * as fs from 'fs';
import * as path from 'path';
import { REPO_ROOT, loadCards, metaDecks } from '../cards';
import { categorize } from '../categories';
import { CHEAP_GROUPS, features } from '../features';
import { GamePhase, GameWinner, PassTurnAction } from '../engine';
import { LinearModel, loadModel } from '../model';
import { playDefense, playOffenseSearch } from '../policy';
import { planTurn, planTurn2, raceEvaluator } from '../planner';
import { WinModel } from '../value';
import { autoWorkers, isMainThread, runPool, serveJobs } from '../pool';
import { prizesLeft } from '../rules';
import { Rng } from '../rng';
import { Sim, randomChooser, resolvePrompts } from '../sim';
import { generateState } from '../stategen';

/** a seat's turn policy: 'v0' (offense search, else defense) or 'plan:<value model file>' */
interface GameJob { seed: number; a: number; b: number; offense: string; defense?: string; budget: number; maxTurns: number; vectors: boolean; seats: [string, string] }
interface TurnRec { turn: number; mover: number; cat: string; prizes: [number, number]; took: number; policy: 'offense' | 'defense' | 'plan' | 'pass'; ms: number; x?: number[] }
interface GameRec { seed: number; decks: [string, string]; seats: [string, string]; startTurn: number; turns: TurnRec[]; winner: number; reason: string; ms: number }

// ---------------------------------------------------------------- worker

const wins = new Map<string, WinModel>();
const winModel = (f: string) => {
  let w = wins.get(f);
  if (!w) {
    w = new WinModel(loadModel(f));
    wins.set(f, w);
  }
  return w;
};
const models = new Map<string, LinearModel>();
const model = (f: string) => {
  let m = models.get(f);
  if (!m) {
    m = loadModel(f);
    models.set(f, m);
  }
  return m;
};

/** End the turn in place (the engine runs the turn change); prompts that come up are answered at
 *  random (a known limit: e.g. the opponent's new Active after a Knock Out). */
function passInPlace(sim: Sim, rng: Rng): boolean {
  try {
    if (!sim.finished && sim.state.phase === GamePhase.PLAYER_TURN) {
      sim.apply(new PassTurnAction(sim.state.players[sim.state.activePlayer].id));
    }
    resolvePrompts(sim, randomChooser(rng), rng);
    return true;
  } catch {
    return false;
  }
}

function playGame(job: GameJob): GameRec {
  const t0 = Date.now();
  const decks = metaDecks();
  const g = generateState(decks[job.a].cards, decks[job.b].cards, new Rng(job.seed));
  let sim = g.sim;
  const rng = new Rng(job.seed * 31 + 7);
  const off = model(job.offense);
  const def = job.defense ? model(job.defense) : undefined;
  const turns: TurnRec[] = [];
  let reason = 'turn limit';
  for (let t = 0; t < job.maxTurns && !sim.finished; t++) {
    const ts = Date.now();
    const mover = sim.state.activePlayer;
    const cat = categorize(sim, mover).key;
    // the cheap feature vector from the mover's side (names in runs/<run>/feature-names.json)
    const x = job.vectors ? features(sim, mover, CHEAP_GROUPS).values.map(v => Math.round(v * 100) / 100) : undefined;
    const before = prizesLeft(sim.state.players[mover]);
    const prizes: [number, number] = [prizesLeft(sim.state.players[0]), prizesLeft(sim.state.players[1])];
    let next: Sim | undefined;
    let policy: TurnRec['policy'] = 'offense';
    const seat = job.seats[mover];
    try {
      if (seat.startsWith('plan:')) {
        policy = 'plan';
        const o = playOffenseSearch(sim, off, { budget: job.budget, maxMs: 3000 });
        const extra = [{ sim: o.end, line: o.line, ended: o.end.finished || o.end.state.activePlayer !== mover }];
        next = planTurn(sim, winModel(seat.slice(5)), { budget: job.budget, maxMs: 4000, seed: job.seed + t, extra }).end;
      } else if (seat === 'race' && def) {
        // policy v1: two-turn prize race from the offense and defense models
        policy = 'plan';
        // the offense policy's tactical line is always a candidate (v1 must not take fewer prizes
        // than v0 unless setting up is predicted to be worth more)
        const o = playOffenseSearch(sim, off, { budget: job.budget, maxMs: 3000 });
        const extra = [{ sim: o.end, line: o.line, ended: o.end.finished || o.end.state.activePlayer !== mover }];
        next = planTurn(sim, raceEvaluator(off, def, 0.8, job.seed + t), { budget: job.budget, maxMs: 4000, seed: job.seed + t, extra }).end;
      } else if (seat === 'race2' && def) {
        // v2: the two-turn prize race tested against sampled opponent replies (disruption-aware)
        policy = 'plan';
        const o = playOffenseSearch(sim, off, { budget: job.budget, maxMs: 3000 });
        const extra = [{ sim: o.end, line: o.line, ended: o.end.finished || o.end.state.activePlayer !== mover }];
        next = planTurn2(sim, raceEvaluator(off, def, 0.8, job.seed + t), { budget: job.budget, maxMs: 4000, seed: job.seed + t, extra, candidates: 5, replies: 6, replyBudget: 40, risk: 0.25 }).end;
      } else if (seat.startsWith('plan2:')) {
        // the win model, tested against sampled replies (same settings as v2), with the tactical line
        policy = 'plan';
        const o = playOffenseSearch(sim, off, { budget: job.budget, maxMs: 3000 });
        const extra = [{ sim: o.end, line: o.line, ended: o.end.finished || o.end.state.activePlayer !== mover }];
        next = planTurn2(sim, winModel(seat.slice(6)), { budget: job.budget, maxMs: 4000, seed: job.seed + t, extra, candidates: 5, replies: 6, replyBudget: 40, risk: 0.25 }).end;
      } else {
        const o = playOffenseSearch(sim, off, { budget: job.budget, maxMs: 3000 });
        if (o.prizes > 0 || !def) {
          next = o.end;
        } else {
          policy = 'defense';
          const d = playDefense(sim, def, job.seed + t);
          next = d.end;
        }
      }
    } catch {
      policy = 'pass';
      next = sim.copy(rng.fork());
    }
    sim = next!;
    // pass only if the line did not end the turn itself (an attack ends it)
    if (!sim.finished && sim.state.activePlayer === mover && !passInPlace(sim, rng)) {
      reason = 'engine error';
      break;
    }
    turns.push({ turn: sim.state.turn, mover, cat, prizes, took: before - prizesLeft(sim.state.players[mover]), policy, ms: Date.now() - ts, x });
  }
  let winner = -1;
  if (sim.finished) {
    winner = sim.state.winner === GameWinner.PLAYER_1 ? 0 : sim.state.winner === GameWinner.PLAYER_2 ? 1 : sim.state.winner === GameWinner.DRAW ? 2 : -1;
    const w = winner < 2 && winner >= 0 ? sim.state.players[winner] : undefined;
    reason = w && prizesLeft(w) === 0 ? 'prizes' : winner === 2 ? 'draw' : 'deck out / no Pokémon';
  }
  return { seed: job.seed, decks: [decks[job.a].archetype, decks[job.b].archetype], seats: job.seats, startTurn: g.info.turn, turns, winner, reason, ms: Date.now() - t0 };
}

serveJobs((job: GameJob) => {
  loadCards();
  return playGame(job);
});

// ---------------------------------------------------------------- main

function arg(name: string, dflt: string): string {
  const i = process.argv.indexOf(`--${name}`);
  return i >= 0 ? process.argv[i + 1] : dflt;
}

function readJsonl<T>(file: string): T[] {
  if (!fs.existsSync(file)) {
    return [];
  }
  return fs.readFileSync(file, 'utf8').split('\n').filter(l => l.trim()).flatMap(l => {
    try {
      return [JSON.parse(l) as T];
    } catch {
      return [];
    }
  });
}

function report(dir: string, games: GameRec[]): void {
  const decided = games.filter(g => g.winner === 0 || g.winner === 1);
  const L: string[] = [];
  L.push(`# Playouts: state categories`);
  L.push('');
  L.push(`${games.length} games, ${decided.length} decided (${games.filter(g => g.reason === 'turn limit').length} hit the turn limit, ${games.filter(g => g.reason === 'engine error').length} engine errors). Ways games ended: ${[...new Set(games.map(g => g.reason))].map(r => `${r} ${games.filter(g => g.reason === r).length}`).join(', ')}.`);
  L.push('');
  L.push('A category is recorded at the start of every turn from the side to move. "Win" = the side to move went on to win the game.');
  L.push('');
  // per category
  const cat = new Map<string, { n: number; w: number }>();
  const deckCat = new Map<string, Map<string, { n: number; w: number }>>();
  const trans = new Map<string, Map<string, number>>();
  for (const g of decided) {
    const lastBy: (string | undefined)[] = [undefined, undefined];
    for (const t of g.turns) {
      const win = g.winner === t.mover ? 1 : 0;
      const c = cat.get(t.cat) ?? { n: 0, w: 0 };
      c.n++;
      c.w += win;
      cat.set(t.cat, c);
      const deck = g.decks[t.mover];
      const dm = deckCat.get(deck) ?? new Map();
      const dc = dm.get(t.cat) ?? { n: 0, w: 0 };
      dc.n++;
      dc.w += win;
      dm.set(t.cat, dc);
      deckCat.set(deck, dm);
      const prev = lastBy[t.mover];
      if (prev) {
        const tm = trans.get(prev) ?? new Map<string, number>();
        tm.set(t.cat, (tm.get(t.cat) ?? 0) + 1);
        trans.set(prev, tm);
      }
      lastBy[t.mover] = t.cat;
    }
  }
  const rows = [...cat].filter(([, c]) => c.n >= 10).sort((a, b) => b[1].w / b[1].n - a[1].w / a[1].n);
  L.push('## Win rate of the side to move, by category (categories seen at least 10 times)');
  L.push('');
  L.push('| category | turns | win rate |');
  L.push('|---|---|---|');
  rows.forEach(([k, c]) => L.push(`| ${k} | ${c.n} | ${(100 * c.w / c.n).toFixed(0)}% |`));
  L.push('');
  L.push('## Where each category leads (the same player\'s next turn), top 3 by frequency');
  L.push('');
  L.push('| from | to (share) |');
  L.push('|---|---|');
  for (const [k] of rows) {
    const tm = trans.get(k);
    if (!tm) {
      continue;
    }
    const tot = [...tm.values()].reduce((s, x) => s + x, 0);
    const top = [...tm].sort((a, b) => b[1] - a[1]).slice(0, 3).map(([to, x]) => `${to} (${(100 * x / tot).toFixed(0)}%)`);
    L.push(`| ${k} | ${top.join('; ')} |`);
  }
  L.push('');
  L.push('## Per deck: best and worst categories (at least 5 turns)');
  L.push('');
  for (const [deck, dm] of [...deckCat].sort()) {
    const r = [...dm].filter(([, c]) => c.n >= 5).sort((a, b) => b[1].w / b[1].n - a[1].w / a[1].n);
    if (r.length < 2) {
      continue;
    }
    const fmt = ([k, c]: [string, { n: number; w: number }]) => `${k} ${(100 * c.w / c.n).toFixed(0)}% (${c.n})`;
    L.push(`- **${deck}**: best ${fmt(r[0])}; worst ${fmt(r[r.length - 1])}`);
  }
  // head to head, when the two seats play different policies
  const specs = [...new Set(games.flatMap(g => g.seats ?? []))];
  if (specs.length === 2) {
    L.push('');
    L.push('## Policies head to head');
    L.push('');
    for (const sp of specs) {
      const mine = decided.filter(g => g.seats.includes(sp));
      const won = mine.filter(g => g.seats[g.winner] === sp).length;
      const kind = sp.startsWith('plan2:') ? 'two-turn planner' : sp.startsWith('plan:') ? 'one-turn planner' : sp === 'race' ? 'v1 (two-turn prize race)' : sp === 'race2' ? 'v2 (prize race vs sampled replies)' : 'v0 (offense, else defense)';
      L.push(`- ${kind}${sp.includes(':') ? ` with \`${path.basename(path.dirname(sp.replace(/^plan2?:/, '')))}\`` : ''}: won ${won}/${mine.length} (${(100 * won / Math.max(1, mine.length)).toFixed(0)}%)`);
    }
  }
  fs.writeFileSync(path.join(dir, 'categories.md'), L.join('\n') + '\n');
}

async function main(): Promise<void> {
  const nGames = Number(arg('games', '200'));
  const run = arg('run', `playout-${new Date().toISOString().replace(/[:.]/g, '-').slice(0, 19)}`);
  const dir = path.join(REPO_ROOT, 'sim', 'runs', run);
  fs.mkdirSync(dir, { recursive: true });
  loadCards();
  const decks = metaDecks();
  const seedBase = Number(arg('seed', String([...run].reduce((h, ch) => (h * 31 + ch.charCodeAt(0)) % 999983, 7))));
  const rng = new Rng(seedBase);
  const resolve = (f: string) => (path.isAbsolute(f) ? f : path.join(REPO_ROOT, 'sim', f));
  const offense = resolve(arg('offense', 'runs/offense-r3/model.json'));
  const defArg = arg('defense', '');
  const seatSpec = (v: string) => {
    const m = /^(plan2?):(.*)$/.exec(v);
    return m ? `${m[1]}:${resolve(m[2])}` : v;
  };
  const seatA = seatSpec(arg('A', 'v0')), seatB = seatSpec(arg('B', 'v0'));
  const defense = defArg ? resolve(defArg) : undefined;
  const jobs: GameJob[] = Array.from({ length: nGames }, (_, k) => ({
    seed: seedBase * 1000 + k, a: rng.int(0, decks.length - 1), b: rng.int(0, decks.length - 1),
    offense, defense, budget: Number(arg('budget', '100')), maxTurns: Number(arg('max-turns', '80')), vectors: process.argv.includes('--vectors'),
    // policy A and B (default both v0); seats swap every game so neither always moves first
    seats: (k % 2 === 0 ? [seatA, seatB] : [seatB, seatA]) as [string, string],
  }));
  if (jobs[0]?.vectors) {
    const g = generateState(decks[0].cards, decks[1].cards, new Rng(1));
    fs.writeFileSync(path.join(dir, 'feature-names.json'), JSON.stringify(features(g.sim, 0, CHEAP_GROUPS).names));
  }
  const file = path.join(dir, 'games.jsonl');
  const games = readJsonl<GameRec>(file);
  const done = new Set(games.map(g => g.seed));
  const todo = jobs.filter(j => !done.has(j.seed));
  const workers = arg('workers', 'auto') === 'auto' ? autoWorkers() : Number(arg('workers', '0'));
  console.log(`# playouts "${run}": ${nGames} games (${games.length} done), ${workers} workers, offense ${offense}, defense ${defense ?? '(none)'}`);
  const t0 = Date.now();
  let n = 0;
  await runPool<GameJob, GameRec>(__filename, todo, {
    workers,
    onResult: g => {
      fs.appendFileSync(file, JSON.stringify(g) + '\n');
      games.push(g);
      if (++n % 20 === 0 || n === todo.length) {
        console.log(`  ${n}/${todo.length} games (${((Date.now() - t0) / 1000).toFixed(0)} s); mean ${(games.reduce((s, x) => s + x.turns.length, 0) / games.length).toFixed(1)} turns, ${(games.reduce((s, x) => s + x.ms, 0) / games.length / 1000).toFixed(1)} s per game in a worker`);
      }
    },
  });
  report(dir, games);
  console.log(`report: ${path.join(dir, 'categories.md')}`);
}

if (isMainThread) {
  main().catch(e => {
    console.error(e);
    process.exitCode = 1;
  });
}
