"""
ARIA smoke test — runs without network or API calls.
All checks must pass before any deployment.
Run: python tests/smoke_test.py
"""

import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

PASS = []
FAIL = []


def check(name, condition, detail=""):
    if condition:
        PASS.append(name)
        print(f"  PASS  {name}")
    else:
        FAIL.append(name)
        print(f"  FAIL  {name}" + (f" — {detail}" if detail else ""))


# ── 1. Core imports ────────────────────────────────────────────────────────────
try:
    from core.analyst import Analyst, identify_cross_domain, BudgetExceeded, _charge, SESSION_SPEND_LIMIT_USD
    from core.budget_guard import BudgetGuard
    check("core.analyst imports", True)
except Exception as e:
    check("core.analyst imports", False, str(e))

try:
    from core.ingest import get_categories, fetch_papers
    check("core.ingest imports", True)
except Exception as e:
    check("core.ingest imports", False, str(e))

try:
    from core.decider import decide, _trigger_novelty_burst, _trigger_cross_domain
    check("core.decider imports", True)
except Exception as e:
    check("core.decider imports", False, str(e))

try:
    from core.store import Database
    check("core.store imports", True)
except Exception as e:
    check("core.store imports", False, str(e))

try:
    from core.reporter import generate_report, _select_notable_papers, _fallback_report
    check("core.reporter imports", True)
except Exception as e:
    check("core.reporter imports", False, str(e))


# ── 2. Config ─────────────────────────────────────────────────────────────────
try:
    from core.config import settings
    check("core.config loads", settings.novelty_threshold == 7 and settings.session_budget_usd == 5.0)
except Exception as e:
    check("core.config loads", False, str(e))


# ── 3. Budget guard ────────────────────────────────────────────────────────────
try:
    check("SESSION_SPEND_LIMIT_USD set", SESSION_SPEND_LIMIT_USD == 5.00,
          f"got {SESSION_SPEND_LIMIT_USD}")
except Exception as e:
    check("SESSION_SPEND_LIMIT_USD set", False, str(e))

try:
    guard = BudgetGuard(session_limit_usd=0.01)
    raised = False
    try:
        # 1M input tokens at Sonnet rates ($3/M) = $3.00 — well over $0.01 limit
        guard.record("claude-sonnet-4-6", 1_000_000, 0)
    except BudgetExceeded:
        raised = True
    check("BudgetExceeded raised when over limit", raised)
except Exception as e:
    check("BudgetExceeded raised when over limit", False, str(e))

try:
    guard2 = BudgetGuard(session_limit_usd=10.00)
    guard2.record("claude-haiku-4-5-20251001", 1000, 500)
    guard2.record("claude-sonnet-4-6", 500, 200)
    check(
        "budget guard tracks spend and call count",
        guard2.call_count == 2 and guard2.session_spend > 0 and len(guard2.summary()) > 0,
        f"count={guard2.call_count} spend={guard2.session_spend:.6f}",
    )
except Exception as e:
    check("budget guard tracks spend and call count", False, str(e))


# ── 4. identify_cross_domain ───────────────────────────────────────────────────
try:
    papers = [
        {"id": "1", "title": "T1", "categories": ["cs.AI", "cs.RO"]},
        {"id": "2", "title": "T2", "categories": ["cs.LG", "q-bio.NC"]},
        {"id": "3", "title": "T3", "categories": ["cs.CV"]},
    ]
    result = identify_cross_domain(papers)
    check("identify_cross_domain filters correctly", len(result) == 2,
          f"expected 2 cross-domain, got {len(result)}")
except Exception as e:
    check("identify_cross_domain filters correctly", False, str(e))


# ── 5. Decider triggers ────────────────────────────────────────────────────────
try:
    # 4 out of 5 papers score >= 7 (80% > 30% threshold) — should fire
    burst_papers = [{"novelty_score": 8.0}] * 4 + [{"novelty_score": 3.0}]
    fired, _ = _trigger_novelty_burst(burst_papers)
    check("decider novelty_burst trigger fires", fired,
          "expected trigger to fire with 80% high-novelty papers")
except Exception as e:
    check("decider novelty_burst trigger fires", False, str(e))

