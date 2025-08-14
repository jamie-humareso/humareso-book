#!/usr/bin/env python3
import argparse
import json
import re
from pathlib import Path
from typing import Dict, List, Tuple


YEAR_RE = re.compile(r"\b(19\d{2}|20\d{2})\b")
YEARS_AGO_RE = re.compile(r"\b(\d{1,2})\s+years\s+ago\b", re.I)


def estimate_story_year(text: str, publish_year: int) -> Tuple[int, str]:
    # Strategy: prefer explicit years that are <= publish_year and >= 1980; pick the earliest year.
    # If none, look for "X years ago" and compute publish_year - X.
    # Fallback: publish_year
    candidates: List[int] = []
    for m in YEAR_RE.finditer(text):
        y = int(m.group(1))
        if 1980 <= y <= publish_year:
            candidates.append(y)
    derived: List[int] = []
    for m in YEARS_AGO_RE.finditer(text):
        x = int(m.group(1))
        if 1 <= x <= 50:
            derived.append(publish_year - x)

    reason = "publish_year"
    if candidates:
        story_year = min(candidates)
        reason = "explicit_year"
    elif derived:
        story_year = min(derived)
        reason = "relative_years_ago"
    else:
        story_year = publish_year
    return story_year, reason


def main() -> None:
    parser = argparse.ArgumentParser(description="Estimate story year per post from content.")
    parser.add_argument("--index", default="build/john_index.json")
    parser.add_argument("--out", default="build/story_years.json")
    args = parser.parse_args()

    index_path = Path(args.index).resolve()
    posts = json.loads(index_path.read_text(encoding="utf-8"))

    out: Dict[str, Dict] = {}
    for p in posts:
        md_path = p.get("markdown_path")
        if not md_path:
            continue
        publish_year = 0
        try:
            publish_year = int(p.get("year") or 0)
        except Exception:
            publish_year = 0
        if publish_year <= 0:
            # best effort: parse from publish_date string
            m = re.search(r"(19\d{2}|20\d{2})", p.get("publish_date") or "")
            publish_year = int(m.group(1)) if m else 2020

        text = Path(md_path).read_text(encoding="utf-8")
        story_year, reason = estimate_story_year(text, publish_year)
        out[p["post_slug"]] = {
            "story_year": story_year,
            "publish_year": publish_year,
            "reason": reason,
        }

    Path(args.out).write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(json.dumps({"count": len(out), "out": str(Path(args.out))}, indent=2))


if __name__ == "__main__":
    main()


