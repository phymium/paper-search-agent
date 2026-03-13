#!/bin/bash
# run_daily.sh — wrapper script for cron to run the paper search agent daily

set -e

# ── Edit this path to match your machine ─────────────────────────────────────
AGENT_DIR="/Users/zhanaoxu/Desktop/TianyouYun/paper_search_agent"
# ─────────────────────────────────────────────────────────────────────────────

LOG_FILE="/tmp/paper_agent_$(date +%Y-%m-%d).log"

echo "======================================" >> "$LOG_FILE"
echo "Run started: $(date)" >> "$LOG_FILE"
echo "======================================" >> "$LOG_FILE"

cd "$AGENT_DIR"

# Activate virtual environment if it exists
if [ -d ".venv" ]; then
    source .venv/bin/activate
fi

python agent.py >> "$LOG_FILE" 2>&1

echo "Run finished: $(date)" >> "$LOG_FILE"
