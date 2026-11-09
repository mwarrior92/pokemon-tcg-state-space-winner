// Statistics and the written report for a tested deck (cli/deckbuilder.ts).
//
// Everything is measured on the tested deck's own turns in its games against the meta field:
//   wins         overall (Wilson 95% interval), per matchup, how games ended
//   stuck        turns in ideal / non-ideal categories (reference/category-rates.json: the side to
//                move wins >= 75% / <= 40% there), how often a non-ideal spot persists to the next
//                own turn, and recovery: wins from the first non-ideal spot of a game against what
//                that category predicts
//   play style   which attacks / abilities take the prizes, how fast, the usual opening, and the
//                cards used more in wins than in losses
import * as fs from 'fs';
import * as path from 'path';
import { REPO_ROOT } from './cards';
import { PokemonCard } from './engine';
import { engineCard, formatDeckList } from './decklist';
import { GameRec } from './playgame';

export interface DeckStats {
  name: string;
  games: number;
  wins: number;
  winRate: number;
  ci: [number, number];
  byMatchup: { opponent: string; games: number; wins: number; rate: number }[];
  endings: Record<string, number>;            // how won / lost games ended
  turnsPerGame: number;
  firstPrizeTurn: number | undefined;         // median own-turn index of the first prize
  prizesPerTurn: number;
  stuck: {
    idealShare: number; idealWin: number;
    nonIdealShare: number; stuckRate: number;
    entered: number; enteredShare: number; recovered: number; expected: number;
    topStuck: { cat: string; turns: number; stuckRate: number }[];
  };
  attackers: { what: string; who: string; prizes: number; share: number; uses: number }[];
  opening: { action: string; share: number }[];
  winCards: { card: string; wins: number; losses: number }[];
  lossCards: { card: string; wins: number; losses: number }[];
}

let ref: Record<string, number> | undefined;
export function categoryRates(): Record<string, number> {
  if (!ref) {
    const j = JSON.parse(fs.readFileSync(path.join(REPO_ROOT, 'sim', 'reference', 'category-rates.json'), 'utf8'));
    ref = Object.fromEntries(Object.entries(j.categories).map(([k, v]: [string, any]) => [k, v.winRate]));
  }
  return ref!;
}

export function wilson(w: number, n: number): [number, number] {
  if (!n) {
    return [0, 1];
  }
  const z = 1.96, p = w / n, d = 1 + z * z / n;
  const c = p + z * z / (2 * n), m = z * Math.sqrt(p * (1 - p) / n + z * z / (4 * n * n));
  return [(c - m) / d, (c + m) / d];
}

/** what an action label is about: "attack Phantom Dive" -> attack Phantom Dive, etc. */
function actionOf(label: string): { kind: string; what: string } {
  const head = label.split(' | ')[0];
  let m: RegExpExecArray | null;
  if ((m = /^attack (.+)$/.exec(head))) return { kind: 'attack', what: m[1] };
  if ((m = /^ability (.+?) \((?:active|bench\d) (.+)\)$/.exec(head))) return { kind: 'ability', what: `${m[1]} (${m[2]})` };
  if ((m = /^play (.+)$/.exec(head))) return { kind: 'play', what: m[1] };
  if ((m = /^bench (.+)$/.exec(head))) return { kind: 'bench', what: m[1] };
  if ((m = /^evolve (?:active|bench\d) .+ -> (.+)$/.exec(head))) return { kind: 'evolve', what: m[1] };
  if ((m = /^attach (.+?) -> (?:active|bench\d) (.+)$/.exec(head))) return { kind: 'attach', what: `${m[1]} to ${m[2]}` };
  if ((m = /^tool (.+?) -> /.exec(head))) return { kind: 'tool', what: m[1] };
  if (/^retreat/.test(head)) return { kind: 'retreat', what: 'retreat' };
  if ((m = /^use stadium (.+)$/.exec(head))) return { kind: 'stadium', what: m[1] };
  return { kind: 'other', what: head };
}

