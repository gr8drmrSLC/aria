"""
backtest_decider.py — replay stored history through core.decider.decide().

Answers "if these rules had been running, how often would ARIA have reported?" before any
threshold change ships (ADR-016). Reads a SQLite snapshot read-only; never writes.

Usage:
    python tests/backtest_decider.py data/aria_prod_2026-11-02.db
    python tests/backtest_decider.py <db> --max-per-week 2.0   # exit 1 if mean reports/week exceeds it

Exit code is non-zero when --max-per-week is exceeded, so it can gate a threshold change.
Days where the analysis step failed (no scored papers) are reported separately and skipped,
because an unscored day would otherwise look like an anomaly.
"""
import argparse
import collections
import datetime as dt
import json
import os
import sqlite3
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.decider import decide  # noqa: E402

CATEGORIES = ["cs.AI", "cs.LG", "cs.RO", "q-bio.*"]  # as stored in the baselines table
MIN_SCORED_FRACTION = 0.5


def load(db_path: str):
    con = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    con.row_factory = sqlite3.Row
    by_day = collections.defaultdict(list)
    for r in con.execute("SELECT categories, novelty_score, ingested_at FROM papers"):
        by_day[r["ingested_at"][:10]].append({
            "categories": json.loads(r["categories"] or "[]"),
            "novelty_score": r["novelty_score"] or 0,
        })
    baselines = [dict(r) for r in con.execute("SELECT * FROM baselines ORDER BY date")]
    return by_day, baselines


def baselines_as_of(baselines, day: str, window_days: int = 30):
    """What runner.py passes to decide(): rows in the trailing window, including today's."""
    start = (dt.date.fromisoformat(day) - dt.timedelta(days=window_days)).isoformat()
    return [b for b in baselines if start <= b["date"] <= day]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("db")
    ap.add_argument("--max-per-week", type=float, default=None)
    args = ap.parse_args()

    by_day, baselines = load(args.db)
    fired_by = collections.Counter()
    reported, skipped = [], []
    for day in sorted(by_day):
        papers = by_day[day]
        scored = [p for p in papers if p["novelty_score"] > 0]
        if len(scored) < MIN_SCORED_FRACTION * len(papers):
            skipped.append(day)
            continue
        result = decide(papers, baselines_as_of(baselines, day))
        for name in result["trigger_names"]:
            fired_by[name] += 1
        if result["should_report"]:
            reported.append(day)

    evaluated = len(by_day) - len(skipped)
    first, last = dt.date.fromisoformat(min(by_day)), dt.date.fromisoformat(max(by_day))
    weeks = max(1.0, ((last - first).days + 1) / 7)
    per_week = len(reported) / weeks
    print(f"days replayed: {evaluated}  (skipped, mostly unscored: {len(skipped)})")
    print(f"days that would report: {len(reported)} ({100 * len(reported) / max(1, evaluated):.0f}%)")
    print(f"mean reports/week: {per_week:.2f}  over {weeks:.1f} weeks")
    for name, n in fired_by.most_common():
        print(f"  {name:20s} fired {n:3d} days")
    months = collections.Counter(d[:7] for d in reported)
    print("by month:", dict(sorted(months.items())))
    if args.max_per_week is not None and per_week > args.max_per_week:
        print(f"FAIL: {per_week:.2f}/week exceeds --max-per-week {args.max_per_week}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
