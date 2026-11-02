# LinkedIn posting — follow-up to the 2026-11-02 analysis

Status: poster repaired locally; **not yet verified by a live post**. Fixing was un-tabled the same
day. No personal profile details in this file (public repo). See ADR-015 in `DECISIONS.md`.

## Confirmed against code, logs and the live system

| Finding | Result |
|---|---|
| No already-posted check | Confirmed. The script posted `reports[0]` every run and stored nothing. |
| Report re-posts | Confirmed, with a correction. Report 62 was loaded on 8 runs, but the 8/15 and 8/18 runs failed, so it was actually posted **6** times (8/7, 8/8, 8/12 x2, 8/13, 8/14). Reports 23, 26, 28, 43, 50, 54, 56, 57, 59, 60 were also loaded on consecutive runs. |
| Two scheduled tasks | Confirmed: `LinkedInARIA` (runs the `.bat`) and `\ARIA\LinkedInPost` (runs Python directly), both with catch-up enabled; `\ARIA\ReenableLinkedIn` is a dead April leftover. `LinkedInPost` wrote nothing to the log, so its runs were invisible. |
| Extra / odd-hour runs | **Not determinable.** Only the `.bat` writes headers to the log, so odd hours are `LinkedInARIA` catch-up or manual runs. The Task Scheduler history log is disabled on this machine, so the exact cause of each cannot be recovered. |
| Composer failure | Confirmed (54 editor, 9 "Next", 10 dashboard-unreachable errors; session still valid). Dashboard was reachable when checked, so the 10 errors look transient. |
| Why the editor failed | The composer is now a light-DOM ProseMirror `div[role=textbox]` with no `aria-label`; the script looked for an `aria-label` inside shadow roots. |
| Why "Next" failed | Playwright strict-mode violation when more than one button matched. On the inspection run only one matched, so it is intermittent. |
| "0.0 out of 10" | Not a calculation bug. `/api/stats` returns 0 when there are no papers in the last 24h, and the template printed it as a score. The 0.0 vs 6.8 disagreement is time-of-day dependent. |
| "20 briefs", "20 of 20 days" | Root cause found: `/api/reports` ignores `?limit=` and always returns 20; the script treated that as "this week". |
| "Baseline still building" | Hardcoded template text, never updated. |
| Task exit code | New finding: the `.bat` ended with an `echo`, so Task Scheduler recorded result 0 even when the log said FAILED. |

## Changed (2026-11-02)

- `update_linkedin.py` (local-only, gitignored): posted-state file with fail-closed dedupe; skip when
  there is no new report or the numbers are missing; weekly counts filtered by date; AI-assisted
  wording; editor and "Next" selectors updated. Tested offline with fake data (dedupe, empty,
  zero-novelty, week filtering, corrupt state); the repo smoke test still passes 17/17.
- `run_linkedin_post.bat`: exits with the real exit code and writes a failure flag file.
- Disabled (not deleted) `\ARIA\LinkedInPost` and `\ARIA\ReenableLinkedIn`. `LinkedInARIA` remains.
- One non-posting inspection of LinkedIn's composer was run (no text typed, Post never clicked,
  draft discarded on close).

## Still open

- **No live post since the fix.** The Post-button click and the state write are unexercised against
  LinkedIn. First scheduled run: Tue 2026-11-03 (a Tuesday post is the weekly type).
- **No real alerting.** The flag file only helps if someone looks. Email or toast needs a decision.
- **About/Project profile text** still says "autonomous"; out of scope here.
- `scripts/create_task.bat` still creates the disabled `ARIA\LinkedInPost` task; it should not be run.
- Another project's scheduled task, `LinkedInBuildWithAI`, runs its own poster daily; it is not part
  of this repo and was not changed.
- GitHub Pages feed last updated 2026-09-04; unclear if intentional.
- `docs/LINKEDIN_EC2_MIGRATION.md` (residential-proxy plan) is a proposal and conflicts with ADR-013.
- Low reach (median about 180 impressions) raises whether daily posting is worth it; the analysis
  suggested weekly with one human observation.
