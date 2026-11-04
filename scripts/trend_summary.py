"""
trend_summary.py - read-only trend summary of ARIA's stored papers (ADR-018).

Reads the SQLite database (never writes), and emits JSON: weekly and monthly shares of four
research fields (AI, ML, robotics, bio) and their overlaps, mean model-assigned novelty, and a
short list of PRE-DECLARED exploratory tests with intervals and a multiple-comparison correction.

What the numbers are, and are not (also written into the output as "caveats"):
- The unit of sampling is one daily run: the 200 most recent arXiv submissions at run time, which
  cover about 9 hours of submission time. Shares describe that slice, not arXiv.
- Intervals are computed across daily runs within a week, not across papers, because papers in
  one run are not independent draws.
- Novelty is a model opinion of an abstract, not validated against citations or experts.
- Field = the arXiv category tags the authors chose. It is not an industry.
- Tests are observational. Nothing here establishes cause.

Usage:  python scripts/trend_summary.py data/aria.db [-o trend_summary.json]
"""

from __future__ import annotations

import argparse
import json
import math
import random
import sqlite3
import statistics
import sys
from collections import defaultdict
from datetime import date, datetime, timezone

FIELDS = ["AI", "ML", "RO", "BIO"]
FIELD_LABELS = {"AI": "AI (cs.AI)", "ML": "ML (cs.LG, stat.ML)", "RO": "Robotics (cs.RO)", "BIO": "Bio (q-bio)"}
OVERLAPS = [("AI", "ML"), ("AI", "RO"), ("ML", "RO"), ("BIO", "*")]  # BIO with any other field
MIN_RUN_PAPERS = 150     # a run with fewer papers is a partial or failed run
MIN_WEEK_PAPERS = 400    # a week with fewer papers is partial
MIN_MONTH_PAPERS = 1200
T95 = {1: 12.706, 2: 4.303, 3: 3.182, 4: 2.776, 5: 2.571, 6: 2.447, 7: 2.365, 8: 2.306, 9: 2.262, 10: 2.228}


def field_flags(categories) -> dict[str, bool]:
    """Which of the four fields a paper's category tags touch."""
    cats = set(categories or [])
    return {
        "AI": "cs.AI" in cats,
        "ML": bool(cats & {"cs.LG", "stat.ML"}),
        "RO": "cs.RO" in cats,
        "BIO": any(c == "q-bio" or c.startswith("q-bio.") for c in cats),
    }


def paper_labels(categories) -> dict[str, bool]:
    f = field_flags(categories)
    lab = dict(f)
    lab["AI&ML"] = f["AI"] and f["ML"]
    lab["AI&RO"] = f["AI"] and f["RO"]
    lab["ML&RO"] = f["ML"] and f["RO"]
    lab["BIO&other"] = f["BIO"] and (f["AI"] or f["ML"] or f["RO"])
    lab["multi"] = sum(f.values()) >= 2
    return lab


LABELS = FIELDS + ["AI&ML", "AI&RO", "ML&RO", "BIO&other", "multi"]


def interval(values: list[float]) -> tuple[float, float, float]:
    """(mean, lo, hi) of per-run values, 95% t-interval. With one run there is no interval."""
    n = len(values)
    m = statistics.mean(values)
    if n < 2:
        return m, float("nan"), float("nan")
    half = T95.get(n - 1, 1.96) * statistics.stdev(values) / math.sqrt(n)
    return m, m - half, m + half


def _rank(xs: list[float]) -> list[float]:
    order = sorted(range(len(xs)), key=lambda i: xs[i])
    ranks = [0.0] * len(xs)
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and xs[order[j + 1]] == xs[order[i]]:
            j += 1
        for k in range(i, j + 1):
            ranks[order[k]] = (i + j) / 2 + 1
        i = j + 1
    return ranks


