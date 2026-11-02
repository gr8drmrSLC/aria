"""
decider.py — Autonomous decision layer for ARIA.

Evaluates today's analyzed papers against ARIA's own recent history and fires four
independent triggers to decide whether a report is warranted (ADR-016).

Each trigger compares one daily metric with its trailing window using a robust z-score
(median and MAD, so one odd day does not distort the baseline):

  1. Volume Spike        — paper count (note: ingest is capped at 200 per run, so this
                           can rarely fire; kept for interface compatibility)
  2. Cross-Domain        — share of papers bridging two or more monitored domains
  3. Novelty Burst       — share of papers scoring >= HIGH_NOVELTY
  4. Significance Surge  — mean novelty score

A trigger fires when its z-score >= Z_THRESHOLD. With fewer than MIN_HISTORY_DAYS of
history (cold start) it falls back to the original absolute thresholds. The previous
absolute rules fired on ~every run (see docs/ARIA_TREND_ANALYSIS_2026-11-02.md).
"""

import collections
import logging
import os
import statistics

logger = logging.getLogger("aria.decider")

# Configurable thresholds
Z_THRESHOLD = float(os.environ.get("ARIA_Z_THRESHOLD", "1.5"))
MIN_HISTORY_DAYS = int(os.environ.get("ARIA_MIN_HISTORY_DAYS", "10"))
HIGH_NOVELTY = float(os.environ.get("ARIA_HIGH_NOVELTY", "8"))
MIN_SCORED_FRACTION = 0.5   # days with fewer scored papers are analysis failures, not signal

# Cold-start (fallback) absolute thresholds — the original rules
VOLUME_SPIKE_MULTIPLIER = float(os.environ.get("ARIA_VOLUME_SPIKE", "1.5"))
NOVELTY_BURST_PCT = float(os.environ.get("ARIA_NOVELTY_BURST_PCT", "0.30"))
SIGNIFICANCE_SURGE_MULTIPLIER = float(os.environ.get("ARIA_SIGNIFICANCE_SURGE", "1.3"))
CROSS_DOMAIN_MIN_PAPERS = int(os.environ.get("ARIA_CROSS_DOMAIN_MIN", "3"))
NOVELTY_THRESHOLD = int(os.environ.get("ARIA_NOVELTY_THRESHOLD", "7"))

# Domain groups for cross-domain detection
DOMAIN_GROUPS = {
    "ai_ml": {"cs.AI", "cs.LG", "stat.ML"},
    "bio": {"q-bio", "q-bio.BM", "q-bio.GN", "q-bio.NC", "q-bio.PE", "q-bio.QM"},
    "robotics": {"cs.RO"},
}


def _count_domains(paper: dict) -> set[str]:
    """Return which monitored domain groups a paper touches.

    A category matches a group entry exactly, or as a parent: the entry "q-bio" matches
    "q-bio.NC". It must NOT match on the shared "cs." prefix. The previous prefix test
    (cat.startswith(entry.split(".")[0] + ".")) made every cs.* paper count as both ai_ml
    and robotics, so ~98% of papers looked cross-domain. See DECISIONS.md ADR-016.
    """
    cats = set(paper.get("categories", []))
    hit_domains = set()
    for domain_name, domain_cats in DOMAIN_GROUPS.items():
        for cat in cats:
            if any(cat == d_cat or cat.startswith(d_cat + ".") for d_cat in domain_cats):
                hit_domains.add(domain_name)
    return hit_domains


def day_metrics(papers: list[dict]) -> dict | None:
    """Daily metrics for one day's papers, or None if too few were scored to be trusted."""
    if not papers:
        return None
    scored = [p["novelty_score"] for p in papers if (p.get("novelty_score") or 0) > 0]
    if len(scored) < MIN_SCORED_FRACTION * len(papers):
        return None  # analysis failure, not a real quiet day
    return {
        "paper_count": len(papers),
        "avg_novelty": statistics.mean(scored),
        "high_share": sum(1 for v in scored if v >= HIGH_NOVELTY) / len(scored),
        "cross_share": sum(1 for p in papers if len(_count_domains(p)) >= 2) / len(papers),
    }


def build_history(rows: list[dict], before_date: str) -> list[dict]:
    """
    Turn paper rows ({categories, novelty_score, ingested_at}) into one metrics dict per
    prior day. Days on or after `before_date` are excluded so today never baselines itself.
    """
    by_day: dict[str, list[dict]] = collections.defaultdict(list)
    for r in rows:
        day = (r.get("ingested_at") or "")[:10]
        if day and day < before_date:
            by_day[day].append(r)
    history = []
    for day in sorted(by_day):
        m = day_metrics(by_day[day])
        if m:
            m["date"] = day
            history.append(m)
    return history


def _robust_z(value: float, series: list[float]) -> tuple[float, float] | None:
    """(z, median) of value against series, using median/MAD. None if no usable spread."""
    med = statistics.median(series)
    sigma = 1.4826 * statistics.median(abs(x - med) for x in series)
    if sigma < 1e-9:
        sigma = statistics.pstdev(series)
    if sigma < 1e-9:
        return None
    return (value - med) / sigma, med


def _relative(metric: str, today: dict | None, history: list[dict] | None):
    """Robust z-score of today's metric vs history, or None when there is not enough history."""
    if today is None or not history or len(history) < MIN_HISTORY_DAYS:
        return None
    return _robust_z(today[metric], [h[metric] for h in history])


