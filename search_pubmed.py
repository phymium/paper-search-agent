"""
search_pubmed.py — fetch last-24h papers from PubMed matching a query.
Uses Biopython's Bio.Entrez module (NCBI E-utilities).
"""

import datetime
import time
from typing import Any
from Bio import Entrez, Medline


def search_pubmed(
    query: str,
    since_date: datetime.date,
    max_results: int = 20,
    email: str = "researcher@example.com",
    api_key: str = "",
) -> list[dict[str, Any]]:
    """
    Search PubMed for papers matching `query` published on or after `since_date`.
    Returns a list of paper dicts with a common schema.
    """
    Entrez.email = email
    if api_key:
        Entrez.api_key = api_key  # raises NCBI rate limit from 3 to 10 req/sec
    today = datetime.date.today()

    # Build date-range filter for NCBI
    date_filter = (
        f"{since_date.strftime('%Y/%m/%d')}:{today.strftime('%Y/%m/%d')}[Date - Publication]"
    )
    full_query = f"({query}) AND {date_filter}"

    # Step 1: eSearch — get list of PMIDs
    try:
        handle = Entrez.esearch(db="pubmed", term=full_query, retmax=max_results, usehistory="y")
        record = Entrez.read(handle)
        handle.close()
    except Exception as e:
        print(f"[pubmed] eSearch error for '{query}': {e}")
        return []

    pmids = record.get("IdList", [])
    if not pmids:
        return []

    # Step 2: eFetch — retrieve full records in MEDLINE format
    time.sleep(0.15 if api_key else 0.4)  # shorter delay when API key raises rate limit
    try:
        handle = Entrez.efetch(
            db="pubmed",
            id=",".join(pmids),
            rettype="medline",
            retmode="text",
        )
        records = list(Medline.parse(handle))
        handle.close()
    except Exception as e:
        print(f"[pubmed] eFetch error: {e}")
        return []

    return [_to_dict(r) for r in records if r.get("TI")]


def _to_dict(record: dict) -> dict[str, Any]:
    pmid = record.get("PMID", "")
    # Parse publication date
    date_str = record.get("DP", "")
    try:
        pub_date = datetime.datetime.strptime(date_str[:10], "%Y %b %d").date().isoformat()
    except Exception:
        pub_date = date_str[:10] if date_str else ""

    # Authors: list of "Last FM" strings
    authors = record.get("AU", [])

    # DOI from AID field (e.g. "10.1234/abc [doi]")
    doi = ""
    for aid in record.get("AID", []):
        if "[doi]" in aid:
            doi = aid.replace("[doi]", "").strip()
            break

    return {
        "source": "pubmed",
        "title": record.get("TI", "").strip(),
        "authors": authors,
        "date": pub_date,
        "abstract": record.get("AB", "").strip(),
        "url": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
        "doi": doi,
        "journal": record.get("JT", record.get("TA", "")),
    }
