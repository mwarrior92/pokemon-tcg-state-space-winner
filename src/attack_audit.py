"""
Audit: does our threat model agree with what the engine actually does when an attack is used?

During engine games between meta decks, at every main-phase decision where attacks are legal, each
legal attack is executed in the engine's search (from the same position) and the damage it really
deals is measured. That is compared with our model's prediction for the same attack
(`_attack_prediction`: base damage, Weakness/Resistance, the defender's protections, and whether we
think the Energy cost is paid).

Mismatch kinds:
  cost      the engine allows the attack but our model thinks Energy is still missing
            (cost reductions, alternative costs);
  bypass    we predict 0 (blocked) but it does damage (we miss an "ignores effects" clause);
  blocked   we predict damage but it does none (a protection or condition we miss; or a failed coin flip);
  amount    both nonzero but different by more than 10 (bonuses, reductions, coin flips we don't model).
Coin-flip attacks are reported separately so their randomness isn't mistaken for a bug.

  python src/attack_audit.py --pairs 24 --games 2 --workers 10
"""
from __future__ import annotations

import argparse
import json
import random
import re
import sys
import time
from collections import defaultdict
from multiprocessing import Pool
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
from cabt_bridge import OT_ATTACK, ST_MAIN, Engine, SearchAgent, _missing_energy, _ntext, _protected_damage  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "matches" / "regression_results" / "attack_audit.json"


def _attack_prediction(eng: Engine, attacker: dict[str, Any], defender: dict[str, Any], aid: int,
                       cur: dict[str, Any] | None = None, side: int = 0) -> tuple[float, int]:
    """Our model's damage for one attack and the Energy it thinks is missing (board-aware when `cur` is given)."""
    if cur is not None:
        from cabt_bridge import attack_estimate
        dmg, _, miss = attack_estimate(eng, cur, side, attacker, defender, aid)
        return dmg, miss
    ac, tc = eng.cards.get(attacker["id"], {}), eng.cards.get(defender["id"], {})
    a = eng.attacks.get(aid, {})
    dmg = float(a.get("damage") or 0)
    if dmg > 0:
        if tc.get("weakness") is not None and tc.get("weakness") == ac.get("energyType"):
            dmg *= 2
        if tc.get("resistance") is not None and tc.get("resistance") == ac.get("energyType"):
            dmg = max(0.0, dmg - 30)
        dmg = _protected_damage(eng, ac, a, defender, dmg)
    return dmg, _missing_energy(a.get("energies") or [], attacker.get("energies") or [])


def _measure(eng: Engine, agent: SearchAgent, ob: dict[str, Any], opt: int) -> float | None:
    """Damage the attack at option `opt` actually does to the Defending Pokemon (its HP if Knocked Out)."""
    cur = ob["current"]
    me = cur["yourIndex"]
    d0 = (cur["players"][1 - me].get("active") or [None])[0]
    if not d0:
        return None
    prizes0 = len(cur["players"][me].get("prize") or [])
    root = eng.search_begin(ob, *agent._guesses(ob))
    if root is None:
        return None
    try:
        st = eng.search_step(root["searchId"], [opt])
        for _ in range(40):                        # resolve the attacker's own sub-choices (targets, discards)
            if st is None:
                return None
            o2 = st["observation"]
            c2 = o2["current"]
            if c2.get("result", -1) >= 0 or c2["yourIndex"] != me or c2["turn"] != cur["turn"] or not o2.get("select"):
                break
            st = eng.search_step(st["searchId"], agent.static_choice(o2))
        if st is None:
            return None
        c2 = st["observation"]["current"]
        if len(c2["players"][me].get("prize") or []) < prizes0:
            return float(d0["hp"])                  # Knocked Out (Prize taken)
        d1 = (c2["players"][1 - me].get("active") or [None])[0]
        if d1 and d1.get("id") == d0.get("id"):
            return float(max(0, d0["hp"] - d1["hp"]))
        return None                                 # defender left the Active Spot some other way
    finally:
        eng.search_end()


_W: dict = {}


def _init() -> None:
    _W["eng"] = Engine.get(2)


def _job(args: tuple) -> list[dict[str, Any]]:
    a_ids, b_ids, games, seed = args
    eng = _W["eng"]
    rng = random.Random(seed)
    rows = []
    for g in range(games):
        d0, d1 = (a_ids, b_ids) if g % 2 == 0 else (b_ids, a_ids)
        agents = (SearchAgent(eng, d0, d1, rng), SearchAgent(eng, d1, d0, rng))
        obs, _ = eng.game.battle_start(d0, d1)
        steps = 0
        try:
            while obs["current"]["result"] < 0 and steps < 5000:
                cur = obs["current"]
                who = cur["yourIndex"]
                sel = obs.get("select")
                if sel and sel["type"] == ST_MAIN:
                    atk = [i for i, o in enumerate(sel["option"]) if o["type"] == OT_ATTACK]
                    me_p, op_p = cur["players"][who], cur["players"][1 - who]
                    att = (me_p.get("active") or [None])[0]
                    dfn = (op_p.get("active") or [None])[0]
                    for i in atk if att and dfn else []:
                        aid = sel["option"][i].get("attackId")
                        pred, miss = _attack_prediction(eng, att, dfn, aid, cur, who)
                        try:
                            actual = _measure(eng, agents[who], obs, i)
                        except OSError:
                            actual = None
                        if actual is None:
                            continue
                        a = eng.attacks.get(aid, {})
                        rows.append({"attacker": eng.cards.get(att["id"], {}).get("name"), "attack": a.get("name"),
                                     "defender": eng.cards.get(dfn["id"], {}).get("name"), "defender_id": dfn["id"], "def_hp": dfn["hp"],
                                     "pred": pred, "missing": miss, "actual": actual,
                                     "coin": "flip" in _ntext(a.get("text")), "text": a.get("text", "")})
                act = agents[who](obs)
                obs = eng.game.battle_select(act)
                steps += 1
        except OSError:
            pass
        finally:
            eng.game.battle_finish()
    return rows


