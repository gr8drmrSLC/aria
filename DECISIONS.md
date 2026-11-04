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

---

## ADR-014: MemoryHigh/MemoryMax added to both services (2026-09-03)

ADR-008 accepted the shared-EC2 risk explicitly: "a misbehaving process on one
project could affect others — accepted given the personal-project nature of the
workloads." This is that revisit, prompted by an actual memory-exhaustion outage
on the shared box (investor repo's DECISIONS.md "EC2 memory-exhaustion outage") —
`investor.service`, `investor-b.service`, and `prediction-markets.service` all got
`MemoryHigh=`/`MemoryMax=` limits so a runaway process is killed within its own
cgroup instead of starving every other program on the box. ARIA's two services had
no equivalent, and no committed unit-file templates existed for either — deploy
config lived only on EC2, never in this repo.

Checked first whether ARIA is exposed to the same *root-cause* mechanism as the
other two (an unhandled exception on a network/DB call at process startup crashing
the whole service into a tight restart loop) — it is not, structurally. ADR-002
(SQLite instead of PostgreSQL) means there's no networked DB service to be briefly
unreachable at startup the way investor's/prediction-markets' Postgres containers
were. ADR-004 (APScheduler) means `runner.py`'s scheduled mode does no eager work
at process start — it just registers a daily job and blocks; the actual arXiv/
Claude network calls only happen once a day when that job fires, and an exception
there is caught by APScheduler's own job-error handling rather than crashing the
process. So this ADR is containment only, not a root-cause fix for a bug that
isn't present here — ARIA's existing architecture already avoided it.

Ceilings set from observed steady-state footprint (~60MB for `runner.py`, ~66MB
for `dashboard/app.py` — both far smaller than investor's or prediction-markets',
since neither loads an ML model or holds a large in-memory dataset):
`MemoryHigh=250M`, `MemoryMax=400M` for both services — roughly 4-6x baseline,
generous headroom for a larger paper batch or report without ever being able to
meaningfully threaten the box's total 3.7GB.

New `scripts/aria-runner.service` and `scripts/aria-dashboard.service` templates
added to the repo (didn't exist before) so the deployed EC2 units and source
control no longer diverge on this going forward. Also committed the
`dashboard/app.py` binding fix (`0.0.0.0` → `127.0.0.1`) that ADR-010 already
called the correct pattern and PROJECT_STATUS.md already recorded as fixed on
2026-05-04 — the code change had only ever been applied live on EC2, never
actually committed, a 4-month gap between documented and actual repo state.


---

## ADR-015: LinkedIn poster — persisted dedupe, refuse-on-missing-data, one scheduled task (2026-11-02)

The poster (`scripts/update_linkedin.py`, local-only/gitignored) failed or misbehaved in ways the
2026-11-02 analysis documented. Decisions:

1. **Posted-state is persisted and enforced in code.** `scripts/linkedin_posted.json` (gitignored)
   stores keys: `report:<id>` (daily), `weekly:<ISO week>`, `perf:<ISO week>`. A key already present
   is never posted again. A key is written only after the Post click succeeds. A corrupt state file
   makes the run abort (fail closed), not post. *Structural.*
   Cause: the old script posted `reports[0]` on every run, so any run with no new report re-posted the
   old one (report 62: six confirmed successful posts). *Correction, 2026-11-02:* this ADR first said
   ARIA writes reports only on anomalous days. The production database shows a report on 87 of 90
   ingest days, so the real reasons for "no new report" are the poster's Saturday runs and pipeline
   outages (e.g. no ingest 2026-08-11 to 2026-08-18, which covers the report-62 repeats).
   See `docs/ARIA_TREND_ANALYSIS_2026-11-02.md`.
2. **Refuse rather than print missing data.** No new report = no daily post. `/api/stats` returns
   `avg_novelty = 0` when there were no papers in the last 24h; that is "no data", so the performance
   post is skipped instead of printing "0.0 out of 10". *Structural.*
3. **Weekly counts are filtered by date in the script.** `/api/reports` ignores `?limit=` and always
   returns 20 rows, which produced "20 briefs this week" and "20 of 20 days". *Structural.*
4. **Exactly one scheduled task: `LinkedInARIA` (runs `run_linkedin_post.bat`).** `\ARIA\LinkedInPost`
   (ran Python directly with no logging, so its runs were invisible) and the dead
   `\ARIA\ReenableLinkedIn` were **disabled, not deleted**. `StartWhenAvailable` catch-up plus manual
   runs explain the off-hour entries in the log. `run_linkedin_post.bat` now exits with the script's
   real exit code (a trailing `echo` previously made every run report result 0) and writes
   `scripts/LINKEDIN_POST_FAILED.txt` on failure. *Structural for the exit code; the flag file is only
   an alert if someone looks at it, so true alerting (email/toast) remains open and is **soft**.*
5. **Wording: "AI-assisted", not "autonomous"** in the post templates, matching the owner's other
   projects. The About/Project profile text is out of scope here and unchanged.
6. **Composer selectors updated.** The editor is now a light-DOM ProseMirror `div[role=textbox]`
   with no `aria-label`; the old aria-label/shadow-DOM lookup matched nothing. "Next" now takes the
   last visible match to avoid Playwright strict-mode errors.

Rejected: keeping both tasks with a lock file (more moving parts than one task); moving the poster
into git (it holds personal profile text, which is why it is gitignored).


---

## ADR-016: Relative triggers and a history backtest (2026-11-02)

**Problem.** A replay of 90 days of stored history (`docs/ARIA_TREND_ANALYSIS_2026-11-02.md`) showed
the four absolute-threshold triggers produced a report on 87 of 90 ingest days (cross-domain 87,
novelty burst 87, volume spike 18, significance surge 0), contradicting the "only when unusual"
framing. Causes: (a) `_count_domains` matched on the shared `cs.` prefix, so about 98% of papers
counted as cross-domain (5.5% intended); (b) novelty scores are compressed (about 85% fall between
6 and 8), so "30% scoring >= 7" was met on 85 of 90 days; (c) the 1.3x significance rule needed a
mean near 9.0; (d) ingest is capped at 200, so the volume rule had almost no variation.

**Decision.**
1. Fix the domain matching bug (exact or parent match). Own commit, with a smoke check.
2. Make every trigger relative: a robust z-score (median, MAD) of one daily metric against the
   trailing 30 days, firing at z >= 1.5 (`ARIA_Z_THRESHOLD`). Metrics: paper count, cross-domain
   share, share of papers scoring >= 8, mean score. Cold start (under 10 days of history) keeps the
   old absolute rules. Days with under half the papers scored are excluded as analysis failures.
3. Choose z = 1.5 from a backtest, with a target of about one or two reports per week (owner
   approved this target). At z = 1.5 the replay reports on 32% of relative-mode runs, about 1.3 a
   week. At z = 1.25, 1.75 and 2.0 the rate is about 1.7, 1.0 and 0.8.
4. `tests/backtest_decider.py` replays any database snapshot read-only and can fail on a
   `--max-per-week` ceiling. It is *structural* only if run before threshold changes; the smoke
   test and CI do not run it (the production snapshot is not in git), so as wired today it is *soft*.
5. Public wording becomes "AI-assisted", "sampled", and "notable relative to the previous month";
   no claim of statistical unusualness. `docs/METHODS.md` records the description and limits.

**Consequences.** Report volume falls from about 87 in 7 months to roughly 1 to 2 a week. The
decision depends on history in the `papers` table (read through `Database.get_paper_rows`), so any
archive plan must keep scores and categories for old rows. Trigger names and `decide()` return keys
are unchanged (a `mode` key is added), so the reporter and dashboard need no change.

**Rejected.** Raising the absolute thresholds (fragile, drifts with the scoring model); a fixed
"one report per week" rule (ignores the data); correcting for multiple comparisons (reports would
become too rare for the one-to-two target). Deferred: embeddings, nearest-neighbour novelty and
stratified sampling.

---

## ADR-017: Claude-written weekly LinkedIn post with code-enforced checks (2026-11-03)

**Context.** Every template post repeated the same intro paragraph, and the 2026-11-03 weekly post
printed "cross-domain cluster, present in 3 of those 3 briefs", a figure produced by the ADR-016
prefix bug. Reach is low (median about 180 impressions), so repeated filler costs more than it earns.

**Decision.**
1. `core/postwriter.py` has Claude write the weekly post from the week's briefs (summary, key-finding
   headlines, exact paper titles). It is a Claude call wired to the budget guard (`_charge`), about
   $0.02 per attempt, at most 3 attempts per week.
2. Every draft is validated in code before it can be used: length, banned wording ("autonomous",
   hype words, trigger and anomaly language), any number not supplied in the facts or a title, at
   least one exact paper title named, and word-trigram similarity under 0.30 against the last 10
   posts. A failing draft is retried with the problems fed back; if none passes, nothing is posted.
   *Structural* for these checks (they run on every draft); *soft* for tone, which the prompt only
   asks for.
3. Trigger names and stats from reports created before 2026-11-03 are never shown (legacy bug).
   The same cutover applies to the daily-report template.
4. The "what ARIA is" sentence appears about once every 28 days, tracked in
   `scripts/linkedin_post_history.json`. A corrupt history fails closed.
5. Posting is automatic once the checks pass (owner decision 2026-11-04). An optional approval gate
   exists (`ARIA_POST_REQUIRE_APPROVAL=1`): the first run of a week saves a draft and writes
   `scripts/LINKEDIN_DRAFT_WAITING.txt`; `--approve` releases it, `--draft` regenerates it. With the
   gate off, the code checks above are the only review, and tone is only prompt-enforced (*soft*).
   A week with no briefs or no passing draft posts nothing and writes the same note file.
6. Daily-report and status posts use the same generator and checks (added 2026-11-04). A report older
   than 2 days is not posted, so history before the state file existed cannot be reposted.
7. The poster itself stays local and gitignored; the generator and its tests are in the repo.

**Consequences.** Weekly posts vary and stay grounded, at a cost of well under $1 a month. The daily
and system-stats templates are unchanged and still repeat the intro. Content is still model-written
text under the owner's name and now posts without review, so the code checks carry the safety.

**Rejected.** Rotating fixed templates (still repetitive); letting the model cite trigger stats
(the legacy data is unreliable). The owner chose auto-posting over keeping the approval gate on.

---

## ADR-018: Trend analysis and chart built for a skeptical reader (2026-11-04)

**Context.** The owner wants multi-field trend charts and a "trend since launch" post, and will not
publish anything a critical reader could call pseudoscience. Checking the data first found three
validity limits: (1) each daily run is the 200 newest arXiv submissions, spanning a median 8.7 hours
(3.6 to 14.3, 43 runs), so shares describe a daily slice, not arXiv; (2) novelty scores cluster at 5 to
7 and differ by at most about 0.5 between fields, which is within plausible scorer noise and is
unvalidated; (3) shares of a capped sample are compositional, so share-vs-share correlation (AI/ML vs
robotics -0.91) is arithmetic, not evidence.

**Decision.**
1. AI (cs.AI) and ML (cs.LG, stat.ML) are separate fields in the analysis, with robotics and bio, plus
   pairwise overlaps (AI+ML 15 percent of papers). The decider keeps its three-group definition, since
   splitting it would make AI+ML overlap fire the cross-domain trigger almost daily.
2. `scripts/trend_summary.py` is read-only, uses intervals across daily runs (not papers), excludes runs
   under 150 papers and weeks under 400, and reports a fixed list of nine tests with bootstrap intervals
   adjusted for nine tests. No share-vs-share correlation. First result on the snapshot: one of nine
   tests is supported (robotics share rising about 0.4 points a week), with autocorrelation making even
   that tentative; all novelty associations are not distinguishable from zero.
3. `scripts/chart_trends.py` plots weekly shares for four fields and four overlaps on separate
   single-axis panels, breaks lines across outage gaps, shows the run-to-run noise in the footnote, and
   carries the "sample, tags, abstracts only" caveats on the image. Palette validated with the dataviz
   validator. *Structural* for the caveats (drawn on every image); *soft* for how a reader interprets it.
4. Every post that uses this must state the sampling and abstracts-only limits; a code check for that
   wording in the generator is the next step. Full-text analysis is not planned: roughly 100 times the
   cost (an estimate) and it would not fix sampling or scorer validity. Limits are documented in
   `docs/METHODS.md`.

**Consequences.** Charts will show mostly flat, noisy lines, which is the honest picture. The monthly
post will lead with what is stable and what is not distinguishable from noise. Deploying the summary
to EC2 and the post type are still to do.

**Rejected.** 95 percent bands from 3 or 4 runs per week (so wide they hid the data); correlating
field shares with each other; a dual-axis chart; calling novelty differences between fields findings.

---

## ADR-019: Report tag counts and cross-listing from arXiv's own totals (2026-11-04)

**Context.** ARIA's daily sample covers about 9 hours of submissions (ADR-018), so it cannot say how
large a field is or how fast it grows, and a first single-month check showed that "all four fields are
growing rapidly" is not supported: Oct 2021 to Oct 2025, all arXiv +67 percent, cs.LG +65, q-bio +64,
cs.RO +134. The owner also clarified the scope: ARIA reports how papers are TAGGED, not what they say.

**Decision.**
1. The quarterly report states only tag counts and combinations (arXiv categories chosen by authors),
   never content, quality, performance or demand. Abstract-term lists and novelty scores are kept out of it.
2. `scripts/arxiv_counts.py` pulls monthly counts (total arXiv, AI, ML, robotics, bio, and their
   cross-listings) from arXiv's API totals back to 2020-01. It is read-only, one request at a time at
   least 3.5 s apart, retried, and cached after every query so a run resumes without refetching.
3. Hypotheses are declared before the data is read: (H1) each field grows faster than arXiv overall;
   (H2) the share of robotics papers also tagged AI or ML rises; (H3) the same for bio in aggregate.
   Each is reported whether it holds or not.
4. Growth is always stated relative to arXiv's total, since arXiv itself grew 67 percent.

**Consequences.** Conclusions rest on complete counts, not the sample; the sample is used only for
within-day detail. Bio subcategories are too small for monthly figures (q-bio.GN about 26 papers a
month), so bio is reported in aggregate, by quarter or year. Cross-listing reflects author and
moderator tagging behavior, which can change with arXiv policy; it is not evidence about the science.

**Rejected.** Using the ARIA sample for growth claims; reporting abstract-term prevalence in the
quarterly report (it is a content claim); claims about demand or performance (no data for them).
