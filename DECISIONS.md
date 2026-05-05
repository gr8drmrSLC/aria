# ARIA — Architectural Decisions

---

## ADR-001: Four anomaly triggers instead of one composite score

A single composite score would hide what's actually happening. Four independent triggers
let each one fire on its own signal and give human-readable explanations in the report.
The decider fires if ANY trigger activates (OR logic), making it sensitive enough to catch
meaningful signals while keeping each trigger's threshold conservative.

---

## ADR-002: SQLite instead of PostgreSQL

This is a single-node research tool processing ~200 papers/day. SQLite is sufficient,
eliminates infra complexity, and the entire database is a single file — easy to back up,
inspect with DB Browser, and delete when testing. Can migrate to PostgreSQL if this scales.

---

## ADR-003: Claude API for both analysis and reporting

Consistency: the same model that scores papers also writes the brief, so the report's
framing reflects the scoring criteria. Alternatives (separate embeddings model for scoring,
LLM only for reporting) add complexity without proven benefit at this scale.

---

## ADR-004: APScheduler instead of cron for the runner

APScheduler runs in-process and is portable across Linux and Windows (dev machine).
Cron is Linux-only and requires separate configuration. APScheduler can be swapped for
cron on EC2 by running `python runner.py --once` from a crontab line — no code changes needed.

---

## ADR-005: feedparser instead of the arxiv Python package

feedparser is lower-level and gives full control over the Atom feed parsing. The arxiv
package adds abstraction but also limitations on query flexibility. feedparser is also
more stable — less likely to break on arXiv API changes.

---

## ADR-006: Flask instead of FastAPI for the dashboard

The dashboard is read-only and low-traffic (personal demo tool). Flask is simpler,
has zero overhead for this use case, and the Jinja2 templates integrate cleanly with the
newspaper-style HTML without requiring a separate build step.

---

## ADR-007: Newspaper/academic aesthetic for dashboard UI

ARIA is positioned as a research intelligence agent. A newspaper aesthetic signals
seriousness, signal over noise, and editorial judgment — which is exactly what ARIA is
doing. It differentiates the project from generic ML dashboards on LinkedIn.

---

## ADR-008: Shared EC2 instead of dedicated t3.micro per project

ARIA, investor, prediction-markets, and job-search all run on the same EC2 instance
(`3.139.164.142`, us-east-2). Each project has its own virtualenv and systemd service.
Rationale: all bots are I/O-bound, not CPU-bound — total compute demand is light.
One instance costs ~$8–10/month vs. $32–40/month for four. Risk: a misbehaving process
on one project could affect others — accepted given the personal-project nature of the
workloads. Revisit if any project goes to production use.

---

## ADR-009: DuckDNS for DNS instead of Route 53 or Elastic IP

DuckDNS is free, simple, and sufficient for a personal demo. Route 53 costs ~$0.50/month
per zone plus query fees. Elastic IP on EC2 costs ~$3.60/month when unattached.
DuckDNS updates every 6 hours via `scripts/duckdns_update.sh` to handle EC2 IP changes
on restart. Tradeoff: DuckDNS subdomains look less professional than a custom domain —
acceptable for a portfolio demo, not for a client-facing product.

---

## ADR-010: nginx + Let's Encrypt instead of direct Flask HTTPS

Flask's built-in dev server is not production-safe. nginx handles HTTPS termination,
HTTP→HTTPS redirect, and proxies to Flask on localhost:5051. Let's Encrypt provides
free TLS certificates; Certbot manages auto-renewal. Flask binds to 127.0.0.1 only —
not reachable directly from the internet. This is the correct single-node Flask pattern.

---

## ADR-011: systemd instead of screen/nohup for service management

systemd provides automatic restart on failure, structured logging via journald, boot-time
startup, and dependency ordering. screen and nohup provide none of these. Cost: one service
unit file per process — acceptable given the benefits. See `docs/USER_MANUAL.md`.

---

## ADR-013: LinkedIn posting runs from Windows, not EC2 (2026-05-05)

LinkedIn actively blocks AWS datacenter IPs for Playwright browser automation — sessions
created on a residential machine are immediately rejected when used from an EC2 IP, even
with identical user-agent strings. Confirmed in live testing: the first request from EC2
redirected to `uas/login` regardless of session validity.

Posting runs from Windows Task Scheduler (`LinkedInARIA`, Tue–Sat 9 AM) using the same
Playwright session and residential IP that created it. The script calls the public
`aria-agent.duckdns.org` dashboard API for live content, so the Windows machine needs
no local ARIA install. EC2 handles pipeline, dashboard, and data — Windows handles posting.

**Rejected alternatives**: Xvfb virtual display on EC2 (complex, still an EC2 IP);
LinkedIn API with OAuth (requires app approval); running headless with a proxy IP (fragile).

---

## ADR-012: DuckDNS token moved from crontab to .env (2026-05-04)

The DuckDNS update token was previously hardcoded in the crontab. Crontab is readable
by anyone with shell access and is not covered by .gitignore. Moved to `~/aria/.env`
(permissions 600) and referenced via `scripts/duckdns_update.sh`. Rule: no secrets in
crontab, systemd unit files, or shell history. Secrets live in .env only.
