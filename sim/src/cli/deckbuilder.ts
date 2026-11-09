// Deck builder and tester.
//
//   Test a list:       node dist/deckbuilder.js --list my-deck.txt
//   Optimise a list:   node dist/deckbuilder.js --list my-deck.txt --optimize
//   Build from a card: node dist/deckbuilder.js --seed "Dragapult ex"
//
// Options: --games 120 (final test)  --screen 24 (games per candidate while optimising)
//          --iterations 4  --mutants 3  --field 12 (meta decks used while optimising)
//          --pilot race|race2|v0|plan:<model>|plan2:<model>  --name <name>  --workers auto
//          --stuck-weight 0.25 (how much time spent stuck counts against a candidate)
//
// The test: full games from turn 1 against the meta decks, chosen by their share of the decklists,
// both sides piloted by the same policy, the tested deck as player 1 in half the games.
// Optimising: each round tries a few small changes (deckgen.ts mutate) and keeps the best if it
// beats the current list on the same games (same opponents and seeds; a fresh set every round) by
// at least 2 points of score = win rate - stuck weight x (share of turns stuck).
// Output in runs/deck-<name>/: report.md, deck.txt, stats.json, games.jsonl.
import * as fs from 'fs';
import * as path from 'path';
import { REPO_ROOT, loadCards, metaDecks, metaShares } from '../cards';
import { isKnownSmoke, isKnownStatic, loadKnownIssues, smokeTest, standardPool, staticCheck } from '../cardcheck';
import { checkLegal, deckFromText, engineCard, formatDeckList } from '../decklist';
import { candidatePool, mutate, seedDeck } from '../deckgen';
import { DeckStats, deckScore, deckStats, renderReport } from '../deckreport';
import { GameRec, GameSpec, playGame } from '../playgame';
import { autoWorkers, isMainThread, runPool, serveJobs } from '../pool';
import { Rng } from '../rng';

serveJobs((spec: GameSpec) => {
  loadCards();
  return playGame(spec);
});

function arg(name: string, dflt: string): string {
  const i = process.argv.indexOf(`--${name}`);
  return i >= 0 ? process.argv[i + 1] : dflt;
}
const flag = (name: string) => process.argv.includes(`--${name}`);
const hash = (s: string) => [...s].reduce((h, ch) => (h * 31 + ch.charCodeAt(0)) % 999983, 7);

interface Opp { name: string; cards: string[]; share: number }

/** opponents for n games, by meta share (largest remainder), from the top `top` decks */
function schedule(field: Opp[], n: number, seed: number): { opp: Opp; seat: number; seed: number }[] {
  const tot = field.reduce((s, o) => s + o.share, 0);
  const want = field.map(o => ({ o, x: n * o.share / tot }));
  const k = want.map(w => Math.floor(w.x));
  let left = n - k.reduce((s, v) => s + v, 0);
  want.map((w, i) => ({ i, r: w.x - Math.floor(w.x) })).sort((a, b) => b.r - a.r).forEach(({ i }) => {
    if (left > 0) {
      k[i]++;
      left--;
    }
  });
  const out: { opp: Opp; seat: number; seed: number }[] = [];
  let g = 0;
  field.forEach((o, i) => {
    for (let j = 0; j < k[i]; j++) {
      out.push({ opp: o, seat: g % 2, seed: seed * 1000 + g });
      g++;
    }
  });
  return out;
}

