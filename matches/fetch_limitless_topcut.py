"""
Top-cut decklists of official events from Limitless (Masters), for replaying commentated matches.

  python matches/fetch_limitless_topcut.py                       # events since Worlds 2025, top 16
  python matches/fetch_limitless_topcut.py --since 2025-01-01 --top 8

limitlesstcg.com/tournaments lists the official events; each event page has the standings with a
link to every player's list, and each list page the cards (set, number, count, name). Saves
meta/decklists_topcut.json in the meta decklist format ({tournament, event, date, rank, player,
deck, list, cards}). Junior and Senior lists are not on Limitless: match logs of those divisions use
the same event's Masters list of that archetype, marked approximate. Reruns skip events already saved.
"""
from __future__ import annotations

import argparse
import datetime as dt
import html
import json
import re
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "meta" / "decklists_topcut.json"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) deck-research"
SITE = "https://limitlesstcg.com"
ROW = re.compile(r"<tr[^>]*>(.*?)</tr>", re.S)
CARD = re.compile(r'<div class="decklist-card" data-set="([^"]*)" data-number="([^"]*)".*?<span class="card-count">(\d+)</span>\s*'
                  r'<span class="card-name">([^<]+)</span>', re.S)


def get(url: str) -> str:
    for attempt in range(4):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=60) as r:
                return r.read().decode("utf-8", "replace")
        except Exception:
            time.sleep(5 * (attempt + 1))
    raise RuntimeError(f"could not fetch {url}")


def text(s: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", s))).strip()


def events(since: dt.date) -> list[dict]:
    out = []
    for page in range(1, 6):
        h = get(f"{SITE}/tournaments?time=all&type=all&show=100&page={page}")
        rows = ROW.findall(h)[1:]
        if not rows:
            break
        older = False
        for r in rows:
            tid = re.search(r'href="/tournaments/(\d+)"', r)
            date = re.search(r"(\d{2} \w{3} \d{2})", text(r))
            if not tid or not date:
                continue
            d = dt.datetime.strptime(date.group(1), "%d %b %y").date()
            if d < since:
                older = True
                continue
            name = re.search(r'href="/tournaments/\d+"[^>]*>([^<]+)</a>', r)
            out.append({"id": tid.group(1), "date": d.isoformat(), "event": html.unescape(name.group(1)).strip() if name else tid.group(1)})
        if older:
            break
        time.sleep(1)
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--since", default="2025-08-01")
    ap.add_argument("--top", type=int, default=16)
    ap.add_argument("--fix-decks", action="store_true", help="re-read the event pages and correct the saved archetype names")
    a = ap.parse_args()
    saved = json.loads(OUT.read_text(encoding="utf-8")) if OUT.exists() else []
    if a.fix_decks:
        for tid in sorted({d["tournament"] for d in saved}):
            page = get(f"{SITE}/tournaments/{tid}")
            names = {m.group(2): html.unescape(m.group(1)) for m in re.finditer(
                r'href="/decks/\d+[^"]*">\s*<span data-tooltip="([^"]+)".*?href="/decks/list/(\d+)"', page, re.S)}
            for d in saved:
                if d["tournament"] == tid and d["list"] in names:
                    d["deck"] = names[d["list"]]
            time.sleep(1)
        OUT.write_text(json.dumps(saved, indent=1, ensure_ascii=False), encoding="utf-8")
        print("archetype names corrected")
        return
    have = {d["tournament"] for d in saved}
    evs = events(dt.date.fromisoformat(a.since))
    print(f"{len(evs)} events since {a.since}; {sum(e['id'] in have for e in evs)} already saved", flush=True)
    for e in evs:
        if e["id"] in have:
            continue
        page = get(f"{SITE}/tournaments/{e['id']}")
        time.sleep(1)
        n = 0
        for r in ROW.findall(page)[1:]:
            cells = re.findall(r"<td[^>]*>(.*?)</td>", r, re.S)
            lst = re.search(r'href="/decks/list/(\d+)"', r)
            if not cells or not lst or not text(cells[0]).isdigit():
                continue
            rank = int(text(cells[0]))
            if rank > a.top:
                break
            player = re.search(r'href="/players/\d+">([^<]+)</a>', r)
            deck = re.search(r'href="/decks/\d+[^"]*">\s*<span data-tooltip="([^"]+)"', r)
            cards = [{"set": s, "num": num, "count": int(c), "name": html.unescape(nm).strip()}
                     for s, num, c, nm in CARD.findall(get(f"{SITE}/decks/list/{lst.group(1)}"))]
            time.sleep(1)
            saved.append({"tournament": e["id"], "event": e["event"], "date": e["date"], "rank": rank,
                          "player": html.unescape(player.group(1)).strip() if player else "",
                          "deck": html.unescape(deck.group(1)) if deck else "", "list": lst.group(1), "cards": cards})
            n += 1
        OUT.write_text(json.dumps(saved, indent=1, ensure_ascii=False), encoding="utf-8")
        print(f"  {e['date']} {e['event']}: {n} lists", flush=True)
    print(f"saved {OUT.relative_to(ROOT)} ({len(saved)} lists)")


if __name__ == "__main__":
    main()
