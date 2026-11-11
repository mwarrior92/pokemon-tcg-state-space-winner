// Alignment with real play: states from commentated tournament games, one per real action, and the
// pilot's choice at each of them compared with the real one.
//
//   node dist/align.js --pilot race --name align-race
//   node dist/align.js --pilot plan2:runs/value-v2/value-model.json --name align-plan2 --logs sim/data/matches
//   node dist/align.js --check                      (replay the logs only: does every action apply?)
//
// Match logs: sim/data/matches/*.json (local, written from the caption transcripts; see matchlog.ts
// for the format). Output in runs/<name>/:
//  - steps.jsonl: every state (board from the mover's side), the real action, the pilot's line,
//    the actions that were interchangeable with the real one, and the match flags;
//  - replay-<game>.md: each decision with its board, real vs pilot;
//  - report.md: how often the pilot's first action is the real one (exactly, or one of the
//    interchangeable ones), by kind of action and by game, and how well the logs replayed.
import * as fs from 'fs';
import * as path from 'path';
import { REPO_ROOT, loadCards } from '../cards';
import { MatchLog, ReplayResult, Step, loadLogs, replayLog } from '../matchlog';
import { pilotLine } from '../playgame';

function arg(name: string, dflt: string): string {
  const i = process.argv.indexOf(`--${name}`);
  return i >= 0 ? process.argv[i + 1] : dflt;
}
const pct = (n: number, d: number) => (d ? `${Math.round((100 * n) / d)}%` : '-');

