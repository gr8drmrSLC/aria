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


### 2026-03-31
- Changed dashboard default port from 5050 to 5051 to avoid conflicts with commonly used services and reduce deployment friction.
- Corrected `get_paper_count_today()` logic to count papers ingested in the last 24 hours rather than papers published today, aligning metric with actual data pipeline timing and improving accuracy of ingestion rate monitoring.
- Switched from string-based `published` column query to timestamp-based `ingested_at` column comparison, enabling precise 24-hour rolling window tracking instead of calendar-day boundaries that could miscount papers depending on timezone and ingestion timing.


### 2026-03-31
- Migrated markdown rendering from client-side (marked.js CDN) to server-side Python markdown library, eliminating external CDN dependency and enabling offline dashboard operation.
- Added markdown content pre-processing in `report_detail()` endpoint with support for tables and fenced code blocks, improving report presentation consistency and reducing JavaScript complexity.
- Removed Marked.js CDN script tag and client-side rendering logic from report template, reducing initial page load burden and JavaScript execution overhead.
- Added "About ARIA" informational strip to dashboard homepage explaining the system's autonomous workflow, monitoring scope, anomaly triggers, and decision criteria�improving user onboarding and system transparency.


### 2026-03-31
- Reduced dashboard homepage report display from 10 to 7 to improve page load performance and surface fresher content above the fold.
- Rewrote ARIA system description and trigger explanations to be more accessible and conversational, moving away from jargon toward business-friendly language that emphasizes autonomous decision-making and cross-domain intelligence.
- Added "View all reports" link to homepage reports section to guide users toward the full archive without cluttering the landing page.
- Fixed HTML entity encoding (changed em-dashes and smart quotes from corrupted UTF-8 to proper HTML entities) for consistent rendering across browsers.


### 2026-03-31
- Created a comprehensive single-page HTML dashboard (`docs/index.html`) to visualize ARIA's daily research intelligence output, enabling stakeholders to browse flagged papers and triggered reports without requiring backend infrastructure.
- Implemented a responsive grid-based layout with report cards, paper feed tables, and novelty scoring visualizations to surface research signals in an editorially-designed format optimized for both desktop and mobile consumption.
- Embedded real-time clock and dynamic statistics (papers processed, reports filed, 48-hour feed count) to communicate system activity and freshness at a glance.
- Designed a trigger taxonomy visualization documenting the four detection mechanisms (Volume, Cross-domain, Novelty, Surge) with color-coded badges to help users understand why specific papers were surfaced.
- Built the dashboard as a static artifact suitable for daily automated generation and distribution, reducing operational overhead while maintaining accessibility for non-technical stakeholders.


### 2026-04-01
- Automated daily GitHub Pages publication via scheduled workflow that triggers 90 minutes after ARIA's main pipeline, ensuring the live dashboard reflects the latest analysis without manual intervention.
- Integrated static page export process (`export_static.py`) that pulls updated metrics and report data from the live ARIA API and commits changes to the `docs/` directory with automated git workflows.
- Added direct link to live dashboard in README to improve discoverability and establish the published GitHub Pages site as the primary user-facing interface for ARIA intelligence briefs.
- Reorganized report card structure to use versioned report directory (`reports/1.html`, `reports/2.html`) instead of date-based naming, enabling cleaner URL schema and easier archival management.


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
