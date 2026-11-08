// Small seeded RNG (mulberry32) so every generated state, shuffle and coin flip is reproducible.
export class Rng {
  private s: number;

  constructor(seed: number) {
    this.s = (seed >>> 0) || 0x9e3779b9;
  }

  /** uniform in [0, 1) */
  next(): number {
    let t = (this.s = (this.s + 0x6d2b79f5) >>> 0);
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  }

  /** integer in [lo, hi] inclusive */
  int(lo: number, hi: number): number {
    return lo + Math.floor(this.next() * (hi - lo + 1));
  }

  pick<T>(xs: readonly T[]): T {
    return xs[Math.floor(this.next() * xs.length)];
  }

  chance(p: number): boolean {
    return this.next() < p;
  }

  shuffle<T>(xs: T[]): T[] {
    for (let i = xs.length - 1; i > 0; i--) {
      const j = Math.floor(this.next() * (i + 1));
      [xs[i], xs[j]] = [xs[j], xs[i]];
    }
    return xs;
  }

  /** k distinct items, order random */
  sample<T>(xs: readonly T[], k: number): T[] {
    return this.shuffle(xs.slice()).slice(0, Math.max(0, Math.min(k, xs.length)));
  }

  /** a permutation of 0..n-1 */
  perm(n: number): number[] {
    return this.shuffle(Array.from({ length: n }, (_, i) => i));
  }

  fork(): Rng {
    return new Rng(Math.floor(this.next() * 4294967296));
  }
}
