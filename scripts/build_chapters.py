#!/usr/bin/env python3
import argparse
import json
import re
from pathlib import Path
from typing import Dict, List

import yaml


def main() -> None:
    parser = argparse.ArgumentParser(description="Assemble chapters from mapping and units.")
    parser.add_argument("--mapping", default="mapping/chapter_map.yml")
    parser.add_argument("--units", default="build/units_enriched.jsonl")
    parser.add_argument("--outdir", default="manuscript/chapters")
    args = parser.parse_args()

    mapping_path = Path(args.mapping).resolve()
    units_path = Path(args.units).resolve()
    outdir = Path(args.outdir).resolve()
    outdir.mkdir(parents=True, exist_ok=True)

    # Load units into a dict
    id_to_unit: Dict[str, Dict] = {}
    with units_path.open("r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                u = json.loads(line)
                id_to_unit[u["stable_id"]] = u

    with mapping_path.open("r", encoding="utf-8") as f:
        mapping = yaml.safe_load(f)
    for ch in mapping.get("chapters", []):
        title = ch.get("title", f"Chapter {ch.get('chapter','')}")
        slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")
        out_path = outdir / f"{ch.get('chapter', 0):02d}-{slug}.md"

        lines: List[str] = []
        lines.append(f"---")
        lines.append(f"title: {title}")
        lines.append(f"target_words: {ch.get('target_words', '')}")
        lines.append(f"estimated_words: {ch.get('estimated_words', '')}")
        lines.append(f"---\n")
        lines.append(f"# {title}\n")

        for sid in ch.get("sources", []):
            unit = id_to_unit.get(sid)
            if not unit:
                continue
            lines.append(unit.get("text_md", ""))
            lines.append("")

        # Endnotes
        lines.append("\n---\nSources\n")
        src_seen = set()
        for sid in ch.get("sources", []):
            unit = id_to_unit.get(sid)
            if not unit:
                continue
            key = (unit.get("post_title"), unit.get("post_url"))
            if key in src_seen:
                continue
            src_seen.add(key)
            title = unit.get("post_title", "")
            url = unit.get("post_url", "")
            date = unit.get("publish_date", "")
            lines.append(f"- {title} ({date}) — {url}")

        out_path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
        print(f"Wrote {out_path}")


if __name__ == "__main__":
    main()