export function deckStats(name: string, cards: string[], games: GameRec[]): DeckStats {
  const rates = categoryRates();
  const seatOf = (g: GameRec) => (g.decks[0] === name ? 0 : 1);
  const decided = games.filter(g => g.winner === 0 || g.winner === 1);
  const wins = decided.filter(g => g.winner === seatOf(g)).length;
  // attacks -> which Pokémon in the deck have them
  const attackOwners = new Map<string, Set<string>>();
  for (const n of new Set(cards)) {
    const c = engineCard(n);
    if (c instanceof PokemonCard) {
      c.attacks.forEach(a => {
        const s = attackOwners.get(a.name) ?? new Set();
        s.add(c.name);
        attackOwners.set(a.name, s);
      });
    }
  }
  const match = new Map<string, { games: number; wins: number }>();
  const endings: Record<string, number> = {};
  let ownTurns = 0, prizes = 0, ideal = 0, idealWon = 0, nonIdeal = 0, stuckNext = 0, nonIdealWithNext = 0;
  let entered = 0, recovered = 0, expected = 0;
  const firstPrize: number[] = [];
  const stuckCat = new Map<string, { turns: number; stuck: number; withNext: number }>();
  const attack = new Map<string, { prizes: number; uses: number }>();
  const opening = new Map<string, number>();
  const useW = new Map<string, number>(), useL = new Map<string, number>();
  let gamesW = 0, gamesL = 0;
  for (const g of decided) {
    const me = seatOf(g);
    const won = g.winner === me;
    const opp = g.decks[1 - me];
    const mm = match.get(opp) ?? { games: 0, wins: 0 };
    mm.games++;
    mm.wins += won ? 1 : 0;
    match.set(opp, mm);
    const key = `${won ? 'won' : 'lost'}: ${g.reason}`;
    endings[key] = (endings[key] ?? 0) + 1;
    won ? gamesW++ : gamesL++;
    const own = g.turns.filter(t => t.mover === me);
    let firstBad = true;
    own.forEach((t, i) => {
      ownTurns++;
      prizes += t.took;
      const r = rates[t.cat];
      if (r !== undefined && r >= 0.75) {
        ideal++;
        idealWon += won ? 1 : 0;
      }
      if (r !== undefined && r <= 0.40) {
        nonIdeal++;
        const sc = stuckCat.get(t.cat) ?? { turns: 0, stuck: 0, withNext: 0 };
        sc.turns++;
        if (own[i + 1]) {
          nonIdealWithNext++;
          sc.withNext++;
          if (own[i + 1].cat === t.cat) {
            stuckNext++;
            sc.stuck++;
          }
        }
        stuckCat.set(t.cat, sc);
        if (firstBad) {
          firstBad = false;
          entered++;
          recovered += won ? 1 : 0;
          expected += r;
        }
      }
      // play style from the moves
      const line = t.line ?? [];
      if (t.took > 0) {
        const hit = [...line].reverse().map(actionOf).find(a => a.kind === 'attack' || a.kind === 'ability');
        const k = hit ? (hit.kind === 'attack' ? `attack ${hit.what}` : `ability ${hit.what}`) : 'other (effects, checkup)';
        const a = attack.get(k) ?? { prizes: 0, uses: 0 };
        a.prizes += t.took;
        attack.set(k, a);
      }
      for (const l of line) {
        const a = actionOf(l);
        if (a.kind === 'attack') {
          const k = `attack ${a.what}`;
          const x = attack.get(k) ?? { prizes: 0, uses: 0 };
          x.uses++;
          attack.set(k, x);
        }
        // cards played (attacks and abilities are in the prize table instead)
        const card = a.kind === 'attach' ? a.what.split(' to ')[0] : ['play', 'bench', 'evolve', 'tool', 'stadium'].includes(a.kind) ? a.what : undefined;
        if (card) {
          const m = won ? useW : useL;
          m.set(card, (m.get(card) ?? 0) + 1);
        }
      }
      if (i < 2) {
        for (const l of new Set(line.map(x => { const a = actionOf(x); return a.kind === a.what ? a.kind : `${a.kind} ${a.what}`; }))) {
          opening.set(l, (opening.get(l) ?? 0) + 1);
        }
      }
    });
    const fp = own.findIndex(t => t.took > 0);
    if (fp >= 0) {
      firstPrize.push(fp + 1);
    }
  }
  const n = decided.length;
  firstPrize.sort((a, b) => a - b);
  const totalPrizes = [...attack.values()].reduce((s, a) => s + a.prizes, 0);
  const attackers = [...attack].filter(([, a]) => a.prizes > 0 || a.uses > 0).map(([k, a]) => {
    const what = k.replace(/^(attack|ability) /, '');
    const who = k.startsWith('attack ') ? [...(attackOwners.get(what) ?? [])].join(' / ') : (/\((.+)\)$/.exec(what)?.[1] ?? '');
    return { what: k, who, prizes: a.prizes, share: totalPrizes ? a.prizes / totalPrizes : 0, uses: a.uses };
  }).sort((a, b) => b.prizes - a.prizes || b.uses - a.uses);
  const perGame = (m: Map<string, number>, k: string, g: number) => (m.get(k) ?? 0) / Math.max(1, g);
  const cardsUsed = [...new Set([...useW.keys(), ...useL.keys()])].filter(k => (useW.get(k) ?? 0) + (useL.get(k) ?? 0) >= 5);
  const diff = cardsUsed.map(k => ({ card: k, wins: perGame(useW, k, gamesW), losses: perGame(useL, k, gamesL) }));
  const firstTwo = decided.length;
  return {
    name, games: n, wins, winRate: n ? wins / n : 0, ci: wilson(wins, n),
    byMatchup: [...match].map(([opponent, v]) => ({ opponent, games: v.games, wins: v.wins, rate: v.wins / v.games })).sort((a, b) => b.games - a.games),
    endings,
    turnsPerGame: n ? decided.reduce((s, g) => s + g.turns.length, 0) / n : 0,
    firstPrizeTurn: firstPrize.length ? firstPrize[Math.floor(firstPrize.length / 2)] : undefined,
    prizesPerTurn: ownTurns ? prizes / ownTurns : 0,
    stuck: {
      idealShare: ownTurns ? ideal / ownTurns : 0, idealWin: ideal ? idealWon / ideal : 0,
      nonIdealShare: ownTurns ? nonIdeal / ownTurns : 0, stuckRate: nonIdealWithNext ? stuckNext / nonIdealWithNext : 0,
      entered, enteredShare: n ? entered / n : 0, recovered: entered ? recovered / entered : 0, expected: entered ? expected / entered : 0,
      topStuck: [...stuckCat].map(([cat, v]) => ({ cat, turns: v.turns, stuckRate: v.withNext ? v.stuck / v.withNext : 0 })).sort((a, b) => b.turns - a.turns).slice(0, 4),
    },
    attackers,
    opening: [...opening].map(([action, k]) => ({ action, share: k / Math.max(1, firstTwo) })).sort((a, b) => b.share - a.share).slice(0, 8),
    winCards: diff.filter(d => d.wins > d.losses).sort((a, b) => (b.wins - b.losses) - (a.wins - a.losses)).slice(0, 6),
    lossCards: diff.filter(d => d.losses > d.wins).sort((a, b) => (b.losses - b.wins) - (a.losses - a.wins)).slice(0, 4),
  };
}

