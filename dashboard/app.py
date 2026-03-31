"""
app.py — Flask dashboard for ARIA.

Serves the live paper feed, published intelligence reports, and agent stats.
Designed to run alongside the pipeline on EC2 (or locally for demo).
"""

import os
import sys

from dotenv import load_dotenv
from flask import Flask, abort, jsonify, render_template

# Load .env from project root
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env"))

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from core.store import Database  # noqa: E402

app = Flask(__name__)
app.config["JSON_SORT_KEYS"] = False

PORT = int(os.environ.get("ARIA_DASHBOARD_PORT", 5050))


def _get_db():
    db = Database()
    db.connect()
    db.init_db()
    return db


@app.route("/")
def index():
    db = _get_db()
    try:
        reports = db.get_reports(limit=10)
        papers = db.get_recent_papers(hours=48)
        stats = {
            "total_reports": len(db.get_reports(limit=1000)),
            "papers_today": db.get_paper_count_today(),
            "recent_papers": len(papers),
        }
    finally:
        db.close()

    return render_template("index.html", reports=reports, papers=papers, stats=stats)


@app.route("/reports")
def reports_list():
    db = _get_db()
    try:
        reports = db.get_reports(limit=50)
    finally:
        db.close()
    return render_template("index.html", reports=reports, papers=[], stats={})


@app.route("/reports/<int:report_id>")
def report_detail(report_id: int):
    db = _get_db()
    try:
        report = db.get_report(report_id)
    finally:
        db.close()
    if not report:
        abort(404)
    return render_template("report.html", report=report)


@app.route("/api/papers")
def api_papers():
    db = _get_db()
    try:
        papers = db.get_recent_papers(hours=24)
    finally:
        db.close()
    return jsonify(papers)


@app.route("/api/reports")
def api_reports():
    db = _get_db()
    try:
        reports = db.get_reports(limit=20)
    finally:
        db.close()
    return jsonify(reports)


@app.route("/api/stats")
def api_stats():
    db = _get_db()
    try:
        papers = db.get_recent_papers(hours=24)
        stats = {
            "papers_today": db.get_paper_count_today(),
            "reports_total": len(db.get_reports(limit=1000)),
            "avg_novelty": (
                round(sum(p.get("novelty_score", 0) for p in papers) / len(papers), 2)
                if papers else 0
            ),
        }
    finally:
        db.close()
    return jsonify(stats)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=PORT, debug=False)
