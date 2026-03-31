# ARIA — System Architecture

This document describes the technical design of ARIA for engineers who want to
understand the decision-making logic, data flow, and implementation choices.

---

## System overview

ARIA is a five-stage agentic pipeline that runs on a daily schedule:

```
arXiv API → ingest → SQLite store → Claude analysis → anomaly detection → report generation → dashboard
```

Each stage is a standalone Python module with a single responsibility. The orchestrator
(`runner.py`) wires them together and handles the daily scheduling via APScheduler.

---

## Data flow

```
runner.py
  │
  ├── core/ingest.py
  │     └── arXiv Atom feed (feedparser)
  │         query: cat:cs.AI OR cat:cs.LG OR cat:q-bio.* OR cat:cs.RO
  │         filter: submissions in last 24 hours
  │         output: list[dict] — id, title, abstract, authors, categories, published
  │
  ├── core/store.py  (SQLite — data/aria.db)
  │     ├── papers table — one row per paper, upsert on id
  │     ├── reports table — published intelligence briefs
  │     └── baselines table — daily aggregate stats per category (rolling 30-day history)
  │
  ├── core/analyst.py
  │     └── Anthropic Claude API (claude-sonnet-4-6)
  │         input: batches of 10 papers (title + abstract + categories)
  │         output per paper: novelty_score (0–10), themes (list[str]), is_notable (bool), rationale (str)
  │         batch size capped at 10 to stay within context window
  │
  ├── core/decider.py  ← the agentic decision layer
  │     ├── trigger 1: Volume Spike
  │     ├── trigger 2: Cross-Domain Cluster
  │     ├── trigger 3: Novelty Burst
  │     ├── trigger 4: Significance Surge
  │     └── output: {should_report: bool, triggers: list[str], stats: dict}
  │
  ├── core/reporter.py  (conditional — only if decider fires)
  │     └── Anthropic Claude API
  │         input: top 20 papers by novelty score + trigger context + stats
  │         output: structured markdown brief (6–8 sections)
  │
  └── core/store.py  (save report)
        └── reports table — brief stored for dashboard retrieval
```

---

## The decision layer (decider.py)

This is the core of the agentic design. Rather than summarizing every day's papers
unconditionally, ARIA decides whether today's activity warrants a report. Four independent
triggers each look for a different kind of significance:

### Trigger 1 — Volume Spike
```python
fired = today_count >= statistics.mean(baseline_counts) * VOLUME_SPIKE_MULTIPLIER  # default 1.5
```
Detects: days when submission volume is unusually high, which often precedes a research trend.
Requires: 30-day baseline data per category. Inactive until baseline window fills.

### Trigger 2 — Cross-Domain Cluster
```python
cross_domain_papers = [p for p in papers if len(_count_domains(p)) >= 2]
fired = len(cross_domain_papers) >= CROSS_DOMAIN_MIN_PAPERS  # default 3
```
Detects: papers that simultaneously touch two or more of the three monitored domain groups
(AI/ML, quantitative biology, robotics). This is the most valuable signal — cross-domain
convergence often precedes field-defining work (e.g., ML techniques applied to genomics).
Active from day one, no baseline required.

Domain groupings:
```python
DOMAIN_GROUPS = {
    "ai_ml":    {"cs.AI", "cs.LG", "stat.ML"},
    "bio":      {"q-bio", "q-bio.BM", "q-bio.GN", "q-bio.NC", ...},
    "robotics": {"cs.RO"},
}
```

### Trigger 3 — Novelty Burst
```python
high_novelty = [p for p in papers if p["novelty_score"] >= NOVELTY_THRESHOLD]  # default 7
fired = len(high_novelty) / len(papers) >= NOVELTY_BURST_PCT  # default 0.30
```
Detects: days where an unusually high fraction of papers score above the novelty threshold.
This fires when the entire field seems to be moving at once, not just individual standout papers.
Active from day one, no baseline required.

### Trigger 4 — Significance Surge
```python
fired = avg_today >= statistics.mean(baseline_avgs) * SIGNIFICANCE_SURGE_MULTIPLIER  # default 1.3
```
Detects: days where the average novelty score is significantly above the historical mean.
Complementary to Novelty Burst — Burst detects count concentration, Surge detects mean elevation.
Requires: 30-day baseline. Inactive until baseline window fills.

### Decision logic
```python
should_report = len(fired_triggers) >= 1  # OR logic — any trigger is sufficient
```
OR logic was chosen over AND because each trigger measures a *different kind* of significance.
Requiring all four to fire simultaneously would make the system nearly silent. The thresholds
on each individual trigger are the calibration point, not the combination logic.

All thresholds are configurable via environment variables — see `.env.example`.

---

## Baseline system

The baseline system is what makes the triggers meaningful rather than hardcoded.

