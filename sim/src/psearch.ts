// Parallel one-turn search: one coordinator, N worker threads, one transposition table.
//
// Every position is identified by its 64-bit stateHash. The coordinator owns the table: when a
// worker reports a child whose hash is already known, the two paths have converged and the child
// is not queued again, so no two workers ever expand the same position. Positions cannot be sent
// between threads (prompt continuations are closures, cards have prototypes), so a work item is
// the position's hash plus the path of replayable steps from the root (search.ts `Step`); chance is
// fixed per state (Sim.chanceSeed) and per action, so a worker that does not hold the position
// rebuilds it exactly by replaying the path, and checks the hash. Each worker caches the positions
// it created, and the coordinator prefers to hand a position to the worker that created it, so
// most expansions need no replay.
//
// The same bundled script runs as coordinator and worker: call serveSearch(factory) at top level
// (it does nothing on the main thread) and create a ParallelSearch on the main thread.
import { Worker, isMainThread, parentPort, workerData } from 'worker_threads';
import { prizesLeft } from './rules';
import { Sim } from './sim';
import { DagNode, ExpandOptions, SearchOptions, Step, backUpValues, bestLine, children, replayStep, stateHash } from './search';
import { autoWorkers } from './pool';

/** Builds the root position from a small, serializable description (e.g. generator seed + decks).
 *  Must be deterministic: coordinator and workers build the same root from the same spec. */
export type RootFactory = (spec: any) => Sim;

interface ExpandMsg { t: 'expand'; id: number; spec: any; specKey: string; key: string; path: Step[]; opts: ExpandOptions }
interface KidOut { key?: string; terminal: boolean; prizes: number; label: string; step: Step }
interface KidsMsg { t: 'kids'; id: number; kids: KidOut[]; replayed: boolean; error?: string }

// ---------------------------------------------------------------- worker side

const CACHE = 300;   // positions kept per worker (~0.3 MB each)

export function serveSearch(factory: RootFactory): void {
  if (isMainThread || !parentPort || !workerData?.psearch) {
    return;
  }
  let specKey = '';
  let root: Sim | undefined;
  const cache = new Map<string, Sim>();
  parentPort.on('message', (m: ExpandMsg) => {
    if (m.t !== 'expand') {
      return;
    }
    let reply: KidsMsg;
    try {
      if (m.specKey !== specKey) {
        specKey = m.specKey;
        root = factory(m.spec);
        cache.clear();
      }
      const mover = root!.state.activePlayer;
      const start = prizesLeft(root!.state.players[mover]);
      let sim = cache.get(m.key);
      let replayed = false;
      if (sim) {
        cache.delete(m.key);
      } else {
        sim = root!;
        for (const step of m.path) {
          const c = replayStep(sim, step, mover, start, m.opts);
          if (!c) {
            throw new Error(`replay failed at "${step.o}"`);
          }
          sim = c.sim;
        }
        if (stateHash(sim.state) !== m.key) {
          throw new Error('replay reached a different position');
        }
        replayed = true;
      }
      const kids = children(sim, mover, start, m.opts);
      const out: KidOut[] = [];
      for (const c of kids) {
        let key: string | undefined;
        if (!c.terminal) {
          key = stateHash(c.sim.state);
          cache.set(key, c.sim);
          if (cache.size > CACHE) {
            cache.delete(cache.keys().next().value!);
          }
        }
        out.push({ key, terminal: c.terminal, prizes: c.prizes, label: c.label, step: c.step });
      }
      reply = { t: 'kids', id: m.id, kids: out, replayed };
    } catch (e) {
      reply = { t: 'kids', id: m.id, kids: [], replayed: false, error: String((e as Error)?.message ?? e) };
    }
    parentPort!.postMessage(reply);
  });
}

// ---------------------------------------------------------------- coordinator

interface PNode extends DagNode {
  key: string;
  depth: number;
  path: Step[];
  owner: number;          // worker that holds this position in its cache (-1: none)
  dispatched: boolean;
  kids: { node?: PNode; terminal?: number; label: string }[];
}

export interface ParallelResult {
  value: number;
  line: string[];
  complete: boolean;
  expansions: number;     // children generated (the budget unit, as in offenseSearch)
  positions: number;      // distinct positions (hashes) seen
  converged: number;      // children whose hash was already known: work skipped
  replays: number;        // expansions that had to rebuild their position from the path
  errors: string[];
  ms: number;
  workers: number;
}

export class ParallelSearch {
  private workers: Worker[] = [];
  private nextId = 1;
  private handlers = new Map<number, (m: KidsMsg) => void>();

