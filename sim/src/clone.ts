// Fast, complete-enough deep copy of an engine State.
//
// The engine's own deepClone shares Card objects between copies. Cards carry mutable per-game data
// (markers, per-card flags set by card code, attack objects some cards edit in place), so sharing
// them leaks state between search branches. This copy clones cards too, but shares the card fields
// that card code never edits in place (only ever reassigns): weakness, resistance, retreat, types,
// tags and evolution lists. Attacks and abilities are copied one level deep, because a few cards
// change their own attack objects in play (Seaking / Dipplin toggle `barrage`, Iron Jugulis edits a
// cost). Aliasing is preserved everywhere through one Map of already-copied objects.
//
// The share list was derived by searching every card and engine file for in-place mutation
// (push/splice/element assignment) of each field - see sim/README.md. Re-check it after an
// upstream sync: `npm test` includes a guard test that repeats the search.
import { Card } from './engine';

export const SHARED_CARD_FIELDS = new Set([
  'weakness', 'resistance', 'retreat', 'cardType', 'cardTag', 'evolvesTo', 'evolvesToStage',
  'evolvesFromBase', 'archetype', 'tags', '_tags', 'text', 'name', 'fullName', 'set', 'setNumber',
]);
export const ONE_LEVEL_CARD_FIELDS = new Set(['attacks', 'powers']);

export function deepCopy<T>(root: T): T {
  const seen = new Map<any, any>();

  const rec = (v: any): any => {
    if (v === null || typeof v !== 'object') {
      return v;
    }
    const hit = seen.get(v);
    if (hit !== undefined) {
      return hit;
    }
    if (Array.isArray(v)) {
      const n = v.length;
      const a: any[] = new Array(n);
      seen.set(v, a);
      for (let i = 0; i < n; i++) {
        const x = v[i];
        a[i] = (x === null || typeof x !== 'object') ? x : rec(x);
      }
      return a;
    }
    if (v instanceof Card) {
      return copyCard(v);
    }
    if (v instanceof Map) {
      const m = new Map();
      seen.set(v, m);
      v.forEach((val, key) => m.set(rec(key), rec(val)));
      return m;
    }
    if (v instanceof Set) {
      const s = new Set();
      seen.set(v, s);
      v.forEach(val => s.add(rec(val)));
      return s;
    }
    if (v instanceof Date) {
      return new Date(v.getTime());
    }
    const o = Object.create(Object.getPrototypeOf(v));
    seen.set(v, o);
    const keys = Object.keys(v);
    for (let i = 0; i < keys.length; i++) {
      const k = keys[i];
      const x = v[k];
      o[k] = (x === null || typeof x !== 'object') ? x : rec(x);
    }
    return o;
  };

  const shallow = (x: any): any => {
    if (x === null || typeof x !== 'object') {
      return x;
    }
    const hit = seen.get(x);
    if (hit !== undefined) {
      return hit;
    }
    const o = Object.assign(Object.create(Object.getPrototypeOf(x)), x);
    seen.set(x, o);
    return o;
  };

  const copyCard = (c: any): any => {
    const o = Object.create(Object.getPrototypeOf(c));
    seen.set(c, o);
    const keys = Object.keys(c);
    for (let i = 0; i < keys.length; i++) {
      const k = keys[i];
      const x = c[k];
      if (x === null || typeof x !== 'object' || SHARED_CARD_FIELDS.has(k)) {
        o[k] = x;
      } else if (ONE_LEVEL_CARD_FIELDS.has(k) && Array.isArray(x)) {
        const hit = seen.get(x);
        if (hit !== undefined) {
          o[k] = hit;
        } else {
          const a = new Array(x.length);
          seen.set(x, a);
          for (let j = 0; j < x.length; j++) {
            a[j] = shallow(x[j]);
          }
          o[k] = a;
        }
      } else {
        o[k] = rec(x);
      }
    }
    return o;
  };

  return rec(root);
}
