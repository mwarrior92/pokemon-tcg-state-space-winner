// Rules-level answers to engine prompts. For every prompt type this produces candidate *raw* results
// (the format the client would send), and keeps those the prompt itself accepts (decode + validate).
// No preferences live here: candidates are either enumerated (small choice sets) or sampled.
//
// Identical cards are interchangeable, so card choices are enumerated as multisets of card names
// instead of index subsets (choosing 2 of 4 identical Ultra Balls is one option, not six).
import {
  AlertPrompt, AttachEnergyPrompt, Card, CardTarget, ChooseAttackPrompt, ChooseCardsPrompt, ChooseEnergyPrompt,
  ChoosePokemonPrompt, ChoosePrizePrompt, CoinFlipPrompt, ConfirmCardsPrompt, ConfirmPrompt, DiscardEnergyPrompt,
  InvitePlayerPrompt, MoveDamagePrompt, MoveEnergyPrompt, OrderCardsPrompt, Player, PlayerType, PokemonCardList,
  Prompt, PutDamagePrompt, RemoveDamagePrompt, SelectOptionPrompt, SelectPrompt, ShowCardsPrompt, ShowMulliganPrompt,
  ShuffleDeckPrompt, ShuffleHandPrompt, ShufflePrizesPrompt, SlotType, State, SuperType, WaitPrompt, matchesPromptFilter,
} from './engine';
import { Rng } from './rng';

/** Prompts with nothing to decide (or decided by chance): the arbiter answers these. */
export function isChancePrompt(p: Prompt<any>): boolean {
  return p instanceof ShuffleDeckPrompt || p instanceof ShuffleHandPrompt || p instanceof ShufflePrizesPrompt
    || p instanceof CoinFlipPrompt || p instanceof WaitPrompt || p instanceof ShowMulliganPrompt
    || p instanceof ShowCardsPrompt || p instanceof AlertPrompt || p instanceof ConfirmCardsPrompt
    || p instanceof InvitePlayerPrompt;
}

/** Raw result for a chance / no-choice prompt. With `rank` (a fixed random number per card, see
 *  Sim.chanceSeed) a deck shuffle puts the deck in rank order, so the same cards in the deck always
 *  shuffle to the same order, whatever happened before. */
export function chanceResult(p: Prompt<any>, state: State, rng: Rng, rank?: (c: Card) => number): any {
  const owner = state.players.find(pl => pl.id === p.getPerspectivePlayerId())!;
  if (p instanceof ShuffleDeckPrompt) {
    if (rank) {
      const cs = owner.deck.cards;
      return cs.map((_, i) => i).sort((a, b) => rank(cs[a]) - rank(cs[b]));
    }
    return rng.perm(owner.deck.cards.length);
  }
  if (p instanceof ShuffleHandPrompt) {
    // the engine validates hand shuffles against the prize count (upstream quirk); answer what it checks
    return rng.perm(owner.hand.cards.length);
  }
  if (p instanceof ShufflePrizesPrompt) {
    const n = owner.prizes.reduce((s, l) => s + l.cards.length, 0);
    return rank ? Array.from({ length: n }, (_, i) => i) : rng.perm(n);
  }
  if (p instanceof CoinFlipPrompt) {
    return rng.chance(0.5);
  }
  return true;
}

export interface Candidate {
  raw: any;
  label: string;
}

function side(state: State, p: Prompt<any>): { player: Player; opponent: Player } {
  const pid = p.getPerspectivePlayerId();
  const player = state.players.find(x => x.id === pid)!;
  const opponent = state.players.find(x => x.id !== pid)!;
  return { player, opponent };
}

function key(t: CardTarget): string {
  return `${t.player}-${t.slot}-${t.index}`;
}

function targets(state: State, p: Prompt<any>, playerType: PlayerType, slots: SlotType[], blocked: CardTarget[] = []): CardTarget[] {
  const { player, opponent } = side(state, p);
  const bl = new Set(blocked.map(key));
  const out: CardTarget[] = [];
  for (const pt of [PlayerType.BOTTOM_PLAYER, PlayerType.TOP_PLAYER]) {
    if (playerType !== PlayerType.ANY && playerType !== pt) {
      continue;
    }
    const pl = pt === PlayerType.BOTTOM_PLAYER ? player : opponent;
    if (slots.includes(SlotType.ACTIVE) && pl.active.cards.length > 0) {
      out.push({ player: pt, slot: SlotType.ACTIVE, index: 0 });
    }
    if (slots.includes(SlotType.BENCH)) {
      pl.bench.forEach((b, i) => {
        if (b.cards.length > 0) {
          out.push({ player: pt, slot: SlotType.BENCH, index: i });
        }
      });
    }
  }
  return out.filter(t => !bl.has(key(t)));
}

