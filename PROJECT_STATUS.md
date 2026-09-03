# ARIA — Project Status

**Last updated:** 2026-09-03
**Phase:** Live on EC2 — pipeline running, dashboard public, retrofit audit in progress

---

## Current state

ARIA is fully deployed and operational on EC2 (`3.139.164.142`, us-east-2).

- Pipeline runs Tue–Fri at 07:00 UTC under `aria-runner.service` (systemd, since 2026-04-23)
- Dashboard live at https://aria-agent.duckdns.org (nginx + Let's Encrypt)
- Dashboard binds to 127.0.0.1:5051 — nginx is the only public face (fixed 2026-05-04;
  the `dashboard/app.py` code change itself had only ever been applied live on EC2 and
  was finally committed 2026-09-03 — see DECISIONS.md ADR-014)
- `.env` permissions set to 600 on EC2 (fixed 2026-05-04)
- `MemoryHigh=250M`/`MemoryMax=400M` added to both `aria-runner.service` and
  `aria-dashboard.service` (2026-09-03, ADR-014) — new
  `scripts/aria-runner.service`/`scripts/aria-dashboard.service` templates added to
  the repo, which had none before (deploy config previously lived only on EC2).
  Confirmed ARIA isn't exposed to the memory-exhaustion mechanism that hit investor/
  prediction-markets on this same box (no networked DB, no eager startup work) — see
  ADR-014 for the full reasoning.
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

## LinkedIn posting pipeline — active

- `scripts/update_linkedin.py` — posts live research findings (gitignored, manual deploy to EC2)
- `scripts/save_linkedin_session.py` — one-time interactive session creator
- `scripts/run_linkedin_post.bat` — Windows Task Scheduler wrapper
- `scripts/setup_linkedin_task.ps1` — creates `LinkedInARIA` scheduled task
- `scripts/linkedin_session.json` — local session file (gitignored, 600 permissions)
- Windows Task Scheduler task `LinkedInARIA` — Tue–Sat 9 AM, catch-up enabled
- Posts live ARIA research findings using public dashboard API (`aria-agent.duckdns.org`)
- **Note**: posting runs from Windows, not EC2 — LinkedIn blocks AWS datacenter IPs for browser automation

---

## Retrofit audit — complete (2026-05-05)

All items from the RETROFIT_GUIDE.md checklist are done:
- [x] Secrets scan — CLEAN (32-commit history)
- [x] .gitignore coverage verified
- [x] SECURITY.md — full rewrite with threat model, EC2 section, per-secret incident response
- [x] CLAUDE.md — 8-step protocol, session protocols, Wall Protocol, budget guard rule
- [x] .env.example — all vars documented including AWS, DuckDNS, EC2
- [x] PROJECT_STATUS.md — reflects live EC2 reality
- [x] DECISIONS.md — ADR-008 through ADR-013 backfilled
- [x] BUDGET_POLICY.md — spend limits, daily cost estimate, model selection
- [x] DuckDNS token moved from crontab to .env
- [x] .env permissions 600 on EC2
- [x] Dashboard bound to 127.0.0.1 (fixed)
- [x] PostgreSQL locked to localhost (Docker port binding)
- [x] Budget guard upgraded to BudgetGuard class
- [x] core/config.py — centralized settings
- [x] pyproject.toml + ruff config
- [x] scripts/pre-commit-hook.sh committed
- [x] DEVELOPMENT_PROTOCOL.md
- [x] smoke_test.py 11 → 17 checks

---

## Next tasks

1. Session renewal — LinkedIn session expires ~2 years; re-run `scripts/save_linkedin_session.py` if posting fails
2. PostgreSQL on EC2 confirmed localhost-only via Docker port binding (fixed); no further action needed
3. No other open items
