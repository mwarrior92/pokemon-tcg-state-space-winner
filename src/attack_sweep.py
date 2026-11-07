"""
Sweep every attack in the engine's card pool through the attack-text compiler (src/attack_text.py) and
report the damage-relevant text it does NOT understand, ranked by how many meta decklists play the card.

  python src/attack_sweep.py               # meta-played cards only
  python src/attack_sweep.py --all         # every card with attacks

A "zero-damage risk" is an attack printed with 0 damage whose text clearly does damage but that the
compiler reads as 0 - the N's Zoroark ex / Night Joker kind of miss.
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from attack_text import norm, parse_attack, typical_damage  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--top", type=int, default=40)
    args = ap.parse_args()
    from cabt_bridge import Engine
    eng = Engine.get(2)
    meta = json.loads((ROOT / "meta" / "decklists_2026-09-19_to_10-31.json").read_text(encoding="utf-8"))
    lists_with: Counter = Counter()
    for d in meta:
        for name in {norm(c["name"]) for c in d["cards"]}:
            lists_with[name] += 1
    seen = set()
    rows = []
    for cid, c in sorted(eng.cards.items()):
        n = norm(c.get("name"))
        for aid in c.get("attacks", []):
            a = eng.attacks.get(aid) or {}
            key = (n, norm(a.get("name")), norm(a.get("text")))
            if key in seen:
                continue
            seen.add(key)
            sp = parse_attack(a.get("text"), a.get("damage"), a.get("energies"), a.get("name"), c.get("name"))
            exp, _ = typical_damage(sp)
            text = norm(a.get("text"))
            zero_risk = exp == 0 and not sp["copy"] and not sp["spread"] and bool(sp["unparsed"])
            rows.append({"card": c.get("name"), "attack": a.get("name"), "lists": lists_with.get(n, 0),
                         "unparsed": sp["unparsed"], "zero_risk": zero_risk, "patched": sp["patched"]})
    pool = [r for r in rows if args.all or r["lists"] > 0]
    with_text = [r for r in pool if r["unparsed"] or r["zero_risk"]]
    print(f"{len(pool)} attacks{'' if args.all else ' on meta-played cards'}; "
          f"{len(pool) - len(with_text)} fully understood, {len(with_text)} with damage text the compiler misses "
          f"({sum(r['zero_risk'] for r in with_text)} read as 0 damage although the text does damage)")
    print(f"\nranked by meta decklists playing the card (of {len(meta)}):")
    for r in sorted(with_text, key=lambda r: -r["lists"])[: args.top]:
        flag = "ZERO-DAMAGE RISK " if r["zero_risk"] else ""
        print(f"  {r['lists']:4d}  {r['card']} - {r['attack']}: {flag}{' | '.join(r['unparsed'])[:150]}")


if __name__ == "__main__":
    main()
