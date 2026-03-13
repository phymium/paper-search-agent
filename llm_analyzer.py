"""
llm_analyzer.py — LLM-powered analysis of academic papers.

Supports two backends (configured via LLM_MODE in .env):
  - 'lmstudio' : local LM Studio server (OpenAI-compatible API)
  - 'openai'   : OpenAI API

Two-pass strategy:
  Pass 1 (all papers)       → keywords, importance (1-5), summary
  Pass 2 (score 4-5 only)  → key_findings, discussion
"""

import json
import time
from typing import Any

import openai
import config


# ── Client Setup ─────────────────────────────────────────────────────────────

def _get_client() -> tuple[openai.OpenAI, str]:
    """Return (OpenAI client, model name) based on config."""
    if config.LLM_MODE == "openai":
        client = openai.OpenAI(api_key=config.OPENAI_API_KEY)
        model = config.OPENAI_MODEL
    elif config.LLM_MODE == "deepseek":
        client = openai.OpenAI(
            api_key=config.DEEPSEEK_API_KEY,
            base_url=config.DEEPSEEK_BASE_URL,
        )
        model = config.DEEPSEEK_MODEL
    else:  # lmstudio (default)
        client = openai.OpenAI(
            api_key="lm-studio",  # LM Studio ignores the key but the field is required
            base_url=config.LMSTUDIO_BASE_URL,
        )
        model = config.LMSTUDIO_MODEL
    return client, model


def _chat(client: openai.OpenAI, model: str, prompt: str, retries: int = 3) -> str:
    """Send a chat completion and return the raw text response."""
    for attempt in range(retries):
        try:
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are an expert biomedical research assistant. "
                            "Always respond with valid JSON only, no markdown fences."
                        ),
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=0.2,
                max_tokens=1024,
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            print(f"[llm] Attempt {attempt + 1} failed: {e}")
            time.sleep(2 ** attempt)
    return "{}"


def _parse_json(raw: str) -> dict:
    """Safely parse JSON, stripping any accidental markdown fences."""
    raw = raw.strip()
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[-1].rsplit("```", 1)[0]
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {}


# ── Pass 1: All Papers ────────────────────────────────────────────────────────

PASS1_PROMPT = """You are a rigorous senior biomedical researcher evaluating papers for a daily digest.
Your job is to score each paper's IMPORTANCE strictly. Most papers are incremental — be honest.

STRICT SCORING RUBRIC (read carefully before scoring):
  1 = Routine/incremental: confirms known findings, small cohort, narrow scope, or methodological replication.
  2 = Modest contribution: solid data but limited novelty; builds on established frameworks without major advance.
  3 = Meaningful advance: clear new finding or useful method, but within an expected line of research.
  4 = High impact: demonstrates a surprising mechanistic insight, a validated therapeutic target, or a new methodology that changes how the field works. Must be reproducible, well-controlled, and broadly applicable.
  5 = Landmark: paradigm-shifting discovery with strong evidence — likely to be widely cited within a year. Reveals a new biological principle, reports a major clinical breakthrough, or fundamentally redefines a disease mechanism.

CALIBRATION — to prevent score inflation, follow this distribution:
  - ~40% of papers should score 1–2 (incremental or routine work)
  - ~45% should score 3 (meaningful but not exceptional)
  - Only ~15% should score 4–5 (genuinely impactful)
  - Score 5 should be rare (≤5%). If you want to give many 4s, re-read the rubric.
  - Negative controls, replication studies, and small descriptive atlases are almost always 1–2.
  - A "novel" method scores 4 only if it solves a problem that had no good prior solution.
  - Clinical trials score 4–5 only if randomized, adequately powered, and showing a clinically meaningful endpoint.

Return a JSON object with EXACTLY these fields (no extra keys, no markdown fences):
{{
  "keywords": ["keyword1", "keyword2", ...],   // 5–8 precise scientific terms (avoid generic words like "cancer" or "cells")
  "importance": 2,                              // integer 1–5 per the rubric — default to conservative
  "importance_rationale": "one sentence citing a specific concrete aspect of the paper that determined the score",
  "summary": "2–3 sentence plain-language summary of what was done and what was actually found"
}}

Paper title: {title}
Authors: {authors}
Source: {source}
Abstract:
{abstract}"""


def analyze_basic(paper: dict[str, Any], client: openai.OpenAI, model: str) -> dict[str, Any]:
    prompt = PASS1_PROMPT.format(
        title=paper.get("title", ""),
        authors=", ".join(paper.get("authors", [])[:5]),
        source=paper.get("source", ""),
        abstract=paper.get("abstract", "")[:2000],
    )
    raw = _chat(client, model, prompt)
    result = _parse_json(raw)

    paper["keywords"] = result.get("keywords", [])
    paper["importance"] = int(result.get("importance", 1))
    paper["importance_rationale"] = result.get("importance_rationale", "")
    paper["summary"] = result.get("summary", "")
    return paper


# ── Pass 2: Deep-Dive for Score 4-5 ─────────────────────────────────────────

PASS2_PROMPT = """You previously rated this paper {importance}/5 in importance. Now provide a deeper analysis.
Return a JSON object with exactly these fields:
{{
  "key_findings": [
    "Finding 1: ...",
    "Finding 2: ...",
    "Finding 3: ..."
  ],
  "discussion": "A paragraph (4-6 sentences) discussing: (1) scientific implications of this work, (2) how it advances the field, (3) potential limitations or caveats, (4) possible future directions this opens up."
}}

Paper title: {title}
Abstract:
{abstract}
Summary already generated: {summary}"""


def analyze_deep(paper: dict[str, Any], client: openai.OpenAI, model: str) -> dict[str, Any]:
    prompt = PASS2_PROMPT.format(
        importance=paper.get("importance", "?"),
        title=paper.get("title", ""),
        abstract=paper.get("abstract", "")[:2000],
        summary=paper.get("summary", ""),
    )
    raw = _chat(client, model, prompt)
    result = _parse_json(raw)

    paper["key_findings"] = result.get("key_findings", [])
    paper["discussion"] = result.get("discussion", "")
    return paper


# ── Public API ────────────────────────────────────────────────────────────────

def analyze_papers(
    papers: list[dict[str, Any]],
    threshold: int = 4,
) -> list[dict[str, Any]]:
    """
    Run Pass 1 on all papers, then Pass 2 on papers with importance >= threshold.
    Returns the same list with LLM fields added in-place.
    """
    client, model = _get_client()
    total = len(papers)

    print(f"[llm] Running Pass 1 on {total} papers…")
    for i, paper in enumerate(papers, 1):
        print(f"  [{i}/{total}] {paper['title'][:70]}…")
        analyze_basic(paper, client, model)
        time.sleep(0.3)  # be polite to local/remote endpoint

    high_score = [p for p in papers if p.get("importance", 0) >= threshold]
    print(f"[llm] Running Pass 2 (deep-dive) on {len(high_score)} high-score papers…")
    for i, paper in enumerate(high_score, 1):
        print(f"  [{i}/{len(high_score)}] {paper['title'][:70]}…")
        analyze_deep(paper, client, model)
        time.sleep(0.3)

    return papers
