#!/usr/bin/env python3
import argparse
import json
import re
from pathlib import Path
from typing import Dict, List


HR_NOISE = {
    'hr','shrm','recap','workhuman','webinar','podcast','carnival','anniversary','press','event','live','recfest'
}


def extract_lead_phrase(title: str) -> str:
    if not title:
        return ''
    parts = re.split(r"\s*[:\-\u2013\u2014]\s*", title, maxsplit=1)  # :, -, –, —
    lead = parts[0].strip()
    # trim quotes
    lead = lead.strip('"\'\u2018\u2019\u201c\u201d ')
    return lead


def is_likely_song_phrase(lead: str, full_title: str) -> bool:
    if not lead:
        return False
    # Reject if mostly digits/initialisms
    if re.search(r"\b(19\d{2}|20\d{2})\b", lead):
        return False
    if lead.lower() in HR_NOISE:
        return False
    words = [w for w in re.findall(r"[A-Za-z][A-Za-z'&,]+", lead)]
    if not words:
        return False
    # Single rare word allowed if stylized
    if len(words) == 1:
        return bool(re.search(r"[',]", lead)) or words[0].lower() in {"dreams","promises","mr","cellophane","regret"}
    # 2–6 words, mostly title-case or contains apostrophes/commas
    if 2 <= len(words) <= 7:
        titlecase_ratio = sum(1 for w in words if w[0].isupper()) / len(words)
        has_punct = bool(re.search(r"[',]", lead))
        if titlecase_ratio >= 0.6 or has_punct:
            return True
    return False


def main() -> None:
    parser = argparse.ArgumentParser(description="Detect likely song-based titles and report coverage.")
    parser.add_argument("--index", default="build/john_index.json")
    parser.add_argument("--out", default="build/song_coverage.json")
    parser.add_argument("--index_out", default="build/john_index_with_song.json")
    args = parser.parse_args()

    posts = json.loads(Path(args.index).read_text(encoding="utf-8"))
    total = 0
    hits = 0
    updated: List[Dict] = []
    examples: List[Dict] = []
    for p in posts:
        if not p.get('post_title'):
            continue
        total += 1
        title = p['post_title']
        lead = extract_lead_phrase(title)
        guess = is_likely_song_phrase(lead, title)
        if guess:
            hits += 1
        q = dict(p)
        q['song_title_guess'] = lead if guess else ''
        q['has_song_title_guess'] = bool(guess)
        updated.append(q)
        if len(examples) < 20 and guess:
            examples.append({'title': title, 'leading_phrase': lead})

    coverage = round(100 * hits / total, 1) if total else 0.0
    Path(args.index_out).write_text(json.dumps(updated, indent=2, ensure_ascii=False), encoding="utf-8")
    Path(args.out).write_text(json.dumps({
        'total_posts': total,
        'song_tied_posts': hits,
        'coverage_pct': coverage,
        'examples': examples,
    }, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps({'coverage_pct': coverage, 'hits': hits, 'total': total}, indent=2))


if __name__ == "__main__":
    main()


