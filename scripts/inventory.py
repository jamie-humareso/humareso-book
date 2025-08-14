#!/usr/bin/env python3
import argparse
import csv
import hashlib
import json
import os
import re
from pathlib import Path
from typing import Dict, List

from bs4 import BeautifulSoup
from markdownify import markdownify as html_to_md
from slugify import slugify
from tqdm import tqdm


def normalize_whitespace(text: str) -> str:
    if not text:
        return ""
    text = text.replace("\u00A0", " ")  # NBSP → space
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def strip_html_preserving_text(html: str) -> str:
    if not html:
        return ""
    # Remove weird formatting blocks (e.g., custom font includes) at the raw text level
    html = re.sub(r"\{\{[^}]*include_custom_fonts[\s\S]*?\}\}", " ", html, flags=re.I)
    html = re.sub(r"include_custom_fonts\([^)]*\)", " ", html, flags=re.I)

    # Strip HubSpot/HubL module blocks and templating
    # Remove entire module blocks with their inner content
    html = re.sub(r"\{\%\s*module_block[\s\S]*?\%\}[\s\S]*?\{\%\s*end_module_block\s*\%\}", " ", html, flags=re.I)
    # Remove {% raw %} ... {% endraw %}
    html = re.sub(r"\{\%\s*raw\s*\%\}[\s\S]*?\{\%\s*endraw\s*\%\}", " ", html, flags=re.I)
    # Remove any other generic HubL blocks and expressions
    html = re.sub(r"\{\%[\s\S]*?\%\}", " ", html)
    html = re.sub(r"\{\{[\s\S]*?\}\}", " ", html)

    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style"]):
        tag.decompose()
    # Drop embedded media
    for tag in soup(["iframe", "video", "audio", "object", "embed", "noscript"]):
        tag.decompose()
    # Unwrap links (keep anchor text, drop href)
    for a in soup.find_all("a"):
        a.replace_with(a.get_text(" ", strip=True))
    return str(soup)


def convert_html_to_markdown(html: str) -> str:
    clean_html = strip_html_preserving_text(html)
    md = html_to_md(clean_html, heading_style="ATX")
    # Trim excessive blank lines
    md = re.sub(r"\n{3,}", "\n\n", md)
    # Remove markdown link syntax and keep text only
    md = re.sub(r"\[([^\]]+)\]\([^\)]+\)", r"\1", md)
    # Remove bare URLs (http/https)
    md = re.sub(r"https?://\S+", "", md)
    # Remove any residual custom font include blocks
    md = re.sub(r"\{\{[^}]*include_custom_fonts[\s\S]*?\}\}", " ", md, flags=re.I)
    # Remove any residual HubL templating
    md = re.sub(r"\{\%[\s\S]*?\%\}", " ", md)
    md = re.sub(r"\{\{[\s\S]*?\}\}", " ", md)
    return md.strip()


def split_into_paragraphs(md_text: str) -> List[str]:
    # Split on two or more newlines to keep paragraphs intact
    paras = [p.strip() for p in re.split(r"\n\s*\n", md_text) if p.strip()]
    return paras


def compute_stable_id(post_slug: str, paragraph_index: int, text: str) -> str:
    # Normalize for hashing to stabilize across trivial whitespace changes
    norm = normalize_whitespace(text).lower()
    digest = hashlib.sha1(norm.encode("utf-8")).hexdigest()[:8]
    return f"{post_slug}#p{paragraph_index:02d}~{digest}"


def extract_year(date_str: str) -> str:
    if not date_str:
        return ""
    m = re.search(r"(20\d{2}|19\d{2})", date_str)
    return m.group(1) if m else ""


