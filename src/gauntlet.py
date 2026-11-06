"""
Meta gauntlet: play a deck against REAL tournament lists with the turn-by-turn simulator.

- Opponents: one representative list per archetype (its best-placing list in the
  512-deck tournament file), weighted by that archetype's meta share.
- Matchups: N sampled games per opponent, alternating who goes first, with fixed seeds
  so different candidate decks face identical shuffles of the opponent (common random
  numbers -> much less noise when comparing decks).
- State values: every game logs board states; aggregating them gives P(win | state),
  e.g. P(first player wins | Pokemon in play when the second player starts) or
  P(win | took the first KO) split by how much comeback the opposing deck has.
"""
from __future__ import annotations

import json
import math
import statistics
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from card_compiler import CompiledCard, StandardCardDatabase
from game_sim import Game
from sim_effects import compile_script

COMEBACK_CONDS = {"BEHIND_ON_PRIZES", "AFTER_OWN_KO", "OPP_PRIZES_LE_3", "OPP_PRIZES_LE_2", "OPP_PRIZES_EQ_2"}


def expand(deck: dict[CompiledCard, int]) -> list[CompiledCard]:
    out: list[CompiledCard] = []
    for c, n in deck.items():
        out += [c] * n
    return out


def comeback_cards(deck: dict[CompiledCard, int]) -> int:
    """Copies of cards that only switch on (or scale) when their player is behind / was just KO'd."""
    n = 0
    for c, k in deck.items():
        conds = set()
        for v in c.action_conditions.values():
            conds |= set(v)
        sc = compile_script(c)
        if conds & COMEBACK_CONDS or (sc.ability and sc.ability.get("after_ko")) or "SEASONED_SKILL" in sc.passives \
                or any(m["mod"] in ("per_opp_prizes_taken", "if_ko_last") for a in sc.attacks for m in a.mods):
            n += k
    return n


def coverage(deck: dict[CompiledCard, int]) -> tuple[float, list[str]]:
    """Share of non-basic-energy card copies whose effects the simulator executes."""
    tot = ok = 0
    missing: Counter[str] = Counter()
    for c, k in deck.items():
        if "BASIC_ENERGY" in c.tags:
            continue
        tot += k
        sc = compile_script(c)
        if sc.unmodeled:
            missing[f"{c.name} ({'; '.join(sc.unmodeled)})"] += k
        else:
            ok += k
    return (ok / tot if tot else 1.0), [f"{n}x {m}" for m, n in missing.most_common()]


@dataclass
class Opponent:
    archetype: str
    weight: float
    deck: dict[CompiledCard, int]
    source: str


def load_meta_decks(db: StandardCardDatabase, meta_path: Path) -> list[tuple[dict[str, Any], dict[CompiledCard, int]]]:
    with open(meta_path, encoding="utf-8") as f:
        meta = json.load(f)
    out = []
    for d in meta:
        deck: dict[CompiledCard, int] = defaultdict(int)
        for c in d["cards"]:
            cc = db.resolve_card(c["name"], c["set"], str(c["num"]))
            if cc:
                deck[cc] += c["count"]
        if sum(deck.values()) == 60:
            out.append((d, dict(deck)))
    return out


def build_gauntlet(db: StandardCardDatabase, meta_path: Path, min_lists: int = 8, max_opponents: int = 14,
                   playable: Any = None) -> list[Opponent]:
    """One representative (best-placing) list per archetype. `playable(deck) -> bool` restricts the choice,
    e.g. to lists the CABT engine supports."""
    decks = load_meta_decks(db, meta_path)
    by_arch: dict[str, list[tuple[dict[str, Any], dict[CompiledCard, int]]]] = defaultdict(list)
    for d, dk in decks:
        by_arch[d["deck"]].append((d, dk))
    archs = sorted((a for a, v in by_arch.items() if len(v) >= min_lists), key=lambda a: -len(by_arch[a]))[:max_opponents]
    total = sum(len(by_arch[a]) for a in archs)
    opps = []
    for a in archs:
        pool = [x for x in by_arch[a] if playable is None or playable(x[1])]
        if not pool:
            continue
        d, dk = min(pool, key=lambda x: x[0]["rank"])
        opps.append(Opponent(a, len(by_arch[a]) / total, dk, f"{d['event']} #{d['rank']}"))
    return opps


@dataclass
class MatchupResult:
    opponent: str
    weight: float
    games: int
    wins_first: float
    games_first: int
    wins_second: float
    games_second: int

    @property
    def win_rate(self) -> float:
        return (self.wins_first + self.wins_second) / max(1, self.games)

    @property
    def wr_first(self) -> float:
        return self.wins_first / max(1, self.games_first)

    @property
    def wr_second(self) -> float:
        return self.wins_second / max(1, self.games_second)


