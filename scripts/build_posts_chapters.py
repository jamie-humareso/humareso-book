#!/usr/bin/env python3
import argparse
import json
import re
from pathlib import Path
from typing import Dict, List

import yaml


def main() -> None:
    parser = argparse.ArgumentParser(description="Assemble chapters from whole-post selections.")
    parser.add_argument("--mapping", default="mapping/chapter_posts.yml")
    parser.add_argument("--index", default="build/john_index.json")
    parser.add_argument("--outbase", default="generated")
    parser.add_argument("--book-title", default="Lead With Humanity (Whole Posts)")
    args = parser.parse_args()

    mapping = yaml.safe_load(Path(args.mapping).read_text(encoding="utf-8"))
    posts = json.loads(Path(args.index).read_text(encoding="utf-8"))
    slug_to_post = {p["post_slug"]: p for p in posts}

    outdir = Path(args.outbase) / args.book_title
    outdir.mkdir(parents=True, exist_ok=True)

    for ch in mapping.get("chapters", []):
        title = ch.get("title", f"Chapter {ch.get('chapter','')}")
        clean_title = re.sub(r"[\\/:*?\"<>|]", "-", title).strip()
        out_path = outdir / f"{ch.get('chapter', 0):02d} - {clean_title}.md"

        lines: List[str] = []
        lines.append("---")
        lines.append(f"title: {title}")
        lines.append(f"target_words: {ch.get('target_words', '')}")
        lines.append(f"estimated_words: {ch.get('estimated_words', '')}")
        lines.append("---\n")
        lines.append(f"# {title}\n")

        for post_slug in ch.get("posts", []):
            meta = slug_to_post.get(post_slug)
            if not meta:
                continue
            md_path_str = meta.get("markdown_path")
            if not md_path_str:
                # Skip posts without saved markdown (older index)
                continue
            # Source comment at the top of each article
            comment = f"Source: {meta.get('post_title')} | {meta.get('publish_date')} | {meta.get('post_url')} | {post_slug}"
            lines.append(f"<!-- {comment.replace('--','—')} -->")
            # Read the saved post markdown from inventory
            md_path = Path(md_path_str)
            if md_path.exists():
                lines.append(md_path.read_text(encoding='utf-8').rstrip())
                lines.append("")

        # Endnotes: list posts
        lines.append("\n---\nSources\n")
        for post_slug in ch.get("posts", []):
            meta = slug_to_post.get(post_slug)
            if not meta:
                continue
            lines.append(f"- {meta.get('post_title')} ({meta.get('publish_date')}) — {meta.get('post_url')}")

        out_path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
        print(f"Wrote {out_path}")


if __name__ == "__main__":
    main()


