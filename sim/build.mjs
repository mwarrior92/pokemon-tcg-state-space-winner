// Bundles the sim entry points (TypeScript, ours + the vendored Twinleaf engine) with esbuild.
// No type-checking here (run `npm run typecheck`); bundling the ~12k engine files takes seconds.
import { build } from 'esbuild';
import { readdirSync, readFileSync, writeFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';

const entries = Object.fromEntries(
  readdirSync('src/cli').filter(f => f.endsWith('.ts')).map(f => [f.replace(/\.ts$/, ''), `src/cli/${f}`]));
entries.tests = 'test/index.ts';

await build({
  entryPoints: entries,
  // SIM_OUT=dist-tools builds elsewhere (e.g. while a run is using dist/)
  outdir: process.env.SIM_OUT ?? 'dist',
  bundle: true,
  platform: 'node',
  target: 'node20',
  format: 'cjs',
  sourcemap: true,
  logLevel: 'warning',
  // the engine lives outside this package, so resolve its npm imports from here
  nodePaths: [fileURLToPath(new URL('./node_modules', import.meta.url))],
  // backend/storage code is never reached from the game engine paths we use
  external: ['sqlite3', 'mysql2', 'typeorm', 'jimp', 'nodemailer', 'express', 'socket.io'],
});

// The engine calls require() inside hot functions (e.g. `require('./prefabs/prefabs')`), which
// esbuild turns into __toCommonJS(module) - a fresh copy of every export on every call. Exports are
// live getters, so caching the wrapper per module is equivalent and removes ~10% of runtime.
const SLOW = 'var __toCommonJS = (mod) => __copyProps(__defProp({}, "__esModule", { value: true }), mod);';
const FAST = 'var __cjsCache = new WeakMap(); var __toCommonJS = (mod) => { let r = __cjsCache.get(mod); if (!r) { r = __copyProps(__defProp({}, "__esModule", { value: true }), mod); __cjsCache.set(mod, r); } return r; };';
for (const name of Object.keys(entries)) {
  const f = `${process.env.SIM_OUT ?? 'dist'}/${name}.js`;
  const src = readFileSync(f, 'utf8');
  if (src.includes(SLOW)) {
    writeFileSync(f, src.replace(SLOW, FAST));
  }
}
