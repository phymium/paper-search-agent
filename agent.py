"""
agent.py — Daily Paper Search Agent orchestrator.

Usage:
    python agent.py                          # use topics from .env
    python agent.py --topics "CRISPR,TME"   # override topics for this run
    python agent.py --dry-run               # search only, skip LLM + export
"""

import argparse
import datetime
import json
import os
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import box
from rich.progress import Progress, SpinnerColumn, TextColumn

import config
from search_arxiv import search_arxiv
from search_biorxiv import search_biorxiv
from search_pubmed import search_pubmed
from llm_analyzer import analyze_papers
from export_obsidian import export_daily_digest

console = Console()


# ── Argument Parsing ──────────────────────────────────────────────────────────

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Daily paper search agent — Arxiv, BioArxiv, PubMed",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--topics",
        type=str,
        default=None,
        help="Comma-separated topics to search (overrides .env SEARCH_TOPICS)",
    )
    parser.add_argument(
        "--days",
        type=int,
        default=1,
        help="Days to look back (default: 1 = last 24 h)",
    )
    parser.add_argument(
        "--max",
        type=int,
        default=config.MAX_RESULTS_PER_TOPIC,
        help="Max results per topic per source",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Fetch papers only — skip LLM analysis and Obsidian export",
    )
    parser.add_argument(
        "--output-json",
        type=str,
        default=None,
        metavar="FILE",
        help="Also export raw JSON of all results to FILE",
    )
    return parser.parse_args()


# ── Search ────────────────────────────────────────────────────────────────────

def _fetch_for_topic(
    topic: str, since_date: datetime.date, max_results: int
) -> list[dict[str, Any]]:
    """Run all three sources for a single topic and return merged results."""
    results: list[dict[str, Any]] = []

    with ThreadPoolExecutor(max_workers=3) as ex:
        futures = {
            ex.submit(search_arxiv, topic, since_date, max_results): "arxiv",
            ex.submit(search_biorxiv, topic, since_date, max_results): "biorxiv",
            ex.submit(
                search_pubmed, topic, since_date, max_results, config.PUBMED_EMAIL, config.NCBI_API_KEY
            ): "pubmed",
        }
        for future in as_completed(futures):
            src = futures[future]
            try:
                papers = future.result()
                results.extend(papers)
                console.log(f"  [green]{src}[/green]: {len(papers)} papers for '{topic}'")
            except Exception as e:
                console.log(f"  [red]{src} error[/red] for '{topic}': {e}")

    return results


def fetch_all_papers(
    topics: list[str], since_date: datetime.date, max_results: int
) -> list[dict[str, Any]]:
    """Fetch papers for all topics, deduplicate by URL/DOI."""
    all_papers: list[dict[str, Any]] = []
    seen: set[str] = set()

    for i, topic in enumerate(topics, 1):
        console.rule(f"[bold cyan]Topic {i}/{len(topics)}: {topic}")
        papers = _fetch_for_topic(topic, since_date, max_results)
        for paper in papers:
            key = paper.get("doi") or paper.get("url") or paper.get("title", "")
            if key and key not in seen:
                seen.add(key)
                paper["topic"] = topic  # tag which topic triggered this
                all_papers.append(paper)

    return all_papers


# ── Terminal Display ──────────────────────────────────────────────────────────

SOURCE_COLORS = {
    "arxiv": "blue",
    "biorxiv": "green",
    "medrxiv": "cyan",
    "pubmed": "magenta",
}


