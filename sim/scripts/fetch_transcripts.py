"""Fetch commentated tournament match transcripts from YouTube (English captions) for play analysis.

    python sim/scripts/fetch_transcripts.py                    # default searches: this season's finals / top 4 / top 8
    python sim/scripts/fetch_transcripts.py --query "..." ...  # other searches
    python sim/scripts/fetch_transcripts.py --id VIDEO_ID ...  # specific videos
    python sim/scripts/fetch_transcripts.py --days             # also the full-day streams (8-10 h each)

Kept: Play! Pokémon / official Pokémon channel TCG broadcasts (the casters explain the plays). Saved
locally to sim/data/transcripts/ (gitignored, never committed: third-party content), one text file per
video with [h:mm:ss] timestamps, plus index.json with title, event, date, duration and URL. Videos
already fetched are skipped. Needs yt-dlp (pip install yt-dlp).
"""
import argparse
import json
import os
import re
import sys
import tempfile
import time
import glob

import yt_dlp

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUT = os.path.join(ROOT, 'sim', 'data', 'transcripts')
OFFICIAL = ('Play Pokémon', 'The Official Pokémon YouTube channel')
SEASON = '2027'      # the season of the meta data (Sept 2026 on)
DEFAULT_QUERIES = [
    f'Pokemon TCG Masters Finals {SEASON} Regional Championships',
    f'Pokemon TCG Top 4 {SEASON} Regional Championships',
    f'Pokemon TCG Top 8 {SEASON} Regional Championships',
    f'Pokemon TCG Masters Finals {SEASON} International Championships',
    f'Pokemon TCG Masters Finals {SEASON} Special Championships',
    f'Play Pokemon TCG {SEASON} Regional Championships Top 4',
]


def search(queries, days):
    found = {}
    with yt_dlp.YoutubeDL({'quiet': True, 'extract_flat': True, 'skip_download': True}) as ydl:
        for q in queries:
            info = ydl.extract_info(f'ytsearch25:{q}', download=False)
            for e in info.get('entries') or []:
                title, channel = e.get('title') or '', e.get('channel') or ''
                if channel not in OFFICIAL or 'TCG' not in title or SEASON not in title:
                    continue
                is_day = re.search(r'TCG Day \d|Championship Sunday', title)
                if is_day and not days:
                    continue
                if not is_day and not re.search(r'Finals?|Top \d', title):
                    continue
                found[e['id']] = e
    return list(found.values())


def fetch_captions(vid, tries=5):
    """(info, json3 captions, 'subtitles' | 'automatic_captions'), via yt-dlp's own downloader; waits
    and retries when YouTube rate-limits (HTTP 429)"""
    for attempt in range(tries):
        with tempfile.TemporaryDirectory() as tmp:
            opts = {'quiet': True, 'no_warnings': True, 'skip_download': True, 'writesubtitles': True, 'writeautomaticsub': True,
                    'subtitleslangs': ['en', 'en-US', 'en-GB'], 'subtitlesformat': 'json3', 'outtmpl': os.path.join(tmp, '%(id)s')}
            try:
                with yt_dlp.YoutubeDL(opts) as ydl:
                    info = ydl.extract_info(f'https://www.youtube.com/watch?v={vid}', download=True)
            except Exception as e:
                if '429' in str(e) and attempt < tries - 1:
                    wait = 60 * 2 ** attempt
                    print(f'  {vid}: rate-limited, waiting {wait} s')
                    time.sleep(wait)
                    continue
                raise
            files = sorted(glob.glob(os.path.join(tmp, f'{vid}*.json3')))
            if not files:
                return info, None, None
            kind = 'subtitles' if any((info.get('subtitles') or {}).get(l) for l in ('en', 'en-US', 'en-GB')) else 'automatic_captions'
            return info, json.load(open(files[0], encoding='utf-8')), kind
    return None, None, None