async function main(): Promise<void> {
  loadCards();
  const pilot = arg('pilot', 'race');
  const workers = arg('workers', 'auto') === 'auto' ? autoWorkers() : Number(arg('workers', '0'));
  const offense = path.join(REPO_ROOT, 'sim', arg('offense', 'runs/offense-r3b/model.json'));
  const defense = path.join(REPO_ROOT, 'sim', arg('defense', 'runs/defense-r1/model.json'));
  const pilotSpec = pilot.startsWith('plan') ? pilot.replace(/^(plan2?):(.*)$/, (_m, k, f) => `${k}:${path.join(REPO_ROOT, 'sim', f)}`) : pilot;
  const stuckWeight = Number(arg('stuck-weight', '0.25'));

  // the starting deck
  let cards: string[];
  let core = new Map<string, number>();
  let pool: string[];
  const how: string[] = [];
  let name: string;
  const listFile = arg('list', '');
  const seedName = arg('seed', '');
  const exportName = arg('export', '');
  if (exportName) {
    // write a meta deck's list (the best-placed complete one) as a decklist file to start from
    const d = metaDecks().find(x => x.archetype.toLowerCase() === exportName.toLowerCase());
    if (!d) {
      console.error(`no meta deck "${exportName}"; meta decks: ${metaDecks().map(x => x.archetype).join(', ')}`);
      process.exitCode = 1;
      return;
    }
    const out = path.resolve(arg('out', `${d.archetype.toLowerCase().replace(/[^a-z0-9]+/g, '-')}.txt`));
    fs.writeFileSync(out, formatDeckList(d.cards));
    console.log(`wrote ${out}`);
    return;
  }
  if (listFile) {
    const text = fs.readFileSync(path.resolve(listFile), 'utf8');
    const { deck } = deckFromText(text, path.basename(listFile).replace(/\.\w+$/, ''));
    const legal = checkLegal(deck, engineCard);
    if (!legal.ok && !flag('force')) {
      console.error(`the list cannot be played:\n  - ${legal.problems.join('\n  - ')}\n(--force to test anyway)`);
      process.exitCode = 1;
      return;
    }
    cards = deck.cards;
    pool = candidatePool(cards);
    name = arg('name', deck.id);
    how.push(`Started from the list in ${path.basename(listFile)}.`);
  } else if (seedName) {
    const sd = seedDeck(seedName);
    cards = sd.cards;
    core = sd.core;
    pool = sd.pool;
    name = arg('name', seedName);
    how.push(`Seed card: ${seedName}. ${sd.how}.`);
  } else {
    console.error('usage: deckbuilder --list <file> [--optimize] | --seed "<card name>"');
    process.exitCode = 1;
    return;
  }
  const slug = name.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '');
  const dir = path.join(REPO_ROOT, 'sim', 'runs', `deck-${slug}`);
  fs.mkdirSync(dir, { recursive: true });
  const tested = `${name} (tested)`;
  const shares = metaShares();
  const field: Opp[] = metaDecks().map(d => ({ name: d.archetype, cards: d.cards, share: shares.get(d.archetype) ?? 0 }));
  const base = hash(name);
  const specFor = (deck: string[], s: { opp: Opp; seat: number; seed: number }): GameSpec => ({
    seed: s.seed,
    decks: s.seat === 0 ? [deck, s.opp.cards] : [s.opp.cards, deck],
    names: s.seat === 0 ? [tested, s.opp.name] : [s.opp.name, tested],
    start: 'full', offense, defense, budget: 100, maxTurns: 120, seats: [pilotSpec, pilotSpec], log: 'lines',
  });
  const play = async (deck: string[], sched: ReturnType<typeof schedule>, label: string) => {
    const t0 = Date.now();
    let n = 0;
    const res = await runPool<GameSpec, GameRec>(__filename, sched.map(s => specFor(deck, s)), {
      workers,
      onResult: () => {
        if (++n % 20 === 0 || n === sched.length) {
          console.log(`    ${label}: ${n}/${sched.length} games (${((Date.now() - t0) / 1000).toFixed(0)} s)`);
        }
      },
    });
    return res.filter(Boolean) as GameRec[];
  };
  console.log(`# ${name}: ${how.join(' ')}`);
  console.log(`  pilot ${pilot}, ${workers} workers, output ${dir}`);

  // optimise
  const changes: string[] = [];
  if (seedName || flag('optimize')) {
    const iterations = Number(arg('iterations', '4'));
    const mutants = Number(arg('mutants', '3'));
    const screen = Number(arg('screen', '24'));
    const top = field.slice().sort((a, b) => b.share - a.share).slice(0, Number(arg('field', '12')));
    const rng = new Rng(base + 17);
    for (let it = 0; it < iterations; it++) {
      const sched = schedule(top, screen, base + 101 * (it + 1));
      const cands = [{ cards, what: '(current list)' }];
      for (let m = 0; m < mutants; m++) {
        const c = mutate(cards, pool, core, rng);
        if (c) {
          cands.push(c);
        }
      }
      // all candidates on the same games, in one pool run
      const results: { c: typeof cands[number]; s: DeckStats; score: number }[] = [];
      const jobs = cands.flatMap((c, ci) => sched.map(s => ({ ci, spec: specFor(c.cards, s) })));
      const t0 = Date.now();
      let n = 0;
      const recs = await runPool<GameSpec, GameRec>(__filename, jobs.map(j => j.spec), {
        workers,
        onResult: () => {
          if (++n % 20 === 0 || n === jobs.length) {
            console.log(`    round ${it + 1}: ${n}/${jobs.length} games (${((Date.now() - t0) / 1000).toFixed(0)} s)`);
          }
        },
      });
      cands.forEach((c, ci) => {
        const gs = recs.filter((r, k) => r && jobs[k].ci === ci) as GameRec[];
        const s = deckStats(tested, c.cards, gs);
        results.push({ c, s, score: deckScore(s, stuckWeight) });
      });
      const cur = results[0];
      const best = results.slice(1).sort((a, b) => b.score - a.score)[0];
      const line = results.map(r => `${r.c.what === '(current list)' ? 'current' : r.c.what}: ${(100 * r.s.winRate).toFixed(0)}% won, stuck ${(100 * r.s.stuck.nonIdealShare * r.s.stuck.stuckRate).toFixed(0)}%, score ${r.score.toFixed(3)}`);
      console.log(`  round ${it + 1}:\n    ${line.join('\n    ')}`);
      if (best && best.score >= cur.score + 0.02) {
        cards = best.c.cards;
        changes.push(`Round ${it + 1}: ${best.c.what} (score ${cur.score.toFixed(2)} -> ${best.score.toFixed(2)}: win rate ${(100 * cur.s.winRate).toFixed(0)}% -> ${(100 * best.s.winRate).toFixed(0)}% on the same ${screen} games)`);
        console.log(`  kept: ${best.c.what}`);
      } else {
        changes.push(`Round ${it + 1}: no change beat the current list (best tried: ${best ? `${best.c.what}, score ${best.score.toFixed(2)} vs ${cur.score.toFixed(2)}` : 'none'})`);
      }
      pool = candidatePool(cards).concat(pool.filter(p => !cards.includes(p)));
    }
  }

  // the final test against the whole field
  const games = Number(arg('games', '120'));
  const sched = schedule(field, games, base + 7);
  console.log(`  final test: ${games} games against ${new Set(sched.map(s => s.opp.name)).size} meta decks`);
  const recs = await play(cards, sched, 'final');
  fs.writeFileSync(path.join(dir, 'games.jsonl'), recs.map(r => JSON.stringify(r)).join('\n') + '\n');
  const stats = deckStats(tested, cards, recs);
  // the deck's cards against their printed text and in play
  const known = loadKnownIssues();
  const printed = standardPool();
  const issues: string[] = [];
  for (const n of new Set(cards)) {
    const c = engineCard(n);
    const pc = printed.get(n);
    if (!c || !pc) {
      continue;
    }
    staticCheck(c, pc).filter(i => !isKnownStatic(known, i)).forEach(i => issues.push(`${n} ${i.field}: engine ${i.twinleaf} vs printed ${i.expected}`));
    smokeTest(n, pc, 2).failures.filter(f => !isKnownSmoke(known, n, f)).forEach(f => issues.push(`${n}: ${f}`));
  }
  how.push(`Tested in ${stats.games} full games from turn 1 against the meta field (by share of decklists), pilot: ${pilot}.`);
  const report = renderReport(stats, cards, {
    title: `Deck report: ${name}`, how, changes: changes.length ? changes : undefined,
    cardIssues: issues.length ? issues : ['All cards in the list match their printed text and work in play (engine card checks).'],
  });
  fs.writeFileSync(path.join(dir, 'report.md'), report);
  fs.writeFileSync(path.join(dir, 'deck.txt'), formatDeckList(cards));
  fs.writeFileSync(path.join(dir, 'stats.json'), JSON.stringify(stats, null, 1));
  console.log(`\n  win rate ${(100 * stats.winRate).toFixed(0)}% (${(100 * stats.ci[0]).toFixed(0)}-${(100 * stats.ci[1]).toFixed(0)}%) over ${stats.games} games`);
  console.log(`  report: ${path.join(dir, 'report.md')}`);
}

if (isMainThread) {
  main().catch(e => {
    console.error(e);
    process.exitCode = 1;
  });
}
