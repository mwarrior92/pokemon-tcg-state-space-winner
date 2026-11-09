// Deck builder and tester.
//
//   Test a list:       node dist/deckbuilder.js --list my-deck.txt
//   Optimise a list:   node dist/deckbuilder.js --list my-deck.txt --optimize
//   Build from a card: node dist/deckbuilder.js --seed "Dragapult ex"
//
// Options: --population 10 (decks searched at once)  --screen 10 (games per deck per generation)
//          --generations 4  --finalists 3  --games 120 (final test; the finalists play half of it)
//          --field 12 (meta decks used while searching)
//          --pilot race|race2|v0|plan:<model>|plan2:<model>  --name <name>  --workers auto
//          --stuck-weight 0.25 (how much time spent stuck counts against a deck)
//
// The test: full games from turn 1 against the meta decks, chosen by their share of the decklists,
// both sides piloted by the same policy, the tested deck as player 1 in half the games.
// Searching (--seed, or --list with --optimize): a population of decks (the start, other meta lists
// that play the seed, and bigger variations of the start). Each generation every deck plays the same
// few games; the top half survives with its games, the rest are replaced by small changes to the
// survivors. Decks are ranked by score = win rate (pulled towards 50% when a deck has few games)
// - stuck weight x (share of turns stuck). The best few, plus the starting list, then play the same
// half of the final test; the best of those plays the other half, as does the starting list.
// Output in runs/deck-<name>/: report.md, deck.txt, stats.json, games.jsonl.
import * as fs from 'fs';
import * as path from 'path';
import { REPO_ROOT, loadCards, metaDecks, metaShares } from '../cards';
import { isKnownSmoke, isKnownStatic, loadKnownIssues, smokeTest, standardPool, staticCheck } from '../cardcheck';
import { checkLegal, deckFromText, engineCard, formatDeckList } from '../decklist';
import { candidatePool, mutate, mutateN, seedDeck } from '../deckgen';
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
  let alternatives: { cards: string[]; what: string }[] = [];
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
    alternatives = sd.alternatives;
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
  /** play several decks on the same games (same opponents, seats and seeds), in one pool run */
  const playMany = async (decks: string[][], sched: ReturnType<typeof schedule>, label: string): Promise<GameRec[][]> => {
    const jobs = decks.flatMap((d, di) => sched.map(sc => ({ di, spec: specFor(d, sc) })));
    const t0 = Date.now();
    let n = 0;
    const recs = await runPool<GameSpec, GameRec>(__filename, jobs.map(j => j.spec), {
      workers,
      onResult: () => {
        if (++n % 20 === 0 || n === jobs.length) {
          console.log(`    ${label}: ${n}/${jobs.length} games (${((Date.now() - t0) / 1000).toFixed(0)} s)`);
        }
      },
    });
    return decks.map((_, di) => recs.filter((r, k) => r && jobs[k].di === di) as GameRec[]);
  };
  const startCards = cards.slice();
  console.log(`# ${name}: ${how.join(' ')}`);
  console.log(`  pilot ${pilot}, ${workers} workers, output ${dir}`);

  const games = Number(arg('games', '120'));
  const finalSched = schedule(field, games, base + 7);
  const key = (c: string[]) => c.slice().sort().join('|');
  const pctS = (x: number) => `${(100 * x).toFixed(0)}%`;
  /** net difference between two lists, by card name: "-2 Judge, +1 Briar, +1 Dawn" */
  const diffText = (from: string[], to: string[]) => {
    const cnt = new Map<string, number>();
    from.forEach(n => cnt.set(n, (cnt.get(n) ?? 0) - 1));
    to.forEach(n => cnt.set(n, (cnt.get(n) ?? 0) + 1));
    const nm = (n: string) => engineCard(n)?.name ?? n;
    const out = [...cnt].filter(([, k]) => k < 0).map(([n, k]) => `${k} ${nm(n)}`)
      .concat([...cnt].filter(([, k]) => k > 0).map(([n, k]) => `+${k} ${nm(n)}`));
    return out.length ? out.join(', ') : 'no change';
  };

  // search
  const changes: string[] = [];
  let changesTitle: string | undefined;
  let preFinal: Map<string, GameRec[]> | undefined;     // list -> its games on the first half of the final test
  if (seedName || flag('optimize')) {
    changesTitle = 'How the list was found';
    const popSize = Number(arg('population', '10'));
    const perGen = Number(arg('screen', '10'));
    const generations = Number(arg('generations', '4'));
    const nFinal = Number(arg('finalists', '3'));
    const top = field.slice().sort((a, b) => b.share - a.share).slice(0, Number(arg('field', '12')));
    const rng = new Rng(base + 17);
    interface Cand { id: number; cards: string[]; parent?: number; change: string; games: GameRec[] }
    const all = new Map<string, Cand>();
    const byId = new Map<number, Cand>();
    const add = (cards: string[], change: string, parent?: number): Cand | undefined => {
      const k = key(cards);
      if (all.has(k)) {
        return undefined;
      }
      const c: Cand = { id: all.size + 1, cards: cards.slice().sort(), parent, change, games: [] };
      all.set(k, c);
      byId.set(c.id, c);
      return c;
    };
    const rank = (c: Cand) => {
      const st = deckStats(tested, c.cards, c.games);
      // pulled towards 50% by 4 imaginary games, so 8 of 10 does not outrank 30 of 45
      return { st, score: deckScore(st, stuckWeight) - st.winRate + (st.wins + 2) / (st.games + 4) };
    };
    const label = (c: Cand) => (c.parent ? `#${c.id} (#${c.parent}: ${c.change})` : `#${c.id} (${c.change})`);
    const startC = add(startCards, 'starting list')!;
    let pop: Cand[] = [startC];
    for (const a of alternatives.slice(0, Math.floor(popSize / 2))) {
      const c = add(a.cards, a.what);
      if (c) {
        pop.push(c);
      }
    }
    for (let guard = 0; pop.length < popSize && guard < popSize * 20; guard++) {
      // bigger jumps for a seed build (a rough first guess) than for a hand-made list
      const m = mutateN(startCards, pool, core, rng, seedName ? rng.int(3, 8) : rng.int(2, 4));
      const c = m && add(m.cards, `variant: ${diffText(startCards, m.cards)}`, startC.id);
      if (c) {
        pop.push(c);
      }
    }
    console.log(`  search: ${pop.length} decks, ${generations} generations of ${perGen} games each`);
    const pools = new Map<number, string[]>();
    let played = 0;
    let ranked: { c: Cand; st: DeckStats; score: number }[] = [];
    for (let g = 0; g < generations; g++) {
      const sched = schedule(top, perGen, base + 101 * (g + 1));
      const recsBy = await playMany(pop.map(c => c.cards), sched, `generation ${g + 1}`);
      pop.forEach((c, i) => c.games.push(...recsBy[i]));
      played += pop.length * sched.length;
      ranked = pop.map(c => ({ c, ...rank(c) })).sort((a, b) => b.score - a.score);
      console.log(`  generation ${g + 1}:`);
      ranked.forEach(r => console.log(`    ${r.score.toFixed(3)}  ${pctS(r.st.winRate)} of ${r.st.games}  ${label(r.c)}`));
      const best = ranked[0];
      changes.push(`Generation ${g + 1}: ${pop.length} decks, ${perGen} games each; leader ${label(best.c)}, ${pctS(best.st.winRate)} won over its ${best.st.games} games`);
      if (g === generations - 1) {
        break;
      }
      // the top half survives; the rest are replaced by changes to survivors (better ones more often)
      const keep = ranked.slice(0, Math.ceil(pop.length / 2)).map(r => r.c);
      const next = keep.slice();
      for (let guard = 0; next.length < popSize && guard < popSize * 20; guard++) {
        const parent = keep[Math.floor(keep.length * rng.next() ** 1.5)];
        if (!pools.has(parent.id)) {
          pools.set(parent.id, [...new Set(candidatePool(parent.cards).concat(pool))]);
        }
        const m = mutate(parent.cards, pools.get(parent.id)!, core, rng);
        const c = m && add(m.cards, m.what, parent.id);
        if (c) {
          next.push(c);
        }
      }
      pop = next;
    }

    // finalists (and the starting list) on the same half of the final test
    const fin = ranked.slice(0, nFinal).map(r => r.c);
    if (!fin.includes(startC)) {
      fin.push(startC);
    }
    const half1 = finalSched.filter((_, i) => i % 2 === 0);
    console.log(`  finalists: ${fin.map(c => `#${c.id}`).join(', ')} on the same ${half1.length} games against the whole field`);
    const fr = await playMany(fin.map(c => c.cards), half1, 'finalists');
    played += fin.length * half1.length;
    preFinal = new Map(fin.map((c, i) => [key(c.cards), fr[i]]));
    const finRanked = fin.map((c, i) => {
      const st = deckStats(tested, c.cards, fr[i]);
      return { c, st, score: deckScore(st, stuckWeight) };
    }).sort((a, b) => b.score - a.score);
    const champ = finRanked[0].c;
    changes.push(`Finalists on the same ${half1.length} games against the whole field: ${finRanked.map(f => `#${f.c.id}${f.c === startC ? ' (starting list)' : ''} ${pctS(f.st.winRate)} (score ${f.score.toFixed(2)})`).join('; ')}`);
    // the champion's family line
    const lineage: Cand[] = [];
    for (let c: Cand | undefined = champ; c; c = c.parent ? byId.get(c.parent) : undefined) {
      lineage.unshift(c);
    }
    if (champ !== startC) {
      changes.push(`Winner #${champ.id}, found by: ${lineage.map(c => label(c)).join(' -> ')}`);
      changes.push(`Net change from the starting list: ${diffText(startCards, champ.cards)}`);
    } else {
      changes.push('No variant beat the starting list in the finalist games; the list is unchanged.');
    }
    finRanked.slice(1).filter(f => f.c !== startC).forEach((f, i) => {
      fs.writeFileSync(path.join(dir, `finalist-${i + 2}.txt`), formatDeckList(f.c.cards));
      changes.push(`Runner-up #${f.c.id} (finalist-${i + 2}.txt), compared with the winner: ${diffText(champ.cards, f.c.cards)}`);
    });
    changes.push(`${all.size} different lists tried in ${played} games before the final test.`);
    cards = champ.cards;
  }

  // the final test against the whole field: the deck and, if it changed, the starting list on the
  // same games (the finalists already played the first half)
  const changed = key(startCards) !== key(cards);
  const decks = changed ? [cards, startCards] : [cards];
  const left = preFinal ? finalSched.filter((_, i) => i % 2 === 1) : finalSched;
  console.log(`  final test: ${games} games against ${new Set(finalSched.map(s => s.opp.name)).size} meta decks${changed ? ' (and the starting list on the same games)' : ''}${preFinal ? `, ${left.length} still to play` : ''}`);
  const more = await playMany(decks, left, 'final');
  const finals = decks.map((d, i) => [...(preFinal?.get(key(d)) ?? []), ...more[i]]);
  const recs = finals[0];
  let beforeAfter: string | undefined;
  if (changed) {
    const st0 = deckStats(tested, startCards, finals[1]);
    const st1 = deckStats(tested, cards, finals[0]);
    // paired by game: same opponent, seat and seed
    const won = (r: GameRec | undefined) => (r && (r.winner === 0 || r.winner === 1) ? (r.winner === (r.decks[0] === tested ? 0 : 1) ? 1 : 0) : undefined);
    const bySeed0 = new Map(finals[1].map(r => [r.seed, won(r)]));
    const diffs = finals[0].map(r => [won(r), bySeed0.get(r.seed)]).filter(([a, b]) => a !== undefined && b !== undefined).map(([a, b]) => a! - b!);
    const md = diffs.reduce((x, y) => x + y, 0) / Math.max(1, diffs.length);
    const sd = Math.sqrt(diffs.reduce((x, y) => x + (y - md) ** 2, 0) / Math.max(1, diffs.length - 1));
    const se = sd / Math.sqrt(Math.max(1, diffs.length));
    beforeAfter = `**Starting list vs final list, on the same ${diffs.length} games:** ${(100 * st0.winRate).toFixed(0)}% -> ${(100 * st1.winRate).toFixed(0)}% (difference ${md >= 0 ? '+' : ''}${(100 * md).toFixed(0)} points, 95% range ${(100 * (md - 1.96 * se)).toFixed(0)} to ${(100 * (md + 1.96 * se)).toFixed(0)}); time stuck ${(100 * st0.stuck.nonIdealShare * st0.stuck.stuckRate).toFixed(0)}% -> ${(100 * st1.stuck.nonIdealShare * st1.stuck.stuckRate).toFixed(0)}% of turns.${preFinal ? ' (Half of these games also picked the winner among the finalists, which flatters it a little.)' : ''}`;
    console.log(`  ${beforeAfter.replace(/\*\*/g, '')}`);
  }
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
    title: `Deck report: ${name}`, how, changes: changes.length ? (beforeAfter ? [...changes, beforeAfter] : changes) : undefined, changesTitle,
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
