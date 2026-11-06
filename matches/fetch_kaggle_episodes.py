"""
Download top-vs-top game replays from the Kaggle Pokemon TCG AI Battle Challenge ladder.

Uses Kaggle's public (unauthenticated) endpoints:
  POST https://www.kaggle.com/api/i/competitions.LeaderboardService/GetLeaderboard   {"competitionId": 116727}
  POST https://www.kaggle.com/api/i/competitions.EpisodeService/ListEpisodes        {"submissionId": N}
  GET  https://www.kaggleusercontent.com/episodes/{episodeId}.json                  (full replay)

Keeps only episodes where BOTH agents were rated in the leaderboard's top `--top-rank` at game
time (the closest thing to semifinals/finals). Replays are saved to matches/kaggle_episodes/.

  python matches/fetch_kaggle_episodes.py --teams 10 --top-rank 30 --max 40
"""
from __future__ import annotations

import argparse
import json
import time
import urllib.request
from pathlib import Path

COMPETITION_ID = 116727
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) winner-deck-research"
OUT = Path(__file__).resolve().parent / "kaggle_episodes"


def _post(url: str, body: dict) -> dict:
    req = urllib.request.Request(url, data=json.dumps(body).encode(), method="POST",
                                 headers={"Content-Type": "application/json", "User-Agent": UA})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read())


def _get(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=120) as r:
        return r.read()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--teams", type=int, default=10, help="pull game lists from the top N teams")
    ap.add_argument("--top-rank", type=int, default=30, help="both players must be rated within the top N")
    ap.add_argument("--max", type=int, default=40, help="maximum episodes to download")
    args = ap.parse_args()
    OUT.mkdir(exist_ok=True)

    lb = _post("https://www.kaggle.com/api/i/competitions.LeaderboardService/GetLeaderboard",
               {"competitionId": COMPETITION_ID})["publicLeaderboard"]
    lb.sort(key=lambda x: x["rank"])
    threshold = float(lb[min(args.top_rank, len(lb)) - 1]["displayScore"])
    print(f"leaderboard: {len(lb)} teams; top-{args.top_rank} rating threshold {threshold:.1f}")

    chosen: dict[int, dict] = {}
    for entry in lb[: args.teams]:
        eps = _post("https://www.kaggle.com/api/i/competitions.EpisodeService/ListEpisodes",
                    {"submissionId": entry["submissionId"]})["episodes"]
        for e in eps:
            if e.get("state") != "COMPLETED" or len(e.get("agents", [])) != 2:
                continue
            if all((a.get("initialScore") or 0) >= threshold for a in e["agents"]):
                chosen[e["id"]] = e
        print(f"  rank {entry['rank']:2d} team {entry['teamId']}: {len(eps)} episodes listed, {len(chosen)} top-vs-top so far")
        time.sleep(1.0)

    picked = sorted(chosen.values(), key=lambda e: -min(a["initialScore"] for a in e["agents"]))[: args.max]
    meta = []
    for e in picked:
        path = OUT / f"{e['id']}.json"
        if not path.exists():
            path.write_bytes(_get(f"https://www.kaggleusercontent.com/episodes/{e['id']}.json"))
            time.sleep(1.0)
        meta.append({"episodeId": e["id"], "createTime": e["createTime"],
                     "agents": [{"teamId": a["teamId"], "score": a["initialScore"], "reward": a.get("reward")} for a in e["agents"]]})
    (OUT / "index.json").write_text(json.dumps(meta, indent=1), encoding="utf-8")
    print(f"saved {len(meta)} top-vs-top episodes to {OUT}")


if __name__ == "__main__":
    main()