try:
    # 3 papers bridging cs.AI + cs.RO — meets CROSS_DOMAIN_MIN_PAPERS=3
    cd_papers = [{"categories": ["cs.AI", "cs.RO"]}] * 3 + [{"categories": ["cs.CV"]}]
    fired, _ = _trigger_cross_domain(cd_papers)
    check("decider cross_domain trigger fires", fired,
          "expected trigger to fire with 3 cross-domain papers")
except Exception as e:
    check("decider cross_domain trigger fires", False, str(e))

try:
    analyzed = [
        {"novelty_score": 8.5, "is_notable": True,  "categories": ["cs.AI"]},
        {"novelty_score": 8.0, "is_notable": True,  "categories": ["cs.LG"]},
        {"novelty_score": 3.0, "is_notable": False, "categories": ["cs.RO"]},
    ]
    decision = decide(analyzed, baselines=[])
    check("decider returns should_report key", "should_report" in decision,
          f"keys: {list(decision.keys())}")
except Exception as e:
    check("decider.decide runs without error", False, str(e))


# ── 6. _select_notable_papers ──────────────────────────────────────────────────
try:
    papers = [{"novelty_score": float(i)} for i in range(25)]
    top = _select_notable_papers(papers, max_papers=10)
    check("_select_notable_papers returns top 10",
          len(top) == 10 and top[0]["novelty_score"] == 24.0,
          f"got {len(top)} papers, top score {top[0]['novelty_score'] if top else 'N/A'}")
except Exception as e:
    check("_select_notable_papers returns top 10", False, str(e))


# ── 7. Database init and CRUD ─────────────────────────────────────────────────
temp_db = None
try:
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        temp_db = f.name

    with Database(temp_db) as db:
        db.init_db()
        db.save_papers([{
            "id": "smoke:001",
            "title": "Smoke Test Paper",
            "abstract": "An abstract.",
            "authors": ["Author A"],
            "categories": ["cs.AI"],
            "published": "2026-01-01",
        }])
        db.update_analysis("smoke:001", novelty_score=8.5, themes=["testing"])
        papers = db.get_recent_papers(hours=48)
        report_id = db.save_report("Test Report", "Content", ["novelty_burst"], 1)
        reports = db.get_reports(limit=5)
        report = db.get_report(report_id)

    check(
        "database init and CRUD",
        len(papers) == 1
        and papers[0]["id"] == "smoke:001"
        and len(reports) >= 1
        and report is not None
        and report["title"] == "Test Report",
        f"papers={len(papers)} reports={len(reports)}",
    )
except Exception as e:
    check("database init and CRUD", False, str(e))
finally:
    if temp_db and os.path.exists(temp_db):
        os.unlink(temp_db)


# ── 8. Reporter fallback ──────────────────────────────────────────────────────
try:
    report_text = _fallback_report(
        papers=[{
            "title": "Fallback Test Paper",
            "novelty_score": 8.0,
            "arxiv_url": "https://arxiv.org/abs/test001",
        }],
        decision={
            "stats": {"paper_count": 1, "avg_novelty": 8.0},
            "triggers": ["Novelty burst"],
            "trigger_names": ["novelty_burst"],
        },
        date="2026-05-05",
    )
    check(
        "reporter fallback report generates",
        "ARIA" in report_text and "2026-05-05" in report_text,
        "expected ARIA and date in output",
    )
except Exception as e:
    check("reporter fallback report generates", False, str(e))


# ── 9. .gitignore covers secrets ─────────────────────────────────────────────
try:
    gitignore_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".gitignore"
    )
    with open(gitignore_path) as f:
        content = f.read()
    required = [".env", "*.pem", "*.key"]
    missing = [r for r in required if r not in content]
    check(".gitignore covers secrets", len(missing) == 0, f"missing: {missing}")
except Exception as e:
    check(".gitignore covers secrets", False, str(e))


# ── Summary ────────────────────────────────────────────────────────────────────
total = len(PASS) + len(FAIL)
print(f"\n{len(PASS)}/{total} checks passed")
if FAIL:
    print(f"FAILED: {', '.join(FAIL)}")
    sys.exit(1)
else:
    print("All checks passed.")
    sys.exit(0)
