"""
config.py — loads and validates environment configuration from .env
"""

import os
from dotenv import load_dotenv

load_dotenv()


def _require(key: str) -> str:
    val = os.getenv(key, "").strip()
    if not val:
        raise EnvironmentError(f"Missing required config: {key}. Check your .env file.")
    return val


def _get(key: str, default: str = "") -> str:
    return os.getenv(key, default).strip()


# ── Search ────────────────────────────────────────────────────────────────────
SEARCH_TOPICS: list[str] = [
    t.strip()
    for t in _get(
        "SEARCH_TOPICS",
        "Tumor metabolism,Tumor microenvironment,Spatial Transcriptomic,"
        "multi-omic,medical agents,AI in medicine",
    ).split(",")
    if t.strip()
]

MAX_RESULTS_PER_TOPIC: int = int(_get("MAX_RESULTS_PER_TOPIC", "20"))

# ── LLM ───────────────────────────────────────────────────────────────────────
LLM_MODE: str = _get("LLM_MODE", "lmstudio").lower()  # 'lmstudio' | 'openai' | 'deepseek'

LMSTUDIO_BASE_URL: str = _get("LMSTUDIO_BASE_URL", "http://localhost:1234/v1")
LMSTUDIO_MODEL: str = _get("LMSTUDIO_MODEL", "qwen3.5-9B")


OPENAI_API_KEY: str = _get("OPENAI_API_KEY", "")
OPENAI_MODEL: str = _get("OPENAI_MODEL", "gpt-4o-mini")

DEEPSEEK_API_KEY: str = _get("DEEPSEEK_API_KEY", "")
DEEPSEEK_MODEL: str = _get("DEEPSEEK_MODEL", "deepseek-chat")
DEEPSEEK_BASE_URL: str = "https://api.deepseek.com/v1"

# ── PubMed ────────────────────────────────────────────────────────────────────
PUBMED_EMAIL: str = _get("PUBMED_EMAIL", "researcher@example.com")
NCBI_API_KEY: str = _get("NCBI_API_KEY", "")  # optional; raises rate limit 3→10 req/sec

# ── Obsidian ──────────────────────────────────────────────────────────────────
OBSIDIAN_VAULT_PATH: str = _get("OBSIDIAN_VAULT_PATH", "./output/daily")
OBSIDIAN_PAPERS_PATH: str = _get("OBSIDIAN_PAPERS_PATH", "./output/papers")

DEEP_DIVE_THRESHOLD: int = int(_get("DEEP_DIVE_THRESHOLD", "4"))
