# ARIA Changelog

All notable changes to this project will be documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/).

### 2026-03-30
- Increased arXiv API retry resilience from 3 to 4 attempts and extended initial backoff from 2 to 15 seconds to accommodate stricter arXiv rate limiting, reducing failed ingestion runs during peak query periods.
- Added weekend detection logic to run_pipeline() to explicitly warn operators that arXiv publishes Monday�Friday only, preventing false alarms when weekend runs legitimately return zero new papers.
- Removed unused `json` imports from reporter.py and dashboard/app.py to reduce dependency surface and improve code hygiene.
- Fixed string interpolation in fallback report generation to eliminate unnecessary f-string when no variable substitution is needed.


### 2026-03-30 - [review and update this description]
Files changed: dashboard/app.py runner.py
- TODO: describe what changed and why


---

## [0.1.0] — 2026-03-29

### Added
- `core/ingest.py` — arXiv API ingestion for cs.AI, cs.LG, q-bio.*, cs.RO categories
  - feedparser-based Atom feed parsing
  - 24-hour date filter
  - 3-retry exponential backoff on HTTP errors
- `core/store.py` — SQLite data layer
  - Tables: papers, reports, baselines
  - Upsert, baseline tracking, report persistence
- `core/analyst.py` — Claude API paper analysis
  - Batched analysis (10 papers/call) for token efficiency
  - Per-paper: novelty_score (0-10), themes, is_notable, rationale
  - Cross-domain paper identification
- `core/decider.py` — Autonomous 4-trigger anomaly detection
  - Volume Spike: paper count > 1.5x baseline mean
  - Cross-Domain Cluster: 3+ papers bridging multiple research domains
  - Novelty Burst: >30% papers score >= 7
  - Significance Surge: avg novelty > 1.3x baseline mean
- `core/reporter.py` — Intelligence brief generation via Claude API
  - Structured markdown brief: executive summary, key findings, emerging themes, notable papers table, analyst note
  - Fallback report when Claude API is unavailable
- `runner.py` — Main orchestrator
  - `--once` flag for single run
  - APScheduler daily cron (default 07:00 UTC, configurable with `--hour`)
  - Full pipeline: ingest → store → analyze → decide → report → store
- `dashboard/app.py` — Flask dashboard
  - Routes: `/` (main), `/reports/<id>` (detail), `/api/papers`, `/api/reports`, `/api/stats`
- `dashboard/templates/index.html` — Newspaper-style academic UI
  - Live paper feed with novelty bars
  - Published reports with trigger tags
  - Live UTC clock, stat strip
- `dashboard/templates/report.html` — Full report detail page with markdown rendering
- `requirements.txt`, `.env.example`, `.gitignore`
- `CLAUDE.md`, `PROJECT_STATUS.md`, `DECISIONS.md`
- `docs/USER_MANUAL.md` — Full setup and operations guide