def spearman(a: list[float], b: list[float]) -> float:
    ra, rb = _rank(a), _rank(b)
    ma, mb = statistics.mean(ra), statistics.mean(rb)
    num = sum((x - ma) * (y - mb) for x, y in zip(ra, rb))
    den = math.sqrt(sum((x - ma) ** 2 for x in ra) * sum((y - mb) ** 2 for y in rb))
    return num / den if den else float("nan")


def theil_sen(x: list[float], y: list[float]) -> float:
    slopes = [(y[j] - y[i]) / (x[j] - x[i]) for i in range(len(x)) for j in range(i + 1, len(x)) if x[j] != x[i]]
    return statistics.median(slopes) if slopes else float("nan")


def bootstrap_ci(stat, x, y, k_tests: int, n_boot: int = 4000, seed: int = 7):
    """Percentile CI for stat(x, y), resampling weeks. Level is Bonferroni-adjusted for k_tests."""
    rng = random.Random(seed)
    n = len(x)
    alpha = 0.05 / max(k_tests, 1)
    vals = []
    for _ in range(n_boot):
        idx = [rng.randrange(n) for _ in range(n)]
        v = stat([x[i] for i in idx], [y[i] for i in idx])
        if not math.isnan(v):
            vals.append(v)
    vals.sort()
    if len(vals) < 100:
        return float("nan"), float("nan")
    return vals[int(alpha / 2 * len(vals))], vals[min(int((1 - alpha / 2) * len(vals)), len(vals) - 1)]


def load_runs(conn: sqlite3.Connection) -> dict[str, list[dict]]:
    """{run_date: [paper dicts]} for scored-or-not papers, grouped by ingest date."""
    runs: dict[str, list[dict]] = defaultdict(list)
    for cats, nov, ing in conn.execute("SELECT categories, novelty_score, ingested_at FROM papers"):
        if not ing:
            continue
        try:
            tags = json.loads(cats or "[]")
        except (TypeError, ValueError):
            continue
        runs[ing[:10]].append({"labels": paper_labels(tags), "nov": nov if nov else None})
    return runs


def _period_stats(run_list: list[list[dict]]) -> dict:
    """Shares and novelty for one period, with intervals across its runs."""
    out = {"runs": len(run_list), "n": sum(len(r) for r in run_list), "shares": {}}
    for lab in LABELS:
        per_run = [sum(p["labels"][lab] for p in r) / len(r) for r in run_list]
        m, lo, hi = interval(per_run)
        sd = statistics.stdev(per_run) if len(per_run) > 1 else float("nan")
        out["shares"][lab] = {"share": m, "lo": lo, "hi": hi, "run_sd": sd}
    nov_runs = [statistics.mean(p["nov"] for p in r if p["nov"]) for r in run_list if any(p["nov"] for p in r)]
    scored = sum(1 for r in run_list for p in r if p["nov"])
    out["scored"] = scored
    if nov_runs:
        m, lo, hi = interval(nov_runs)
        out["novelty"] = {"mean": m, "lo": lo, "hi": hi}
    return out


