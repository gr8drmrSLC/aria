# ARIA — Claude Code Instructions

## Start of every session
1. Read `PROJECT_STATUS.md` — current deployment state and open items
2. Read `DECISIONS.md` — why things are built the way they are
3. Update both files at the end of every session before committing

## Project layout
```
aria/
├── core/
│   ├── ingest.py      # arXiv API fetching
│   ├── store.py       # SQLite data layer
│   ├── analyst.py     # Claude API paper analysis
│   ├── decider.py     # 4-trigger anomaly detection (the agentic core)
│   └── reporter.py    # Intelligence brief generation
├── dashboard/
│   ├── app.py         # Flask dashboard
│   └── templates/     # index.html (feed + reports), report.html (detail)
├── runner.py          # Main orchestrator + APScheduler
├── data/aria.db       # SQLite (gitignored)
└── logs/aria.log      # Rotating log (gitignored)
```

## Key design decisions
- The four anomaly triggers in `decider.py` are the autonomous core — ARIA decides whether to report, no human prompting
- Analysis is batched (10 papers/call) to stay within Claude token limits
- Baselines are stored per-category per-day — needed to detect volume spikes and significance surges
- Dashboard reads from the same SQLite — no separate API server needed for demo purposes

## Environment
- Python 3.11+
- `ANTHROPIC_API_KEY` must be set
- Install: `pip install -r requirements.txt`
- Run once: `python runner.py --once`
- Scheduled: `python runner.py` (daily 07:00 UTC)
- Dashboard: `python dashboard/app.py` (port 5050)

## Workflow rules
- Update `CHANGELOG.md` after every significant change
- Never commit `.env` or `data/aria.db` or `logs/`
- Use `git add -p` to review changes before committing