function slotOf(state: State, p: Prompt<any>, t: CardTarget): PokemonCardList {
  const { player, opponent } = side(state, p);
  const pl = t.player === PlayerType.BOTTOM_PLAYER ? player : opponent;
  return t.slot === SlotType.ACTIVE ? pl.active : pl.bench[t.index];
}

function tname(state: State, p: Prompt<any>, t: CardTarget): string {
  const s = slotOf(state, p, t);
  const pc = s?.getPokemonCard();
  return `${t.player === PlayerType.BOTTOM_PLAYER ? 'own' : 'opp'} ${t.slot === SlotType.ACTIVE ? 'active' : 'bench' + t.index}${pc ? ' ' + pc.name : ''}`;
}

/** All multisets of size lo..hi over groups (each group = interchangeable indices), capped. */
function multisets(groups: number[][], lo: number, hi: number, cap: number): number[][] {
  const out: number[][] = [];
  const cur: number[] = [];
  const rec = (g: number, left: number) => {
    if (out.length >= cap) {
      return;
    }
    if (g === groups.length) {
      if (cur.length >= lo) {
        out.push(cur.slice());
      }
      return;
    }
    const n = Math.min(groups[g].length, left);
    for (let take = n; take >= 0; take--) {
      for (let i = 0; i < take; i++) {
        cur.push(groups[g][i]);
      }
      rec(g + 1, left - take);
      cur.length -= take;
      if (out.length >= cap) {
        return;
      }
    }
  };
  rec(0, hi);
  return out;
}

function groupByName(cards: Card[], idx: number[]): number[][] {
  const m = new Map<string, number[]>();
  for (const i of idx) {
    const k = cards[i].fullName;
    const l = m.get(k) ?? [];
    l.push(i);
    m.set(k, l);
  }
  return [...m.values()];
}