/** One score for comparing versions of a deck: win rate, minus a penalty for time spent stuck. */
export function deckScore(s: DeckStats, stuckWeight = 0.25): number {
  return s.winRate - stuckWeight * s.stuck.nonIdealShare * s.stuck.stuckRate;
}

const pct = (x: number) => `${(100 * x).toFixed(0)}%`;

function advice(s: DeckStats): string[] {
  const out: string[] = [];
  const main = s.attackers.filter(a => a.prizes > 0).slice(0, 3);
  if (main.length) {
    out.push(`**Win condition.** Prizes come mostly from ${main.map(a => `${a.what.replace(/^attack /, '')}${a.who ? ` (${a.who})` : ''} – ${pct(a.share)} of prizes`).join('; ')}. Build towards ${main[0].who || main[0].what} first.`);
  }
  if (s.firstPrizeTurn) {
    out.push(`**Tempo.** First prize typically on its own turn ${s.firstPrizeTurn}; ${s.prizesPerTurn.toFixed(2)} prizes per own turn.`);
  }
  const open = s.opening.filter(o => !o.action.startsWith('other')).slice(0, 5);
  if (open.length) {
    out.push(`**Opening (first two turns).** Most games: ${open.map(o => `${o.action} (${pct(o.share)})`).join(', ')}.`);
  }
  if (s.winCards.length) {
    out.push(`**Cards that show up in wins.** ${s.winCards.map(c => `${c.card} (${c.wins.toFixed(1)} uses per won game vs ${c.losses.toFixed(1)} per lost game)`).join('; ')}. Prioritise getting these into play / using them.`);
  }
  if (s.lossCards.length) {
    out.push(`**Cards that show up in losses.** ${s.lossCards.map(c => `${c.card} (${c.losses.toFixed(1)} vs ${c.wins.toFixed(1)})`).join('; ')} – often a sign of playing from behind with them, or of a weak slot.`);
  }
  const st = s.stuck.topStuck[0];
  if (st) {
    const tips: string[] = [];
    if (/ready:0-/.test(st.cat)) tips.push('get a second attacker ready earlier (bench and power up the next attacker before the first is Knocked Out)');
    if (/threat:yes/.test(st.cat)) tips.push('avoid leaving the Active in Knock Out range (retreat, switch, or put a cheaper Pokémon in front)');
    if (/race:behind/.test(st.cat) && /ko:no/.test(st.cat)) tips.push('keep a way to take a prize every turn (gust for weak benched targets, damage spread)');
    out.push(`**Where it gets stuck.** Most often "${st.cat}" (${st.turns} turns; still there the next turn ${pct(st.stuckRate)} of the time). ${tips.length ? `To get out: ${tips.join('; ')}.` : ''}`);
  }
  const good = s.byMatchup.filter(m => m.games >= 4).sort((a, b) => b.rate - a.rate);
  if (good.length >= 2) {
    out.push(`**Matchups.** Best against ${good.slice(0, 2).map(m => `${m.opponent} (${pct(m.rate)})`).join(', ')}; weakest against ${good.slice(-2).reverse().map(m => `${m.opponent} (${pct(m.rate)})`).join(', ')}.`);
  }
  return out;
}