def clean(json3):
    """caption events -> lines of about a sentence, with the start time of each line"""
    words = []
    for ev in json3.get('events', []):
        segs = ev.get('segs')
        if not segs:
            continue
        t0 = ev.get('tStartMs', 0)
        for s in segs:
            w = s.get('utf8', '').replace(chr(10), ' ')     # caption line breaks separate words too
            if w:
                words.append((t0 + s.get('tOffsetMs', 0), w))
        words.append((t0, ' '))
    lines, cur, start = [], [], None
    for t, w in words:
        if start is None:
            start = t
        cur.append(w)
        text = ''.join(cur)
        if (re.search(r'[.!?]\s*$', w) and len(text) > 60) or len(text) > 220:
            lines.append((start, re.sub(r'\s+', ' ', text).strip()))
            cur, start = [], None
    if cur:
        lines.append((start, re.sub(r'\s+', ' ', ''.join(cur)).strip()))
    stamp = lambda ms: f'{ms // 3600000}:{ms // 60000 % 60:02d}:{ms // 1000 % 60:02d}'
    return '\n'.join(f'[{stamp(t)}] {x}' for t, x in lines if x)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--query', nargs='*')
    ap.add_argument('--id', nargs='*')
    ap.add_argument('--days', action='store_true')
    ap.add_argument('--reclean', action='store_true', help='rewrite the text files from the saved raw captions')
    a = ap.parse_args()
    os.makedirs(OUT, exist_ok=True)
    index_file = os.path.join(OUT, 'index.json')
    index = json.load(open(index_file, encoding='utf-8')) if os.path.exists(index_file) else {}
    if a.reclean:
        for vid, e in index.items():
            raw = os.path.join(OUT, 'raw', f'{vid}.json3')
            if os.path.exists(raw):
                path = os.path.join(OUT, e['file'])
                head = ''.join(open(path, encoding='utf-8').readlines()[:4])
                text = clean(json.load(open(raw, encoding='utf-8')))
                open(path, 'w', encoding='utf-8').write(head + text + chr(10))
        print('recleaned')
        return
    ids = a.id or [e['id'] for e in search(a.query or DEFAULT_QUERIES, a.days)]
    print(f'{len(ids)} videos; {sum(1 for i in ids if i in index)} already fetched')
    if True:
        for vid in ids:
            if vid in index:
                continue
            try:
                info, cap, kind = fetch_captions(vid)
            except Exception as e:      # private, removed, region-locked, still rate-limited
                print(f'  {vid}: {str(e)[:200]}')
                continue
            if not cap:
                print(f'  {vid}: no English captions ({info.get("title") if info else ""})')
                continue
            os.makedirs(os.path.join(OUT, 'raw'), exist_ok=True)
            json.dump(cap, open(os.path.join(OUT, 'raw', f'{vid}.json3'), 'w', encoding='utf-8'))
            text = clean(cap)
            title = info.get('title', '')
            event = re.search(r'\|\s*(.+)$', title)
            fname = f'{info.get("upload_date", "")}-{vid}.txt'
            header = f'# {title}\n# {info.get("webpage_url")}\n# channel {info.get("channel")}, uploaded {info.get("upload_date")}, {info.get("duration_string")}, captions: {kind}\n\n'
            with open(os.path.join(OUT, fname), 'w', encoding='utf-8') as f:
                f.write(header + text + '\n')
            index[vid] = {'title': title, 'event': event.group(1).strip() if event else '', 'uploaded': info.get('upload_date'),
                          'duration': info.get('duration'), 'url': info.get('webpage_url'), 'captions': kind, 'file': fname,
                          'words': len(text.split())}
            json.dump(index, open(index_file, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
            print(f'  {vid}: {len(text.split())} words  {title}', flush=True)
            time.sleep(20)                # be gentle: YouTube rate-limits caption downloads
    print(f'{len(index)} transcripts in {OUT}')


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    main()