Each day after analysis, the runner writes one row per monitored category to `baselines`:
```sql
INSERT OR REPLACE INTO baselines (category, date, paper_count, avg_novelty) VALUES (?, ?, ?, ?)
```

When the decider runs, it queries the last 30 days of baselines per category and computes
the mean paper count and mean average novelty. Triggers 1 and 4 compare today's numbers
against these means.

**Bootstrap period:** For the first 30 days, the baseline-dependent triggers (Volume Spike,
Significance Surge) have insufficient history and do not fire. Cross-Domain Cluster and
Novelty Burst are active immediately. After 30 days, all four triggers are fully operational.

---

## Claude API integration

Two separate calls per run:

**Analysis call** (`analyst.py`) — batched, 10 papers per call:
```python
system = "You are a research intelligence analyst..."
user = f"Analyze these papers and return JSON: {json.dumps(paper_payload)}"
# Returns: [{novelty_score, themes, is_notable, rationale}, ...]
```
JSON mode is enforced via prompt instruction with markdown fence stripping as fallback.
Failed batches are logged and skipped — partial analysis is better than no run.

**Report call** (`reporter.py`) — one call per triggered run:
```python
# Input: top 20 papers by novelty + trigger context + daily stats
# Output: structured markdown brief with 5 sections
```
The reporter receives pre-scored papers, so Claude is doing synthesis and narrative,
not re-evaluating novelty. This separation keeps the report grounded in the quantitative
scores rather than letting the report generation introduce its own biases.

---

## Storage schema

```sql
CREATE TABLE papers (
    id TEXT PRIMARY KEY,          -- arXiv paper ID
    title TEXT,
    abstract TEXT,
    authors TEXT,                  -- JSON array
    categories TEXT,               -- JSON array
    published TEXT,                -- ISO 8601
    novelty_score REAL DEFAULT 0,  -- set by analyst.py
    themes TEXT,                   -- JSON array, set by analyst.py
    ingested_at TEXT               -- UTC timestamp, set on insert
);

CREATE TABLE reports (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT,
    content TEXT,                  -- markdown brief
    triggers TEXT,                 -- JSON array of trigger descriptions
    paper_count INTEGER,
    created_at TEXT                -- UTC timestamp
);

CREATE TABLE baselines (
    category TEXT,
    date TEXT,
    paper_count INTEGER,
    avg_novelty REAL,
    PRIMARY KEY (category, date)   -- upsert-safe composite key
);
```

---

## Scheduling

The scheduler uses APScheduler's `BlockingScheduler` with a UTC cron trigger:
```python
scheduler.add_job(run_pipeline, "cron", hour=7, minute=0)
```
07:00 UTC was chosen because arXiv publishes new submissions at approximately 00:00 UTC,
so by 07:00 UTC the full day's batch is available and settled. Running earlier risks
catching an incomplete submission window.

For EC2 deployment, the scheduler runs as a systemd service so it restarts automatically
on instance reboot. See `docs/USER_MANUAL.md` for the service configuration.

---

## Design decisions not obvious from the code

**Why batch size 10 for analysis?**
Claude's context window is large enough to handle more, but larger batches produce lower-quality
per-paper analysis — the model attention distributes across too many abstracts. 10 papers at ~300
words each is approximately 3,000 tokens of user content, which keeps each paper well within
Claude's effective attention range. 134 papers = 14 API calls, which takes ~4 minutes.

**Why store baselines per-category rather than aggregate?**
Volume in cs.AI (100+ papers/day) is structurally different from cs.RO (10-20/day).
An aggregate baseline would make cs.RO spikes invisible. Per-category baselines let each
domain's normal be measured against itself.

**Why OR logic on triggers (any fires = report)?**
Each trigger measures a genuinely different phenomenon. A day with a Cross-Domain Cluster
is significant regardless of whether Volume Spike also fires. AND logic would require
multiple unusual things happening simultaneously, which is too rare to be useful.

**Why not use embeddings for novelty scoring?**
Embedding-based similarity (e.g., comparing to a corpus of known papers) would require
maintaining and updating a reference corpus, adds significant infrastructure, and still
requires a judgment call about what "novel" means. Delegating that judgment to Claude
via a structured prompt is more adaptable and produces human-interpretable rationale.

---

## Extending ARIA

**Add a new arXiv category:**
Edit `MONITORED_CATEGORIES` in `core/ingest.py`. Add it to the appropriate domain group
in `core/decider.py` if relevant to cross-domain detection.

**Add a new anomaly trigger:**
Add a `_trigger_*` function in `core/decider.py` returning `(bool, str)`, then add it
to the `checks` list in `decide()`. No other files need to change.

**Change report format:**
Edit the prompt in `core/reporter.py`. The pipeline doesn't parse the report content
after generation — it's stored as raw markdown — so any format works.

**Add notifications (email/Slack):**
In `runner.py`, after `db.save_report(...)`, add a notification call. The report dict
is available at that point with title, content, and trigger list.
