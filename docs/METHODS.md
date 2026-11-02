# ARIA methods — how it works and what it can and cannot claim

Last reviewed: 2026-11-02 (ADR-016). Written so ARIA can be described accurately to someone who asks.

## In two sentences

ARIA pulls a sample of up to 200 new arXiv papers per run (Tuesday to Friday) in AI/ML, robotics and
quantitative biology, has the Claude API score each abstract for novelty and tag its themes, and
compares each day against its own previous 30 days. It files a short report on days that stand out,
which works out to roughly one or two a week.

## Pipeline

1. **Ingest.** `core/ingest.py` fetches up to 200 papers from the arXiv API. This is a sample, not
   the whole feed: it is dominated by cs.LG and cs.AI, and quantitative biology is about 4 percent.
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

- **Sampled data.** Volumes are artifacts of the 200-paper cap; shares and rates are meaningful.
- **Model-assigned scores.** Novelty scores are the model's opinion, compressed into roughly 6 to 8,
  and can drift if the model or prompt changes. They are not validated against citations or experts.
- **Free-text themes** are not normalized ("llms" vs "large language models").
- **Pipeline gaps.** 34 expected run days have no ingest (outages), which weakens the baseline in
  those weeks. Causes are undiagnosed.
- **Unscored papers.** Some days have papers that were never scored; those days are excluded.
- **No external validation.** ARIA has not been checked against a ground truth of important papers.
- **Multiple triggers** raise the chance that some trigger fires on a normal day; at z = 1.5 that is
  accepted, not corrected for.

## Possible future work (not built)

Embedding-based topic clustering, nearest-neighbour novelty against ARIA's own history, stratified
sampling across categories, re-scoring a sample to measure scoring noise, and change-point detection.
