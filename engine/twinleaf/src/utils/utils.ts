
export function deepCompare(x: any, y: any): boolean {

  if (x === y) { return true; }
  // if both x and y are null or undefined and exactly the same

  if (!(x instanceof Object) || !(y instanceof Object)) { return false; }
  // if they are not strictly equal, they both need to be Objects

  if (x.constructor !== y.constructor) { return false; }
  // they must have the exact same prototype chain, the closest we can do is
  // test there constructor.

  for (const p in x) {
    if (!Object.prototype.hasOwnProperty.call(x, p)) { continue; }
    // other properties were tested using x.constructor === y.constructor

    if (!Object.prototype.hasOwnProperty.call(y, p)) { return false; }
    // allows to compare x[ p ] and y[ p ] when set to undefined

    if (x[p] === y[p]) { continue; }
    // if they have the same strict value or identity then they are equal

    if (typeof (x[p]) !== 'object') { return false; }
    // Numbers, Strings, Functions, Booleans must be strictly equal

    if (!deepCompare(x[p], y[p])) { return false; }
    // Objects and Arrays must be tested recursively
  }

  for (const p in y) {
    if (Object.prototype.hasOwnProperty.call(y, p) && !Object.prototype.hasOwnProperty.call(x, p)) { return false; }
    // allows x[ p ] to be set to undefined
  }
  return true;
}

export function deepIterate(source: any, callback: (holder: any, key: string, value: any) => void): void {
  if (source === null) { return; }

  if (source instanceof Array) {
    source.forEach((item: any) => deepIterate(item, callback));
  }

  if (source instanceof Object) {
    for (const key in source) {
      if (Object.prototype.hasOwnProperty.call(source, key)) {
        deepIterate(source[key], callback);
        callback(source, key, source[key]);
      }
    }
  }
}

// [winner patch 001] Same contract as upstream (ignored classes are shared, functions shared,
// aliasing preserved), but: references are tracked in a Map instead of a linear array scan
// (upstream is O(n^2) in the number of objects), and copies take the source's *prototype* rather
// than the source object itself (upstream's Object.create(source) made prototype chains grow
// with every clone of a clone).
export function deepClone(source: any, ignores: Function[] = [], refMap?: Map<any, any>): any {
  const seen = refMap ?? new Map<any, any>();
  const rec = (v: any): any => {
    if (v === null || typeof v !== 'object') {
      return v;
    }
    const hit = seen.get(v);
    if (hit !== undefined) {
      return hit;
    }
    if (v instanceof Array) {
      const a: any[] = new Array(v.length);
      seen.set(v, a);
      for (let i = 0; i < v.length; i++) {
        a[i] = rec(v[i]);
      }
      return a;
    }
    for (let i = 0; i < ignores.length; i++) {
      if (v instanceof ignores[i]) {
        return v;
      }
    }
    const dest = Object.create(Object.getPrototypeOf(v));
    seen.set(v, dest);
    for (const key in v) {
      if (Object.prototype.hasOwnProperty.call(v, key)) {
        dest[key] = rec(v[key]);
      }
    }
    return dest;
  };
  return rec(source);
}

export function generateId<T extends { id: number }[]>(array: T): number {
  if (array.length === 0) {
    return 1;
  }

  const last = array[array.length - 1];
  let id = last.id + 1;

  while (array.find(g => g.id === id)) {
    if (id === Number.MAX_VALUE) {
      id = 0;
    }
    id = id + 1;
  }

  return id;
}