export function renderReport(s: DeckStats, cards: string[], extra: { title: string; how: string[]; changes?: string[]; cardIssues?: string[] }): string {
  const L: string[] = [];
  L.push(`# ${extra.title}`);
  L.push('');
  extra.how.forEach(h => L.push(`- ${h}`));
  L.push('');
  L.push('## Deck list');
  L.push('');
  L.push('```');
  L.push(formatDeckList(cards).trimEnd());
  L.push('```');
  if (extra.changes?.length) {
    L.push('');
    L.push('## Changes made by the optimiser');
    L.push('');
    extra.changes.forEach(c => L.push(`- ${c}`));
  }
  L.push('');
  L.push('## Win statistics');
  L.push('');
  L.push(`- **Win rate against the meta field: ${pct(s.winRate)}** (95% range ${pct(s.ci[0])}–${pct(s.ci[1])}), ${s.wins} of ${s.games} games.`);
  L.push(`- Games last ${s.turnsPerGame.toFixed(1)} turns on average; ${s.prizesPerTurn.toFixed(2)} prizes per own turn; first prize on own turn ${s.firstPrizeTurn ?? '-'} (median).`);
  L.push(`- How games ended: ${Object.entries(s.endings).sort((a, b) => b[1] - a[1]).map(([k, v]) => `${k} ${v}`).join(', ')}.`);
  L.push('');
  L.push('## Meta matchups');
  L.push('');
  L.push('| opponent | games | won | win rate (95% range) |');
  L.push('|---|---|---|---|');
  s.byMatchup.forEach(m => {
    const ci = wilson(m.wins, m.games);
    L.push(`| ${m.opponent} | ${m.games} | ${m.wins} | ${pct(m.rate)} (${pct(ci[0])}–${pct(ci[1])}) |`);
  });
  L.push('');
  L.push('## Stuck statistics');
  L.push('');
  const st = s.stuck;
  L.push(`- Turns in an **ideal** spot (the side to move usually wins from there): ${pct(st.idealShare)}; it won ${pct(st.idealWin)} of those games.`);
  L.push(`- Turns in a **non-ideal** spot (the side to move usually loses): ${pct(st.nonIdealShare)}; **still in the same spot on its next turn ${pct(st.stuckRate)}** of the time.`);
  L.push(`- Games that reached a non-ideal spot: ${st.entered} (${pct(st.enteredShare)}); won ${pct(st.recovered)} of them, against ${pct(st.expected)} expected for an average deck (${st.recovered >= st.expected ? '+' : ''}${(100 * (st.recovered - st.expected)).toFixed(0)} points).`);
  if (st.topStuck.length) {
    L.push('');
    L.push('| most frequent non-ideal spots | turns | stuck next turn |');
    L.push('|---|---|---|');
    st.topStuck.forEach(t => L.push(`| ${t.cat} | ${t.turns} | ${pct(t.stuckRate)} |`));
  }
  L.push('');
  L.push('## How it takes prizes');
  L.push('');
  L.push('| attack / ability | Pokémon | prizes | share | times used |');
  L.push('|---|---|---|---|---|');
  s.attackers.slice(0, 8).forEach(a => L.push(`| ${a.what} | ${a.who} | ${a.prizes} | ${pct(a.share)} | ${a.uses} |`));
  L.push('');
  L.push('## Recommended play style');
  L.push('');
  advice(s).forEach(a => L.push(`- ${a}`));
  if (extra.cardIssues?.length) {
    L.push('');
    L.push('## Card implementation checks');
    L.push('');
    extra.cardIssues.forEach(c => L.push(`- ${c}`));
  }
  L.push('');
  L.push('## How to read this');
  L.push('');
  L.push('- Games are full games from turn 1 against meta decks chosen by their share of the decklists, piloted by the same simulator policy on both sides. Set-up choices (opening Active and Bench) and the opponent\'s prompts during a turn are made at random.');
  L.push('- The result says how well this simulator plays the deck, not only how strong the deck is: decks whose plan relies on long ability chains are likely under-piloted. Compare a new deck with known meta decks tested the same way.');
  return L.join('\n') + '\n';
}
