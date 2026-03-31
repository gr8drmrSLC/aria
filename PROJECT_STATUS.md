# ARIA — Project Status

**Last updated:** 2026-03-30
**Phase:** 1 complete — local validated, awaiting Anthropic credits to go fully live

## Current state
- All 23 files built, linted, committed, pushed to https://github.com/gr8drmrSLC/aria
- ruff pre-commit hook live (auto-fix + AI CHANGELOG entries via shared/changelog_ai.py)
- python-dotenv installed — .env loads automatically on runner.py and dashboard/app.py startup
- .env populated with ANTHROPIC_API_KEY (from investor project)
- arXiv ingest confirmed working (15 papers fetched in test run — rate limited during dev, clears overnight)
- Anthropic API key confirmed loading correctly — account needs credits before Claude analysis runs
- Today is Sunday — no new arXiv submissions; first real run will be Monday

## Blocking item
**Add Anthropic credits** — console.anthropic.com → Plans & Billing
Account balance is zero. Without credits, analyst.py and reporter.py will fail.
The fallback report path handles it gracefully but no AI analysis will occur.

## Next steps
1. Add Anthropic credits (blocking everything else)
2. Monday: `python runner.py --once` — first real pipeline run with new papers
3. `python dashboard/app.py` — verify UI at localhost:5050 with real data
4. Run 2-3 days to build baseline data (Volume Spike + Significance Surge triggers need 30-day history)
5. EC2 deployment — see docs/USER_MANUAL.md for systemd service setup
6. LinkedIn post — see docs/LINKEDIN_WRITEUP.md (3 post options + screenshot checklist)

## Open questions
- Share EC2 with job-search bot, or separate t3.micro?
- Dashboard public-facing or localhost tunnel for LinkedIn demo?
- Add email/Slack notification when a report publishes?

## Known gaps
- No test suite yet
- No dashboard authentication (fine for demo)
