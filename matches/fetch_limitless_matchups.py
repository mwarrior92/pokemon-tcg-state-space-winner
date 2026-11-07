"""
Real head-to-head records between archetypes, from Limitless Labs matchup tables (all rounds, Day 1 included).

For every tournament in the meta decklist file:
  limitlesstcg.com/tournaments/{id}            -> its Labs id
  labs.limitlesstcg.com/{labs}/decks           -> archetype slugs and names
  labs.limitlesstcg.com/{labs}/decks/{slug}/matchups -> that archetype's W-L-T vs every other archetype

Saves meta/matchups_<range>.json: per-event and summed records {deck: {opponent: [W, L, T]}}, with
archetype names mapped onto the names used in the decklist file.

  python matches/fetch_limitless_matchups.py
"""
from __future__ import annotations

import html
import json
import re
import time
import urllib.request
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
META = ROOT / "meta" / "decklists_2026-09-19_to_10-31.json"
OUT = ROOT / "meta" / "matchups_2026-09-19_to_10-31.json"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) deck-research"
ROW = re.compile(r'<a href="/\d+/decks/([^/"]+)/matchups">([^<]+)</a></td><td>(\d+)</td>'
                 r'<td[^>]*>\s*(\d+)\s*-\s*(\d+)\s*-\s*(\d+)\s*</td>')
DECK_LINK = re.compile(r'<a href="/\d+/decks/([a-z0-9-]+)"[^>]*>([^<]+)</a>')
# Labs names that differ from the decklist file's archetype names
ALIASES = {"ogerpon meganium hydrapple": "Hydrapple"}


def get(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read().decode("utf-8", "replace")


def norm(s: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(s).replace("’", "'")).strip().lower()


def main() -> None:
    meta = json.loads(META.read_text(encoding="utf-8"))
    names = {norm(d["deck"]): d["deck"] for d in meta}
    events = {}
    for d in meta:
        events.setdefault(d["tournament"], d["event"])

    def canon(labs_name: str) -> str:
        n = norm(labs_name)
        return ALIASES.get(n) or names.get(n) or html.unescape(labs_name).strip()

    total: dict[str, dict[str, list[int]]] = defaultdict(lambda: defaultdict(lambda: [0, 0, 0]))
    per_event = {}
    for tid, ev in events.items():
        labs = re.search(r"labs\.limitlesstcg\.com/(\d+)/", get(f"https://limitlesstcg.com/tournaments/{tid}"))
        time.sleep(1.0)
        if not labs:
            print(f"  {ev}: no Labs page, skipped")
            continue
        lid = labs.group(1)
        decks_page = get(f"https://labs.limitlesstcg.com/{lid}/decks")
        time.sleep(1.0)
        slugs = {}
        for slug, name in DECK_LINK.findall(decks_page):
            if slug not in slugs and canon(name) in names.values():
                slugs[slug] = canon(name)
        rec: dict[str, dict[str, list[int]]] = defaultdict(dict)
        for slug, deck in slugs.items():
            page = get(f"https://labs.limitlesstcg.com/{lid}/decks/{slug}/matchups")
            time.sleep(1.0)
            for _, opp, _, w, l, t in ROW.findall(page):
                o = canon(opp)
                rec[deck][o] = [int(w), int(l), int(t)]
                for k, v in enumerate((int(w), int(l), int(t))):
                    total[deck][o][k] += v
        per_event[ev] = {"labs_id": lid, "records": rec}
        print(f"  {ev}: Labs {lid}, {len(slugs)} archetypes, "
              f"{sum(sum(v) for r in rec.values() for v in r.values())} deck-vs-deck results", flush=True)
    OUT.write_text(json.dumps({"source": "labs.limitlesstcg.com matchup tables (all rounds)",
                               "events": per_event, "total": total}, indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"saved {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
