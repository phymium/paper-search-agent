"""
export_obsidian.py — generate Obsidian-compatible Markdown files.

Two outputs:
  1. Daily digest  → OBSIDIAN_VAULT_PATH/YYYY-MM-DD_paper_digest.md
  2. Individual    → OBSIDIAN_PAPERS_PATH/YYYY-MM-DD_<title_slug>.md
     (only for papers with importance >= DEEP_DIVE_THRESHOLD)
"""

import os
import re
import datetime
from typing import Any


# ── Helpers ───────────────────────────────────────────────────────────────────

def _stars(score: int) -> str:
    return "⭐" * score + "☆" * (5 - score)


def _slug(title: str, max_len: int = 60) -> str:
    """Convert a title to a filesystem-safe slug."""
    slug = title.lower()
    slug = re.sub(r"[^\w\s-]", "", slug)
    slug = re.sub(r"[\s_-]+", "_", slug).strip("_")
    return slug[:max_len]


def _authors_str(authors: list[str], limit: int = 5) -> str:
    if not authors:
        return "Unknown"
    if len(authors) > limit:
        return ", ".join(authors[:limit]) + " et al."
    return ", ".join(authors)


def _source_emoji(source: str) -> str:
    return {"arxiv": "📐", "biorxiv": "🔬", "medrxiv": "🏥", "pubmed": "🧬"}.get(source.lower(), "📄")


def _ensure_dir(path: str) -> None:
    os.makedirs(path, exist_ok=True)


# ── Individual paper note (score 4-5) ─────────────────────────────────────────

def _paper_note(paper: dict[str, Any], date_str: str) -> str:
    keywords_md = ", ".join(f"`{kw}`" for kw in paper.get("keywords", []))
    findings_md = "\n".join(
        f"- {f}" for f in paper.get("key_findings", ["No key findings extracted."])
    )
    discussion = paper.get("discussion", "*No discussion generated.*")
    source = paper.get("source", "unknown")
    emoji = _source_emoji(source)

    lines = [
        "---",
        f"tags: [paper, high-impact, {source}]",
        f"date: {date_str}",
        f"source: {source}",
        f"url: {paper.get('url', '')}",
        f"doi: {paper.get('doi', '')}",
        f"importance: {paper.get('importance', '?')}",
        "---",
        "",
        f"# {emoji} {paper.get('title', 'Untitled')}",
        "",
        f"**Authors:** {_authors_str(paper.get('authors', []))}  ",
        f"**Journal/Source:** {paper.get('journal', source)}  ",
        f"**Published:** {paper.get('date', date_str)}  ",
        f"**URL:** [{paper.get('url', '')}]({paper.get('url', '')})",
        "",
        "---",
        "",
        "## 🔑 Keywords",
        "",
        keywords_md or "*No keywords extracted.*",
        "",
        "## ⭐ Importance",
        "",
        f"{_stars(paper.get('importance', 0))} **{paper.get('importance', '?')}/5**",
        "",
        f"> {paper.get('importance_rationale', '')}",
        "",
        "## 📝 Summary",
        "",
        paper.get("summary", "*No summary generated.*"),
        "",
        "## 🔬 Key Findings",
        "",
        findings_md,
        "",
        "## 💬 Discussion",
        "",
        discussion,
        "",
        "## 📄 Abstract",
        "",
        f"> {paper.get('abstract', 'No abstract available.')}",
        "",
    ]
    return "\n".join(lines)


def export_individual_note(paper: dict[str, Any], papers_path: str, date_str: str) -> str:
    """Write an individual paper note and return the filename (for wiki-linking)."""
    _ensure_dir(papers_path)
    filename = f"{date_str}_{_slug(paper.get('title', 'paper'))}.md"
    filepath = os.path.join(papers_path, filename)
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(_paper_note(paper, date_str))
    return os.path.splitext(filename)[0]  # return note name without .md for wiki-link


# ── Daily Digest ──────────────────────────────────────────────────────────────

SOURCE_ORDER = ["pubmed", "biorxiv", "medrxiv", "arxiv"]

def _paper_digest_entry(paper: dict[str, Any], wiki_name: str | None) -> list[str]:
    score = paper.get("importance", 0)
    keywords_md = ", ".join(f"`{kw}`" for kw in paper.get("keywords", []))
    title = paper.get("title", "Untitled")
    url = paper.get("url", "")
    summary = paper.get("summary", "")
    rationale = paper.get("importance_rationale", "")

    title_link = f"[{title}]({url})" if url else title
    wiki_suffix = f" → [[{wiki_name}]]" if wiki_name else ""

    lines = [
        f"### {title_link}",
        "",
        f"**Authors:** {_authors_str(paper.get('authors', []))}  ",
        f"**Date:** {paper.get('date', '')} | **Source:** {paper.get('source', '').upper()}",
        "",
        f"**Keywords:** {keywords_md or '*none*'}",
        "",
        f"**Importance:** {_stars(score)} **{score}/5** — {rationale}",
        "",
        f"**Summary:** {summary}{wiki_suffix}",
        "",
        "---",
        "",
    ]
    return lines


def export_daily_digest(
    papers: list[dict[str, Any]],
    topics: list[str],
    vault_path: str,
    papers_path: str,
    date_str: str,
    threshold: int = 4,
) -> str:
    """
    Write the daily digest .md and individual notes for high-score papers.
    Returns the path to the digest file.
    """
    _ensure_dir(vault_path)

    # Write individual notes first, collect wiki-link names
    wiki_map: dict[str, str] = {}
    for paper in papers:
        if paper.get("importance", 0) >= threshold:
            wiki_name = export_individual_note(paper, papers_path, date_str)
            wiki_map[paper.get("url", "") or paper.get("title", "")] = wiki_name

    # Group papers by source, sorted by importance desc within each group
    by_source: dict[str, list] = {}
    for paper in sorted(papers, key=lambda p: p.get("importance", 0), reverse=True):
        src = paper.get("source", "unknown").lower()
        by_source.setdefault(src, []).append(paper)

    total = len(papers)
    high = sum(1 for p in papers if p.get("importance", 0) >= threshold)

    lines: list[str] = [
        "---",
        "tags: [paper-digest, daily]",
        f"date: {date_str}",
        f"topics: [{', '.join(topics)}]",
        f"total_papers: {total}",
        f"high_impact_papers: {high}",
        "---",
        "",
        f"# 📄 Daily Paper Digest — {date_str}",
        "",
        f"> **{total} papers** found across {len(by_source)} sources | "
        f"**{high} high-impact** (⭐ 4–5)",
        "",
        f"**Topics:** {' · '.join(f'`{t}`' for t in topics)}",
        "",
        "---",
        "",
    ]

    for source in SOURCE_ORDER + [s for s in by_source if s not in SOURCE_ORDER]:
        src_papers = by_source.get(source, [])
        if not src_papers:
            continue
        emoji = _source_emoji(source)
        lines += [
            f"## {emoji} {source.upper()} ({len(src_papers)} papers)",
            "",
        ]
        for paper in src_papers:
            key = paper.get("url", "") or paper.get("title", "")
            wiki_name = wiki_map.get(key)
            lines += _paper_digest_entry(paper, wiki_name)

    digest_filename = f"{date_str}_paper_digest.md"
    digest_path = os.path.join(vault_path, digest_filename)
    with open(digest_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    return digest_path