def display_results(papers: list[dict[str, Any]], date_str: str) -> None:
    console.print()
    console.print(
        Panel.fit(
            f"[bold white]📄 Daily Paper Digest — {date_str}[/bold white]\n"
            f"[dim]{len(papers)} unique papers found[/dim]",
            border_style="bright_blue",
        )
    )

    # Summary table
    table = Table(
        show_header=True,
        header_style="bold magenta",
        box=box.ROUNDED,
        expand=False,
        show_lines=True,
    )
    table.add_column("⭐", width=3, justify="center")
    table.add_column("Source", width=8)
    table.add_column("Title", max_width=55)
    table.add_column("Date", width=10)
    table.add_column("Authors", max_width=25)
    table.add_column("Keywords", max_width=35)

    sorted_papers = sorted(papers, key=lambda p: p.get("importance", 0), reverse=True)

    for paper in sorted_papers:
        score = paper.get("importance", 0)
        src = paper.get("source", "?")
        color = SOURCE_COLORS.get(src.lower(), "white")
        stars = "⭐" * score
        keywords_str = ", ".join(paper.get("keywords", [])[:4])
        authors = ", ".join(paper.get("authors", [])[:2])
        if len(paper.get("authors", [])) > 2:
            authors += " et al."

        table.add_row(
            stars,
            f"[{color}]{src.upper()}[/{color}]",
            paper.get("title", "")[:55],
            paper.get("date", ""),
            authors,
            keywords_str,
        )

    console.print(table)

    high = [p for p in papers if p.get("importance", 0) >= config.DEEP_DIVE_THRESHOLD]
    if high:
        console.print()
        console.print(
            f"[bold yellow]🔥 {len(high)} high-impact paper(s) (score ≥ {config.DEEP_DIVE_THRESHOLD}) — individual notes created[/bold yellow]"
        )
        for p in high:
            console.print(f"  [green]✓[/green] {p.get('title', '')[:70]}")


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    args = parse_args()

    topics = (
        [t.strip() for t in args.topics.split(",") if t.strip()]
        if args.topics
        else config.SEARCH_TOPICS
    )
    since_date = datetime.date.today() - datetime.timedelta(days=args.days)
    date_str = datetime.date.today().isoformat()

    console.print(
        Panel(
            f"[bold]🔬 Paper Search Agent[/bold]\n"
            f"[dim]Date:[/dim] {date_str}  "
            f"[dim]Looking back:[/dim] {args.days} day(s)\n"
            f"[dim]Topics:[/dim] {', '.join(topics)}\n"
            f"[dim]LLM mode:[/dim] {config.LLM_MODE.upper()}  "
            f"[dim]Sources:[/dim] Arxiv · BioArxiv · PubMed",
            border_style="cyan",
            title="[cyan]Daily Run[/cyan]",
        )
    )

    # 1. Fetch
    console.rule("[bold]Step 1 — Fetching Papers")
    papers = fetch_all_papers(topics, since_date, args.max)
    console.print(f"\n[bold green]✓ {len(papers)} unique papers collected[/bold green]")

    if not papers:
        console.print("[yellow]No papers found. Check your topics or try a wider date range.[/yellow]")
        sys.exit(0)

    # 2. Optional JSON dump before LLM (raw data)
    if args.output_json:
        with open(args.output_json, "w", encoding="utf-8") as f:
            json.dump(papers, f, indent=2, ensure_ascii=False, default=str)
        console.print(f"[dim]Raw JSON saved to {args.output_json}[/dim]")

    if args.dry_run:
        console.print("[yellow]--dry-run set: skipping LLM analysis and export.[/yellow]")
        display_results(papers, date_str)
        return

    # 3. LLM analysis
    console.rule("[bold]Step 2 — LLM Analysis")
    papers = analyze_papers(papers, threshold=config.DEEP_DIVE_THRESHOLD)

    # 4. Display
    display_results(papers, date_str)

    # 5. Export to Obsidian
    console.rule("[bold]Step 3 — Exporting to Obsidian")
    digest_path = export_daily_digest(
        papers=papers,
        topics=topics,
        vault_path=config.OBSIDIAN_VAULT_PATH,
        papers_path=config.OBSIDIAN_PAPERS_PATH,
        date_str=date_str,
        threshold=config.DEEP_DIVE_THRESHOLD,
    )
    high_count = sum(1 for p in papers if p.get("importance", 0) >= config.DEEP_DIVE_THRESHOLD)
    console.print(f"[bold green]✓ Daily digest:[/bold green] {digest_path}")
    console.print(
        f"[bold green]✓ Individual notes:[/bold green] {high_count} files → {config.OBSIDIAN_PAPERS_PATH}"
    )
    console.print("\n[bold]Done! 🎉[/bold]")


if __name__ == "__main__":
    main()
