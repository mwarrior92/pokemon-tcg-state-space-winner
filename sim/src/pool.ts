// Minimal worker-thread pool. The same bundled script runs as the main thread and as workers; a
// worker registers a handler with `serveJobs` and the main thread sends jobs with `runPool`.
//
// Each worker has a heap cap; a worker that dies (out of memory, crash) is replaced and its job
// reported as failed, so one bad state cannot stall or shrink the pool.
import { Worker, isMainThread, parentPort, workerData } from 'worker_threads';
import * as os from 'os';

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

/** Workers the machine can run without swapping: one per core but two, and no more than fit in
 *  free memory (keeping 2 GB for the OS) at `perWorkerMb` each. */
export function autoWorkers(perWorkerMb = 700): number {
  const byCpu = Math.max(1, os.cpus().length - 2);
  const byMem = Math.max(1, Math.floor((os.freemem() / 1e6 - 2000) / perWorkerMb));
  return Math.min(byCpu, byMem);
}

export interface PoolOptions<R> {
  workers?: number;
  /** heap cap per worker (MB); a worker over it is replaced and its job fails */
  heapMb?: number;
  onResult?: (r: R, i: number, done: number) => void;
}

export async function runPool<J, R>(script: string, jobs: J[], opts: PoolOptions<R> = {}): Promise<(R | undefined)[]> {
  const n = Math.max(1, Math.min(opts.workers ?? autoWorkers(), jobs.length));
  const results: (R | undefined)[] = new Array(jobs.length);
  let next = 0;
  let done = 0;
  const errors: string[] = [];
  const lane = () => new Promise<void>(resolve => {
    const w = new Worker(script, { workerData: { worker: true }, resourceLimits: { maxOldGenerationSizeMb: opts.heapMb ?? Number(process.env.POOL_HEAP_MB ?? 2500) } });
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
