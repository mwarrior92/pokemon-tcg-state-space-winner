// Plays complete games between meta decks with uniformly random *legal* choices (no strategy at all),
// to check that the engine runs every deck end to end, to surface engine card bugs, and to measure
// throughput.
//   node dist/randomgame.js [games=20] [seed=1]
import { loadCards, metaDecks } from '../cards';
import { GamePhase } from '../engine';
import { Rng } from '../rng';
import { Sim, bugLog, bugStats, legalMainOptions, randomChooser, resolvePrompts, runStep } from '../sim';

export interface RandomGameResult {
  sim: Sim;
  steps: number;
  stuck: string;
  deadEnds: string[];
}

export function playRandomGame(deckA: string[], deckB: string[], seed: number, maxSteps = 2000): RandomGameResult {
  const rng = new Rng(seed);
  const choose = randomChooser(rng);
  let sim = Sim.newGame(deckA, deckB, rng.fork());
  resolvePrompts(sim, choose, rng);   // setup: starting Pokémon, mulligans, who goes first
  let steps = 0;
  let stuck = '';
  const deadEnds: string[] = [];
  while (!sim.finished && steps < maxSteps) {
    steps++;
    if (sim.state.phase !== GamePhase.PLAYER_TURN) {
      stuck = `phase ${GamePhase[sim.state.phase]} with no prompt`;
      break;
    }
    const opts = legalMainOptions(sim);
    const pass = opts.find(x => x.kind === 'pass')!;
    let next: Sim | undefined;
    const tried = new Set<string>();
    while (!next) {
      // keep games moving: ending the turn is always legal, so pick it 1 time in 8 at most
      const nonPass = opts.filter(o => o.kind !== 'pass' && !tried.has(o.label));
      const o = nonPass.length && !rng.chance(0.12) ? rng.pick(nonPass) : pass;
      tried.add(o.label);
      const r = runStep(sim, o, choose, rng);
      deadEnds.push(...r.deadEnds);
      next = r.sim;
      if (!next && o === pass) {
        stuck = `cannot even end the turn: ${r.deadEnds.join(' / ')}`;
        break;
      }
    }
    if (!next) {
      break;
    }
    sim = next;
  }
  return { sim, steps, stuck, deadEnds };
}

if (require.main === module) {
  const games = Number(process.argv[2] ?? 20);
  const seed = Number(process.argv[3] ?? 1);
  loadCards();
  const decks = metaDecks();
  console.log(`${decks.length} meta archetypes with a fully-resolved list`);
  const rng = new Rng(seed);
  const t0 = Date.now();
  let totalSteps = 0;
  const problems: string[] = [];
  const deadEnds = new Map<string, number>();
  for (let g = 0; g < games; g++) {
    const a = rng.pick(decks);
    const b = rng.pick(decks);
    const s = rng.int(1, 1e9);
    let r: RandomGameResult;
    try {
      r = playRandomGame(a.cards, b.cards, s);
    } catch (e) {
      problems.push(`${a.archetype} vs ${b.archetype} seed ${s}: CRASH ${String((e as Error)?.stack ?? e).split('\n').slice(0, 4).join(' | ')}`);
      continue;
    }
    totalSteps += r.steps;
    r.deadEnds.forEach(d => {
      const k = d.replace(/:\s*\{.*$/, '').replace(/bench\d/g, 'bench#').slice(0, 160);
      deadEnds.set(k, (deadEnds.get(k) ?? 0) + 1);
    });
    const tag = r.sim.finished ? `winner P${r.sim.state.winner + 1}` : `UNFINISHED${r.stuck ? ' - ' + r.stuck : ''}`;
    console.log(`${String(g).padStart(3)} ${a.archetype.padEnd(24)} vs ${b.archetype.padEnd(24)} turns ${String(r.sim.state.turn).padStart(3)} steps ${String(r.steps).padStart(5)}  ${tag}`);
    if (!r.sim.finished) {
      problems.push(`${a.archetype} vs ${b.archetype} seed ${s}: ${tag}; last: ${r.sim.trace.slice(-3).join(' / ')}`);
    }
  }
  const dt = (Date.now() - t0) / 1000;
  console.log(`\n${games} games, ${totalSteps} main-phase decisions in ${dt.toFixed(1)} s (${(totalSteps / dt).toFixed(0)}/s)`);
  console.log(`engine exceptions on candidate actions (not rule rejections): ${bugStats.count}`);
  const byLabel = new Map<string, number>();
  bugLog.forEach(b => {
    const k = b.label.replace(/ -> .*/, '') + ' :: ' + b.error.slice(0, 160);
    byLabel.set(k, (byLabel.get(k) ?? 0) + 1);
  });
  [...byLabel.entries()].sort((x, y) => y[1] - x[1]).slice(0, 15).forEach(([k, n]) => console.log(`  ${n}x ${k}`));
  console.log(`dead ends (action raised a prompt with no valid answer): ${[...deadEnds.values()].reduce((x, y) => x + y, 0)}`);
  [...deadEnds.entries()].sort((x, y) => y[1] - x[1]).slice(0, 15).forEach(([k, n]) => console.log(`  ${n}x ${k}`));
  if (problems.length) {
    console.log('\nproblems:');
    problems.forEach(p => console.log('  ' + p));
  }
}
