#!/usr/bin/env python3
import argparse
import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Dict, Iterable, List


STOPWORDS = {
    "a","an","and","are","as","at","be","but","by","for","if","in","into","is","it","no","not","of","on","or","such","that","the","their","then","there","these","they","this","to","was","will","with","we","our","you","your","from","have","has","had","were","i","me","my","mine","us",
}


def tokenize(text: str) -> List[str]:
    text = text.lower()
    tokens = re.findall(r"[a-z][a-z']+", text)
    return [t for t in tokens if t not in STOPWORDS and len(t) >= 2]


def normalize_for_fingerprint(text: str) -> str:
    # Remove non-letters, collapse spaces
    text = text.lower()
    text = re.sub(r"[^a-z\s]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    # Drop stopwords for stability
    tokens = [t for t in text.split() if t not in STOPWORDS]
    return " ".join(tokens)


def main() -> None:
    parser = argparse.ArgumentParser(description="Enrich paragraph units with simple keywords and duplicate fingerprints.")
    parser.add_argument("--indir", default="build", help="Directory containing john_units.jsonl and john_index.json")
    parser.add_argument("--outdir", default="build", help="Directory to write enriched artifacts")
    args = parser.parse_args()

    indir = Path(args.indir).resolve()
    outdir = Path(args.outdir).resolve()
    outdir.mkdir(parents=True, exist_ok=True)

    units_path = indir / "john_units.jsonl"
    index_path = indir / "john_index.json"
    enriched_path = outdir / "units_enriched.jsonl"
    dupe_index_path = outdir / "dupe_index.json"

    # Load units
    units: List[Dict] = []
    with units_path.open("r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                units.append(json.loads(line))

    # Compute keywords per unit
    dupe_map: Dict[str, List[str]] = defaultdict(list)
    with enriched_path.open("w", encoding="utf-8") as out:
        for u in units:
            text = u.get("text_md", "")
            toks = tokenize(text)
            top = [w for w, _ in Counter(toks).most_common(10)]
            norm = normalize_for_fingerprint(text)
            # Simple fingerprint: sha1 of normalized text
            import hashlib
            fp = hashlib.sha1(norm.encode("utf-8")).hexdigest()
            u_en = dict(u)
            u_en["keywords"] = top
            u_en["fingerprint"] = fp
            out.write(json.dumps(u_en, ensure_ascii=False) + "\n")
            dupe_map[fp].append(u["stable_id"])

    # Build dupe index summary
    dupe_summary = {
        "total_units": len(units),
        "fingerprints": {fp: ids for fp, ids in dupe_map.items() if len(ids) > 1},
        "num_duplicate_groups": sum(1 for fp, ids in dupe_map.items() if len(ids) > 1),
    }
    with dupe_index_path.open("w", encoding="utf-8") as f:
        json.dump(dupe_summary, f, indent=2)

    print(json.dumps({
        "units_enriched": enriched_path.name,
        "duplicates": dupe_summary["num_duplicate_groups"],
    }, indent=2))


if __name__ == "__main__":
    main()