def split_tags(raw: str) -> List[str]:
    if not raw:
        return []
    parts = re.split(r"[|;,]", raw)
    return [p.strip() for p in parts if p and p.strip()]


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def main() -> None:
    parser = argparse.ArgumentParser(description="Inventory John Baldino Humareso blog posts into paragraph-level units.")
    parser.add_argument("--csv", required=True, help="Path to blog-export.csv")
    parser.add_argument("--outdir", default="build", help="Output directory for generated artifacts")
    args = parser.parse_args()

    csv_path = Path(args.csv).expanduser().resolve()
    outdir = Path(args.outdir).expanduser().resolve()
    ensure_dir(outdir)

    index_path = outdir / "john_index.json"
    units_path = outdir / "john_units.jsonl"
    stats_path = outdir / "stats.json"
    posts_md_dir = outdir / "posts_markdown"
    posts_md_dir.mkdir(parents=True, exist_ok=True)

    # Read CSV and filter rows
    rows: List[Dict[str, str]] = []
    with csv_path.open("r", encoding="utf-8", errors="replace", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            author = (row.get("Author") or "").strip().lower()
            blog_name = (row.get("Blog name") or "").strip().lower()
            if author != "john baldino":
                continue
            if "humar" not in blog_name:
                continue
            rows.append(row)

    posts_meta: List[Dict[str, object]] = []
    total_paragraphs = 0
    total_words = 0

    with units_path.open("w", encoding="utf-8") as units_out:
        for row in tqdm(rows, desc="Processing posts"):
            title = (row.get("Post title") or "").strip()
            url = (row.get("Post URL") or "").strip()
            date = (row.get("Publish date") or "").strip()
            year = extract_year(date)
            tags = split_tags(row.get("Tags") or "")
            body_html = row.get("Post body") or ""

            # Prefer URL slug; fallback to title slug
            post_slug = ""
            if url:
                m = re.search(r"https?://[^/]+/(.+)$", url.strip())
                tail = m.group(1) if m else url
                # remove trailing slashes and querystrings/fragments
                tail = tail.split("?")[0].split("#")[0].strip("/")
                post_slug = slugify(tail) if tail else ""
            if not post_slug:
                post_slug = slugify(title) if title else "post"

            md = convert_html_to_markdown(body_html)
            paragraphs = split_into_paragraphs(md)

            post_word_count = 0
            for idx, para in enumerate(paragraphs, start=1):
                words = normalize_whitespace(para).split()
                wc = len(words)
                post_word_count += wc
                total_words += wc
                total_paragraphs += 1
                stable_id = compute_stable_id(post_slug, idx, para)
                rec = {
                    "stable_id": stable_id,
                    "post_slug": post_slug,
                    "post_title": title,
                    "post_url": url,
                    "publish_date": date,
                    "year": year,
                    "tags": tags,
                    "paragraph_index": idx,
                    "text_md": para,
                    "word_count": wc,
                    "char_count": len(para),
                }
                units_out.write(json.dumps(rec, ensure_ascii=False) + "\n")

            # Write full-post markdown for whole-article assembly
            post_md_path = posts_md_dir / f"{post_slug}.md"
            post_md_path.write_text(md + "\n", encoding="utf-8")

            posts_meta.append({
                "post_slug": post_slug,
                "post_title": title,
                "post_url": url,
                "publish_date": date,
                "year": year,
                "tags": tags,
                "num_paragraphs": len(paragraphs),
                "word_count": post_word_count,
                "markdown_path": str(post_md_path),
            })

    # Write index and stats
    with index_path.open("w", encoding="utf-8") as f:
        json.dump(posts_meta, f, indent=2, ensure_ascii=False)

    stats = {
        "num_posts": len(posts_meta),
        "total_paragraphs": total_paragraphs,
        "total_words": total_words,
        "avg_words_per_post": round(total_words / len(posts_meta), 1) if posts_meta else 0,
    }
    with stats_path.open("w", encoding="utf-8") as f:
        json.dump(stats, f, indent=2, ensure_ascii=False)

    print(json.dumps(stats, indent=2))


if __name__ == "__main__":
    main()


