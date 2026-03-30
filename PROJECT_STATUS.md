# ARIA — Project Status

**Last updated:** 2026-03-29
**Phase:** 1 — Initial build complete, not yet deployed

## Current state
- All core modules written: ingest, store, analyst, decider, reporter, runner
- Dashboard built: Flask app + newspaper-style UI
- GitHub repo: pending (gr8drmrSLC/aria)
- EC2 deployment: not started
- LinkedIn presentation: not started

## Next steps
1. Push to GitHub (gr8drmrSLC/aria, public)
2. Set up EC2 instance (can share with job-search bot or use separate t3.micro)
3. Add .env with ANTHROPIC_API_KEY and run `python runner.py --once` to validate pipeline
4. Verify SQLite creates correctly, papers ingest, Claude analysis runs
5. Start Flask dashboard and confirm UI renders
6. Run 2-3 days of pipeline to build baseline data (needed for anomaly triggers)
7. LinkedIn post with project write-up

## Open questions
- Share EC2 with job-search bot, or separate instance?
- Should dashboard be public-facing or private (localhost tunnel for demo)?
- Add email/Slack notification when a report is published?

## Known gaps
- No authentication on dashboard (fine for demo, needed if public-facing)
- store.py authors/categories stored as JSON strings — need to deserialize on read
- No test suite yet
