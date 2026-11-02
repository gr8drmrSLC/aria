# LinkedIn posting analysis — 2026-11-02

Status: analysis only. Fixing the poster is **tabled** (decision 2026-11-02). Nothing in this
file has been acted on. This repo is public, so this file covers the poster only: no personal
profile details, no names.

## Summary

The LinkedIn poster (`scripts/update_linkedin.py`) has been failing for roughly 11 weeks.
Before it broke it also produced duplicate and low-value posts. Both problems are in the
poster, not in ARIA's analysis pipeline.

## What the log shows (`scripts/linkedin_post.log`)

- Last run logged as SUCCESS: Fri 2026-08-14. Last post seen on the feed used 2026-08-07 data.
- Every failed run since at least 2026-09-26 **logs in successfully**: it lands on
  `linkedin.com/feed/`. The saved session (`linkedin_session.json`, dated 2026-05-05) is still
  valid. **Expired cookies are not the cause.**
- Failure point: after the composer opens and both screenshots upload, the script cannot focus
  the text box. Error counts across the whole log:
  - 54x `Could not focus the shadow DOM editor` (likely a LinkedIn composer markup change)
  - 10x `Dashboard not reachable at aria-agent.duckdns.org`
  - 9x `Next button not found` (the locator matched 2 or 3 buttons instead of 1)
- Two scheduled tasks appear to exist (`LinkedInARIA` daily 9 AM per PROJECT_STATUS.md, and
  `ARIA\LinkedInPost` at 18:00 Tue-Sat per `scripts/create_task.bat`). Some days show two runs.
  Whether this caused the duplicates is **unconfirmed**.

## What the posts showed (40 posts, 2026-07-07 to 2026-08-08)

- 31 daily-report posts but only 16 distinct report days, so about half were duplicates. The
  2026-08-07 report was posted 7 times, and the 2026-07-28 report 3 times.
- No record of what was already posted was found in `update_linkedin.py`, so a rerun cannot
  skip a report that already went out.
- Reach: about 12,200 impressions in total, median about 180 per post. Reactions were 0-5 per
  post. Early-July posts reached the most (up to 1,111); August posts mostly 56-251.
- Content defects:
  - 4 of 5 "system performance" posts say `average novelty score ... 0.0 out of 10`
    (looks like a calculation bug).
  - Each says the 30-day baseline is "still building", unchanged from July through August.
  - Weekly posts say the cross-domain signal "fired 20 out of 20 reporting days", which
    contradicts "publishes only when statistically unusual".
  - Weekly posts say "20 briefs this week", but the pipeline runs 5 days a week, so the label
    looks wrong.

## Recommended fixes (tabled)

Structural (enforced by code):
1. Persist posted-state (date + post type) and refuse to post a duplicate.
2. Refuse to publish a report with a 0.0 novelty score or a missing baseline.
3. Alert (email or similar) when a run fails, instead of only logging.
4. Replace the shadow-DOM editor focus step and make the "Next" locator unambiguous.
5. Run exactly one scheduled task.

Soft (depends on someone remembering):
- Checking the log or feed periodically.

Content direction: weekly instead of daily, with one human observation per post; a monthly
build-log note on what changed in ARIA.

## Open questions

- Does the posted content still need the "published autonomously" framing? (Other repos use
  "AI-assisted" per their own ADRs.)
- Is the GitHub Pages feed intentionally stopped? Last update commit is 2026-09-04.
