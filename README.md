# Humareso Book Project

This repository turns John Baldino’s Humareso blog into two readable, cohesive books. We will reuse as much of John’s original copy as possible, stitch passages lightly for flow, and provide transparent citations back to the original posts.

Source data: `blog-export.csv` (do not edit). All tooling reads from this CSV.

## Targets

- Two volumes, each ~50–70k words
- Volume 1: Lead with Humanity (feedback, leadership, management, mental health, culture)
- Volume 2: Build the System (talent strategy, hiring, performance systems, development, business/tech, decision‑making)

## Workflow overview

1) Inventory
- Filter to John on `Humareso Blog`
- Convert `Post body` HTML → Markdown
- Segment into paragraphs (and sentences when needed)
- Assign stable excerpt IDs: `post-slug#p{index}~{hash}`
- Output:
  - `build/john_index.json` – post‑level metadata and counts
  - `build/john_units.jsonl` – one record per paragraph (text, word_count, indices, tags, date, URL)

2) Analyze
- Compute per‑unit signals: keywords, length, year, basic readability
- Semantic vectors for chapter‑theme matching (planned)
- Near‑duplicate detection to avoid repetition (planned)

3) Map
- Chapter briefs: theme, thesis, target length, arc (story → principle → application → reflection)
- Candidate selection: tag/title seeds + semantic similarity + diversity (year/post)
- Constraints: cap excerpts per post; avoid over‑reliance; meet target word count per chapter
- Artifact: `mapping/chapter_map.yml` with ordered list of excerpt IDs and minimal transition notes

4) Build
- Renderer assembles chapters from `chapter_map.yml`
- Inserts brief transitions in John’s tone; preserves original wording
- Appends endnotes with citations (title, date, URL, excerpt IDs)
- Output: `manuscript/chapters/*.md` and `manuscript/SUMMARY.md`

## Repository layout

```
humareso-book/
  blog-export.csv              # source (read‑only)
  README.md
  requirements.txt
  scripts/
    inventory.py              # build john_index.json + john_units.jsonl
    # analyze.py (planned)
    # map.py (planned)
    # build_chapters.py (planned)
  build/                      # generated artifacts (ignored by git except placeholders)
  mapping/                    # chapter maps (planned)
  manuscript/                 # assembled chapters
```

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Usage

Inventory (John on Humareso → Markdown paragraphs with stable IDs):

```bash
python scripts/inventory.py \
  --csv /Users/jamieaquila/git/humareso-book/blog-export.csv \
  --outdir build
```

Outputs:
- `build/john_index.json`
- `build/john_units.jsonl`
- `build/stats.json`

Next (planned):
- `scripts/analyze.py` → semantic signals and de‑duplication
- `scripts/map.py` → propose `mapping/chapter_map.yml`
- `scripts/build_chapters.py` → assemble `manuscript/chapters/*.md`

## Stable excerpt IDs

- Format: `post-slug#p{paragraphIndex}[-s{sentenceIndex}]~{hash8}`
- Example: `made-you-look-talent-attraction-at-its-finest#p04~7f3ca1d2`
- Encodes post, paragraph index, optional sentence index, and an 8‑char hash of normalized text

## Notes

- Do not edit `blog-export.csv`. Scripts are read‑only on the CSV.
- All generated artifacts go under `build/` and can be regenerated.


