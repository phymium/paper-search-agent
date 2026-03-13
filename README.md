<div align="center">

# 🔬 Daily Paper Search Agent

**Automatically fetches, scores, and summarizes the latest biomedical preprints and publications — every day.**

[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue?logo=python)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Sources](https://img.shields.io/badge/sources-Arxiv%20%7C%20BioArxiv%20%7C%20PubMed-orange)]()
[![LLM](https://img.shields.io/badge/LLM-LM%20Studio%20%7C%20OpenAI%20%7C%20DeepSeek-purple)]()
[![Obsidian](https://img.shields.io/badge/export-Obsidian%20Markdown-7C3AED?logo=obsidian)]()

</div>

---

A Python agent that runs daily, searches **Arxiv**, **BioArxiv**, and **PubMed** for the past 24 hours, uses an **LLM** (local or cloud) to evaluate each paper's importance, and exports structured **Obsidian-compatible Markdown** notes — automatically, every morning.

## ✨ Features

- 🔍 **3 sources in parallel** — Arxiv, BioArxiv, PubMed (last 24 h, configurable)
- 🧬 **6 default research topics** — Tumor metabolism, TME, Spatial Transcriptomics, multi-omic, medical agents, AI in medicine
- 🤖 **LLM two-pass analysis**:
  - **Pass 1 (all papers):** keywords · importance score (1–5 ⭐) · summary
  - **Pass 2 (score 4–5 only):** key findings · discussion of implications
- 🗒️ **Two Obsidian exports per run:**
  - `Daily Papers/YYYY-MM-DD_paper_digest.md` — full digest, grouped by source
  - `Papers/YYYY-MM-DD_title.md` — individual deep-dive per high-impact paper
- 🔗 **Auto wiki-links** — digest entries link `[[...]]` to individual notes
- ⏰ **Cron-ready** — shell script + one-liner crontab setup
- 🔑 **Strict scoring rubric** — calibrated to keep scores 4–5 genuinely rare (~15%)

## 🗂️ Project Structure

```
paper_search_agent/
├── agent.py              # Main orchestrator (CLI entry point)
├── config.py             # .env config loader
├── search_arxiv.py       # Arxiv search (official Python client)
├── search_biorxiv.py     # BioArxiv search (REST API + local keyword filter)
├── search_pubmed.py      # PubMed search (NCBI Entrez / Biopython)
├── llm_analyzer.py       # LLM two-pass analysis
├── export_obsidian.py    # Obsidian .md export
├── run_daily.sh          # Cron wrapper script
├── requirements.txt
├── .env.example          # ← copy this to .env and fill in
└── README.md
```

## 🚀 Quick Start

### 1. Clone & install

```bash
git clone https://github.com/phymium/paper-search-agent.git
cd paper-search-agent

python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Configure

```bash
cp .env.example .env
# Edit .env with your favourite editor
```

Key settings in `.env`:

| Variable | Required | Description |
|---|---|---|
| `SEARCH_TOPICS` | ✅ | Comma-separated topics to monitor |
| `LLM_MODE` | ✅ | `lmstudio` · `openai` · `deepseek` |
| `PUBMED_EMAIL` | ✅ | Your email (NCBI requirement) |
| `OBSIDIAN_VAULT_PATH` | ✅ | Absolute path to your daily digest folder |
| `OBSIDIAN_PAPERS_PATH` | ✅ | Absolute path to your individual papers folder |
| `NCBI_API_KEY` | ⬜ | Optional — raises PubMed rate limit 3→10 req/s |

**LLM backend options:**

| `LLM_MODE` | Required keys | Notes |
|---|---|---|
| `lmstudio` | `LMSTUDIO_BASE_URL`, `LMSTUDIO_MODEL` | Local server at `localhost:1234` |
| `openai` | `OPENAI_API_KEY`, `OPENAI_MODEL` | e.g. `gpt-4o-mini` |
| `deepseek` | `DEEPSEEK_API_KEY`, `DEEPSEEK_MODEL` | e.g. `deepseek-chat` (V3) or `deepseek-reasoner` (R1) |

### 3. Run

```bash
# Full run (fetch → LLM → export to Obsidian)
python agent.py

# Override topics for this run
python agent.py --topics "CRISPR, spatial transcriptomics"

# Dry-run: fetch only, no LLM or export (quick connectivity test)
python agent.py --dry-run

# Look back 3 days instead of 1
python agent.py --days 3
```

### 4. Schedule daily (cron)

```bash
chmod +x run_daily.sh
crontab -e
```

Add this line to run every day at **08:00**:
```
0 8 * * * /path/to/paper_search_agent/run_daily.sh
```

Logs are written to `/tmp/paper_agent_YYYY-MM-DD.log`.

## 📄 Output Format

### Daily Digest (`YYYY-MM-DD_paper_digest.md`)

```markdown
---
tags: [paper-digest, daily]
date: 2026-03-13
topics: [Tumor metabolism, Spatial Transcriptomics, ...]
total_papers: 38
high_impact_papers: 4
---
# 📄 Daily Paper Digest — 2026-03-13

## 🧬 PUBMED (14 papers)

### [Metabolic reprogramming drives immunosuppression in TME](url)
**Keywords:** `glycolysis`, `lactate`, `T-cell exhaustion`, ...
**Importance:** ⭐⭐⭐⭐ 4/5 — First mechanistic link between...
**Summary:** … → [[2026-03-13_metabolic_reprogramming_tme]]
```

### Individual Paper Note (`Papers/YYYY-MM-DD_title.md`, score 4–5 only)

```markdown
---
tags: [paper, high-impact, pubmed]
importance: 4
---
# 📄 Metabolic reprogramming drives immunosuppression in TME

## 🔑 Keywords
`glycolysis`, `lactate`, `T-cell exhaustion` ...

## ⭐ Importance
⭐⭐⭐⭐ 4/5 — First mechanistic link between...

## 📝 Summary  |  ## 🔬 Key Findings  |  ## 💬 Discussion
...
```

## ⚙️ Scoring Rubric

The LLM uses a strict calibrated rubric to prevent score inflation:

| Score | Criteria | Expected % |
|---|---|---|
| 1 | Routine / replication / small cohort | ~20% |
| 2 | Modest contribution, limited novelty | ~20% |
| 3 | Meaningful advance within expected research | ~45% |
| 4 | Surprising mechanistic insight, validated target, field-changing method | ~12% |
| 5 | Paradigm-shifting, likely widely cited within a year | ~3% |

Only papers scoring **4 or 5** receive individual deep-dive notes.

## 📦 Dependencies

| Package | Purpose |
|---|---|
| [`arxiv`](https://pypi.org/project/arxiv/) | Arxiv Python client |
| [`biopython`](https://biopython.org/) | PubMed via NCBI Entrez |
| [`openai`](https://pypi.org/project/openai/) | LLM calls (OpenAI / DeepSeek / LM Studio) |
| [`python-dotenv`](https://pypi.org/project/python-dotenv/) | `.env` config loading |
| [`rich`](https://github.com/Textualize/rich) | Terminal output |
| [`requests`](https://requests.readthedocs.io/) | BioArxiv REST API |

## 📝 License

MIT — free to use, modify, and share.

---

<div align="center">
Made for researchers who want to stay on top of the literature — without spending hours on it.
</div>