  constructor(script: string, private factory: RootFactory, n = autoWorkers()) {
    for (let i = 0; i < n; i++) {
      const w = new Worker(script, { workerData: { psearch: true }, resourceLimits: { maxOldGenerationSizeMb: 800 } });
      w.on('message', (m: KidsMsg) => {
        const h = this.handlers.get(m.id);
        this.handlers.delete(m.id);
        h?.(m);
      });
      this.workers.push(w);
    }
  }

  get size(): number {
    return this.workers.length;
  }

  async close(): Promise<void> {
    await Promise.all(this.workers.map(w => w.terminate()));
  }

  /** Most prizes the mover can take this turn from the position `spec` describes; same budget,
   *  depth and value semantics as offenseSearch. */
  search(spec: any, opts: SearchOptions = {}): Promise<ParallelResult> {
    const t0 = Date.now();
    const root = this.factory(spec);
    const mover = root.state.activePlayer;
    const bound = prizesLeft(root.state.players[mover]);
    const budget = opts.budget ?? 2000;
    const maxDepth = opts.maxDepth ?? 12;
    const maxMs = opts.maxMs ?? 15000;
    const expandOpts: ExpandOptions = { promptCap: opts.promptCap, branchCap: opts.branchCap, seed: opts.seed, cheapPass: opts.cheapPass ?? true };
    const specKey = JSON.stringify(spec);
    const memo = new Map<string, PNode>();
    const nodes: PNode[] = [];
    const queue: PNode[] = [];
    let head = 0;
    let expansions = 0, converged = 0, replays = 0, inflight = 0, best = 0;
    const errors: string[] = [];
    const idle = this.workers.map((_, i) => i);

    const rootNode: PNode = { key: stateHash(root.state), depth: 0, path: [], owner: -1, dispatched: false, taken: 0, value: 0, complete: false, expanded: false, kids: [] };
    memo.set(rootNode.key, rootNode);
    nodes.push(rootNode);
    queue.push(rootNode);

    return new Promise(resolve => {
      const stopping = () => expansions >= budget || best >= bound || Date.now() - t0 >= maxMs;
      const finish = () => {
        backUpValues(nodes, bound);
        resolve({
          value: rootNode.value, line: bestLine(rootNode), complete: rootNode.complete, expansions, positions: nodes.length,
          converged, replays, errors, ms: Date.now() - t0, workers: this.workers.length,
        });
      };
      // next position for worker w: one it already holds if any is near the head of the queue
      const take = (w: number): PNode | undefined => {
        while (head < queue.length && queue[head].dispatched) {
          head++;
        }
        let pick: PNode | undefined;
        for (let i = head; i < Math.min(queue.length, head + 64); i++) {
          const n = queue[i];
          if (!n.dispatched && n.owner === w) {
            pick = n;
            break;
          }
        }
        pick = pick ?? (head < queue.length ? queue[head] : undefined);
        if (pick) {
          pick.dispatched = true;
        }
        return pick;
      };
      const pump = () => {
        while (idle.length && !stopping()) {
          const w = idle[idle.length - 1];
          const n = take(w);
          if (!n) {
            break;
          }
          idle.pop();
          inflight++;
          const id = this.nextId++;
          this.handlers.set(id, m => onKids(w, n, m));
          this.workers[w].postMessage({ t: 'expand', id, spec, specKey, key: n.key, path: n.path, opts: expandOpts } as ExpandMsg);
        }
        if (inflight === 0) {
          finish();
        }
      };
      const onKids = (w: number, n: PNode, m: KidsMsg) => {
        inflight--;
        idle.push(w);
        if (m.error) {
          errors.push(m.error);
        } else {
          n.expanded = true;
          replays += m.replayed ? 1 : 0;
          expansions += Math.max(1, m.kids.length);
          for (const k of m.kids) {
            if (k.terminal) {
              n.kids.push({ terminal: k.prizes, label: k.label });
              best = Math.max(best, k.prizes);
              continue;
            }
            let c = memo.get(k.key!);
            if (c) {
              converged++;      // another path already reached this position
            } else {
              c = { key: k.key!, depth: n.depth + 1, path: [...n.path, k.step], owner: w, dispatched: false, taken: k.prizes, value: k.prizes, complete: false, expanded: false, kids: [] };
              memo.set(c.key, c);
              nodes.push(c);
              best = Math.max(best, c.taken);
              if (c.depth < maxDepth) {
                queue.push(c);
              }
            }
            if (c !== n) {
              n.kids.push({ node: c, label: k.label });
            }
          }
        }
        pump();
      };
      pump();
    });
  }
}
