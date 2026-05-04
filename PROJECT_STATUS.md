# ARIA — Project Status

**Last updated:** 2026-05-04
**Phase:** Live on EC2 — pipeline running, dashboard public, retrofit audit in progress

---

## Current state

ARIA is fully deployed and operational on EC2 (`3.139.164.142`, us-east-2).

- Pipeline runs Tue–Fri at 07:00 UTC under `aria-runner.service` (systemd, since 2026-04-23)
- Dashboard live at https://aria-agent.duckdns.org (nginx + Let's Encrypt)
- Dashboard binds to 127.0.0.1:5051 — nginx is the only public face (fixed 2026-05-04)
- `.env` permissions set to 600 on EC2 (fixed 2026-05-04)
- GitHub Actions exports static pages to `docs/` Mon–Fri at 08:30 UTC
- Weekly S3 backup running (Sundays 08:00 UTC via `scripts/backup_db.sh`)
- DuckDNS token moved from crontab to `.env`, wrapper script at `scripts/duckdns_update.sh`
- Retrofit audit started 2026-05-04 — security and framework gaps being closed

---

## What is working

- arXiv ingest (Tue–Fri, ~100–200 papers/day across cs.AI, cs.LG, q-bio.*, cs.RO)
- Claude analysis — novelty scoring, theme extraction, cross-domain detection
- Four anomaly triggers — Volume Spike, Cross-Domain, Novelty Burst, Significance Surge
- Intelligence brief generation when any trigger fires
- SQLite baseline tracking (30-day rolling per category)
- Flask dashboard — paper feed, report list, report detail, JSON API endpoints
- Static export to GitHub Pages via GitHub Actions
- Weekly database backup to S3

---

## What is not fully done

- PostgreSQL listening on `0.0.0.0:5432` — needs to be restricted to localhost (requires sudo)
- Budget guard is a module-level global — should be upgraded to `BudgetGuard` class
- No `BUDGET_POLICY.md`
- No `DEVELOPMENT_PROTOCOL.md`
- No centralized `core/config.py` — env loading scattered across modules
- No pyproject.toml or committed ruff/pre-commit config
- `smoke_test.py` covers imports and env only — no functional tests

---

## Open questions

- PostgreSQL fix: who has sudo access on EC2?
- Email or Slack notification when a report publishes?
- Dashboard authentication — open, acceptable for current demo phase
- Anthropic Console monthly spend cap — confirm $20/month is set

---

## EC2 services

```
aria-runner.service      active (running) since 2026-04-23
aria-dashboard.service   active (running), 127.0.0.1:5051
```

Crontab:
```
*/10 * * * *   investor healthcheck
0 10 * * *     investor integration tests
0 */6 * * *    scripts/duckdns_update.sh
0 8 * * 0      scripts/backup_db.sh (S3)
0 9 * * 2-5    aria silent failure check
15 9 * * 2-5   aria fallback check
```

---

## Next tasks (in order)

1. Fix PostgreSQL `listen_addresses = 'localhost'` (requires sudo)
2. Add `BUDGET_POLICY.md`
3. Upgrade budget guard from global variable to `BudgetGuard` class
4. Add `DEVELOPMENT_PROTOCOL.md`
5. Add `pyproject.toml` with ruff config + commit `.pre-commit-config.yaml`
6. Expand `smoke_test.py` to include functional checks
