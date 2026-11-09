// Local archive of every simulated game, for later training and tuning: win-model refits, category
// rates, a card value model for the deck generator, matchup tables and audits of the pilot's play.
// Lives in sim/data/archive/ (gitignored, never committed): games-<YYYY-MM-DD>.jsonl.gz, one game per
// line (each batch of games appended as its own gzip member; about 90 KB per game before compression,
// mostly feature vectors), plus feature-names-<hash>.json for each feature set the vectors use.
//
// Each record keeps what is needed to judge or reuse the game later:
//  - the game (turns with the mover's cheap feature vector, category, prizes, moves) and its result;
//  - the spec to replay it (seed, seats, budget, models; decks as card counts);
//  - version tags: git commit, and a fingerprint of every card in both decks, so games played with a
//    card that has since been fixed can be left out (`fresh`).
import { execSync } from 'child_process';
import { createHash } from 'crypto';
import * as fs from 'fs';
import * as path from 'path';
import * as zlib from 'zlib';
import { REPO_ROOT } from './cards';
import { cardFingerprint } from './cardcheck';
import { engineCard } from './decklist';
import { CHEAP_GROUPS, features } from './features';
import { GameRec, GameSpec } from './playgame';
import { Rng } from './rng';
import { generateState } from './stategen';

export const ARCHIVE_DIR = path.join(REPO_ROOT, 'sim', 'data', 'archive');

export interface ArchiveRec {
  v: 1;
  kind: string;                    // deck-search | deck-finalist | deck-final | playout | ...
  run: string;
  when: string;
  commit: string;
  spec: Omit<GameSpec, 'decks' | 'names' | 'vectors' | 'log'>;
  decks: [[string, number][], [string, number][]];
  fp: Record<string, string>;      // card -> rules fingerprint when played
  features?: string;               // feature-set hash of the turn vectors
  game: GameRec;
}

let commitTag: string | undefined;
function commit(): string {
  if (commitTag === undefined) {
    try {
      const head = execSync('git rev-parse --short HEAD', { cwd: REPO_ROOT, stdio: ['ignore', 'pipe', 'ignore'] }).toString().trim();
      const dirty = execSync('git status --porcelain --untracked-files=no', { cwd: REPO_ROOT, stdio: ['ignore', 'pipe', 'ignore'] }).toString().trim();
      commitTag = head + (dirty ? '+dirty' : '');
    } catch {
      commitTag = 'unknown';
    }
  }
  return commitTag;
}

const fpCache = new Map<string, string>();
function fingerprint(card: string): string {
  let f = fpCache.get(card);
  if (f === undefined) {
    const c = engineCard(card);
    f = c ? cardFingerprint(c) : '';
    fpCache.set(card, f);
  }
  return f;
}

const counts = (cards: string[]): [string, number][] => {
  const m = new Map<string, number>();
  cards.forEach(c => m.set(c, (m.get(c) ?? 0) + 1));
  return [...m];
};
export const expand = (entries: [string, number][]): string[] => entries.flatMap(([c, k]) => Array(k).fill(c));

let featureHash: string | undefined;
/** the hash of the current cheap feature set (and its names file in the archive) */
export function currentFeatureSet(deckA: string[], deckB: string[]): string {
  if (!featureHash) {
    const names = features(generateState(deckA, deckB, new Rng(1)).sim, 0, CHEAP_GROUPS).names;
    featureHash = createHash('sha1').update(names.join('|')).digest('hex').slice(0, 10);
    fs.mkdirSync(ARCHIVE_DIR, { recursive: true });
    const f = path.join(ARCHIVE_DIR, `feature-names-${featureHash}.json`);
    if (!fs.existsSync(f)) {
      fs.writeFileSync(f, JSON.stringify(names));
    }
  }
  return featureHash;
}

/** append finished games (recs[i] played from specs[i]; missing results are skipped) */
export function archiveGames(recs: (GameRec | undefined)[], specs: GameSpec[], kind: string, run: string): void {
  if (process.env.NO_ARCHIVE) {
    return;
  }
  try {
    fs.mkdirSync(ARCHIVE_DIR, { recursive: true });
    const when = new Date().toISOString();
    const file = path.join(ARCHIVE_DIR, `games-${when.slice(0, 10)}.jsonl.gz`);
    const lines: string[] = [];
    recs.forEach((g, i) => {
      const s = specs[i];
      if (!g || !s) {
        return;
      }
      const { decks, names, vectors, log, ...spec } = s;
      void names; void log;
      const fp: Record<string, string> = {};
      new Set([...decks[0], ...decks[1]]).forEach(c => (fp[c] = fingerprint(c)));
      const rec: ArchiveRec = {
        v: 1, kind, run, when, commit: commit(), spec, decks: [counts(decks[0]), counts(decks[1])], fp,
        features: vectors ? currentFeatureSet(decks[0], decks[1]) : undefined, game: g,
      };
      lines.push(JSON.stringify(rec));
    });
    if (lines.length) {
      fs.appendFileSync(file, zlib.gzipSync(lines.join('\n') + '\n'));
    }
  } catch (e) {
    console.error(`archive: could not write games (${(e as Error).message})`);
  }
}

/** every archived game, oldest first; `fresh` leaves out games with a card whose rules changed since */
export function* readArchive(opts: { fresh?: boolean; kinds?: string[] } = {}): Generator<ArchiveRec> {
  if (!fs.existsSync(ARCHIVE_DIR)) {
    return;
  }
  for (const f of fs.readdirSync(ARCHIVE_DIR).filter(x => /^games-.*\.jsonl(\.gz)?$/.test(x)).sort()) {
    let text: string;
    try {
      const buf = fs.readFileSync(path.join(ARCHIVE_DIR, f));
      // a gzip file of several members (one per batch); an interrupted write can leave a cut member
      text = f.endsWith('.gz') ? zlib.gunzipSync(buf, { finishFlush: zlib.constants.Z_SYNC_FLUSH }).toString('utf8') : buf.toString('utf8');
    } catch {
      continue;
    }
    for (const line of text.split('\n')) {
      if (!line) {
        continue;
      }
      let r: ArchiveRec;
      try {
        r = JSON.parse(line);
      } catch {
        continue;                    // a line cut short by an interrupted run
      }
      if (opts.kinds && !opts.kinds.includes(r.kind)) {
        continue;
      }
      if (opts.fresh && !isFresh(r)) {
        continue;
      }
      yield r;
    }
  }
}

export function isFresh(r: ArchiveRec): boolean {
  return Object.entries(r.fp).every(([c, f]) => fingerprint(c) === f);
}

export function featureNames(hash: string): string[] | undefined {
  const f = path.join(ARCHIVE_DIR, `feature-names-${hash}.json`);
  return fs.existsSync(f) ? JSON.parse(fs.readFileSync(f, 'utf8')) : undefined;
}