def _trigger_volume_spike(papers, baselines, today=None, history=None) -> tuple[bool, str]:
    """Paper count well above its trailing window. Ingest is capped, so this rarely fires."""
    rel = _relative("paper_count", today, history)
    if rel is not None:
        z, med = rel
        if z >= Z_THRESHOLD:
            return True, f"Volume spike: {len(papers)} papers vs trailing median {med:.0f} (z={z:.1f})"
        return False, ""
    counts = [b["paper_count"] for b in (baselines or []) if b.get("paper_count")]
    if counts and len(papers) >= statistics.mean(counts) * VOLUME_SPIKE_MULTIPLIER:  # cold start
        return True, f"Volume spike: {len(papers)} papers vs. {statistics.mean(counts):.0f} historical mean"
    return False, ""


def _trigger_cross_domain(papers, today=None, history=None) -> tuple[bool, str]:
    """Share of papers bridging two or more monitored domains, vs trailing window."""
    count = sum(1 for p in papers if len(_count_domains(p)) >= 2)
    rel = _relative("cross_share", today, history)
    if rel is not None:
        z, med = rel
        if z >= Z_THRESHOLD:
            return True, (
                f"Cross-domain cluster: {count} papers ({count / len(papers):.0%}) bridge monitored "
                f"domains vs trailing median {med:.0%} (z={z:.1f})"
            )
        return False, ""
    if count >= CROSS_DOMAIN_MIN_PAPERS:  # cold start
        return True, f"Cross-domain cluster: {count} papers bridge multiple research domains"
    return False, ""


def _trigger_novelty_burst(papers, today=None, history=None) -> tuple[bool, str]:
    """Share of papers scoring >= HIGH_NOVELTY, vs trailing window."""
    if not papers:
        return False, ""
    rel = _relative("high_share", today, history)
    if rel is not None:
        z, med = rel
        if z >= Z_THRESHOLD:
            return True, (
                f"Novelty burst: {today['high_share']:.0%} of papers scored >= {HIGH_NOVELTY:g} "
                f"vs trailing median {med:.0%} (z={z:.1f})"
            )
        return False, ""
    high = [p for p in papers if p.get("novelty_score", 0) >= NOVELTY_THRESHOLD]  # cold start
    pct = len(high) / len(papers)
    if pct >= NOVELTY_BURST_PCT:
        return True, f"Novelty burst: {len(high)}/{len(papers)} papers ({pct:.0%}) scored high-novelty"
    return False, ""


def _trigger_significance_surge(papers, baselines, today=None, history=None) -> tuple[bool, str]:
    """Mean novelty score vs trailing window."""
    rel = _relative("avg_novelty", today, history)
    if rel is not None:
        z, med = rel
        if z >= Z_THRESHOLD:
            return True, (
                f"Significance surge: mean novelty {today['avg_novelty']:.2f} "
                f"vs trailing median {med:.2f} (z={z:.1f})"
            )
        return False, ""
    scored = [p["novelty_score"] for p in papers if (p.get("novelty_score") or 0) > 0]  # cold start
    avgs = [b["avg_novelty"] for b in (baselines or []) if b.get("avg_novelty")]
    if scored and avgs and statistics.mean(scored) >= statistics.mean(avgs) * SIGNIFICANCE_SURGE_MULTIPLIER:
        return True, f"Significance surge: mean novelty {statistics.mean(scored):.1f} vs. {statistics.mean(avgs):.1f}"
    return False, ""


def decide(papers: list[dict], baselines: list[dict] | None = None,
           history: list[dict] | None = None) -> dict:
    """
    Run all four triggers and decide whether to publish a report.

    Args:
        papers:    Today's analyzed papers (must have novelty_score set).
        baselines: Legacy per-category baseline rows (used only in cold start).
        history:   Per-day metrics for prior days from build_history(). With at least
                   MIN_HISTORY_DAYS entries, triggers are relative; otherwise cold-start rules.

    Returns:
        {"should_report": bool, "triggers": [...descriptions], "trigger_names": [...],
         "stats": {...}, "mode": "relative" | "cold_start"}
    """
    today = day_metrics(papers)
    relative = bool(history) and len(history) >= MIN_HISTORY_DAYS and today is not None

    checks = [
        ("volume_spike", _trigger_volume_spike(papers, baselines, today, history)),
        ("cross_domain", _trigger_cross_domain(papers, today, history)),
        ("novelty_burst", _trigger_novelty_burst(papers, today, history)),
        ("significance_surge", _trigger_significance_surge(papers, baselines, today, history)),
    ]

    fired_triggers: list[str] = []
    fired_names: list[str] = []
    for name, (fired, description) in checks:
        if fired:
            fired_triggers.append(description)
            fired_names.append(name)
            logger.info("Trigger fired: %s", name)

    novelty_scores = [p.get("novelty_score", 0) for p in papers if p.get("novelty_score")]
    stats = {
        "paper_count": len(papers),
        "avg_novelty": round(statistics.mean(novelty_scores), 2) if novelty_scores else 0,
        "high_novelty_count": sum(1 for s in novelty_scores if s >= NOVELTY_THRESHOLD),
        "cross_domain_count": sum(1 for p in papers if len(_count_domains(p)) >= 2),
        "triggers_fired": len(fired_triggers),
    }
    mode = "relative" if relative else "cold_start"
    logger.info("Decision (%s): should_report=%s, triggers=%s, stats=%s",
                mode, bool(fired_triggers), fired_names, stats)

    return {
        "should_report": len(fired_triggers) >= 1,
        "triggers": fired_triggers,
        "trigger_names": fired_names,
        "stats": stats,
        "mode": mode,
    }
