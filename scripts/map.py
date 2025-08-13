#!/usr/bin/env python3
import argparse
import json
import random
from collections import defaultdict
from pathlib import Path
from typing import Dict, List


CHAPTER_BRIEFS = [
    {
        "chapter": 1,
        "title": "Feedback that Heals and Enables",
        "theme_tags": ["feedback", "leadership", "management"],
        "target_words": 6000,
    },
    {
        "chapter": 2,
        "title": "Talent Attraction That’s Real",
        "theme_tags": ["talent strategy", "hiring", "aquisition", "human resources"],
        "target_words": 6000,
    },
]


def main() -> None:
    parser = argparse.ArgumentParser(description="Propose a simple chapter map using tags and length heuristics.")
    parser.add_argument("--units", default="build/units_enriched.jsonl", help="Path to enriched units JSONL")
    parser.add_argument("--out", default="mapping/chapter_map.yml", help="Output YAML map path")
    args = parser.parse_args()

    units_path = Path(args.units).resolve()
    out_path = Path(args.out).resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)

    units: List[Dict] = []
    with units_path.open("r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                u = json.loads(line)
                # Lowercase tags for matching
                u["tags_lc"] = [t.lower() for t in u.get("tags", [])]
                units.append(u)

    # Group units by post to avoid over-using a single post
    post_to_units: Dict[str, List[Dict]] = defaultdict(list)
    for u in units:
        post_to_units[u["post_slug"]].append(u)

    chapters: List[Dict] = []
    for brief in CHAPTER_BRIEFS:
        theme = set(t.lower() for t in brief["theme_tags"])
        candidates: List[Dict] = []
        for u in units:
            if theme & set(u.get("tags_lc", [])):
                candidates.append(u)
        # De-duplicate by fingerprint; keep first occurrence
        seen_fp = set()
        filtered: List[Dict] = []
        for u in candidates:
            fp = u.get("fingerprint")
            if fp and fp in seen_fp:
                continue
            seen_fp.add(fp)
            filtered.append(u)

        # Build a naive balanced selection across posts
        by_post = defaultdict(list)
        for u in filtered:
            by_post[u["post_slug"]].append(u)
        # Shuffle to diversify
        rng = random.Random(42)
        for lst in by_post.values():
            rng.shuffle(lst)

        target = brief["target_words"]
        picked: List[Dict] = []
        total = 0
        # Round-robin across posts until target reached
        while total < target and any(by_post.values()):
            for slug in list(by_post.keys()):
                if not by_post[slug]:
                    continue
                u = by_post[slug].pop()
                picked.append(u)
                total += int(u.get("word_count", 0))
                if total >= target:
                    break
            # Remove exhausted posts
            for slug in list(by_post.keys()):
                if not by_post[slug]:
                    by_post.pop(slug, None)

        chapters.append({
            "chapter": brief["chapter"],
            "title": brief["title"],
            "target_words": target,
            "estimated_words": total,
            "sources": [u["stable_id"] for u in picked],
        })

    # Minimal YAML serializer
    def to_yaml(obj, indent=0):
        sp = "  " * indent
        if isinstance(obj, dict):
            lines = []
            for k, v in obj.items():
                if isinstance(v, (dict, list)):
                    lines.append(f"{sp}{k}:")
                    lines.append(to_yaml(v, indent + 1))
                else:
                    lines.append(f"{sp}{k}: {v}")
            return "\n".join(lines)
        elif isinstance(obj, list):
            lines = []
            for item in obj:
                if isinstance(item, (dict, list)):
                    lines.append(f"{sp}-")
                    lines.append(to_yaml(item, indent + 1))
                else:
                    lines.append(f"{sp}- {item}")
            return "\n".join(lines)
        else:
            return f"{sp}{obj}"

    mapping = {"chapters": chapters}
    out_path.write_text(to_yaml(mapping) + "\n", encoding="utf-8")
    print(f"Wrote {out_path}")


if __name__ == "__main__":
    main()


