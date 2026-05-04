# ARIA — Claude Code Instructions

This file is auto-loaded by Claude Code at session start.
Follow every instruction in this file exactly.

---

## Session start protocol (mandatory, in order)

1. Read `PROJECT_STATUS.md` — current deployment state and open items
2. Read `DECISIONS.md` — why things are built the way they are
3. Confirm you have read both before taking any action
4. State the next proposed task based on what you read

Do not skip this protocol. Do not begin work before completing it.

---

## Session end protocol (mandatory)

Before ending any session:

1. Update `PROJECT_STATUS.md` — current state, what was completed, open questions, next task
2. Update `DECISIONS.md` — any architectural decisions made this session
3. Update `CHANGELOG.md` — what changed and why
4. Confirm all changes are committed and pushed

Do not skip this protocol. The next session depends on it.

---

## The 8-step regression safety protocol

Before making any change to existing, working code:

1. State what is currently working and must not break
2. Identify the smallest change that achieves the goal
3. Check whether the change affects any other file or system
4. Make the change
5. Verify the change works (run `python tests/smoke_test.py` or manual check)
6. Verify nothing that was working before is now broken
7. Commit with a message that explains *why*, not just *what*
8. Update PROJECT_STATUS.md if the change was significant

Do not skip steps. Do not batch steps across tasks.

---

## The Wall Protocol

When you hit a blocker, before escalating:

1. List ALL approaches to the problem (minimum 3)
2. Identify tools already in the ecosystem that could solve it
3. Ask: what is the simplest solution?
4. Ask: what would a senior engineer try before writing code?
5. Ask: can the problem be decomposed differently to avoid the wall entirely?

Only escalate after completing all five steps. Present findings — not just "I'm stuck."

---

## Project layout

```
aria/
├── core/
│   ├── ingest.py            # arXiv API fetching + retry logic
│   ├── store.py             # SQLite data layer + baseline tracking
│   ├── analyst.py           # Claude API paper analysis + budget guard
│   ├── decider.py           # 4-trigger anomaly detection (the agentic core)
│   └── reporter.py          # Intelligence brief generation
├── dashboard/
│   ├── app.py               # Flask dashboard (binds to 127.0.0.1:5051)
│   └── templates/           # index.html (feed + reports), report.html (detail)
├── scripts/
│   ├── backup_db.sh         # Weekly S3 backup (cron: Sundays 08:00 UTC)
│   ├── duckdns_update.sh    # DuckDNS IP update (cron: every 6h)
│   ├── export_static.py     # GitHub Pages export (GitHub Actions: Mon-Fri 08:30 UTC)
│   └── update_linkedin.py   # LinkedIn automation (gitignored — run manually)
├── tests/
│   └── smoke_test.py        # 10 pre-deployment checks
├── runner.py                # Main orchestrator + APScheduler (Tue-Fri 07:00 UTC)
├── data/aria.db             # SQLite (gitignored)
└── logs/aria.log            # Rotating log (gitignored)
```

---

## Key design decisions

- Four anomaly triggers in `decider.py` are the autonomous core — ARIA decides whether to report
- Analysis is batched (10 papers/call) to stay within Claude token limits
- Baselines stored per-category per-day — needed for Volume Spike and Significance Surge
- Dashboard reads from the same SQLite — no separate API server
- Dashboard binds to 127.0.0.1:5051 — nginx handles HTTPS and is the only public face
- Budget guard in `analyst.py` hard-caps session spend at $5.00

---

## Budget guard rule

Every Claude API call must wire `_charge(model, response.usage)` immediately after the response.
Never add a new Claude API call without also wiring the charge. If `BudgetExceeded` is raised,
do not catch and suppress it — let it halt the process.

---

## Environment setup

```bash
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # then fill in values
python runner.py --once
python dashboard/app.py   # port 5051
```

---

## Workflow rules

- Run `python tests/smoke_test.py` before any deployment
- Update `CHANGELOG.md` after every significant change
- Never commit `.env`, `data/aria.db`, or `logs/`
- Use `git add -p` to review changes before committing
- One logical change per commit — commit messages explain *why*
