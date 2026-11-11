// Minimal worker-thread pool. The same bundled script runs as the main thread and as workers; a
// worker registers a handler with `serveJobs` and the main thread sends jobs with `runPool`.
//
// Each worker has a heap cap; a worker that dies (out of memory, crash) is replaced and its job
// reported as failed, so one bad state cannot stall or shrink the pool.
//
// Speed on Windows: a windowless background process is power-throttled (efficiency mode) and runs on
// the efficiency cores only. On the i7-13650HX the 8 E-cores sat at 100% and the 6 P-cores idled, so
// 7 workers and 14 workers ran equally slowly. `fullSpeed` turns that off for this process (all its
// worker threads; scripts/fullspeed.ps1, no admin rights): 42 games went from 797 s to 226 s.
// Memory: a game holds about 45 MB of live data, but with a large heap cap V8 lets garbage grow to
// ~500 MB per worker before collecting; a 256 MB cap plays at the same speed with ~365 MB per worker
// (160 MB is 15% slower), so more workers fit.
import { Worker, isMainThread, parentPort, workerData } from 'worker_threads';
import { spawn } from 'child_process';
import * as fs from 'fs';
import * as os from 'os';
import * as path from 'path';

export { isMainThread, workerData };

export function serveJobs(handler: (job: any) => any): void {
  if (isMainThread || !parentPort || !workerData?.worker) {   // (psearch workers serve their own messages)
    return;
  }
  parentPort.on('message', (msg: { id: number; job: any }) => {
    let reply: any;
    try {
      reply = { id: msg.id, ok: true, result: handler(msg.job) };
    } catch (e) {
      reply = { id: msg.id, ok: false, error: String((e as Error)?.stack ?? e) };
    }
    parentPort!.postMessage(reply);
  });
}

/** default heap cap per worker (MB); POOL_HEAP_MB overrides */
export const HEAP_MB = Number(process.env.POOL_HEAP_MB ?? 320);

/** Workers the machine can run well: one per logical CPU less two, and no more than fit in free
 *  memory (keeping 1.5 GB for the OS) at `perWorkerMb` each; POOL_WORKERS_MAX caps it. */
export function autoWorkers(perWorkerMb = HEAP_MB + 130, max = Number(process.env.POOL_WORKERS_MAX ?? 16)): number {
  const byCpu = Math.max(1, os.cpus().length - 2);
  const byMem = Math.max(1, Math.floor((os.freemem() / 1e6 - 1500) / perWorkerMb));
  return Math.min(byCpu, byMem, max);
}

let fullSpeedDone = false;
/** Windows: let this process (every worker thread) use the performance cores, not just the
 *  efficiency cores (see the top of this file). Once per process; SIM_THROTTLE=1 skips it. */
export function fullSpeed(): void {
  if (fullSpeedDone || process.platform !== 'win32' || process.env.SIM_THROTTLE) {
    return;
  }
  fullSpeedDone = true;
  const script = path.join(__dirname, '..', 'scripts', 'fullspeed.ps1');   // bundles live in sim/dist*/
  if (!fs.existsSync(script)) {
    return;
  }
  try {
    spawn('powershell', ['-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', script, '-ProcessId', String(process.pid)], { stdio: 'ignore', windowsHide: true }).on('error', () => undefined);
  } catch {
    // not fatal: runs slower
  }
}

export interface PoolOptions<R> {
  workers?: number;
  /** heap cap per worker (MB); a worker over it is replaced and its job fails */
  heapMb?: number;
  onResult?: (r: R, i: number, done: number) => void;
}

export async function runPool<J, R>(script: string, jobs: J[], opts: PoolOptions<R> = {}): Promise<(R | undefined)[]> {
  fullSpeed();
  const n = Math.max(1, Math.min(opts.workers || autoWorkers(), jobs.length));
  const results: (R | undefined)[] = new Array(jobs.length);
  let next = 0;
  let done = 0;
  const errors: string[] = [];
  const lane = () => new Promise<void>(resolve => {
    const w = new Worker(script, { workerData: { worker: true }, resourceLimits: { maxOldGenerationSizeMb: opts.heapMb ?? HEAP_MB } });
    let current = -1;
    let dead = false;
    const feed = () => {
      if (next >= jobs.length) {
        dead = true;   // a deliberate stop, not a crash
        w.terminate().then(() => resolve());
        return;
      }
      current = next++;
      w.postMessage({ id: current, job: jobs[current] });
    };
    w.on('message', (m: { id: number; ok: boolean; result?: R; error?: string }) => {
      done++;
      current = -1;
      if (m.ok) {
        results[m.id] = m.result;
        opts.onResult?.(m.result!, m.id, done);
      } else {
        errors.push(m.error!);
      }
      feed();
    });
    const replace = (why: string) => {
      if (dead) {
        return;
      }
      dead = true;
      if (current >= 0) {
        done++;
        errors.push(`job ${current}: worker died: ${why}`);
      }
      // carry on in a fresh worker
      lane().then(resolve);
    };
    w.on('error', e => replace(String(e)));
    w.on('exit', code => replace(`exit code ${code}`));
    feed();
  });
  await Promise.all(Array.from({ length: n }, lane));
  if (errors.length) {
    console.error(`${errors.length} jobs failed; first: ${errors[0].slice(0, 600)}`);
  }
  return results;
}