@dataclass
class GauntletReport:
    win_rate: float
    win_rate_first: float
    win_rate_second: float
    stderr: float
    matchups: list[MatchupResult]
    coverage: float
    unmodeled: list[str]
    state_values: dict[str, Any] = field(default_factory=dict)
    games: int = 0


def play_matchup(deck: list[CompiledCard], opp: list[CompiledCard], n_games: int, seed: int = 0,
                 traces: list[dict[str, Any]] | None = None, opp_comeback: int = 0) -> tuple[float, int, float, int]:
    wf = ws = 0.0
    gf = gs = 0
    for i in range(n_games):
        first = i % 2          # we are player 0; alternate who goes first
        g = Game(deck, opp, seed=seed * 100003 + i, first=first)
        try:
            w = g.play()
        except Exception as ex:  # a simulator bug must not silently bias a matchup
            raise RuntimeError(f"simulation failed (seed={seed * 100003 + i}): {ex}") from ex
        score = 0.5 if w is None else (1.0 if w == 0 else 0.0)
        if first == 0:
            wf += score
            gf += 1
        else:
            ws += score
            gs += 1
        if traces is not None:
            traces.append({"we_first": first == 0, "score": score, "trace": g.trace, "events": g.events,
                           "opp_comeback": opp_comeback, "plies": g.turn, "reason": g.end_reason})
    return wf, gf, ws, gs


def evaluate_gauntlet(deck: dict[CompiledCard, int], opponents: list[Opponent], games_per_opp: int = 20,
                      seed: int = 7, collect_states: bool = True) -> GauntletReport:
    me = expand(deck)
    results: list[MatchupResult] = []
    traces: list[dict[str, Any]] = [] if collect_states else None  # type: ignore[assignment]
    for k, o in enumerate(opponents):
        wf, gf, ws, gs = play_matchup(me, expand(o.deck), games_per_opp, seed=seed + 1000 * k, traces=traces,
                                      opp_comeback=comeback_cards(o.deck))
        results.append(MatchupResult(o.archetype, o.weight, gf + gs, wf, gf, ws, gs))
    wsum = sum(r.weight for r in results) or 1.0
    wr = sum(r.weight * r.win_rate for r in results) / wsum
    wr1 = sum(r.weight * r.wr_first for r in results) / wsum
    wr2 = sum(r.weight * r.wr_second for r in results) / wsum
    var = sum((r.weight / wsum) ** 2 * r.win_rate * (1 - r.win_rate) / max(1, r.games) for r in results)
    cov, missing = coverage(deck)
    rep = GauntletReport(wr, wr1, wr2, math.sqrt(var), results, cov, missing, games=sum(r.games for r in results))
    if collect_states:
        rep.state_values = state_value_tables(traces)
    return rep


def state_value_tables(traces: list[dict[str, Any]]) -> dict[str, Any]:
    """Empirical P(win | state) from sampled games (we are player 0)."""
    out: dict[str, Any] = {}
    # 1. Pokemon the FIRST player has in play when the second player starts their first turn
    t1: dict[int, list[float]] = defaultdict(list)
    for tr in traces:
        snap = next((s for s in tr["trace"] if s["tag"] == "start_second_turn1"), None)
        if not snap:
            continue
        first_idx = 0 if tr["we_first"] else 1
        n = snap["in_play"][first_idx]
        first_won = tr["score"] if tr["we_first"] else 1.0 - tr["score"]
        t1[min(n, 5)].append(first_won)
    out["first_player_in_play_at_opp_t1"] = {
        k: {"freq": round(len(v) / max(1, sum(len(x) for x in t1.values())), 3), "p_first_wins": round(statistics.mean(v), 3), "n": len(v)}
        for k, v in sorted(t1.items())
    }
    # 2. Who took the first KO (and by which of their turns), split by opposing comeback density
    fk: dict[tuple[str, str], list[float]] = defaultdict(list)
    for tr in traces:
        ko = next((e for e in tr["events"] if e[2].startswith("KO:")), None)
        if not ko:
            continue
        ply, victim, _ = ko
        we_took = victim == 1
        cb = "opp comeback-heavy (3+)" if tr["opp_comeback"] >= 3 else "opp few comeback cards"
        key = ("we took first KO" if we_took else "they took first KO", cb)
        fk[key].append(tr["score"])
    out["first_ko"] = {f"{a} | {b}": {"p_win": round(statistics.mean(v), 3), "n": len(v)} for (a, b), v in sorted(fk.items())}
    # 3. Prize lead after each of our turns -> P(win)
    lead: dict[int, list[float]] = defaultdict(list)
    for tr in traces:
        seen = set()
        for s in tr["trace"]:
            if s["tag"] != "end_turn" or s["mover"] != 0:
                continue
            d = s["prizes"][1] - s["prizes"][0]   # >0 = we are ahead (we have fewer Prizes left)
            d = max(-3, min(3, d))
            if d not in seen:
                seen.add(d)
                lead[d].append(tr["score"])
    out["prize_lead_after_our_turn"] = {k: {"p_win": round(statistics.mean(v), 3), "n": len(v)} for k, v in sorted(lead.items())}
    reasons = Counter(tr["reason"] for tr in traces)
    out["end_reasons"] = dict(reasons.most_common())
    out["mean_plies"] = round(statistics.mean(tr["plies"] for tr in traces), 1) if traces else 0
    return out


