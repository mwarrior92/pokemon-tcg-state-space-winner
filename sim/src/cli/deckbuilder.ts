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
//          --starts 3 (starting decks for --seed)  --draw 0 (another number: other random starts)
//          --start meta (for --seed: one start, from the meta lists, as before)
//          --any-shape (starts drawn from all cards alike: about 40 Pokémon and few Trainers)
//          --show-starts (print the starting decks and stop)
//          --recheck 20 (random starts: fresh games for each family's best two before the finalists)
//          --fix 0.5 (share of the changes aimed at the parent deck's most flagged issue; 0 = none)
//          --out <name> (output folder runs/deck-<name>, when it should differ from --name: the
//          starts and the games depend on --name, so two runs to compare share it)
//
// The test: full games from turn 1 against the meta decks, chosen by their share of the decklists,
// both sides piloted by the same policy, the tested deck as player 1 in half the games.
// Starting from a seed card: --starts decks drawn at random around the card's line (deckgen.ts
// randomStarts) that share nothing else. Each is the root of its own family: the population is
// split evenly between the families, a deck is only ever replaced by a change to a deck of its own
// family (one copy at a time, or a whole group out and cards from the pool in: deckgen.ts swapGroup;
// no basic Energy of types the seed's line does not pay with), each family's best two play --recheck
// fresh games, and the finalists are the best deck of each family, so the lists the run ends with are
// different decks, not three versions of one.
// Searching (--seed, or --list with --optimize): a population of decks (the starts and bigger
// variations of them; with --start meta or --list the one start, other meta lists that play the
// seed, and variations). Each generation every deck plays the same few games; in each family the top half survives with its games, the rest are replaced by changes
// to the survivors. Decks are ranked by score = win rate (pulled towards 50% when a deck has few games)
// - stuck weight x (share of turns stuck). The finalists (the best of each family; with one family
// the best few plus the starting list) then play the same half of the final test; the best of those
// plays the other half, as does the start of its family.
// Flags: every game records, turn by turn, why the tested deck could not attack (no Energy to
// attach, Energy attached but no attack paid for, Active stuck with a ready Pokémon behind it), dead
// hands and empty Benches, and how lost games ended (no Pokémon left, deck out, prize cards):
// diagnose.ts. Half of the changes (--fix) are aimed at a flag of the parent deck, drawn by how often
// it came up: a card that answers it comes in for the cards the deck used least (deckgen.ts fixIssue).
// Output in runs/deck-<name>/: report.md, deck.txt, stats.json, games.jsonl.
import * as fs from 'fs';
import * as path from 'path';
import { REPO_ROOT, loadCards, metaDecks, metaShares } from '../cards';
import { isKnownSmoke, isKnownStatic, loadKnownIssues, smokeTest, standardPool, staticCheck } from '../cardcheck';
import { checkLegal, deckFromText, engineCard, formatDeckList } from '../decklist';
import { SeedDeck, candidatePool, fixIssue, mutate, mutateN, randomStarts, seedDeck, swapGroup } from '../deckgen';
import { ISSUE_TEXT, describeDiagnosis, diagnose, fixable } from '../diagnose';
import { unusableCards } from '../usability';
import { archiveGames } from '../archive';
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
  let starts: SeedDeck[] | undefined;   // --seed: the random starting decks, one family each
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
  } else if (seedName && arg('start', 'random') !== 'meta') {
    // several random starts around the seed, each the root of its own family in the search
    name = arg('name', seedName);
    starts = randomStarts(seedName, Math.max(1, Number(arg('starts', '3'))), new Rng(hash(name) + 29 + 1009 * Number(arg('draw', '0'))), !flag('any-shape'));
    cards = starts[0].cards;
    core = starts[0].core;
    pool = starts[0].pool;
    how.push(`Seed card: ${seedName}. ${starts.length} starting decks drawn at random around its line; they share only the line and its Energy.`);
    starts.forEach(sd => how.push(`${sd.how[0].toUpperCase()}${sd.how.slice(1)}.`));
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
  const slug = arg('out', name).toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '');
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
    vectors: true,                   // for the local game archive (training data), see archive.ts
    diagnose: true,                  // the deck flags of every turn (diagnose.ts)
  });
  // every game goes to the local archive (sim/data/archive/, not committed)
  const kindOf = (label: string) => (/^generation/.test(label) ? 'deck-search' : /^finalists/.test(label) ? 'deck-finalist' : 'deck-final');
  const play = async (deck: string[], sched: ReturnType<typeof schedule>, label: string) => {
    const t0 = Date.now();
    let n = 0;
    const specs = sched.map(s => specFor(deck, s));
    const res = await runPool<GameSpec, GameRec>(__filename, specs, {
      workers,
      onResult: () => {
        if (++n % 20 === 0 || n === sched.length) {
          console.log(`    ${label}: ${n}/${sched.length} games (${((Date.now() - t0) / 1000).toFixed(0)} s)`);
        }
      },
    });
    archiveGames(res, specs, kindOf(label), name);
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
    archiveGames(recs, jobs.map(j => j.spec), kindOf(label), name);
    const failed = decks.map((_, di) => recs.filter((r, k) => !r && jobs[k].di === di).length);
    if (failed.some(Boolean)) {
      console.log(`    ${label}: games that did not finish (engine error), by deck: ${failed.join(', ')}`);
    }
    return decks.map((_, di) => recs.filter((r, k) => r && jobs[k].di === di) as GameRec[]);
  };
  starts?.forEach((sd, i) => fs.writeFileSync(path.join(dir, `start-${i + 1}.txt`), formatDeckList(sd.cards)));
  if (flag('show-starts')) {
    console.log(`# ${name}: ${how.join('\n  ')}`);
    starts?.forEach((sd, i) => console.log(`\n## start ${i + 1} (start-${i + 1}.txt)\n${formatDeckList(sd.cards)}`));
    return;
  }
  let startCards = cards.slice();
  const startBad = unusableCards(cards);
  if (startBad.length) {
    how.push(`Cards in the starting list that the rules check says cannot be used: ${startBad.map(u => `${engineCard(u.card)?.name} (${u.reason})`).join('; ')}.`);
  }
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
    interface Cand { id: number; cards: string[]; parent?: number; change: string; games: GameRec[]; family: number }
    const all = new Map<string, Cand>();
    const byId = new Map<number, Cand>();
    const add = (cards: string[], change: string, parent?: number, family = parent ? byId.get(parent)!.family : 0): Cand | undefined => {
      const k = key(cards);
      if (all.has(k)) {
        return undefined;
      }
      const c: Cand = { id: all.size + 1, cards: cards.slice().sort(), parent, change, games: [], family };
      all.set(k, c);
      byId.set(c.id, c);
      return c;
    };
    // `usual`: the win rate of the decks being compared, taken together
    const rank = (c: Cand, usual = 0.5) => {
      const st = deckStats(tested, c.cards, c.games);
      // a deck none of whose games finished (the engine cannot play it) ranks last
      if (!st.games) {
        return { st, score: -1 };
      }
      // pulled towards the usual win rate by 4 imaginary games, so 8 of 10 does not outrank 30 of 45.
      // (Towards 50% it favoured new decks wherever the decks win 10% to 20%: 1 of 10 counted as
      // 21%, 6 of 40 as 18%.)
      return { st, score: deckScore(st, stuckWeight) - st.winRate + (st.wins + 4 * usual) / (st.games + 4) };
    };
    const rankAll = (cs: Cand[]) => {
      const sts = cs.map(c => deckStats(tested, c.cards, c.games));
      const n = sts.reduce((x, st) => x + st.games, 0);
      const usual = n ? sts.reduce((x, st) => x + st.wins, 0) / n : 0.5;
      return cs.map(c => ({ c, ...rank(c, usual) })).sort((a, b) => b.score - a.score);
    };
    const label = (c: Cand) => (c.parent ? `#${c.id} (#${c.parent}: ${c.change})` : `#${c.id} (${c.change})`);
    // the families: one for each starting deck (one in all for a list or a meta start)
    const roots: Cand[] = starts ? starts.map((sd, i) => add(sd.cards, `start ${i + 1}`, undefined, i)!) : [add(startCards, 'starting list')!];
    const famPool = (f: number) => (starts ? starts[f].pool : pool);
    const famSize = Math.max(2, Math.ceil(popSize / roots.length));
    const fam = (c: Cand) => (roots.length > 1 ? `family ${c.family + 1} ` : '');
    let startC = roots[0];
    let pop: Cand[] = roots.slice();
    if (!starts) {
      for (const a of alternatives.slice(0, Math.floor(popSize / 2))) {
        const c = add(a.cards, a.what);
        if (c) {
          pop.push(c);
        }
      }
    }
    roots.forEach((root, f) => {
      for (let guard = 0; pop.filter(c => c.family === f).length < famSize && guard < famSize * 20; guard++) {
        // bigger jumps for a seed build (a rough first guess) than for a hand-made list
        // a random start: every other variant has whole groups swapped (one, or two)
        let m = starts && guard % 2 === 0 ? swapGroup(root.cards, famPool(f), core, rng)
          : mutateN(root.cards, famPool(f), core, rng, seedName ? rng.int(3, 8) : rng.int(2, 4));
        if (m && starts && guard % 4 === 0) {
          m = swapGroup(m.cards, famPool(f), core, rng) ?? m;
        }
        const c = m && add(m.cards, `variant: ${diffText(root.cards, m.cards)}`, root.id);
        if (c) {
          pop.push(c);
        }
      }
    });
    console.log(`  search: ${pop.length} decks${roots.length > 1 ? ` in ${roots.length} families` : ''}, ${generations} generations of ${perGen} games each`);
    const pools = new Map<number, string[]>();
    const fixShare = Number(arg('fix', '0.5'));
    const fixes = new Map<string, number>();              // flag -> changes aimed at it
    let played = 0;
    let ranked: { c: Cand; st: DeckStats; score: number }[] = [];
    for (let g = 0; g < generations; g++) {
      const sched = schedule(top, perGen, base + 101 * (g + 1));
      const recsBy = await playMany(pop.map(c => c.cards), sched, `generation ${g + 1}`);
      pop.forEach((c, i) => c.games.push(...recsBy[i]));
      played += pop.length * sched.length;
      ranked = rankAll(pop);
      console.log(`  generation ${g + 1}:`);
      ranked.forEach(r => console.log(`    ${r.score.toFixed(3)}  ${pctS(r.st.winRate)} of ${r.st.games}  ${fam(r.c)}${label(r.c)}`));
      const best = ranked[0];
      const famBest = roots.length > 1 ? `; best of each family: ${roots.map((_r, f) => ranked.find(r => r.c.family === f)!).map(r => `${pctS(r.st.winRate)} of ${r.st.games}`).join(', ')}; all decks together ${pctS(ranked.reduce((x, r) => x + r.st.wins, 0) / Math.max(1, ranked.reduce((x, r) => x + r.st.games, 0)))}` : '';
      const popDiag = diagnose(tested, pop.flatMap(c => c.games));
      console.log(`    flags, all decks: ${describeDiagnosis(popDiag)}`);
      changes.push(`Generation ${g + 1}: ${pop.length} decks, ${perGen} games each; leader ${label(best.c)}, ${pctS(best.st.winRate)} won over its ${best.st.games} games${famBest}; most flagged over all decks: ${describeDiagnosis(popDiag, 2)}`);
      if (g === generations - 1) {
        break;
      }
      // in each family the top half survives; the rest are replaced by changes to that family's
      // survivors (better ones more often). A random start is a rough list: in the first half of the
      // generations its family changes several cards at a time.
      const next: Cand[] = [];
      roots.forEach((_root, f) => {
        const mine = ranked.filter(r => r.c.family === f).map(r => r.c);
        const size = Math.max(mine.length, roots.length > 1 ? famSize : popSize);
        const keep = mine.slice(0, Math.ceil(mine.length / 2));
        const born: Cand[] = [];
        // each survivor's flags and how much it used each card, from its own games
        const seen = new Map(keep.map(c => [c.id, {
          issues: fixable(diagnose(tested, c.games)),
          used: new Map(ranked.find(r => r.c === c)!.st.usage.map(u => [u.card, u.games])),
        }]));
        for (let guard = 0; keep.length + born.length < size && guard < size * 20; guard++) {
          const parent = keep[Math.floor(keep.length * rng.next() ** 1.5)];
          if (!pools.has(parent.id)) {
            pools.set(parent.id, [...new Set(candidatePool(parent.cards, starts?.[f].energyTypes).concat(famPool(f)))]);
          }
          // a random start: a whole group swapped in half of the changes early on, a quarter later
          const big = !!starts && g < Math.floor(generations / 2);
          // a change aimed at one of the parent's flags, drawn by how often it came up
          const flags = seen.get(parent.id)!;
          const tot = flags.issues.reduce((x, i) => x + i.weight, 0);
          let aimed: ReturnType<typeof fixIssue>;
          if (tot > 0 && rng.chance(fixShare)) {
            let r = rng.next() * tot;
            const issue = (flags.issues.find(i => (r -= i.weight) <= 0) ?? flags.issues[0]).issue;
            aimed = fixIssue(parent.cards, pools.get(parent.id)!, core, rng, issue, flags.used);
            const ca = aimed && add(aimed.cards, aimed.what, parent.id);
            if (ca) {
              fixes.set(issue, (fixes.get(issue) ?? 0) + 1);
              born.push(ca);
            }
            if (aimed) {
              continue;
            }
          }
          const group = !!starts && rng.chance(big ? 0.5 : 0.25);
          const m = group ? swapGroup(parent.cards, pools.get(parent.id)!, core, rng)
            : big ? mutateN(parent.cards, pools.get(parent.id)!, core, rng, rng.int(2, 5)) : mutate(parent.cards, pools.get(parent.id)!, core, rng);
          const c = m && add(m.cards, big && !group ? diffText(parent.cards, m.cards) : m.what, parent.id);
          if (c) {
            born.push(c);
          }
        }
        next.push(...keep, ...born);
      });
      pop = next;
    }

    // random starts: ten games tell a 10% deck from a 20% one badly, so each family's best two play
    // fresh games before its best is taken
    const recheck = Number(arg('recheck', starts ? '20' : '0'));
    if (recheck > 0 && roots.length > 1) {
      const again = roots.flatMap((_r, f) => ranked.filter(r => r.c.family === f).slice(0, 2).map(r => r.c));
      const recsBy = await playMany(again.map(c => c.cards), schedule(top, recheck, base + 101 * (generations + 1) + 53), 'generation recheck');
      again.forEach((c, i) => c.games.push(...recsBy[i]));
      played += again.length * recheck;
      const rest = ranked.filter(r => !again.includes(r.c));
      ranked = [...rankAll(again), ...rest];
      console.log('  recheck:');
      ranked.slice(0, again.length).forEach(r => console.log(`    ${r.score.toFixed(3)}  ${pctS(r.st.winRate)} of ${r.st.games}  ${fam(r.c)}${label(r.c)}`));
      changes.push(`Each family's best two on ${recheck} more games: ${ranked.slice(0, again.length).map(r => `${fam(r.c)}#${r.c.id} ${pctS(r.st.winRate)} of ${r.st.games}`).join('; ')}`);
    }

    // finalists (and the starting list) on the same half of the final test
    // several families: the best deck of each (then the next best of any, up to --finalists)
    const fin = roots.length > 1
      ? roots.map((_r, f) => ranked.find(r => r.c.family === f)!.c)
      : ranked.slice(0, nFinal).map(r => r.c);
    ranked.forEach(r => {
      if (roots.length > 1 && fin.length < nFinal && !fin.includes(r.c)) {
        fin.push(r.c);
      }
    });
    if (roots.length === 1 && !fin.includes(startC)) {
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
    // the before/after comparison is with the start of the winner's own family
    startC = roots[champ.family];
    startCards = startC.cards.slice();
    changes.push(`Finalists on the same ${half1.length} games against the whole field: ${finRanked.map(f => `${fam(f.c)}#${f.c.id}${roots.includes(f.c) ? ' (starting list)' : ''} ${pctS(f.st.winRate)} (score ${f.score.toFixed(2)})`).join('; ')}`);
    // the champion's family line
    const lineage: Cand[] = [];
    for (let c: Cand | undefined = champ; c; c = c.parent ? byId.get(c.parent) : undefined) {
      lineage.unshift(c);
    }
    if (champ !== startC) {
      changes.push(`Winner ${fam(champ)}#${champ.id}, found by: ${lineage.map(c => label(c)).join(' -> ')}`);
      changes.push(`Net change from ${roots.length > 1 ? `its family's starting list (start-${champ.family + 1}.txt)` : 'the starting list'}: ${diffText(startCards, champ.cards)}`);
    } else {
      changes.push('No variant beat the starting list in the finalist games; the list is unchanged.');
    }
    const shared = (a: string[], b: string[]) => {
      const rest = b.slice();
      return a.filter(n => {
        const i = rest.indexOf(n);
        return i >= 0 && rest.splice(i, 1).length > 0;
      }).length;
    };
    finRanked.slice(1).filter(f => roots.length > 1 || f.c !== startC).forEach((f, i) => {
      fs.writeFileSync(path.join(dir, `finalist-${i + 2}.txt`), formatDeckList(f.c.cards));
      changes.push(f.c.family !== champ.family
        ? `Runner-up ${fam(f.c)}#${f.c.id} (finalist-${i + 2}.txt): another deck, ${shared(champ.cards, f.c.cards)} of 60 cards shared with the winner; from its own start (start-${f.c.family + 1}.txt): ${diffText(roots[f.c.family].cards, f.c.cards)}`
        : `Runner-up ${fam(f.c)}#${f.c.id} (finalist-${i + 2}.txt), compared with the winner: ${diffText(champ.cards, f.c.cards)}`);
    });
    if (fixes.size) {
      changes.push(`Changes aimed at a flag: ${[...fixes].sort((a, b) => b[1] - a[1]).map(([i, k]) => `${ISSUE_TEXT[i as keyof typeof ISSUE_TEXT]} ${k}`).join('; ')}.`);
    }
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
    beforeAfter = `**Starting list vs final list, on the same ${diffs.length} games:** ${(100 * st0.winRate).toFixed(0)}% -> ${(100 * st1.winRate).toFixed(0)}% (difference ${md >= 0 ? '+' : ''}${(100 * md).toFixed(0)} points, 95% range ${(100 * (md - 1.96 * se)).toFixed(0)} to ${(100 * (md + 1.96 * se)).toFixed(0)}); time stuck ${(100 * st0.stuck.nonIdealShare * st0.stuck.stuckRate).toFixed(0)}% -> ${(100 * st1.stuck.nonIdealShare * st1.stuck.stuckRate).toFixed(0)}% of turns.${preFinal && preFinal.has(key(startCards)) ? ' (Half of these games also picked the winner among the finalists, which flatters it a little.)' : ''}`;
    console.log(`  ${beforeAfter.replace(/\*\*/g, '')}`);
  }
  fs.writeFileSync(path.join(dir, 'games.jsonl'), recs.map(r => JSON.stringify(r)).join('\n') + '\n');
  const stats = deckStats(tested, cards, recs);
  const diagnosis = [`Final list, ${recs.length} games: ${describeDiagnosis(diagnose(tested, recs))}.`];
  if (changed) {
    diagnosis.push(`Starting list, ${finals[1].length} games: ${describeDiagnosis(diagnose(tested, finals[1]))}.`);
  }
  console.log(`  flags: ${diagnosis.join(' ')}`);
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
    diagnosis,
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
