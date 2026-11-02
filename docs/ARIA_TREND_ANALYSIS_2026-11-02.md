# ARIA trend analysis, first pass — 2026-11-02

Source: read-only snapshot of the production database taken 2026-11-02 (checksum-verified copy,
gitignored). Covers ingests from 2026-03-31 to 2026-10-30. Counts are of a **sampled** feed (see
Caveats). No personal details (public repo).

## Headline findings

1. **ARIA reports almost every day, so its "anomaly" triggers are not selective.** A report exists
   for 87 of 90 ingest days. Cross-domain cluster fired on 87 of 87 reports, novelty burst on 87 of
   87, volume spike on 18. Public wording such as "it only writes a report when the day looks
   unusual" and "when nothing stands out, it stays quiet" is not supported by this data. The
   post wording should be corrected, and the trigger thresholds are a design question (see below).
2. **The pipeline has had outages.** 34 expected Tue-Fri days have no ingest. Longest gaps:
   2026-09-15 to 09-25 (7 days), 2026-08-11 to 08-18 (5), 2026-08-25 to 09-01 (5). Causes are not
   diagnosed. This also explains the August paper-count dip and the report-62 repeats.
3. **Rising themes, April-May to September-October (per 1,000 papers):** robot learning 3.3 to
   13.1; world models 7.6 to 17.0; robot manipulation 5.2 to 11.6; vision-language-action models
   7.4 to 14.2; coding agents 2.0 to 5.4; dexterous manipulation 2.2 to 5.6; test-time adaptation
   2.0 to 6.0; diffusion language models 1.7 to 4.3.
4. **Falling themes:** deep reinforcement learning 5.0 to 1.3; "llms" 10.0 to 4.1 (partly
   vocabulary: "large language models" and "llm agents" persist); LLM fine-tuning 7.8 to 3.0; RAG,
   RLHF, data augmentation, edge computing all fell.
5. **Robotics is the clearest structural shift in category mix:** cs.RO primary share went from
   8-11 percent (April-May) to 14-17 percent (June-October). cs.AI rose from 17 to 18-24 percent.
6. **Novelty scores are nearly flat:** monthly average 6.84-6.99; the share scoring 8 or higher
   crept from 8 to 12 percent. Scores cluster tightly, so they discriminate poorly between days.
7. **Top themes overall:** reinforcement learning, LLM agents, vision-language models, benchmark,
   diffusion models, multi-agent systems, graph neural networks.

## Caveats

- **Sampled, not complete.** Runs ingest about 200 papers (41 of 90 days are exactly 200).
  Volume trends are artifacts; shares and theme rates per 1,000 papers are the meaningful measures.
- **Unscored papers:** 197 in April, 280 in June, 482 in October (16 percent of that month). The
  cause is unexamined; run failures or the budget guard are plausible but unconfirmed.
- **Free-text themes are not normalized** ("llms" vs "large language models"), which exaggerates
  some rises and falls. A normalization pass is needed before publishing specific numbers.
- **Model-assigned scores** can drift with model or prompt changes.
- The rising/falling lists use a minimum of 25 mentions across the two windows; small counts can
  still be noisy (for example 9 to 25).

## Implications

- Weekly posts can be built on real, specific findings (a rising theme, a category shift) instead of
  a fixed intro paragraph.
- The anomaly claim needs either honest wording or tighter trigger thresholds; this is a decision for
  the owner, not changed here.
- Pipeline reliability (the gaps) is a separate open item.

## Addendum: why the triggers always fire (code read + backtest on the same snapshot)

Read `core/decider.py`, `core/analyst.py` and `core/ingest.py`, then replayed the history.

| Trigger | Finding |
|---|---|
| Cross-domain | **Bug.** The prefix test `cat.startswith(d_cat.split(".")[0] + ".")` turns `cs.RO` and `cs.AI` into the prefix `cs.`, so any `cs.*` paper counts as both "ai_ml" and "robotics". A lone `cs.CV` paper registers two domains. 97.7 percent of papers "bridge" domains under the current logic versus 5.5 percent under the intended logic. Even with the bug fixed, the rule is an absolute count of 3, and the intended logic yields about 10 per day (3 to 22), so it would still fire every day. |
| Novelty burst | Absolute rule (30 percent of papers at 7 or higher). Model scores are compressed: 6 to 8 holds about 85 percent of papers and 53 percent score 7 or higher, so the rule fired on 85 of 90 days. |
| Significance surge | Needs the day's average to be 1.3 times the baseline (about 9.0), when daily averages sit near 6.9. Effectively impossible; never fired. |
| Volume spike | Ingest is capped at 200 papers per run, so count can barely vary; the 18 firings likely come from low-count baseline days after outages. |

Only the two baseline-relative triggers are designed correctly, and neither can fire as configured.

Backtest of a relative alternative (z-score of each day versus its trailing 30 days, threshold 2):
high-novelty share fires on 3 of 90 days, cross-domain count on 10, average score on 3, any of the
three on 13 of 90 (about 14 percent). This is a sketch, not a tuned model.

Other findings: q-bio papers are 632 of 16,064 (4 percent), so the fixed 200-paper sample is dominated
by cs.LG and cs.AI. Days with unscored papers show a 0 percent high-novelty share, which would cause
false drops in any relative detector unless unscored days are excluded.
