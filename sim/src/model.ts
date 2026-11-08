// Value models over feature vectors. v1: standardized linear (ridge) regression, solved exactly
// with a Cholesky factorization. Small, fast to evaluate inside the turn search, and its weights are
// readable, which the review step uses. Saved as JSON (feature names + weights) so a model keeps
// working when the feature list changes (missing features count as 0).
import * as fs from 'fs';

export interface LinearModel {
  kind: 'linear';
  target: string;           // what it predicts, e.g. "offense: prizes reachable this turn"
  names: string[];
  groups?: string[];        // feature group of each name (features.ts), so only those are computed
  mean: number[];
  scale: number[];
  weights: number[];        // on standardized features
  bias: number;
  lambda: number;
  trainedOn: number;
  metrics?: Record<string, number>;
}

export function fitRidge(X: number[][], y: number[], names: string[], lambda = 1, target = ''): LinearModel {
  const n = X.length;
  const d = names.length;
  const mean = new Array(d).fill(0);
  const scale = new Array(d).fill(0);
  for (const r of X) {
    for (let j = 0; j < d; j++) {
      mean[j] += r[j];
    }
  }
  for (let j = 0; j < d; j++) {
    mean[j] /= n;
  }
  for (const r of X) {
    for (let j = 0; j < d; j++) {
      scale[j] += (r[j] - mean[j]) ** 2;
    }
  }
  for (let j = 0; j < d; j++) {
    scale[j] = Math.sqrt(scale[j] / n) || 1;
  }
  const ym = y.reduce((s, v) => s + v, 0) / n;
  // normal equations on standardized X: (Z'Z + lambda I) w = Z'(y - ym)
  const A = new Float64Array(d * d);
  const bvec = new Float64Array(d);
  const z = new Float64Array(d);
  for (let i = 0; i < n; i++) {
    const r = X[i];
    for (let j = 0; j < d; j++) {
      z[j] = (r[j] - mean[j]) / scale[j];
    }
    const yi = y[i] - ym;
    for (let j = 0; j < d; j++) {
      const zj = z[j];
      if (zj === 0) {
        continue;
      }
      bvec[j] += zj * yi;
      const row = j * d;
      for (let k = 0; k <= j; k++) {
        A[row + k] += zj * z[k];
      }
    }
  }
  for (let j = 0; j < d; j++) {
    A[j * d + j] += lambda;
  }
  const w = choleskySolve(A, bvec, d);
  return { kind: 'linear', target, names, mean, scale, weights: Array.from(w), bias: ym, lambda, trainedOn: n };
}

/** Solve A x = b for symmetric positive definite A (lower triangle filled), in place. */
function choleskySolve(A: Float64Array, b: Float64Array, d: number): Float64Array {
  for (let j = 0; j < d; j++) {
    let s = A[j * d + j];
    for (let k = 0; k < j; k++) {
      s -= A[j * d + k] * A[j * d + k];
    }
    const ljj = Math.sqrt(Math.max(s, 1e-12));
    A[j * d + j] = ljj;
    for (let i = j + 1; i < d; i++) {
      let t = A[i * d + j];
      for (let k = 0; k < j; k++) {
        t -= A[i * d + k] * A[j * d + k];
      }
      A[i * d + j] = t / ljj;
    }
  }
  const y = new Float64Array(d);
  for (let i = 0; i < d; i++) {
    let t = b[i];
    for (let k = 0; k < i; k++) {
      t -= A[i * d + k] * y[k];
    }
    y[i] = t / A[i * d + i];
  }
  const x = new Float64Array(d);
  for (let i = d - 1; i >= 0; i--) {
    let t = y[i];
    for (let k = i + 1; k < d; k++) {
      t -= A[k * d + i] * x[k];
    }
    x[i] = t / A[i * d + i];
  }
  return x;
}

/** Predict for a feature vector given by name -> value (names the model does not know are ignored,
 *  names it knows but the vector lacks count as 0). */
export class Predictor {
  private idx: Map<string, number>;
  constructor(public m: LinearModel) {
    this.idx = new Map(m.names.map((n, i) => [n, i]));
  }
  predict(names: string[], values: number[]): number {
    let s = this.m.bias;
    const seen = new Set<number>();
    for (let i = 0; i < names.length; i++) {
      const j = this.idx.get(names[i]);
      if (j === undefined) {
        continue;
      }
      seen.add(j);
      s += this.m.weights[j] * (values[i] - this.m.mean[j]) / this.m.scale[j];
    }
    // features missing from the vector are 0
    for (let j = 0; j < this.m.names.length; j++) {
      if (!seen.has(j)) {
        s += this.m.weights[j] * (0 - this.m.mean[j]) / this.m.scale[j];
      }
    }
    return s;
  }
  /** fast path when the vector has exactly the model's names in order */
  predictAligned(values: number[]): number {
    let s = this.m.bias;
    const { weights, mean, scale } = this.m;
    for (let j = 0; j < weights.length; j++) {
      s += weights[j] * (values[j] - mean[j]) / scale[j];
    }
    return s;
  }
}

export function mse(model: LinearModel, X: number[][], y: number[]): number {
  const p = new Predictor(model);
  let s = 0;
  for (let i = 0; i < X.length; i++) {
    s += (p.predictAligned(X[i]) - y[i]) ** 2;
  }
  return s / Math.max(1, X.length);
}

/** Importance of each feature: |weight| on the standardized scale (how much one standard deviation
 *  of the feature moves the prediction). */
export function importance(m: LinearModel): { name: string; weight: number; abs: number }[] {
  return m.names.map((name, i) => ({ name, weight: m.weights[i], abs: Math.abs(m.weights[i]) })).sort((a, b) => b.abs - a.abs);
}

export function saveModel(m: LinearModel, file: string): void {
  fs.writeFileSync(file, JSON.stringify(m));
}

export function loadModel(file: string): LinearModel {
  return JSON.parse(fs.readFileSync(file, 'utf8'));
}

/** Keep only the columns of X whose names pass `keep`. */
export function selectColumns(names: string[], X: number[][], keep: (name: string, i: number) => boolean): { names: string[]; X: number[][] } {
  const cols = names.map((n, i) => (keep(n, i) ? i : -1)).filter(i => i >= 0);
  return { names: cols.map(i => names[i]), X: X.map(r => cols.map(i => r[i])) };
}