function main(): void {
  loadCards();
  const check = process.argv.includes('--check');
  const pilot = arg('pilot', 'race');
  const name = arg('name', `align-${pilot.replace(/^(plan2?):.*?([^/\\]+?)(?:\.json)?$/, '$1-$2').replace(/[^a-z0-9-]+/gi, '-')}`);
  const logsDir = path.resolve(REPO_ROOT, arg('logs', 'sim/data/matches'));
  const only = arg('game', '');
  const offense = path.join(REPO_ROOT, 'sim', arg('offense', 'runs/offense-r3b/model.json'));
  const defense = path.join(REPO_ROOT, 'sim', arg('defense', 'runs/defense-r1/model.json'));
  const seat = pilot.startsWith('plan') ? pilot.replace(/^(plan2?):(.*)$/, (_m, k, f) => `${k}:${path.join(REPO_ROOT, 'sim', f)}`) : pilot;
  const logs = loadLogs(logsDir).filter(l => !only || l.id === only);
  if (!logs.length) {
    console.error(`no match logs in ${logsDir}`);
    process.exit(1);
  }
  // --check replays the logs without a pilot (every state's board still goes to the replay files)
  const dir = path.join(REPO_ROOT, 'sim', 'runs', check ? 'align-check' : name);
  fs.mkdirSync(dir, { recursive: true });
  const decide = check ? () => ['end turn'] : (s: any, seed: number) => pilotLine(s, seat, { seed, offense, defense }).line;
  const all: { id: string; log: MatchLog; r: ReplayResult }[] = [];
  for (const { id, log } of logs) {
    const t0 = Date.now();
    const r = replayLog(log, id, decide, 1);
    all.push({ id, log, r });
    console.log(`${id}: ${r.applied} actions applied, ${r.failed.length} failed${r.stopped ? `, stopped: ${r.stopped}` : ''} (${((Date.now() - t0) / 1000).toFixed(0)} s)`);
    for (const f of r.failed) {
      console.log(`    turn ${f.turn} action ${f.k}: ${f.action} - ${f.why}`);
    }
    {
      const L = [`# ${id}: ${log.decks[0].archetype} vs ${log.decks[1].archetype} (game ${log.game}), pilot ${pilot}`, ''];
      for (const s of r.steps) {
        L.push(`### Turn ${s.turn + 1}, action ${s.k + 1} (P${s.mover}, ${s.kind}${s.inferred ? ', inferred' : ''}): ${s.aligned ? 'aligned' : 'different'}`, '',
          '```', s.board.trimEnd(), '```', `- real: ${s.realFull}`, `- pilot: ${s.aiFull}${s.aiLine.length > 1 ? `  (then ${s.aiLine.slice(1).join(' -> ')})` : ''}`);
        if (s.admissible.length > 1) {
          L.push(`- interchangeable real actions: ${s.admissible.join('; ')}`);
        }
        L.push('');
      }
      fs.writeFileSync(path.join(dir, `replay-${id}.md`), L.join('\n') + '\n');
    }
  }
  if (check) {
    return;
  }
  const steps: Step[] = all.flatMap(x => x.r.steps);
  fs.writeFileSync(path.join(dir, 'steps.jsonl'), steps.map(s => JSON.stringify(s)).join('\n') + '\n');
  const scored = (xs: Step[]) => xs.filter(s => !s.inferred);
  const row = (label: string, xs: Step[]) => {
    const n = xs.length;
    return `| ${label} | ${n} | ${pct(xs.filter(s => s.exact).length, n)} | ${pct(xs.filter(s => s.aligned).length, n)} | ${pct(xs.filter(s => s.inLine).length, n)} | ${pct(xs.filter(s => s.sameCard).length, n)} | ${pct(xs.filter(s => s.fullMatch).length, n)} |`;
  };
  const L = [`# Alignment with real play: ${name}`, '',
    `Pilot \`${pilot}\`. ${all.length} real games from commentated tournament matches, a state before each real action (${steps.length} states; actions the commentators did not state but that are implied are replayed and left out of the scores).`, '',
    '| | states | same action | same or interchangeable | in the pilot’s planned turn | same card, any target | same action and choices |', '|---|---|---|---|---|---|---|',
    row('all stated actions', scored(steps))];
  for (const k of ['bench', 'evolve', 'attach', 'tool', 'play', 'ability', 'retreat', 'attack', 'end']) {
    const xs = scored(steps).filter(s => s.kind === k);
    if (xs.length) {
      L.push(row(k, xs));
    }
  }
  L.push('', '- **same action**: the pilot\'s first action is the real one (same card, same target).',
    '- **same or interchangeable**: or it is a later real action of that turn that does not depend on the ones before it (playing it first, then those, gives the same board).',
    '- **in the pilot’s planned turn**: the real action is somewhere in the line the pilot planned from this state (a later step, in any order); for a real "end turn", the pilot planned no attack.',
    '- **same card, any target**: same kind of action with the same card (e.g. the Energy attached to another Pokémon).',
    '- **same action and choices**: also the same answers inside the action (what was discarded, searched, targeted).', '',
    '## Games', '', '| game | decks | states | same or interchangeable | actions applied | failed | replay |', '|---|---|---|---|---|---|---|');
  for (const x of all) {
    const xs = scored(x.r.steps);
    L.push(`| ${x.id} | ${x.log.decks[0].archetype} vs ${x.log.decks[1].archetype} | ${xs.length} | ${pct(xs.filter(s => s.aligned).length, xs.length)} | ${x.r.applied} | ${x.r.failed.length} | ${x.r.stopped ?? 'complete'} |`);
  }
  L.push('', '## Most common disagreements', '');
  const pairs = new Map<string, number>();
  for (const s of scored(steps).filter(s => !s.aligned)) {
    const k = `real **${s.real.replace(/ -> .*$/, ' -> ...')}**, pilot **${s.ai.replace(/ -> .*$/, ' -> ...')}**`;
    pairs.set(k, (pairs.get(k) ?? 0) + 1);
  }
  [...pairs].sort((a, b) => b[1] - a[1]).slice(0, 25).forEach(([k, v]) => L.push(`- ${v} x ${k}`));
  fs.writeFileSync(path.join(dir, 'report.md'), L.join('\n') + '\n');
  console.log(`report: ${path.join(dir, 'report.md')}`);
}

main();
