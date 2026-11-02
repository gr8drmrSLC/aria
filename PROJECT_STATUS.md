# ARIA — Project Status

**Last updated:** 2026-11-02
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

## Decision logic — changed 2026-11-02 (ADR-016), not yet deployed to EC2

- Replay of history showed the old triggers reported on 87 of 90 days. Cross-domain prefix bug fixed
  (commit 6519d11); triggers are now relative (robust z >= 1.5 vs trailing 30 days), about 1.3 reports
  per week in backtest. See `docs/METHODS.md`, `docs/ARIA_TREND_ANALYSIS_2026-11-02.md`.
- Local repo only: needs push, `git pull` on EC2 and a service restart. First production run after
  deploy will use relative mode only if at least 10 days of history exist (they do).
- Known gaps: 34 expected run days have no ingest (undiagnosed outages); some papers unscored.

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

## LinkedIn posting pipeline — repaired 2026-11-02, awaiting first live run

- `scripts/update_linkedin.py` — posts research findings (gitignored, local-only, manual deploy)
- `scripts/run_linkedin_post.bat` — the only scheduled entry point; exits with the script's real exit code
- Windows Task Scheduler: **`LinkedInARIA` only** (Tue–Sat 9 AM, catch-up on). `\ARIA\LinkedInPost` and
  `\ARIA\ReenableLinkedIn` are **disabled** (not deleted).
- Posted-state: `scripts/linkedin_posted.json` (gitignored). Duplicates are refused in code (ADR-015).
- Failures: `scripts/linkedin_post.log` plus `scripts/LINKEDIN_POST_FAILED.txt` (flag, cleared on success)
- Posting runs from Windows, not EC2 (ADR-013). A residential-proxy EC2 plan exists in
  `docs/LINKEDIN_EC2_MIGRATION.md` and is only a proposal.
- Was failing from 2026-08-15 (last logged success 2026-08-14). Details: `docs/LINKEDIN_POSTING_ANALYSIS_2026-11-02.md`
- **Not yet verified live**: the editor and "Next" fixes were checked against LinkedIn's composer with a
  non-posting inspection, but the Post click and state write have not run against LinkedIn since the fix.

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

1. Watch the next scheduled LinkedIn run (Tue 2026-11-03): confirm a post appears and `linkedin_posted.json` gains a key
2. Decide on a real failure alert (email/toast); the flag file is soft
3. Session renewal — re-run `scripts/save_linkedin_session.py` if posting fails with a login error
4. Confirm the $20/month Anthropic Console spend cap is set
5. Decide whether the stale GitHub Pages feed (last update 2026-09-04) is intentional