/** Raw candidate results for a decision prompt, at most `cap` (sampled when there are more). */
export function rawCandidates(p: Prompt<any>, state: State, rng: Rng, cap = 64): Candidate[] {
  const out: Candidate[] = [];
  const add = (raw: any, label: string) => out.push({ raw, label });
  const cancel = (p as any).options?.allowCancel === true;

  if (p instanceof ConfirmPrompt) {
    add(true, 'yes');
    add(false, 'no');
  } else if (p instanceof SelectPrompt || p instanceof SelectOptionPrompt) {
    const disabled: boolean[] = (p as any).options?.disabled ?? [];
    p.values.forEach((v, i) => {
      if (!disabled[i]) {
        add(i, String(v));
      }
    });
  } else if (p instanceof ChooseAttackPrompt) {
    const blocked = p.options.blocked;
    p.cards.forEach((c, i) => c.attacks.forEach(a => {
      if (!blocked.some(b => b.index === i && b.attack === a.name)) {
        add({ index: i, attack: a.name }, `${c.name}: ${a.name}`);
      }
    }));
  } else if (p instanceof ChooseCardsPrompt) {
    const cards = p.cards.cards;
    const blocked = new Set(p.options.blocked);
    const ok = cards.map((_, i) => i).filter(i => !blocked.has(i) && matchesPromptFilter(cards[i], p.filter));
    const hi = Math.min(p.options.max, ok.length);
    const lo = Math.min(p.options.min, hi);
    const groups = rng.shuffle(groupByName(cards, ok));
    // largest selections first: "take everything allowed" is the natural default of a search card
    for (const sel of multisets(groups, lo, hi, cap * 4)) {
      add(sel, sel.length ? sel.map(i => cards[i].name).join(' + ') : 'nothing');
    }
  } else if (p instanceof ChoosePokemonPrompt) {
    const ts = targets(state, p, p.playerType, p.slots, p.options.blocked);
    const hi = Math.min(p.options.max, ts.length);
    const lo = Math.min(p.options.min, hi);
    for (const sel of multisets(ts.map((_, i) => [i]), lo, hi, cap * 4)) {
      add(sel.map(i => ts[i]), sel.map(i => tname(state, p, ts[i])).join(' + ') || 'nobody');
    }
  } else if (p instanceof AttachEnergyPrompt) {
    const cards = p.cardList.cards;
    const blocked = new Set(p.options.blocked);
    const en = cards.map((_, i) => i).filter(i => !blocked.has(i) && cards[i].superType === SuperType.ENERGY && matchesPromptFilter(cards[i], p.filter));
    const ts = targets(state, p, p.playerType, p.slots, p.options.blockedTo);
    const hi = Math.min(p.options.max, en.length);
    const lo = Math.min(p.options.min, hi);
    // choose which energies (as multisets of names), then sample target assignments
    for (const sel of multisets(groupByName(cards, en), lo, hi, cap)) {
      const tries = sel.length === 0 ? 1 : Math.min(cap, Math.pow(ts.length, sel.length));
      const seen = new Set<string>();
      for (let k = 0; k < tries * 2 && seen.size < tries; k++) {
        const asg = sel.map(i => ({ to: ts.length ? (sel.length === 1 && k < ts.length ? ts[k] : rng.pick(ts)) : undefined, index: i }));
        if (asg.some(a => !a.to)) {
          break;
        }
        const sig = asg.map(a => `${cards[a.index].fullName}>${key(a.to!)}`).sort().join('|');
        if (seen.has(sig)) {
          continue;
        }
        seen.add(sig);
        add(asg, asg.map(a => `${cards[a.index].name} -> ${tname(state, p, a.to!)}`).join(', ') || 'attach nothing');
      }
    }
  } else if (p instanceof ChooseEnergyPrompt) {
    const n = p.energy.length;
    const groups = new Map<string, number[]>();
    p.energy.forEach((e, i) => {
      const k = e.card.fullName + '|' + e.provides.join(',');
      groups.set(k, [...(groups.get(k) ?? []), i]);
    });
    for (const sel of multisets([...groups.values()], 0, n, cap * 4)) {
      add(sel, sel.map(i => p.energy[i].card.name).join(' + ') || 'none');
    }
  } else if (p instanceof ChoosePrizePrompt) {
    const { player, opponent } = side(state, p);
    const owner = p.options.useOpponentPrizes ? opponent : player;
    const prizes = owner.prizes.filter(x => x.cards.length > 0);
    const idx = prizes.map((_, i) => i).filter(i => !p.options.blocked.includes(i));
    // prize cards are face down: which ones you pick is chance, not a decision. Always the first
    // ones, so every line of a search that takes a prize finds the same card (prizes are dealt at
    // random, so this is still a random card)
    const sel = idx.slice(0, p.options.count);
    add(sel, sel.length === 1 ? 'take a prize' : `take ${sel.length} prizes`);
  } else if (p instanceof OrderCardsPrompt) {
    const n = p.cards.cards.length;
    add(Array.from({ length: n }, (_, i) => i), 'keep order');
    for (let k = 0; k < Math.min(cap, 8); k++) {
      add(rng.perm(n), 'reorder');
    }
  } else if (p instanceof PutDamagePrompt) {
    const maxd = (p as any).maxAllowedDamage as { target: CardTarget; damage: number }[];
    const blocked = new Set(((p as any).options.blocked ?? (p as any).options.blockedTo ?? []).map(key));
    const ts = maxd.filter(d => d.damage > 0 && !blocked.has(key(d.target)));
    const total: number = (p as any).damage ?? 0;
    const step = (p as any).options.damageMultiple ?? 10;
    {
      // all on one target, then random spreads
      for (const t of ts) {
        add([{ target: t.target, damage: Math.min(total, t.damage) }], `${total} on ${tname(state, p, t.target)}`);
      }
      for (let k = 0; k < Math.min(cap, 12) && ts.length > 1; k++) {
        const m = new Map<string, { target: CardTarget; damage: number }>();
        let left = total;
        let guard = 0;
        while (left > 0 && guard++ < 200) {
          const t = rng.pick(ts);
          const cur = m.get(key(t.target))?.damage ?? 0;
          if (cur + step <= t.damage) {
            m.set(key(t.target), { target: t.target, damage: cur + step });
            left -= step;
          }
        }
        if (left === 0) {
          add([...m.values()], 'spread ' + [...m.values()].map(d => `${d.damage}@${tname(state, p, d.target)}`).join(' '));
        }
      }
    }
  } else if (p instanceof MoveDamagePrompt || p instanceof RemoveDamagePrompt) {
    // both answer with damage-counter transfers {from, to}, one counter each
    const q = p as any;
    const all = targets(state, p, q.playerType, q.slots);
    const bf = new Set((q.options.blockedFrom ?? []).map(key));
    const bt = new Set((q.options.blockedTo ?? []).map(key));
    const from = all.filter(t => !bf.has(key(t)) && slotOf(state, p, t).damage > 0);
    const to = all.filter(t => !bt.has(key(t)));
    const max = Math.min(q.options.max ?? 6, 12);
    const min = q.options.min ?? 0;
    const capacity = (t: CardTarget) => Math.floor(slotOf(state, p, t).damage / 10);
    for (const dest of to) {
      const srcs = from.filter(f => key(f) !== key(dest));
      if (!srcs.length) {
        continue;
      }
      for (let n = max; n >= Math.max(min, 1); n--) {
        // fill from one source at a time, sources in a few different orders
        for (let k = 0; k < 3; k++) {
          const order = k === 0 ? srcs : rng.shuffle(srcs.slice());
          const tr: any[] = [];
          for (const f of order) {
            for (let c = 0; c < capacity(f) && tr.length < n; c++) {
              tr.push({ from: f, to: dest });
            }
          }
          if (tr.length === n) {
            add(tr, `move ${n} counters -> ${tname(state, p, dest)}`);
          }
        }
      }
    }
    if (min === 0) {
      add([], 'move nothing');
    }
  } else if (p instanceof MoveEnergyPrompt || p instanceof DiscardEnergyPrompt) {
    const isMove = p instanceof MoveEnergyPrompt;
    const all = targets(state, p, (p as any).playerType, (p as any).slots);
    const blockedFrom = new Set(((p as any).options.blockedFrom ?? []).map(key));
    const blockedTo = new Set(((p as any).options.blockedTo ?? []).map(key));
    const blockedMap: { source: CardTarget; blocked: number[] }[] = (p as any).options.blockedMap ?? [];
    const singles: { from: CardTarget; index: number; name: string }[] = [];
    for (const t of all) {
      if (blockedFrom.has(key(t))) {
        continue;
      }
      const bl = new Set(blockedMap.find(b => key(b.source) === key(t))?.blocked ?? []);
      slotOf(state, p, t).cards.forEach((c, i) => {
        if (c.superType === SuperType.ENERGY && !bl.has(i) && matchesPromptFilter(c, (p as any).filter)) {
          singles.push({ from: t, index: i, name: c.name });
        }
      });
    }
    const min = (p as any).options.min ?? 0;
    const max = Math.min((p as any).options.max ?? singles.length, singles.length);
    const tos = all.filter(t => !blockedTo.has(key(t)));
    for (let k = 0; k < cap; k++) {
      const n = k === 0 ? max : rng.int(Math.min(min, max), max);
      const pick = rng.sample(singles, n);
      if (isMove) {
        const tr = pick.map(s => ({ from: s.from, to: rng.pick(tos.filter(t => key(t) !== key(s.from))), index: s.index }));
        if (tr.every(x => x.to)) {
          add(tr, tr.map(x => `${singles.find(s => s.index === x.index && key(s.from) === key(x.from))?.name} ${tname(state, p, x.from)} -> ${tname(state, p, x.to)}`).join(', ') || 'move nothing');
        }
      } else {
        add(pick.map(s => ({ from: s.from, index: s.index })), pick.map(s => `${s.name}@${tname(state, p, s.from)}`).join(', ') || 'discard nothing');
      }
    }
  }

  if (cancel) {
    add(null, 'cancel');
  }
  return out;
}

