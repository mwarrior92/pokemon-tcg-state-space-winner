"""Play one engine game between two meta lists and print every decision turn by turn.

  python src/play_log.py "Lopunny Dusknoir" "Crustle" --sub "Pokémon Center Lady=Cook" --seed 1
"""
from __future__ import annotations
import argparse, random, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from cabt_bridge import CardMap, Engine, SearchAgent, ST_MAIN  # noqa: E402
from card_compiler import StandardCardDatabase  # noqa: E402
from decision_benchmark import kind_of, option_signature  # noqa: E402
from gauntlet import load_meta_decks  # noqa: E402
from tail_check import META, ROOT, engine_ids  # noqa: E402

OT = {7: "play", 8: "attach", 9: "evolve", 10: "use ability of", 11: "discard", 12: "retreat", 13: "attack with", 14: "end turn"}


def mon(eng, m):
    c = eng.cards.get(m["id"], {})
    en = len(m.get("energy") or [])
    return f"{c.get('name','?')} {m.get('hp')}/{m.get('maxHp')}hp" + (f" {en}E" if en else "")


def board(eng, cur, s):
    p = cur["players"][s]
    act = [mon(eng, m) for m in (p.get("active") or []) if m]
    bench = [mon(eng, m) for m in p.get("bench") or []]
    return (f"prizes {len(p.get('prize') or [])}, hand {p.get('handCount')}, deck {p.get('deckCount')} | "
            f"Active: {', '.join(act) or '-'} | Bench: {'; '.join(bench) or '-'}")


def describe(eng, ob, act):
    sel = ob["select"]
    if sel["type"] == ST_MAIN and act:
        o = sel["option"][act[0]]
        typ, card, target, atk = option_signature(ob, act[0])
        name = lambda i: eng.cards.get(i, {}).get("name", "?") if i is not None else None
        if o["type"] == 13:
            return f"attack with {name(card) or 'Active'}: {eng.attacks.get(atk, {}).get('name', '?')}"
        s = OT.get(o["type"], f"option {o['type']}")
        if card is not None:
            s += f" {name(card)}"
        if target is not None:
            s += f" -> {name(target)}"
        return s
    picked = []
    for i in act:
        o = sel["option"][i] if i < len(sel["option"]) else {}
        cid = o.get("id") or o.get("cardId")
        picked.append(eng.cards.get(cid, {}).get("name") if cid else str(i))
    return f"  [{kind_of(ob)}] {', '.join(map(str, picked)) or 'none'}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("deck_a"); ap.add_argument("deck_b")
    ap.add_argument("--sub", action="append", default=[])
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--mcts", type=int, default=0, help="use the tree-search agent with this many iterations")
    ap.add_argument("--turns", type=int, default=3)
    a = ap.parse_args()
    subs = dict(s.split("=", 1) for s in a.sub)
    db = StandardCardDatabase(ROOT / "pokemon-tcg-data-standard", META)
    eng = Engine.get(); cmap = CardMap(eng, db)
    decks = load_meta_decks(db, META)
    def best(arch):
        for d, dk in sorted((x for x in decks if x[0]["deck"] == arch), key=lambda x: x[0]["rank"]):
            ids = engine_ids(cmap, eng, dk, subs)
            if ids:
                return ids, f"{arch} ({d['event']} #{d['rank']})"
        sys.exit(f"no playable {arch} list")
    (A, la), (B, lb) = best(a.deck_a), best(a.deck_b)
    rng = random.Random(a.seed)
    if a.mcts:
        from mcts import MCTSAgent
        agents = (MCTSAgent(eng, A, B, rng, iterations=a.mcts, n_turns=a.turns),
                  MCTSAgent(eng, B, A, rng, iterations=a.mcts, n_turns=a.turns))
    else:
        agents = (SearchAgent(eng, A, B, rng), SearchAgent(eng, B, A, rng))
    label = {0: la, 1: lb}
    print(f"P0 (goes first): {la}\nP1: {lb}\n")
    obs, _ = eng.game.battle_start(A, B)
    turn = -1
    try:
        while obs["current"]["result"] < 0:
            cur = obs["current"]; who = cur["yourIndex"]
            if cur["turn"] != turn:
                turn = cur["turn"]
                print(f"\n=== Turn {turn}: P{who} {label[who].split(' (')[0]} ===")
                for s in (who, 1 - who):
                    print(f"  P{s}: {board(eng, cur, s)}")
            act = agents[who](obs)
            sel = obs["select"]
            if sel and (len(sel["option"]) > 1 or sel["type"] == ST_MAIN):
                print(f"  P{who} {describe(eng, obs, act)}")
            obs = eng.game.battle_select(act)
            for _ag in agents:
                getattr(_ag, "observe", lambda o: None)(obs)
        r = obs["current"]["result"]
        print(f"\nResult: {'P%d %s wins' % (r, label[r].split(' (')[0]) if r in (0, 1) else 'draw'} on turn {turn}")
        for s in (0, 1):
            print(f"  P{s}: {board(eng, obs['current'], s)}")
    finally:
        eng.game.battle_finish()


if __name__ == "__main__":
    main()
