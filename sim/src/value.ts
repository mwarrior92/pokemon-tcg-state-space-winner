// Win-probability model: P(the player to move at the start of a turn goes on to win), fitted on
// playout outcomes (cli/playout.ts --vectors) by L2-regularised logistic regression on the cheap
// feature groups. Stored as a LinearModel whose output goes through the logistic function.
import { LinearModel, Predictor } from './model';

export const sigmoid = (z: number) => 1 / (1 + Math.exp(-Math.max(-30, Math.min(30, z))));

/** Fit P(y = 1 | x) = sigmoid(bias + w . standardize(x)); full-batch gradient descent with
 *  momentum. X rows are feature vectors, y 0/1. */
export function fitLogistic(X: number[][], y: number[], names: string[], lambda = 1, iters = 400, target = ''): LinearModel {
  const n = X.length, d = names.length;
  const mean = new Array(d).fill(0), scale = new Array(d).fill(0);
  for (const r of X) {
    for (let j = 0; j < d; j++) {
      mean[j] += r[j] / n;
    }
  }
  for (const r of X) {
    for (let j = 0; j < d; j++) {
      scale[j] += (r[j] - mean[j]) ** 2 / n;
    }
  }
  for (let j = 0; j < d; j++) {
    scale[j] = Math.sqrt(scale[j]) || 1;
  }
  const Z = X.map(r => r.map((v, j) => (v - mean[j]) / scale[j]));
  const w = new Array(d).fill(0), vel = new Array(d).fill(0);
  let b = Math.log((y.reduce((s, v) => s + v, 0) + 1) / (n - y.reduce((s, v) => s + v, 0) + 1)), vb = 0;
  const lr = 0.5, mom = 0.9;
  for (let it = 0; it < iters; it++) {
    const g = new Array(d).fill(0);
    let gb = 0;
    for (let i = 0; i < n; i++) {
      const zi = Z[i];
      let s = b;
      for (let j = 0; j < d; j++) {
        s += w[j] * zi[j];
      }
      const e = sigmoid(s) - y[i];
      gb += e / n;
      for (let j = 0; j < d; j++) {
        g[j] += e * zi[j] / n;
      }
    }
    for (let j = 0; j < d; j++) {
      g[j] += lambda * w[j] / n;
      vel[j] = mom * vel[j] - lr * g[j];
      w[j] += vel[j];
    }
    vb = mom * vb - lr * gb;
    b += vb;
  }
  return { kind: 'linear', target, names, mean, scale, weights: w, bias: b, lambda, trainedOn: n, metrics: { link: 1 } };
}

/** P(win) for the player the vector was computed for. */
export class WinModel {
  private p: Predictor;
  constructor(public m: LinearModel) {
    this.p = new Predictor(m);
  }
  prob(names: string[], values: number[]): number {
    return sigmoid(this.p.predict(names, values));
  }
}

export function logLoss(p: number[], y: number[]): number {
  return -p.reduce((s, pi, i) => s + (y[i] ? Math.log(Math.max(1e-9, pi)) : Math.log(Math.max(1e-9, 1 - pi))), 0) / p.length;
}

/** Area under the ROC curve (probability a random winner scores above a random loser). */
export function auc(p: number[], y: number[]): number {
  const idx = p.map((v, i) => i).sort((a, b) => p[a] - p[b]);
  let rank = 0, sumPos = 0, pos = 0;
  for (const i of idx) {
    rank++;
    if (y[i]) {
      sumPos += rank;
      pos++;
    }
  }
  const neg = p.length - pos;
  return pos && neg ? (sumPos - pos * (pos + 1) / 2) / (pos * neg) : 0.5;
}
