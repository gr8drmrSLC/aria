# ARIA methods — how it works and what it can and cannot claim

Last reviewed: 2026-11-02 (ADR-016). Written so ARIA can be described accurately to someone who asks.

## In two sentences

ARIA pulls a sample of up to 200 new arXiv papers per run (Tuesday to Friday) in AI/ML, robotics and
quantitative biology, has the Claude API score each abstract for novelty and tag its themes, and
compares each day against its own previous 30 days. It files a short report on days that stand out,
which works out to roughly one or two a week.

## Pipeline

1. **Ingest.** `core/ingest.py` asks the arXiv API for the 200 most recently submitted papers in
   cs.AI, cs.LG, cs.RO and q-bio (sorted by submission time, newest first). Measured on 43 full runs,
   those 200 papers span a median of 8.7 hours of submission time (3.6 to 14.3), so each day is a
   slice of the day's submissions, not a random sample and not the whole feed. The slice is taken at
   about the same clock time each day, so day-to-day comparisons are consistent, but absolute shares
   (for example bio at about 3 percent) describe that slice, not arXiv.
2. **Score.** `core/analyst.py` asks Claude for a novelty score from 0 to 10 and 3 to 5 theme keywords
   per paper, in batches of 10. A budget guard caps session spend.
3. **Compare.** `core/decider.py` computes four daily metrics and a robust z-score for each against
   the trailing 30 days (median and MAD, so a single odd day does not distort the baseline).
4. **Report.** If any trigger reaches z >= 1.5, Claude drafts a brief; otherwise nothing is filed.
5. **Publish.** The dashboard and a static GitHub Pages export.

## The four triggers

| Trigger | Daily metric |
|---|---|
| Volume spike | paper count (capped at 200, so rarely fires) |
| Cross-domain cluster | share of papers in two or more monitored domains (AI/ML, bio, robotics) |
| Novelty burst | share of papers scoring 8 or above |
| Significance surge | mean novelty score |

With fewer than 10 days of history the old absolute thresholds are used (cold start).
Days where fewer than half the papers were scored are treated as analysis failures and excluded from
baselines, so a failed run cannot look like a quiet day.

## How the threshold was chosen

Replaying the stored history (`tests/backtest_decider.py`) at z = 1.5 gives a report on about 32
percent of runs, roughly 1.3 per week. That rate was a deliberate target (one or two a week), not a
statistical significance level. Calling a flagged day "statistically unusual" would overstate it;
"notable relative to the previous month" is accurate.

## History: why this was changed (ADR-016)

The original rules used fixed absolute thresholds and fired on almost every run (a report on 87 of
90 ingest days). A prefix-matching bug also made about 98 percent of papers count as cross-domain.
Details: `docs/ARIA_TREND_ANALYSIS_2026-11-02.md`.

## Known limits

- **Sampled data.** Volumes are artifacts of the 200-paper cap. Shares are meaningful only as
  "share of ARIA's daily slice", and changes over time are more trustworthy than levels.
- **Abstracts only.** Everything is read from titles and abstracts. Claims in a paper's body, results
  tables and methods are not checked. Full-text analysis would cost about 100 times more (an estimate)
  and is not planned; checking a few highlighted papers against full text is the intended next step.
- **Fields are tags.** AI, ML, robotics and bio mean arXiv category tags authors chose, not industries.
- **Model-assigned scores.** Novelty scores are the model's opinion, compressed into roughly 6 to 8,
  and can drift if the model or prompt changes. They are not validated against citations or experts.
- **Free-text themes** are not normalized ("llms" vs "large language models").
- **Pipeline gaps.** 34 expected run days have no ingest (outages), which weakens the baseline in
  those weeks. Causes are undiagnosed.
- **Unscored papers.** Some days have papers that were never scored; those days are excluded.
- **No external validation.** ARIA has not been checked against a ground truth of important papers.
- **Multiple triggers** raise the chance that some trigger fires on a normal day; at z = 1.5 that is
  accepted, not corrected for.

## Trend analysis (ADR-018)

`scripts/trend_summary.py` (read-only on the database) produces weekly and monthly shares for AI, ML,
robotics and bio and their overlaps, with intervals taken across daily runs. A fixed list of nine
exploratory tests (five trends, four associations with mean novelty) is reported with bootstrap
intervals adjusted for nine tests. Weekly series are autocorrelated, so the intervals are likely too
narrow. Shares are not correlated with each other: with a capped sample they compete for the same
slots, which produces a strong negative correlation by arithmetic (about -0.9 for AI/ML against
robotics) that means nothing. Nothing here establishes cause.

## Possible future work (not built)

Embedding-based topic clustering, nearest-neighbour novelty against ARIA's own history, stratified
sampling across categories, re-scoring a sample to measure scoring noise, and change-point detection.
