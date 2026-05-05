# ARIA Changelog

All notable changes to this project will be documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/).

### 2026-03-30
- Increased arXiv API retry resilience from 3 to 4 attempts and extended initial backoff from 2 to 15 seconds to accommodate stricter arXiv rate limiting, reducing failed ingestion runs during peak query periods.
- Added weekend detection logic to run_pipeline() to explicitly warn operators that arXiv publishes Monday–Friday only, preventing false alarms when weekend runs legitimately return zero new papers.
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
- Added "About ARIA" informational strip to dashboard homepage explaining the system's autonomous workflow, monitoring scope, anomaly triggers, and decision criteria—improving user onboarding and system transparency.


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


### 2026-04-02
- Converted paper title citations in Key Findings section from bold text to clickable markdown links pointing to arXiv URLs, enabling direct navigation to source materials in generated briefs.
- Enhanced Notable Papers table formatting to use dual markdown links—one for paper titles and one for the Link column—improving accessibility and reducing URL ambiguity in structured reports.
- Updated reporter prompt guidance to enforce consistent markdown link usage throughout briefing output, ensuring users can instantly access papers without manual URL lookup.
- Reinforced link-based citation pattern in system instructions to maintain formatting consistency across all report sections and reduce friction in researcher workflows.


### 2026-04-02
- Migrated dashboard URL configuration from hardcoded localhost to environment variable with production fallback, enabling ARIA to operate across development and production environments without code changes.
- Rewrote LinkedIn post narrative to emphasize real-world detection impact over technical architecture, shifting from explanatory content to demonstrated value through three consecutive days of autonomous anomaly detection and field convergence signals.
- Refactored post copy to lead with outcomes (three intelligence briefs generated autonomously) rather than system mechanics, making the autonomous decision-making capability the primary narrative driver for audience engagement.
- Updated GitHub repository link placement and framing to position source code transparency as a trust mechanism rather than a technical footnote, supporting the credibility of autonomous reporting claims.


### 2026-04-02
- Removed `scripts/update_linkedin.py` to decouple LinkedIn profile automation from the core ARIA research agent, reducing external dependencies and operational complexity tied to third-party session management.
- Added `scripts/update_linkedin.py` and `scripts/diag_*.png` to `.gitignore` to prevent accidental commits of LinkedIn automation scripts and diagnostic screenshot artifacts.
- Eliminated 793 lines of Playwright-based LinkedIn browser automation (profile updates, project creation, post publishing) to focus ARIA on its primary mission: autonomous research analysis rather than social media integration.


### 2026-04-06
- Updated ARIA's execution schedule from daily to Tuesday–Saturday at 07:00 UTC to align with arXiv's announcement cycle, which publishes new submissions on weekday evenings US Eastern time, making batches available the following morning.
- Modified scheduler configuration and pipeline logic to explicitly skip Sunday and Monday runs, eliminating wasteful executions when arXiv produces no new announcements over the weekend.
- Enhanced documentation in both dashboard UI and codebase comments to clarify the arXiv publication cadence and justify the Tuesday–Saturday operational window, reducing user confusion about why certain days are skipped.
- Changed early-exit behavior from logging a warning for weekend runs to cleanly returning a "skipped_no_arxiv" status, improving observability and preventing unnecessary resource consumption on non-operational days.


### 2026-04-12
- Adjusted ARIA's execution schedule from Tuesday–Saturday to Tuesday–Friday at 07:00 UTC to align with arXiv's actual submission announcement window (Monday–Thursday evenings ET), eliminating wasteful Saturday runs that yielded no new papers.
- Updated scheduler configuration and weekday skip logic in `runner.py` to exclude Saturday, Sunday, and Monday (weekdays 5, 6, 0) instead of only Sunday and Monday, reflecting the corrected operational window.
- Clarified documentation to explain that Friday evening arXiv submissions are batched into Monday's announcement and captured during Tuesday's processing cycle, improving transparency on the data availability timing.


### 2026-04-19
- Added budget guard to `core/analyst.py` and `core/reporter.py` with a $5.00 USD spend ceiling per session to prevent runaway API costs from a leaked Anthropic API key; `_charge()` function tracks token usage across Claude calls and raises `BudgetExceeded` to halt execution when limit is exceeded.
- Expanded `.gitignore` to exclude `.env.*`, `*.pem`, and `*.key` files to prevent accidental credential exposure beyond the base `.env` file.
- Created `SECURITY.md` documenting the threat model, secrets inventory, budget guard implementation, and incident response procedures for API key or LinkedIn cookie exposure.
- Added `tests/smoke_test.py` smoke test suite covering core imports, budget guard enforcement, cross-domain filtering, decision logic, and `.gitignore` coverage validation to gate deployments.