# ---------------------------------------------------------------------------
# CABT-engine gauntlet (real rules engine; see cabt_bridge.py)
# ---------------------------------------------------------------------------

def evaluate_gauntlet_engine(deck: dict[CompiledCard, int], opponents: list[Opponent], db: StandardCardDatabase,
                             games_per_opp: int = 20, seed: int = 7) -> GauntletReport:
    """
    Play `deck` against each opponent in the CABT engine with the search agent on both sides,
    alternating who goes first. Falls back to the Python simulator (game_sim) if the engine
    lacks any card in `deck`; `rep.state_values["engine"]` says which was used.
    """
    import random as _random

    from cabt_bridge import CardMap, Engine, SearchAgent, play_engine_game

    eng = Engine.get()
    cmap = CardMap(eng, db)
    me_ids, missing = cmap.deck_ids(deck)
    if missing:
        rep = evaluate_gauntlet(deck, opponents, games_per_opp=games_per_opp, seed=seed)
        rep.state_values["engine"] = "python simulator (CABT engine lacks: " + ", ".join(missing) + ")"
        return rep
    rng = _random.Random(seed)
    results: list[MatchupResult] = []
    traces: list[dict[str, Any]] = []
    for o in opponents:
        op_ids, op_missing = cmap.deck_ids(o.deck)
        if op_missing:
            continue
        wf = ws = 0.0
        gf = gs = 0
        for i in range(games_per_opp):
            we_first = i % 2 == 0
            d0, d1 = (me_ids, op_ids) if we_first else (op_ids, me_ids)
            agents = (SearchAgent(eng, d0, d1, rng), SearchAgent(eng, d1, d0, rng))
            r = play_engine_game(d0, d1, agents)
            me_seat = 0 if we_first else 1
            score = 0.5 if r["winner"] is None else (1.0 if r["winner"] == me_seat else 0.0)
            if we_first:
                wf += score
                gf += 1
            else:
                ws += score
                gs += 1
            traces.append({"me_seat": me_seat, "first": r["first"], "score": score, "trace": r["trace"],
                           "opp_comeback": comeback_cards(o.deck), "plies": r["turns"]})
        results.append(MatchupResult(o.archetype, o.weight, gf + gs, wf, gf, ws, gs))
    wsum = sum(r.weight for r in results) or 1.0
    wr = sum(r.weight * r.win_rate for r in results) / wsum
    wr1 = sum(r.weight * r.wr_first for r in results) / wsum
    wr2 = sum(r.weight * r.wr_second for r in results) / wsum
    var = sum((r.weight / wsum) ** 2 * r.win_rate * (1 - r.win_rate) / max(1, r.games) for r in results)
    rep = GauntletReport(wr, wr1, wr2, math.sqrt(var), results, 1.0, [], games=sum(r.games for r in results))
    rep.state_values = engine_state_value_tables(traces)
    rep.state_values["engine"] = "CABT"
    return rep


