"""
runner.py — Main orchestrator for ARIA.

Runs the full pipeline: ingest → store → analyze → decide → report → store report.
Can run once (--once) or on a daily schedule via APScheduler.

Usage:
    python runner.py --once          # Run immediately and exit
    python runner.py                 # Run on daily schedule (default 07:00 UTC)
    python runner.py --hour 9        # Schedule at 09:00 UTC daily
"""

import argparse
import logging
import os
import sys
from datetime import datetime, timezone

# Ensure project root is on path when run directly
sys.path.insert(0, os.path.dirname(__file__))

from core.ingest import fetch_papers, get_categories
from core.store import Database
from core.analyst import Analyst, identify_cross_domain
from core.decider import decide
from core.reporter import generate_report

LOG_LEVEL = os.environ.get("ARIA_LOG_LEVEL", "INFO").upper()
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.INFO),
    format="%(asctime)s %(levelname)-8s %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("logs/aria.log", encoding="utf-8"),
    ],
)
logger = logging.getLogger("aria.runner")


def run_pipeline() -> dict:
    """
    Execute one full ARIA pipeline cycle.

    Returns a summary dict with run statistics.
    """
    run_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    logger.info("=== ARIA pipeline starting — %s ===", run_date)

    with Database() as db:
        db.init_db()

        # 1. Ingest
        logger.info("Step 1/5: Ingesting papers from arXiv")
        papers = fetch_papers(max_results=200, date_filter=True)
        if not papers:
            logger.warning("No papers fetched — arXiv may be unavailable or no new submissions today")
            return {"status": "no_papers", "date": run_date}

        db.save_papers(papers)
        logger.info("Saved %d papers to database", len(papers))

        # 2. Analyze
        logger.info("Step 2/5: Analyzing papers with Claude")
        analyst = Analyst()
        analyzed = analyst.analyze_papers(papers)

        for paper in analyzed:
            if paper.get("novelty_score") is not None:
                db.update_analysis(
                    paper["id"],
                    paper["novelty_score"],
                    paper.get("themes", []),
                )

        # 3. Update baselines
        logger.info("Step 3/5: Updating baselines")
        categories = get_categories()
        for category in categories:
            cat_papers = [
                p for p in analyzed
                if any(c.startswith(category.split(".")[0]) for c in p.get("categories", []))
            ]
            if cat_papers:
                scores = [p.get("novelty_score", 0) for p in cat_papers if p.get("novelty_score")]
                avg_novelty = sum(scores) / len(scores) if scores else 0.0
                db.update_baseline(category, run_date, len(cat_papers), avg_novelty)

        # 4. Decide
        logger.info("Step 4/5: Running anomaly detection")
        # Aggregate baselines across all categories for decision making
        all_baselines = []
        for category in categories:
            all_baselines.extend(db.get_baselines(category, days=30))

        decision = decide(analyzed, all_baselines)
        logger.info(
            "Decision: should_report=%s, triggers=%s",
            decision["should_report"],
            decision["trigger_names"],
        )

        # 5. Generate and store report
        report_id = None
        if decision["should_report"]:
            logger.info("Step 5/5: Generating intelligence brief")
            report = generate_report(analyzed, decision, date=run_date)
            report_id = db.save_report(
                report["title"],
                report["content"],
                report["triggers"],
                report["paper_count"],
            )
            logger.info("Report #%d saved: %s", report_id, report["title"])
        else:
            logger.info("Step 5/5: No anomalies detected — no report generated")

    summary = {
        "status": "ok",
        "date": run_date,
        "papers_ingested": len(papers),
        "papers_analyzed": len(analyzed),
        "triggers_fired": decision["trigger_names"],
        "report_generated": decision["should_report"],
        "report_id": report_id,
    }
    logger.info("=== ARIA pipeline complete: %s ===", summary)
    return summary


def main():
    parser = argparse.ArgumentParser(description="ARIA — Autonomous Research Intelligence Agent")
    parser.add_argument(
        "--once",
        action="store_true",
        help="Run the pipeline once and exit",
    )
    parser.add_argument(
        "--hour",
        type=int,
        default=7,
        help="UTC hour to run the daily pipeline (default: 7)",
    )
    args = parser.parse_args()

    if args.once:
        result = run_pipeline()
        print(f"\nRun complete: {result}")
        sys.exit(0)

    # Scheduled mode
    try:
        from apscheduler.schedulers.blocking import BlockingScheduler
    except ImportError:
        logger.error("APScheduler not installed. Run: pip install apscheduler")
        sys.exit(1)

    scheduler = BlockingScheduler(timezone="UTC")
    scheduler.add_job(run_pipeline, "cron", hour=args.hour, minute=0)
    logger.info("ARIA scheduler started — running daily at %02d:00 UTC", args.hour)
    logger.info("Press Ctrl+C to stop")

    try:
        scheduler.start()
    except KeyboardInterrupt:
        logger.info("ARIA scheduler stopped")


if __name__ == "__main__":
    main()