def summarize(runs: dict[str, list[dict]]) -> dict:
    complete = {d: r for d, r in runs.items() if len(r) >= MIN_RUN_PAPERS}
    weeks: dict[str, list[tuple[str, list[dict]]]] = defaultdict(list)
    months: dict[str, list[tuple[str, list[dict]]]] = defaultdict(list)
    for d, r in sorted(complete.items()):
        y, w, _ = date.fromisoformat(d).isocalendar()
        weeks[f"{y}-W{w:02d}"].append((d, r))
        months[d[:7]].append((d, r))

    week_rows, skipped_weeks = [], []
    for wk, items in sorted(weeks.items()):
        n = sum(len(r) for _, r in items)
        if n < MIN_WEEK_PAPERS:
            skipped_weeks.append({"week": wk, "papers": n, "reason": "partial week"})
            continue
        row = _period_stats([r for _, r in items])
        row.update({"week": wk, "start": items[0][0]})
        week_rows.append(row)

    month_rows = []
    for mo, items in sorted(months.items()):
        n = sum(len(r) for _, r in items)
        row = _period_stats([r for _, r in items])
        row.update({"month": mo, "partial": n < MIN_MONTH_PAPERS})
        month_rows.append(row)

    tests = exploratory_tests(week_rows)
    return {
        "generated": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "papers_total": sum(len(r) for r in runs.values()),
        "runs_used": len(complete),
        "runs_excluded": len(runs) - len(complete),
        "weeks": week_rows,
        "weeks_skipped": skipped_weeks,
        "months": month_rows,
        "typical_run_sd": {
            lab: statistics.median(w["shares"][lab]["run_sd"] for w in week_rows
                                   if not math.isnan(w["shares"][lab]["run_sd"]))
            for lab in LABELS
        } if week_rows else {},
        "exploratory_tests": tests,
        "field_labels": FIELD_LABELS,
        "caveats": CAVEATS,
    }


def exploratory_tests(week_rows: list[dict]) -> list[dict]:
    """A fixed, pre-declared list. Bonferroni-adjusted over the whole list."""
    nov_weeks = [w for w in week_rows if "novelty" in w]
    declared = [
        ("trend", "AI share", "AI"), ("trend", "ML share", "ML"), ("trend", "Robotics share", "RO"),
        ("trend", "Bio share", "BIO"), ("trend", "Multi-field share", "multi"),
        ("assoc", "Multi-field share vs mean novelty", "multi"), ("assoc", "ML share vs mean novelty", "ML"),
        ("assoc", "Robotics share vs mean novelty", "RO"), ("assoc", "Bio share vs mean novelty", "BIO"),
    ]
    k = len(declared)
    results = []
    for kind, name, lab in declared:
        if kind == "trend":
            x = list(range(len(week_rows)))
            y = [w["shares"][lab]["share"] for w in week_rows]
            stat, label = theil_sen, "Theil-Sen slope (share per week)"
        else:
            x = [w["shares"][lab]["share"] for w in nov_weeks]
            y = [w["novelty"]["mean"] for w in nov_weeks]
            stat, label = spearman, "Spearman rho"
        if len(x) < 8:
            continue
        est = stat(x, y)
        lo, hi = bootstrap_ci(stat, x, y, k)
        results.append({
            "name": name, "kind": kind, "statistic": label, "n_weeks": len(x),
            "estimate": est, "ci_lo": lo, "ci_hi": hi, "tests_in_family": k,
            "supported": bool(not math.isnan(lo) and (lo > 0 or hi < 0)),
        })
    return results


CAVEATS = [
    "Each daily run is the 200 most recent arXiv submissions at about 07:00 UTC, covering roughly 9 hours of submission time; shares describe that slice, not all of arXiv.",
    "Intervals are 95% t-intervals across the daily runs in a period, so a week has only 3 or 4 runs and its interval is wide.",
    "Field means the arXiv category tags authors chose, not an industry; a paper can carry several.",
    "Novelty is a model-assigned reading of an abstract and has not been validated against citations or expert judgement.",
    "Tests are exploratory and pre-declared; intervals are bootstrapped over weeks with a Bonferroni adjustment, and weekly series are autocorrelated, so the intervals are likely too narrow.",
    "Nothing here establishes cause. Analysis uses abstracts only.",
]


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("db")
    ap.add_argument("-o", "--out", default="-")
    args = ap.parse_args(argv)
    conn = sqlite3.connect(f"file:{args.db}?mode=ro", uri=True)  # read-only
    try:
        result = summarize(load_runs(conn))
    finally:
        conn.close()
    text = json.dumps(result, indent=2, default=str).replace("NaN", "null")
    if args.out == "-":
        sys.stdout.write(text + "\n")
    else:
        with open(args.out, "w", encoding="utf-8") as f:
            f.write(text + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