def engine_state_value_tables(traces: list[dict[str, Any]]) -> dict[str, Any]:
    """P(win | state) from engine games (engine turn numbers: 1 = first player's first turn)."""
    out: dict[str, Any] = {}
    t1: dict[int, list[float]] = defaultdict(list)
    fk: dict[str, list[float]] = defaultdict(list)
    lead: dict[int, list[float]] = defaultdict(list)
    for tr in traces:
        me, first = tr["me_seat"], tr["first"]
        first_won = tr["score"] if me == first else 1.0 - tr["score"]
        snap = next((s for s in tr["trace"] if s["turn"] == 2), None)
        if snap:
            t1[min(5, snap["in_play"][first])].append(first_won)
        # first KO = first turn where someone's Prize count dropped
        prev = None
        for s in tr["trace"]:
            if prev and s["prizes"] != prev["prizes"]:
                we_took = s["prizes"][me] < prev["prizes"][me]
                cb = "opp comeback-heavy (3+)" if tr["opp_comeback"] >= 3 else "opp few comeback cards"
                fk[("we took first KO" if we_took else "they took first KO") + " | " + cb].append(tr["score"])
                break
            prev = s
        seen = set()
        for s in tr["trace"]:
            d = max(-3, min(3, s["prizes"][1 - me] - s["prizes"][me]))
            if d not in seen:
                seen.add(d)
                lead[d].append(tr["score"])
    tot = sum(len(v) for v in t1.values()) or 1
    out["first_player_in_play_at_opp_t1"] = {k: {"freq": round(len(v) / tot, 3), "p_first_wins": round(statistics.mean(v), 3), "n": len(v)}
                                             for k, v in sorted(t1.items())}
    out["first_ko"] = {k: {"p_win": round(statistics.mean(v), 3), "n": len(v)} for k, v in sorted(fk.items())}
    out["prize_lead"] = {k: {"p_win": round(statistics.mean(v), 3), "n": len(v)} for k, v in sorted(lead.items())}
    out["mean_plies"] = round(statistics.mean(t["plies"] for t in traces), 1) if traces else 0
    return out


def meta_round_robin(db: StandardCardDatabase, meta_path: Path, games_per_pair: int = 12, seed: int = 11,
                     agent_kwargs: dict[str, Any] | None = None, progress: bool = False) -> dict[str, Any]:
    """
    Play every engine-playable meta archetype against every other in the CABT engine and compare
    each archetype's meta-weighted simulated win rate with its real top-16 conversion rate.
    """
    import random as _random
    import time as _time

    from cabt_bridge import CardMap, Engine, SearchAgent, play_engine_game

    eng = Engine.get()
    cmap = CardMap(eng, db)
    opps = build_gauntlet(db, meta_path, playable=lambda dk: not cmap.deck_ids(dk)[1])
    ids = [cmap.deck_ids(o.deck)[0] for o in opps]
    rng = _random.Random(seed)
    kw = agent_kwargs or {}
    mat: dict[tuple[int, int], float] = {}
    t0 = _time.perf_counter()
    for i in range(len(opps)):
        for j in range(i + 1, len(opps)):
            w = 0.0
            for g in range(games_per_pair):
                a, b = (ids[i], ids[j]) if g % 2 == 0 else (ids[j], ids[i])
                r = play_engine_game(a, b, (SearchAgent(eng, a, b, rng, **kw), SearchAgent(eng, b, a, rng, **kw)))
                i_seat = 0 if g % 2 == 0 else 1
                w += 0.5 if r["winner"] is None else (1.0 if r["winner"] == i_seat else 0.0)
            mat[(i, j)] = w / games_per_pair
            mat[(j, i)] = 1 - w / games_per_pair
        if progress:
            print(f"  round-robin: {opps[i].archetype} done ({_time.perf_counter() - t0:.0f}s)", flush=True)
    decks = load_meta_decks(db, meta_path)
    rows = []
    for i, o in enumerate(opps):
        xs = [d for d, _ in decks if d["deck"] == o.archetype]
        conv = sum(1 for d in xs if d["rank"] <= 16) / len(xs) / 0.25
        others = [(b.weight, mat[(i, j)]) for j, b in enumerate(opps) if j != i]
        wr = sum(w * v for w, v in others) / sum(w for w, _ in others)
        rows.append({"archetype": o.archetype, "sim_wr": wr, "top16_conversion": conv, "lists": len(xs)})

    def _rank(v: list[float]) -> list[int]:
        order = sorted(range(len(v)), key=lambda k: v[k])
        rk = [0] * len(v)
        for p, k in enumerate(order):
            rk[k] = p
        return rk

    def _rho(x: list[float], y: list[float]) -> float:
        a, b = _rank(x), _rank(y)
        n = len(x)
        return 1 - 6 * sum((p - q) ** 2 for p, q in zip(a, b)) / (n * (n * n - 1)) if n > 2 else 0.0

    return {"rows": sorted(rows, key=lambda r: -r["sim_wr"]), "games_per_pair": games_per_pair,
            "spearman_vs_conversion": _rho([r["sim_wr"] for r in rows], [r["top16_conversion"] for r in rows]),
            "seconds": _time.perf_counter() - t0}
