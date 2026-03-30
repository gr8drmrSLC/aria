# ARIA — Architectural Decisions

## Why four anomaly triggers instead of one score
A single composite score would hide what's actually happening. Four independent triggers
let each one fire on its own signal and give human-readable explanations in the report.
The decider fires if ANY trigger activates (OR logic), making it sensitive enough to catch
meaningful signals while keeping each trigger's threshold conservative.

## Why SQLite instead of PostgreSQL
This is a single-node research tool processing ~200 papers/day. SQLite is sufficient,
eliminates infra complexity, and the entire database is a single file — easy to back up,
inspect with DB Browser, and delete when testing. Can migrate to PostgreSQL if this scales.

## Why Claude API for both analysis and reporting
Consistency: the same model that scores papers also writes the brief, so the report's
framing reflects the scoring criteria. Alternatives (separate embeddings model for scoring,
LLM only for reporting) add complexity without proven benefit at this scale.

## Why APScheduler instead of cron
APScheduler runs in-process and is portable across Linux and Windows (dev machine).
Cron is Linux-only and requires separate configuration. APScheduler can be swapped for
cron on EC2 by running `python runner.py --once` from a crontab line — no code changes needed.

## Why feedparser instead of the arxiv Python package
feedparser is lower-level and gives full control over the Atom feed parsing. The arxiv
package adds abstraction but also limitations on query flexibility. feedparser is also
more stable — less likely to break on arXiv API changes.

## Why Flask instead of FastAPI for the dashboard
The dashboard is read-only and low-traffic (personal demo tool). Flask is simpler,
has zero overhead for this use case, and the Jinja2 templates integrate cleanly with the
newspaper-style HTML without requiring a separate build step.

## Why newspaper/academic aesthetic for dashboard UI
ARIA is positioned as a research intelligence agent. A newspaper aesthetic signals
seriousness, signal over noise, and editorial judgment — which is exactly what ARIA is
doing. It differentiates the project from generic ML dashboards on LinkedIn.
