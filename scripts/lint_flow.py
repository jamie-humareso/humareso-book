#!/usr/bin/env python3
import argparse
import json
import math
import re
from collections import Counter
from pathlib import Path
from typing import Dict, List, Tuple


STOPWORDS = {
    "a","an","and","are","as","at","be","but","by","for","if","in","into","is","it","no","not","of","on","or","such","that","the","their","then","there","these","they","this","to","was","will","with","we","our","you","your","from","have","has","had","were","i","me","my","mine","us",
}


def tokenize(text: str) -> List[str]:
    text = text.lower()
    tokens = re.findall(r"[a-z][a-z']+", text)
    return [t for t in tokens if t not in STOPWORDS and len(t) >= 2]


def cosine_from_counters(a: Counter, b: Counter) -> float:
    if not a or not b:
        return 0.0
    common = set(a.keys()) & set(b.keys())
    dot = sum(a[t] * b[t] for t in common)
    na = math.sqrt(sum(v * v for v in a.values()))
    nb = math.sqrt(sum(v * v for v in b.values()))
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)


def parse_chapter_paragraphs(md_path: Path) -> List[Tuple[str, str]]:
    """Return list of (comment, paragraph) pairs. Comment contains stable_id if available."""
    lines = md_path.read_text(encoding="utf-8").splitlines()
    paras: List[Tuple[str, str]] = []
    buf: List[str] = []
    last_comment = ""
    in_frontmatter = False
    for line in lines:
        if line.strip() == '---' and not in_frontmatter and not buf and not paras:
            in_frontmatter = True
            continue
        elif line.strip() == '---' and in_frontmatter:
            in_frontmatter = False
            continue
        if in_frontmatter:
            continue
        if line.strip().startswith('#'):
            # treat headings as paragraph breaks
            if buf:
                paras.append((last_comment, "\n".join(buf).strip()))
                buf = []
            last_comment = ""
            continue
        if line.strip().startswith('<!--') and line.strip().endswith('-->'):
            # capture comment as source meta for next paragraph
            last_comment = line.strip()
            continue
        if line.strip() == "":
            if buf:
                paras.append((last_comment, "\n".join(buf).strip()))
                buf = []
                last_comment = ""
            continue
        buf.append(line)
    if buf:
        paras.append((last_comment, "\n".join(buf).strip()))
    return paras


def extract_stable_id(comment: str) -> str:
    m = re.search(r"\|\s*([a-z0-9\-]+#p\d{2}~[a-f0-9]{8})\s*-->", comment)
    return m.group(1) if m else ""


def load_units(units_path: Path) -> Dict[str, Dict]:
    id_to_unit: Dict[str, Dict] = {}
    with units_path.open("r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                u = json.loads(line)
                id_to_unit[u["stable_id"]] = u
    return id_to_unit


def main() -> None:
    parser = argparse.ArgumentParser(description="Lint chapter flow for topic jumps; suggest transitions.")
    parser.add_argument("--chapters", nargs='+', help="Paths to chapter .md files or directories")
    parser.add_argument("--units", default="build/units_enriched.jsonl", help="Units file for metadata lookup")
    parser.add_argument("--threshold", type=float, default=0.08, help="Min cosine similarity between consecutive paragraphs")
    args = parser.parse_args()

    # Collect chapter files
    chapter_files: List[Path] = []
    for p in args.chapters:
        path = Path(p)
        if path.is_dir():
            chapter_files.extend(sorted([f for f in path.glob('*.md')]))
        elif path.suffix.lower() == '.md':
            chapter_files.append(path)

    id_to_unit = load_units(Path(args.units))

    report = []
    for ch_path in chapter_files:
        paras = parse_chapter_paragraphs(ch_path)
        vecs = [Counter(tokenize(text)) for (_, text) in paras]
        warnings = []
        for i in range(1, len(vecs)):
            sim = cosine_from_counters(vecs[i-1], vecs[i])
            if sim < args.threshold:
                prev_id = extract_stable_id(paras[i-1][0])
                curr_id = extract_stable_id(paras[i][0])
                prev_meta = id_to_unit.get(prev_id, {})
                curr_meta = id_to_unit.get(curr_id, {})
                warnings.append({
                    "index": i,
                    "similarity": round(sim, 3),
                    "prev": {
                        "id": prev_id,
                        "title": prev_meta.get("post_title"),
                        "tags": prev_meta.get("tags"),
                        "year": prev_meta.get("year"),
                    },
                    "curr": {
                        "id": curr_id,
                        "title": curr_meta.get("post_title"),
                        "tags": curr_meta.get("tags"),
                        "year": curr_meta.get("year"),
                    },
                    "suggestion": "Add a transition or regroup this paragraph with a closer subtheme.",
                })
        report.append({
            "chapter": ch_path.name,
            "paragraphs": len(paras),
            "warnings": warnings,
        })

    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()