### 2026-05-05
- Extracted budget tracking logic into dedicated `BudgetGuard` class in new `core/budget_guard.py` module to enable reusable, testable spend enforcement across multiple callsites (analyst.py and reporter.py share a single guard instance).
- Replaced ad-hoc global `_session_spend_usd` counter and inline cost calculation with `BudgetGuard.record()` method, adding structured call history with timestamps and per-call cost breakdowns for operational visibility and debugging.
- Added `CallRecord` dataclass and `summary()` method to provide detailed spend audit trail (model, token counts, costs per call) for compliance and cost analysis.
- Improved pricing lookup robustness with case-insensitive model matching and fallback to Sonnet defaults, reducing risk of budget bypass due to model name mismatches.
- Refactored smoke tests to instantiate isolated `BudgetGuard` instances with test-specific limits, eliminating brittle global state mutation and enabling parallel test execution.


### 2026-05-05
- Established an 8-step regression safety protocol to prevent silent failures during AI-assisted development, requiring baseline smoke test verification before and after each change to catch breaking changes early.
- Created centralized configuration module (`core/config.py`) with single source of truth for environment settings, enabling future modules to safely read settings without duplicating `os.environ` calls across the codebase.
- Standardized code style in `core/analyst.py` (import ordering, whitespace cleanup) to improve maintainability and reduce merge conflicts during future refactoring.
- Documented ARIA's module dependency graph and cross-module impact analysis within the protocol to reduce risk of cascading failures when changing shared functions or constants.


### 2026-05-05
- Added interactive LinkedIn session persistence mechanism via `save_linkedin_session.py` to enable automated posting without hardcoded credentials, improving security posture by eliminating plaintext password storage.
- Implemented Playwright-based browser automation for one-time interactive login flow that captures authenticated session state (cookies/tokens) to `linkedin_session.json`, allowing subsequent posts to reuse valid sessions rather than re-authenticating.
- Added `scripts/linkedin_session.json` to `.gitignore` to prevent accidental commit of sensitive session tokens to version control.
- Designed session lifecycle management with ~2-year validity window and manual refresh trigger on expiration, reducing operational friction for long-running autonomous posting workflows.


---

## [0.1.0] â€” 2026-03-29

### Added
- `core/ingest.py` â€” arXiv API ingestion for cs.AI, cs.LG, q-bio.*, cs.RO categories
  - feedparser-based Atom feed parsing
  - 24-hour date filter
  - 3-retry exponential backoff on HTTP errors
- `core/store.py` â€” SQLite data layer
  - Tables: papers, reports, baselines
  - Upsert, baseline tracking, report persistence
- `core/analyst.py` â€” Claude API paper analysis
  - Batched analysis (10 papers/call) for token efficiency
  - Per-paper: novelty_score (0-10), themes, is_notable, rationale
  - Cross-domain paper identification
- `core/decider.py` â€” Autonomous 4-trigger anomaly detection
  - Volume Spike: paper count > 1.5x baseline mean
  - Cross-Domain Cluster: 3+ papers bridging multiple research domains
  - Novelty Burst: >30% papers score >= 7
  - Significance Surge: avg novelty > 1.3x baseline mean
- `core/reporter.py` â€” Intelligence brief generation via Claude API
  - Structured markdown brief: executive summary, key findings, emerging themes, notable papers table, analyst note
  - Fallback report when Claude API is unavailable
- `runner.py` â€” Main orchestrator
  - `--once` flag for single run
  - APScheduler daily cron (default 07:00 UTC, configurable with `--hour`)
  - Full pipeline: ingest â†’ store â†’ analyze â†’ decide â†’ report â†’ store
- `dashboard/app.py` â€” Flask dashboard
  - Routes: `/` (main), `/reports/<id>` (detail), `/api/papers`, `/api/reports`, `/api/stats`
- `dashboard/templates/index.html` â€” Newspaper-style academic UI
  - Live paper feed with novelty bars
  - Published reports with trigger tags
  - Live UTC clock, stat strip
- `dashboard/templates/report.html` â€” Full report detail page with markdown rendering
- `requirements.txt`, `.env.example`, `.gitignore`
- `CLAUDE.md`, `PROJECT_STATUS.md`, `DECISIONS.md`
- `docs/USER_MANUAL.md` â€” Full setup and operations guide
