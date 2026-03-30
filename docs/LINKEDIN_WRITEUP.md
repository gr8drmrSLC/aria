# ARIA — LinkedIn Post + Profile Presentation

---

## Option A: Project announcement post (conversational)

---

I built an agent that reads the entire arXiv AI/ML/biology/robotics feed every morning and
decides — without being asked — whether what it found is worth telling you about.

It's called ARIA (Autonomous Research Intelligence Agent).

Here's what it does autonomously:

- Pulls every new paper from cs.AI, cs.LG, q-bio, and cs.RO via the arXiv API
- Asks Claude to score each paper for novelty (0–10) and identify its core themes
- Runs four independent anomaly detectors against a rolling 30-day baseline:
  → Volume Spike (is today's submission count unusually high?)
  → Cross-Domain Cluster (are AI and biology papers converging on the same idea?)
  → Novelty Burst (is an unusual fraction of papers scoring high?)
  → Significance Surge (is the average novelty score above baseline?)
- If any trigger fires, Claude drafts a structured intelligence brief — executive summary,
  key findings, emerging themes, notable papers table, analyst assessment
- Everything lands on a newspaper-style dashboard with a live paper feed and published reports

No daily prompt from me. No manual curation. ARIA just runs at 07:00 UTC and decides.

The interesting engineering challenge wasn't the API calls — it was the decider layer.
How do you give a system principled criteria for "this is significant" without hardcoding
it to a specific threshold? The answer here is: baseline relative thresholds. ARIA learns
what "normal" looks like for each category over 30 days, then flags deviations from that
normal. The first month is bootstrapping. After that, it has its own sense of what's routine.

Built with: Python, Anthropic Claude API, arXiv API, Flask, SQLite, APScheduler.

GitHub: https://github.com/gr8drmrSLC/aria

---

## Option B: Short-form post (max engagement)

---

I built ARIA — an AI agent that monitors 200+ arXiv papers/day across AI, ML, biology,
and robotics and autonomously decides when something is significant enough to report.

Four anomaly triggers. Baseline-relative thresholds. No human in the loop.

When it fires, Claude drafts a full intelligence brief. Newspaper-style dashboard.
Runs on a daily schedule on EC2.

Built with Claude API + Python. Full source on GitHub.

[screenshot of dashboard]

---

## Option C: Technical deep-dive post (for engineers)

---

**How I gave an AI agent a sense of "normal"**

ARIA monitors arXiv daily. But the hard problem isn't fetching papers — it's deciding
whether today's papers are *actually notable* or just noise.

My solution: four independent anomaly triggers, each comparing today against a 30-day
rolling baseline stored per category per day.

**Volume Spike** — if today's paper count exceeds the category's 30-day mean by 1.5x,
something unusual is happening in terms of publishing activity.

**Cross-Domain Cluster** — if 3+ papers simultaneously touch AI/ML AND biology AND/OR
robotics, that's a potential convergence signal worth surfacing.

**Novelty Burst** — if >30% of papers score ≥7/10 on Claude's novelty assessment,
that's a statistically unusual concentration of significant work.

**Significance Surge** — if the average novelty score for the day exceeds the 30-day
baseline average by 1.3x, the entire day's research is running hotter than normal.

Each trigger is independent. ANY trigger publishes a report. This makes the system
sensitive to different *kinds* of significance — not just one.

The thresholds are all configurable. The system bootstraps over the first 30 days.
After that, it has its own learned sense of what "normal" looks like.

Stack: Python, Claude API (claude-sonnet-4-6), arXiv Atom feed (feedparser),
SQLite, Flask, APScheduler.

Source: https://github.com/gr8drmrSLC/aria

---

## Featured Project section (LinkedIn profile)

**Title:** ARIA — Autonomous Research Intelligence Agent

**Description:**
An autonomous AI agent that monitors the arXiv research feed daily across AI, machine learning,
biology, and robotics. ARIA analyzes each paper with Claude, maintains rolling baselines by
category, and fires four independent anomaly triggers to decide — without human prompting —
when research activity is significant enough to publish an intelligence brief.

Built with: Python · Anthropic Claude API · arXiv API · SQLite · Flask · APScheduler

[GitHub link] [Dashboard screenshot]

---

## Skills to tag on the post
- Artificial Intelligence
- Autonomous Agents
- Python
- Anthropic Claude
- API Development
- Machine Learning

---

## Screenshot checklist (take these before posting)
1. Dashboard main page — masthead + trigger-tagged report cards + paper feed with novelty bars
2. A full intelligence brief (report detail page) showing the structured markdown output
3. Terminal output of a successful `python runner.py --once` run (clean log lines)
4. (Optional) GitHub repo page showing the file structure

---

## Timing recommendation
Post on a Tuesday or Wednesday morning (US Eastern) for maximum LinkedIn reach.
Tag the post with the screenshots — posts with images get 3-5x the organic reach.