/** Decode + validate a raw result; undefined when the prompt rejects it. */
export function decodeValid(p: Prompt<any>, state: State, raw: any): { decoded: any } | undefined {
  try {
    const decoded = p.decode(raw, state);
    if (p.validate(decoded, state) === false) {
      return undefined;
    }
    return { decoded };
  } catch {
    return undefined;
  }
}

/** Valid, de-duplicated options for a decision prompt (at most `cap`). */
export function promptOptions(p: Prompt<any>, state: State, rng: Rng, cap = 32): (Candidate & { decoded: any })[] {
  const out: (Candidate & { decoded: any })[] = [];
  const seen = new Set<string>();
  const raws = rawCandidates(p, state, rng, cap);
  // "Cancel" (a null answer) is the client's undo button, not a game choice: once an effect is
  // under way the rules let you decline only through the choices the card itself offers ("you
  // may", "up to"), which appear here as real options (e.g. choosing nothing). Many card
  // implementations also crash on null. So null is used only when nothing else is valid.
  const anyOther = raws.some(c => c.raw !== null && decodeValid(p, state, c.raw));
  for (const c of raws) {
    if (c.raw === null && anyOther) {
      continue;
    }
    const sig = JSON.stringify(c.raw);
    if (seen.has(sig)) {
      continue;
    }
    seen.add(sig);
    const v = decodeValid(p, state, c.raw);
    if (v) {
      out.push({ ...c, decoded: v.decoded });
      if (out.length >= cap) {
        break;
      }
    }
  }
  return out;
}
