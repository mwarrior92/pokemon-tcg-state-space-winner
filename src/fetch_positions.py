"""
Collect turn-start positions from real top-vs-top Kaggle games, for fitting the board evaluation.

Replays are streamed (not stored): for every game, the first main-phase position of each player's turn
is kept in compact form with the mover, turn, episode and winner, in matches/eval_positions.jsonl.gz.
Local replays (matches/kaggle_episodes*, the race-graph episode list) are used first.

  python src/fetch_positions.py --max 800 --teams 25 --top-rank 40
"""
from __future__ import annotations

import argparse
import gzip
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "matches"))
OUT = ROOT / "matches" / "eval_positions.jsonl.gz"
DROP = ("hand", "looking")


def compact(cur: dict) -> dict:
    """The parts of an observation the evaluation reads (own hand contents dropped; counts kept)."""
    c = {k: v for k, v in cur.items() if k not in ("players",)}
    c["players"] = [{k: v for k, v in p.items() if k not in DROP} for p in cur["players"]]
    return c


def positions(rep: dict) -> list[dict]:
    from decision_benchmark import decision_points, winner_seat
    w = winner_seat(rep)
    if w is None:
        return []
    out, seen = [], set()
    for _, seat, ob, _, _ in decision_points(rep):
        cur = ob["current"]
        t = cur.get("turn", 0)
        if t < 1 or (seat, t) in seen or ob["select"]["type"] != 0:
            continue
        seen.add((seat, t))
        out.append({"seat": seat, "turn": t, "won": int(seat == w), "cur": compact(cur)})
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--max", type=int, default=800, help="new episodes to stream")
    ap.add_argument("--teams", type=int, default=25)
    ap.add_argument("--top-rank", type=int, default=40)
    args = ap.parse_args()
    from fetch_kaggle_episodes import COMPETITION_ID, _get, _post
    done: set[int] = set()
    if OUT.exists():
        with gzip.open(OUT, "rt", encoding="utf-8") as f:
            for line in f:
                done.add(json.loads(line)["episode"])
    local = {int(f.stem): f for d in ("kaggle_episodes", "kaggle_episodes_deck/crustle")
             for f in (ROOT / "matches" / d).glob("*.json") if f.stem.isdigit()}
    ids = list(local)
    seq = ROOT / "matches" / "race_sequences.jsonl"
    if seq.exists():
        ids += [json.loads(line)["episode"] for line in seq.read_text(encoding="utf-8").splitlines()]
    lb = _post("https://www.kaggle.com/api/i/competitions.LeaderboardService/GetLeaderboard",
               {"competitionId": COMPETITION_ID})["publicLeaderboard"]
    lb.sort(key=lambda x: x["rank"])
    threshold = float(lb[min(args.top_rank, len(lb)) - 1]["displayScore"])
    for entry in lb[: args.teams]:
        try:
            eps = _post("https://www.kaggle.com/api/i/competitions.EpisodeService/ListEpisodes",
                        {"submissionId": entry["submissionId"]})["episodes"]
        except Exception as ex:  # one failed listing must not stop the scan
            print(f"  listing failed for rank {entry['rank']}: {ex}")
            continue
        ids += [e["id"] for e in eps if e.get("state") == "COMPLETED" and len(e.get("agents", [])) == 2
                and all((a.get("initialScore") or 0) >= threshold for a in e["agents"])]
        time.sleep(1.0)
    todo = [i for i in dict.fromkeys(ids) if i not in done]
    todo = sorted(todo, key=lambda i: (i not in local, -i))[: args.max + len(local)]
    print(f"{len(done)} episodes already collected; {len(todo)} to process ({sum(i in local for i in todo)} local)", flush=True)
    added = n_pos = 0
    with gzip.open(OUT, "at", encoding="utf-8") as out:
        for k, eid in enumerate(todo, 1):
            try:
                raw = local[eid].read_bytes() if eid in local else _get(f"https://www.kaggleusercontent.com/episodes/{eid}.json")
                pos = positions(json.loads(raw))
            except Exception as ex:  # one bad replay must not stop the stream
                print(f"  skip {eid}: {ex}")
                continue
            for p in pos:
                out.write(json.dumps({"episode": eid, **p}) + "\n")
            added += bool(pos)
            n_pos += len(pos)
            if eid not in local:
                time.sleep(1.0)
            if k % 25 == 0:
                out.flush()
                print(f"  {k}/{len(todo)} episodes, {n_pos} positions", flush=True)
    print(f"added {added} games, {n_pos} positions -> {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
