"""
search_biorxiv.py — fetch last-24h papers from BioArxiv/MedRxiv matching a query.

BioArxiv's public API is date-range based (no keyword search), so we:
  1. Fetch all papers posted since `since_date` (up to 200 per cursor page)
  2. Filter locally by keyword match in title + abstract
"""

import datetime
import requests
from typing import Any

BIORXIV_API = "https://api.biorxiv.org/details/{server}/{start}/{end}/{cursor}/json"
PAGE_SIZE = 100  # API returns max 100 per page


def search_biorxiv(
    query: str,
    since_date: datetime.date,
    max_results: int = 20,
    server: str = "biorxiv",
) -> list[dict[str, Any]]:
    """
    Fetch papers from BioArxiv (or MedRxiv) posted since `since_date`
    that match `query` keywords in their title or abstract.
    """
    today = datetime.date.today()
    keywords = [kw.lower().strip() for kw in query.replace(",", " ").split() if len(kw) > 2]

    results: list[dict[str, Any]] = []
    cursor = 0

    while True:
        url = BIORXIV_API.format(
            server=server,
            start=since_date.isoformat(),
            end=today.isoformat(),
            cursor=cursor,
        )
        try:
            resp = requests.get(url, timeout=15)
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            print(f"[biorxiv] Error fetching page (cursor={cursor}): {e}")
            break

        collection = data.get("collection", [])
        if not collection:
            break

        for item in collection:
            title = item.get("title", "")
            abstract = item.get("abstract", "")
            text = (title + " " + abstract).lower()
            # Keyword match: at least one keyword must appear
            if any(kw in text for kw in keywords):
                results.append(_to_dict(item, server))
                if len(results) >= max_results:
                    return results

        total = int(data.get("messages", [{}])[0].get("total", 0))
        cursor += PAGE_SIZE
        if cursor >= total:
            break

    return results


def _to_dict(item: dict, server: str) -> dict[str, Any]:
    authors_raw = item.get("authors", "")
    # BioArxiv returns authors as semicolon-separated string
    authors = [a.strip() for a in authors_raw.split(";") if a.strip()]
    return {
        "source": server,
        "title": item.get("title", "").strip(),
        "authors": authors,
        "date": item.get("date", ""),
        "abstract": item.get("abstract", "").strip(),
        "url": f"https://www.biorxiv.org/content/{item.get('doi', '')}",
        "doi": item.get("doi", ""),
        "journal": item.get("published_journal", "") or server,
    }
