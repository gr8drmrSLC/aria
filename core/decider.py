"""
decider.py — Autonomous decision layer for ARIA.

Evaluates today's analyzed papers against historical baselines and fires
four independent anomaly triggers to decide whether a report is warranted.
The decision is made without human prompting — this is the agentic core of ARIA.

Triggers:
  1. Volume Spike     — today's paper count > baseline mean * 1.5
  2. Cross-Domain     — significant cluster of papers bridging multiple monitored domains
  3. Novelty Burst    — >30% of papers scored as high-novelty (>= threshold)
  4. Significance Surge — avg novelty score > baseline avg * 1.3
"""

import logging
import os
import statistics

logger = logging.getLogger("aria.decider")

# Configurable thresholds
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
    """Return which monitored domain groups a paper touches."""
    cats = set(paper.get("categories", []))
    hit_domains = set()
    for domain_name, domain_cats in DOMAIN_GROUPS.items():
        # Check if any category starts with a domain prefix (handles q-bio.* etc.)
        for cat in cats:
            for d_cat in domain_cats:
                if cat == d_cat or cat.startswith(d_cat.split(".")[0] + "."):
                    hit_domains.add(domain_name)
    return hit_domains


def _trigger_volume_spike(papers: list[dict], baselines: list[dict]) -> tuple[bool, str]:
    """Fires when today's paper count significantly exceeds the historical mean."""
    today_count = len(papers)
    if not baselines:
        logger.debug("Volume spike: no baseline data, skipping")
        return False, ""

    counts = [b["paper_count"] for b in baselines if b.get("paper_count")]
    if not counts:
        return False, ""

    baseline_mean = statistics.mean(counts)
    threshold = baseline_mean * VOLUME_SPIKE_MULTIPLIER
    fired = today_count >= threshold

    logger.debug(
        "Volume spike: today=%d, baseline_mean=%.1f, threshold=%.1f, fired=%s",
        today_count, baseline_mean, threshold, fired,
    )
    if fired:
        return True, (
            f"Volume spike: {today_count} papers today vs. "
            f"{baseline_mean:.0f} historical mean ({VOLUME_SPIKE_MULTIPLIER}x threshold)"
        )
    return False, ""


def _trigger_cross_domain(papers: list[dict]) -> tuple[bool, str]:
    """Fires when multiple papers bridge two or more monitored research domains."""
    cross_domain_papers = [p for p in papers if len(_count_domains(p)) >= 2]
    count = len(cross_domain_papers)
    fired = count >= CROSS_DOMAIN_MIN_PAPERS

    logger.debug("Cross-domain: %d bridging papers, min=%d, fired=%s", count, CROSS_DOMAIN_MIN_PAPERS, fired)
    if fired:
        return True, (
            f"Cross-domain cluster: {count} papers bridge multiple research domains "
            f"(AI/ML + bio or robotics) — potential convergence signal"
        )
    return False, ""


def _trigger_novelty_burst(papers: list[dict]) -> tuple[bool, str]:
    """Fires when an unusually high fraction of papers score as high-novelty."""
    if not papers:
        return False, ""

    high_novelty = [p for p in papers if p.get("novelty_score", 0) >= NOVELTY_THRESHOLD]
    pct = len(high_novelty) / len(papers)
    fired = pct >= NOVELTY_BURST_PCT

    logger.debug(
        "Novelty burst: %d/%d high-novelty (%.0f%%), threshold=%.0f%%, fired=%s",
        len(high_novelty), len(papers), pct * 100, NOVELTY_BURST_PCT * 100, fired,
    )
    if fired:
        return True, (
            f"Novelty burst: {len(high_novelty)}/{len(papers)} papers ({pct:.0%}) "
            f"scored high-novelty — unusual concentration of significant work"
        )
    return False, ""


def _trigger_significance_surge(papers: list[dict], baselines: list[dict]) -> tuple[bool, str]:
    """Fires when average novelty score significantly exceeds historical baseline."""
    scored = [p for p in papers if p.get("novelty_score") is not None and p["novelty_score"] > 0]
    if not scored:
        return False, ""

    avg_today = statistics.mean(p["novelty_score"] for p in scored)

    if not baselines:
        return False, ""

    avg_baselines = [b["avg_novelty"] for b in baselines if b.get("avg_novelty")]
    if not avg_baselines:
        return False, ""

    baseline_avg = statistics.mean(avg_baselines)
    threshold = baseline_avg * SIGNIFICANCE_SURGE_MULTIPLIER
    fired = avg_today >= threshold

    logger.debug(
        "Significance surge: today_avg=%.2f, baseline_avg=%.2f, threshold=%.2f, fired=%s",
        avg_today, baseline_avg, threshold, fired,
    )
    if fired:
        return True, (
            f"Significance surge: avg novelty {avg_today:.1f} vs. "
            f"{baseline_avg:.1f} historical average ({SIGNIFICANCE_SURGE_MULTIPLIER}x threshold)"
        )
    return False, ""


def decide(papers: list[dict], baselines: list[dict] | None = None) -> dict:
    """
    Run all four anomaly triggers and decide whether to publish a report.

    Args:
        papers:    Today's analyzed papers (must have novelty_score set).
        baselines: Historical baseline records from store.get_baselines().
                   If None or empty, baseline-dependent triggers are skipped.

    Returns:
        {
            "should_report": bool,
            "triggers": list[str],       # human-readable trigger descriptions
            "trigger_names": list[str],  # machine names of fired triggers
            "stats": dict,               # summary stats for logging/reporting
        }
    """
    if baselines is None:
        baselines = []

    fired_triggers: list[str] = []
    fired_names: list[str] = []

    checks = [
        ("volume_spike", _trigger_volume_spike(papers, baselines)),
        ("cross_domain", _trigger_cross_domain(papers)),
        ("novelty_burst", _trigger_novelty_burst(papers)),
        ("significance_surge", _trigger_significance_surge(papers, baselines)),
    ]

    for name, (fired, description) in checks:
        if fired:
            fired_triggers.append(description)
            fired_names.append(name)
            logger.info("Trigger fired: %s", name)

    should_report = len(fired_triggers) >= 1

    novelty_scores = [p.get("novelty_score", 0) for p in papers if p.get("novelty_score")]
    stats = {
        "paper_count": len(papers),
        "avg_novelty": round(statistics.mean(novelty_scores), 2) if novelty_scores else 0,
        "high_novelty_count": sum(1 for s in novelty_scores if s >= NOVELTY_THRESHOLD),
        "cross_domain_count": sum(1 for p in papers if len(_count_domains(p)) >= 2),
        "triggers_fired": len(fired_triggers),
    }

    logger.info(
        "Decision: should_report=%s, triggers=%s, stats=%s",
        should_report, fired_names, stats,
    )

    return {
        "should_report": should_report,
        "triggers": fired_triggers,
        "trigger_names": fired_names,
        "stats": stats,
    }
