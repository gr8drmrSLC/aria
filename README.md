# ARIA — Autonomous Research Intelligence Agent

ARIA monitors arXiv daily, analyzes new research papers with Claude AI, and autonomously
decides when activity is significant enough to warrant publishing an intelligence brief.
No human prompting required — ARIA runs on a schedule, detects anomalies, and reports.

**[Live Dashboard](https://gr8drmrslc.github.io/aria/)** — updated daily after each pipeline run.

---

## What it does

Every day at 07:00 UTC, ARIA:

1. **Ingests** new papers from arXiv across four research domains: AI/ML (cs.AI, cs.LG), biology (q-bio.*), and robotics (cs.RO)
2. **Analyzes** each paper with Claude — assigning novelty scores (0–10), identifying themes, and flagging notable work
3. **Decides** autonomously whether today's activity is significant using four anomaly triggers:
   - **Volume Spike** — unusually high paper count vs. historical baseline
   - **Cross-Domain Cluster** — papers bridging AI, biology, and robotics simultaneously
   - **Novelty Burst** — concentration of high-scoring papers above the threshold
   - **Significance Surge** — average novelty score significantly exceeds historical mean
4. **Reports** — when any trigger fires, Claude drafts a structured intelligence brief covering key findings, emerging themes, and notable papers
5. **Displays** everything on a newspaper-style dashboard with a live paper feed and published reports

---

## Stack

| Component    | Technology                          |
|--------------|-------------------------------------|
| Data source  | arXiv API (feedparser)              |
| Analysis     | Anthropic Claude API (claude-sonnet-4-6) |
| Storage      | SQLite                              |
| Scheduler    | APScheduler                         |
| Dashboard    | Flask + Jinja2                      |

---

## Setup

```bash
# 1. Clone and install
git clone https://github.com/gr8drmrSLC/aria.git
cd aria
pip install -r requirements.txt

# 2. Configure
cp .env.example .env
# Edit .env — add your ANTHROPIC_API_KEY

# 3. Run once to validate
python runner.py --once

# 4. Start dashboard (separate terminal)
python dashboard/app.py
# Open http://localhost:5050

# 5. Run on schedule (daily 07:00 UTC)
python runner.py
```

---

## Environment variables

| Variable                 | Default              | Description                                  |
|--------------------------|----------------------|----------------------------------------------|
| `ANTHROPIC_API_KEY`      | required             | Your Anthropic API key                       |
| `ARIA_MODEL`             | claude-sonnet-4-6    | Claude model for analysis and reporting      |
| `ARIA_DB_PATH`           | data/aria.db         | SQLite database path                         |
| `ARIA_LOG_LEVEL`         | INFO                 | Log verbosity                                |
| `ARIA_NOVELTY_THRESHOLD` | 7                    | Min score to flag a paper as high-novelty    |
| `ARIA_VOLUME_SPIKE`      | 1.5                  | Multiplier over baseline for volume trigger  |
| `ARIA_NOVELTY_BURST_PCT` | 0.30                 | Fraction of high-novelty papers for trigger  |
| `ARIA_SIGNIFICANCE_SURGE`| 1.3                  | Multiplier over baseline avg for surge trigger |
| `ARIA_CROSS_DOMAIN_MIN`  | 3                    | Min cross-domain papers for trigger          |
| `ARIA_DASHBOARD_PORT`    | 5050                 | Flask dashboard port                         |

---

## Project structure

```
aria/
├── core/
│   ├── ingest.py       # arXiv API fetching
│   ├── store.py        # SQLite data layer
│   ├── analyst.py      # Claude API analysis
│   ├── decider.py      # Autonomous anomaly detection
│   └── reporter.py     # Intelligence brief generation
├── dashboard/
│   ├── app.py          # Flask app
│   └── templates/
│       ├── index.html  # Main dashboard (newspaper UI)
│       └── report.html # Report detail page
├── runner.py           # Orchestrator + scheduler
├── data/               # SQLite database (gitignored)
├── logs/               # Pipeline logs (gitignored)
└── docs/
    └── USER_MANUAL.md
```

---

## License

MIT