def classify(r: dict[str, Any]) -> str | None:
    if r["missing"] > 0:
        return "cost"
    if r["pred"] == 0 and r["actual"] > 0:
        return "bypass"
    if r["pred"] > 0 and r["actual"] == 0:
        return "blocked"
    if r["actual"] >= r["def_hp"] and r["pred"] >= r["def_hp"]:
        return None                       # Knocked Out as predicted (measured damage is capped at the HP left)
    if abs(r["pred"] - r["actual"]) > 10:
        return "amount"
    return None


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pairs", type=int, default=24, help="random deck pairings from the meta lists")
    ap.add_argument("--games", type=int, default=2)
    ap.add_argument("--workers", type=int, default=10)
    ap.add_argument("--seed", type=int, default=5)
    args = ap.parse_args()
    from cabt_bridge import CardMap
    from card_compiler import StandardCardDatabase
    from gauntlet import load_meta_decks
    from tail_check import META, engine_ids
    db = StandardCardDatabase(ROOT / "pokemon-tcg-data-standard", META)
    eng = Engine.get(2)
    cmap = CardMap(eng, db)
    by_arch: dict[str, list[int]] = {}
    for d, dk in sorted(load_meta_decks(db, META), key=lambda x: x[0]["rank"]):
        if d["deck"] not in by_arch:
            ids = engine_ids(cmap, eng, dk, {"Pokémon Center Lady": "Cook"})
            if ids:
                by_arch[d["deck"]] = ids
    archs = sorted(by_arch)
    rng = random.Random(args.seed)
    pairs = [("Lopunny Dusknoir", "Crustle")] + [tuple(rng.sample(archs, 2)) for _ in range(args.pairs - 1)]
    print(f"{len(archs)} archetypes; {len(pairs)} pairings x {args.games} games")
    rows = []
    t0 = time.perf_counter()
    with Pool(args.workers, initializer=_init) as p:
        for k, res in enumerate(p.imap_unordered(_job, [(by_arch[a], by_arch[b], args.games, 31 * n) for n, (a, b) in enumerate(pairs)]), 1):
            rows += res
            print(f"  {k}/{len(pairs)} pairings, {len(rows)} attacks measured ({time.perf_counter() - t0:.0f}s)", flush=True)

    groups: dict[tuple, list] = defaultdict(list)
    for r in rows:
        groups[(r["attacker"], r["attack"], r["defender"])].append(r)
    report = defaultdict(list)
    for key, rs in groups.items():
        kinds = [classify(r) for r in rs]
        bad = [k for k in kinds if k]
        if not bad:
            continue
        kind = max(set(bad), key=bad.count)
        report[kind].append({"attacker": key[0], "attack": key[1], "defender": key[2], "n": len(rs),
                             "mismatch_share": len(bad) / len(rs), "pred": rs[0]["pred"], "missing": rs[0]["missing"],
                             "actual_mean": sum(r["actual"] for r in rs) / len(rs),
                             "actual_range": [min(r["actual"] for r in rs), max(r["actual"] for r in rs)],
                             "coin": rs[0]["coin"], "text": rs[0]["text"][:150]})
    total = len(rows)
    print(f"\n{total} attacks measured across {len(groups)} (attacker, attack, defender) combinations")
    labels = {"cost": "Engine allows the attack, our model says Energy is missing",
              "bypass": "We predict 0 (blocked), engine does damage",
              "blocked": "We predict damage, engine does 0",
              "amount": "Damage differs by more than 10"}
    for kind in ("cost", "bypass", "blocked", "amount"):
        items = sorted(report[kind], key=lambda x: (x["coin"], -x["n"]))
        print(f"\n== {labels[kind]}: {len(items)} combinations ==")
        for x in items[:14]:
            rng_s = f"{x['actual_range'][0]:.0f}-{x['actual_range'][1]:.0f}"
            print(f"  {x['attacker']:24s} {x['attack']:20s} vs {x['defender']:22s} n={x['n']:3d}  "
                  f"pred {x['pred']:4.0f} (missing {x['missing']})  actual {x['actual_mean']:5.0f} [{rng_s}]"
                  f"{'  coin' if x['coin'] else ''}  | {x['text'][:70]}")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({"rows": len(rows), "report": report}, indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"\nsaved {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
