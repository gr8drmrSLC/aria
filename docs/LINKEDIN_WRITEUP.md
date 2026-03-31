# ARIA — LinkedIn Post + Profile Presentation

---

## Profile About Section — Who you are and what this represents

*This goes in the About section of your LinkedIn profile. Tone: honest, direct, no jargon. You are not a software engineer — you are someone who identifies problems, designs automated solutions using AI, and builds tools that keep working without you.*

---

I'm not a software engineer. I don't write code from scratch. What I do is design systems — I identify a problem, map out what an automated solution should do, and use AI tools to build it. The result is usually something that keeps running on its own long after the initial build.

ARIA is a good example. I wanted a way to monitor research across AI, machine learning, biology, and robotics without reading hundreds of papers a day. So I designed a system that does it automatically — it pulls every new submission from arXiv each morning, uses Claude AI to score each one for significance, and decides on its own whether what it found is worth writing a report about. No alerts telling it what to do. It just runs.

The same underlying pattern — monitor a data source, apply AI analysis, make an autonomous decision, produce an output — is something I've applied to options trading and prediction markets as well. The domain changes. The structure doesn't.

What I'm good at is seeing where that structure fits, defining what the system should decide and when, and building it in a way that doesn't require constant maintenance. The goal is always a tool that works while you're doing something else.

---

## Project Entry — ARIA (for LinkedIn Projects section)

*This goes under Projects on your profile. Keep it factual and grounded.*

**Project name:** ARIA — Autonomous Research Intelligence Agent

**Description:**
ARIA monitors the arXiv research database daily across artificial intelligence, machine learning, quantitative biology, and robotics. It uses the Claude API to score each new paper for novelty, tracks rolling baselines by category, and applies four independent anomaly triggers to decide autonomously whether the day's research activity is significant enough to publish an intelligence brief. When it decides yes, it writes one.

I designed this as a demonstration of a reusable pattern: any high-volume data source — research papers, market filings, pricing data, news feeds, job postings — can be monitored with the same architecture. The system ingests, analyzes, decides, and reports without ongoing human input.

Built with Python, the Anthropic Claude API, arXiv API, SQLite, Flask, and APScheduler. Runs on a daily schedule on AWS EC2.

**Link:** https://github.com/gr8drmrSLC/aria

---

## The honest framing — use this if anyone asks

If a recruiter, hiring manager, or engineer asks about your background, this is the accurate version:

*"I'm not a software engineer by training. I design automated systems and use AI to build them. I understand how these systems work at the architecture level — the data flow, the decision logic, the tradeoffs — but I'm not the person writing low-level code from memory. What I build tends to be production-ready in the sense that it runs continuously, handles errors, logs what it does, and doesn't need babysitting. ARIA is a fair representation of that."*

This is a defensible and genuinely interesting position. The people building the most useful AI tools right now are often not traditional engineers — they're people who understand a problem domain and know how to direct AI to solve it. That's a real skill and a growing one.

---

## What ARIA demonstrates as a reusable pattern

*Use this framing in conversations or posts to show the broader applicability:*

The core loop ARIA uses is:

1. **Ingest** — pull structured data from a live source on a schedule
2. **Analyze** — use an AI model to score or classify each item against defined criteria
3. **Decide** — compare results against a historical baseline and determine if action is warranted
4. **Act** — generate an output (report, alert, trade, email) only when the threshold is met

The same loop applies to:
- **Market research** — monitor competitor pricing pages, product releases, or review sites daily; flag when something changes materially
- **Investment signals** — monitor SEC filings, earnings transcripts, or news feeds; surface anomalies before the market prices them in
- **Hiring intelligence** — track job postings across target companies; detect when a company starts hiring aggressively in a new area
- **Regulatory monitoring** — watch agency comment periods, rule filings, or legislative trackers; alert when something relevant moves
- **Customer intelligence** — monitor review platforms or social signals for a product category; detect sentiment shifts early

The domain is a variable. The architecture is the same.

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
