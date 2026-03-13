# 🔬 Daily Paper Search Agent

A daily-running Python agent that searches **Arxiv**, **BioArxiv**, and **PubMed** for the last 24 hours of publications, uses an **LLM** (OpenAI API or local LM Studio) to evaluate each paper, and exports two types of **Obsidian-compatible Markdown** notes.

---

## ✨ Features

| Feature | Details |
|---|---|
| **3 sources** | Arxiv, BioArxiv, PubMed (last 24 h) |
| **6 default topics** | Tumor metabolism, TME, Spatial Transcriptomics, multi-omic, medical agents, AI in medicine |
| **LLM Pass 1** | Keywords, importance score (1–5 ⭐), short summary — for every paper |
| **LLM Pass 2** | Key findings + discussion — only for papers scored 4–5 |
| **Daily digest** | `YYYY-MM-DD_paper_digest.md` with all papers, grouped by source |
| **Individual notes** | One `.md` per high-score paper (4–5), with full analysis |
| **Wiki-links** | Digest links `[[...]]` to individual notes automatically |
| **Daily scheduling** | Shell script + cron setup for hands-free daily runs |

---

## 🚀 Setup

### 1. Install dependencies

```bash
cd paper_search_agent

# Create a virtual environment (recommended)
python3 -m venv .venv
source .venv/bin/activate

pip install -r requirements.txt
```

### 2. Configure

```bash
cp .env.example .env
```

Open `.env` and fill in:

| Variable | Required | Description |
|---|---|---|
| `SEARCH_TOPICS` | ✅ | Comma-separated topics to monitor |
| `LLM_MODE` | ✅ | `lmstudio` or `openai` |
| `LMSTUDIO_BASE_URL` | if LM Studio | Default: `http://localhost:1234/v1` |
| `LMSTUDIO_MODEL` | if LM Studio | Name of model loaded in LM Studio |
| `OPENAI_API_KEY` | if OpenAI | Your API key |
| `OPENAI_MODEL` | if OpenAI | e.g. `gpt-4o-mini` |
| `PUBMED_EMAIL` | ✅ | Your email (NCBI requirement) |
| `OBSIDIAN_VAULT_PATH` | ✅ | Absolute path to your daily digest folder |
| `OBSIDIAN_PAPERS_PATH` | ✅ | Absolute path to your individual papers folder |

> **LM Studio** — Make sure a model is loaded and the local server is running (`http://localhost:1234`).

### 3. Set up Obsidian folders

Create two folders in your Obsidian vault:
```
📂 YourVault/
├── 📁 Daily Papers/    ← paste path into OBSIDIAN_VAULT_PATH
└── 📁 Papers/          ← paste path into OBSIDIAN_PAPERS_PATH
```

---

## ▶️ Running manually

```bash
# Run with topics from .env
python agent.py

# Override topics for this run
python agent.py --topics "CRISPR, spatial transcriptomics"

# Fetch only — no LLM, no export (quick test)
python agent.py --dry-run

# Look back 3 days instead of 1
python agent.py --days 3

# Also save raw JSON output
python agent.py --output-json /tmp/papers.json
```

---

## 🕗 Scheduling daily runs (cron)

Make the script executable:
```bash
chmod +x run_daily.sh
```

Open your crontab:
```bash
crontab -e
```

Add this line to run every day at **08:00**:
```
0 8 * * * /Users/zhanaoxu/Desktop/TianyouYun/paper_search_agent/run_daily.sh
```

Logs are written to `/tmp/paper_agent_YYYY-MM-DD.log`.

> **Note:** If you use a virtual environment and cron, the `run_daily.sh` script handles `source .venv/bin/activate` automatically.

---

## 📄 Output File Structure

### Daily Digest — `YYYY-MM-DD_paper_digest.md`

```markdown
---
tags: [paper-digest, daily]
date: 2026-03-13
topics: [Tumor metabolism, ...]
total_papers: 42
high_impact_papers: 5
---
# 📄 Daily Paper Digest — 2026-03-13
## 🧬 PUBMED (15 papers)
### [Title](url)
**Keywords:** `kw1`, `kw2`  |  **Importance:** ⭐⭐⭐⭐⭐ 5/5 — rationale
**Summary:** … → [[2026-03-13_title_slug]]   ← wiki-links to individual notes
...
```

### Individual Paper Note — `YYYY-MM-DD_title_slug.md` (score 4–5 only)

```markdown
---
tags: [paper, high-impact, pubmed]
importance: 5
---
# 📄 Paper Title
## 🔑 Keywords
`tumor metabolism`, `glycolysis`, ...
## ⭐ Importance
⭐⭐⭐⭐⭐ 5/5
> Rationale sentence
## 📝 Summary
...
## 🔬 Key Findings
- Finding 1
- Finding 2
## 💬 Discussion
Implications, limitations, future directions...
## 📄 Abstract
> Full abstract
```

---

## 🛠 Project Structure

```
paper_search_agent/
├── agent.py              # Main orchestrator
├── config.py             # .env loader
├── search_arxiv.py       # Arxiv search
├── search_biorxiv.py     # BioArxiv search
├── search_pubmed.py      # PubMed search
├── llm_analyzer.py       # LLM analysis (Pass 1 + Pass 2)
├── export_obsidian.py    # Obsidian .md export
├── run_daily.sh          # Cron wrapper script
├── requirements.txt
├── .env.example          # Config template
└── README.md
```

---

## 📦 Dependencies

- [`arxiv`](https://pypi.org/project/arxiv/) — Arxiv Python client
- [`biopython`](https://biopython.org/) — PubMed via NCBI Entrez
- [`openai`](https://pypi.org/project/openai/) — LLM calls (OpenAI or LM Studio)
- [`python-dotenv`](https://pypi.org/project/python-dotenv/) — `.env` config loading
- [`rich`](https://github.com/Textualize/rich) — Beautiful terminal output
- [`requests`](https://requests.readthedocs.io/) — BioArxiv REST API
