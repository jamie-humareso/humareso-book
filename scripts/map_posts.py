#!/usr/bin/env python3
import argparse
import json
from pathlib import Path
from typing import Dict, List


DEFAULT_BRIEFS = [
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
    parser = argparse.ArgumentParser(description="Select whole posts for chapters based on tags.")
    parser.add_argument("--index", default="build/john_index.json")
    parser.add_argument("--out", default="mapping/chapter_posts.yml")
    args = parser.parse_args()

    index_path = Path(args.index).resolve()
    out_path = Path(args.out).resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)

    posts: List[Dict] = json.loads(index_path.read_text(encoding="utf-8"))
    for p in posts:
        p["tags_lc"] = [t.lower() for t in p.get("tags", [])]

    chapters: List[Dict] = []
    for brief in DEFAULT_BRIEFS:
        theme = set(t.lower() for t in brief["theme_tags"])
        candidates = [p for p in posts if theme & set(p.get("tags_lc", []))]
        # Sort by year desc, then word_count desc to favor newer and substantive
        candidates.sort(key=lambda x: (x.get("year", ""), x.get("word_count", 0)), reverse=True)

        picked: List[Dict] = []
        total = 0
        for c in candidates:
            if total >= brief["target_words"] * 1.1:  # small buffer
                break
            picked.append(c)
            total += int(c.get("word_count", 0))

        chapters.append({
            "chapter": brief["chapter"],
            "title": brief["title"],
            "target_words": brief["target_words"],
            "estimated_words": total,
            "posts": [p["post_slug"] for p in picked],
        })

    # Minimal YAML writer
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


