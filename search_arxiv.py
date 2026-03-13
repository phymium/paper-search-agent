"""
search_arxiv.py — fetch last-24h papers from Arxiv matching a query
"""

import datetime
import arxiv
from typing import Any

ARXIV_MAX_RESULTS = 100  # upper cap for the API call


def search_arxiv(query: str, since_date: datetime.date, max_results: int = 20) -> list[dict[str, Any]]:
    """
    Search Arxiv for papers posted since `since_date` matching `query`.
    Returns a list of paper dicts with a common schema.
    """
    client = arxiv.Client()
    search = arxiv.Search(
        query=query,
        max_results=ARXIV_MAX_RESULTS,
        sort_by=arxiv.SortCriterion.SubmittedDate,
        sort_order=arxiv.SortOrder.Descending,
    )

    results = []
    for paper in client.results(search):
        paper_date = paper.published.date()
        if paper_date < since_date:
            break  # results are sorted newest-first; stop early
        results.append(_to_dict(paper))
        if len(results) >= max_results:
            break

    return results


def _to_dict(paper: arxiv.Result) -> dict[str, Any]:
    return {
        "source": "arxiv",
        "title": paper.title.strip(),
        "authors": [a.name for a in paper.authors],
        "date": paper.published.date().isoformat(),
        "abstract": paper.summary.strip(),
        "url": paper.entry_id,
        "doi": paper.doi or "",
        "journal": "arXiv",
    }
