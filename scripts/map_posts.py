#!/usr/bin/env python3
import argparse
import json
from pathlib import Path
from typing import Dict, List


VOLUME1_BRIEFS = [
    {"chapter": 1,  "title": "Seeing the Person at Work",              "theme_tags": ["human resources","culture","leadership","mental health"], "target_words": 6000},
    {"chapter": 2,  "title": "Leading Without Ego",                    "theme_tags": ["management","leadership","professionalism"],              "target_words": 6000},
    {"chapter": 3,  "title": "Feedback that Heals and Enables",        "theme_tags": ["feedback","performance","performance management"],       "target_words": 6000},
    {"chapter": 4,  "title": "Joy, Care, and Mental Health",           "theme_tags": ["mental health","development","culture"],                 "target_words": 6000},
    {"chapter": 5,  "title": "Building Cultures You Can Live In",      "theme_tags": ["culture","inclusion","employee engagement"],             "target_words": 6000},
    {"chapter": 6,  "title": "Relationships and Trust",                 "theme_tags": ["employee relations","cooperation","leadership"],         "target_words": 6000},
    {"chapter": 7,  "title": "Hard Conversations, Human Outcomes",      "theme_tags": ["professionalism","employee relations","regret"],        "target_words": 6000},
    {"chapter": 8,  "title": "Purpose, Values, and Work",               "theme_tags": ["business","leadership","human resources"],               "target_words": 6000},
    {"chapter": 9,  "title": "Resilience without Toxicity",             "theme_tags": ["culture","development"],                                  "target_words": 6000},
    {"chapter": 10, "title": "The Human Future of Work",                "theme_tags": ["leadership","decision-making","human resources"],        "target_words": 6000},
]

VOLUME2_BRIEFS = [
    {"chapter": 1,  "title": "Talent Attraction That’s Real",          "theme_tags": ["talent strategy","aquisition","hiring"],                 "target_words": 6000},
    {"chapter": 2,  "title": "Hiring Decisions that Stick",            "theme_tags": ["hiring","decision-making","management"],                 "target_words": 6000},
    {"chapter": 3,  "title": "Onboarding and Early Performance",        "theme_tags": ["performance","performance management","development"],     "target_words": 6000},
    {"chapter": 4,  "title": "Performance Systems that Elevate",        "theme_tags": ["performance management","performance","feedback"],       "target_words": 6000},
    {"chapter": 5,  "title": "Coaching and Development that Stick",     "theme_tags": ["development","management","leadership"],                 "target_words": 6000},
    {"chapter": 6,  "title": "Managers as Multipliers",                 "theme_tags": ["management","leadership","leadership development"],     "target_words": 6000},
    {"chapter": 7,  "title": "Culture by Design",                        "theme_tags": ["culture","employee engagement","inclusion"],             "target_words": 6000},
    {"chapter": 8,  "title": "Retention: Keeping the Talent You Won",   "theme_tags": ["management","employee relations","performance"],         "target_words": 6000},
    {"chapter": 9,  "title": "HR Tech and Tools that Serve People",     "theme_tags": ["tech","business","human resources"],                    "target_words": 6000},
    {"chapter": 10, "title": "Strategy in Practice",                    "theme_tags": ["talent strategy","business","management"],              "target_words": 6000},
    {"chapter": 11, "title": "Measuring What Matters",                  "theme_tags": ["performance","decision-making"],                         "target_words": 6000},
    {"chapter": 12, "title": "What’s Next",                              "theme_tags": ["leadership","talent strategy"],                          "target_words": 6000},
]


def main() -> None:
    parser = argparse.ArgumentParser(description="Select whole posts for chapters based on tags.")
    parser.add_argument("--index", default="build/john_index.json")
    parser.add_argument("--out", default="mapping/chapter_posts.yml")
    parser.add_argument("--profile", choices=["v1","v2"], default="v1", help="Volume profile: v1=Lead With Humanity, v2=Build The System")
    args = parser.parse_args()

    index_path = Path(args.index).resolve()
    out_path = Path(args.out).resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)

    posts: List[Dict] = json.loads(index_path.read_text(encoding="utf-8"))
    for p in posts:
        p["tags_lc"] = [t.lower() for t in p.get("tags", [])]

    briefs = VOLUME1_BRIEFS if args.profile == "v1" else VOLUME2_BRIEFS
    chapters: List[Dict] = []
    used_slugs = set()
    for brief in briefs:
        theme = set(t.lower() for t in brief["theme_tags"])
        candidates = [p for p in posts if theme & set(p.get("tags_lc", []))]
        # Sort by year desc, then word_count desc to favor newer and substantive
        candidates.sort(key=lambda x: (x.get("year", ""), x.get("word_count", 0)), reverse=True)

        picked: List[Dict] = []
        total = 0
        for c in candidates:
            if c["post_slug"] in used_slugs:
                continue
            if total >= brief["target_words"] * 1.1:  # small buffer
                break
            picked.append(c)
            total += int(c.get("word_count", 0))
            used_slugs.add(c["post_slug"])

        chapters.append({
            "chapter": brief["chapter"],
            "title": brief["title"],
            "target_words": brief["target_words"],
            "estimated_words": total,
            "posts": [p["post_slug"] for p in picked],
        })

    def quote_str(s: str) -> str:
        return '"' + s.replace('"', '\\"') + '"'

    def to_yaml(obj, indent=0):
        sp = "  " * indent
        if isinstance(obj, dict):
            lines = []
            for k, v in obj.items():
                if isinstance(v, list) and len(v) == 0:
                    lines.append(f"{sp}{k}: []")
                elif isinstance(v, (dict, list)):
                    lines.append(f"{sp}{k}:")
                    lines.append(to_yaml(v, indent + 1))
                else:
                    if isinstance(v, str):
                        lines.append(f"{sp}{k}: {quote_str(v)}")
                    else:
                        lines.append(f"{sp}{k}: {v}")
            return "\n".join(lines)
        elif isinstance(obj, list):
            if not obj:
                return f"{sp}[]"
            lines = []
            for item in obj:
                if isinstance(item, (dict, list)):
                    lines.append(f"{sp}-")
                    lines.append(to_yaml(item, indent + 1))
                else:
                    if isinstance(item, str):
                        lines.append(f"{sp}- {quote_str(item)}")
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


