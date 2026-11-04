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
    from core.decider import _count_domains
    ok = (
        _count_domains({"categories": ["cs.CV"]}) == set()                    # not a monitored domain
        and _count_domains({"categories": ["cs.AI", "cs.LG"]}) == {"ai_ml"}   # one domain, not two
        and _count_domains({"categories": ["cs.AI", "cs.RO"]}) == {"ai_ml", "robotics"}
        and _count_domains({"categories": ["cs.LG", "q-bio.NC"]}) == {"ai_ml", "bio"}
    )
    check("decider domain matching has no cs.* prefix leak", ok,
          "cs.CV must not count as a monitored domain (ADR-016)")
except Exception as e:
    check("decider domain matching has no cs.* prefix leak", False, str(e))

try:
    from core.decider import build_history
    def _day(d, hi_share, n=20):
        k = round(n * hi_share)
        return ([{"categories": ["cs.AI"], "novelty_score": 8.5, "ingested_at": f"{d}T07:00:00"}] * k
                + [{"categories": ["cs.AI"], "novelty_score": 6.0, "ingested_at": f"{d}T07:00:00"}] * (n - k))
    rows = []
    for i in range(14):   # 14 quiet days with a small wobble in the high-novelty share
        rows += _day(f"2026-05-{i + 1:02d}", 0.10 + 0.05 * (i % 2))
    hist = build_history(rows, "2026-05-20")
    calm = _day("2026-05-20", 0.10)
    spike = _day("2026-05-20", 0.80)
    d_calm, d_spike = decide(calm, [], hist), decide(spike, [], hist)
    check("decider relative mode: quiet day does not report",
          d_calm["mode"] == "relative" and not d_calm["should_report"], str(d_calm["trigger_names"]))
    check("decider relative mode: genuine spike reports",
          d_spike["should_report"] and "novelty_burst" in d_spike["trigger_names"], str(d_spike["trigger_names"]))
    failed_day = [{"categories": ["cs.AI"], "novelty_score": 0, "ingested_at": "2026-05-15T07:00:00"}] * 20
    check("build_history drops unscored (failed-analysis) days",
          len(build_history(rows + failed_day, "2026-05-20")) == len(hist), "unscored day leaked into baseline")
except Exception as e:
    check("decider relative mode checks", False, str(e))

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


# ── 10. Weekly post writer (ADR-017) ──────────────────────────────────────────
try:
    from datetime import datetime, timezone
    from types import SimpleNamespace
    from core import postwriter as pw

    _now = datetime(2026, 11, 8, tzinfo=timezone.utc)
    _content = chr(10).join([
        "# Brief", "", "## Executive Summary", "", "World models meet proofs, 62% novelty.", "",
        "## Key Findings", "",
        "- **Formal proofs for agents.** [Algebraic World Model: From Exploration to Proofs]"
        "(https://arxiv.org/abs/2610.40503v1) does things.", "",
    ])
    _reports = [
        {"id": 90, "created_at": "2026-11-05T07:00:00+00:00", "paper_count": 200,
         "triggers": ["novelty_burst"], "content": _content},
        {"id": 87, "created_at": "2026-11-02T07:00:00+00:00", "paper_count": 150,
         "triggers": ["Cross-domain cluster: 193"], "content": _content},
        {"id": 50, "created_at": "2026-10-01T07:00:00+00:00", "paper_count": 99, "content": _content},
    ]
    _facts = pw.build_facts(_reports, _now)
    check("postwriter facts: window filter and counts",
          _facts["report_count"] == 2 and _facts["paper_count"] == 350, str(_facts["report_count"]))
    check("postwriter facts: legacy triggers hidden, new ones kept",
          "triggers" in _facts["reports"][0] and "triggers" not in _facts["reports"][1], "")

    _title = "Algebraic World Model: From Exploration to Proofs"
    _good = f"This week ARIA flagged {_title}, which pairs search with formal proofs. These are model readings of abstracts, not verified results."
    check("postwriter accepts a grounded draft", pw.validate(_good, _facts, []) == [], str(pw.validate(_good, _facts, [])))
    check("postwriter rejects invented numbers", any("number" in x for x in pw.validate(_good + " It scored 96.5.", _facts, [])), "")
    check("postwriter rejects banned wording", any("banned" in x for x in pw.validate(_good + " It is autonomous.", _facts, [])), "")
    check("postwriter rejects ungrounded draft", any("exact title" in x for x in pw.validate("Something interesting happened.", _facts, [])), "")
    _hist = [{"key": "weekly:x", "posted_at": "2026-11-03T00:00:00+00:00", "had_intro": True, "text": _good}]
    check("postwriter rejects a near-duplicate of a past post", any("similar" in x for x in pw.validate(_good, _facts, _hist)), "")
    check("postwriter intro rule: no intro within 28 days, intro after",
          not pw.wants_intro(_hist, _now) and pw.wants_intro(_hist, datetime(2026, 12, 20, tzinfo=timezone.utc)), "")

    class _FakeClient:
        def __init__(self, texts):
            self.texts, self.calls = list(texts), 0
            self.messages = SimpleNamespace(create=self._create)
        def _create(self, **kw):
            self.calls += 1
            return SimpleNamespace(content=[SimpleNamespace(text=self.texts.pop(0))],
                                   usage=SimpleNamespace(input_tokens=1000, output_tokens=200))

    _fc = _FakeClient(["no title here", _good])
    check("postwriter retries after a rejected draft and charges the guard",
          pw.generate_post(_facts, [], False, client=_fc) == _good and _fc.calls == 2, str(_fc.calls))
    _fc2 = _FakeClient(["bad"] * pw.MAX_ATTEMPTS)
    try:
        pw.generate_post(_facts, [], False, client=_fc2)
        check("postwriter raises PostRejected when nothing passes", False, "no exception")
    except pw.PostRejected:
        check("postwriter raises PostRejected when nothing passes", _fc2.calls == pw.MAX_ATTEMPTS, str(_fc2.calls))
    _daily = pw.build_daily_facts(_reports[0])
    check("postwriter daily facts: one brief, kind daily",
          _daily["kind"] == "daily" and _daily["report_count"] == 1 and _daily["paper_count"] == 200, "")
    _stats = pw.build_stats_facts({"reports_total": 87, "avg_novelty": 6.8})
    check("postwriter stats facts: built only when numbers exist",
          _stats is not None and pw.build_stats_facts({"reports_total": 87, "avg_novelty": 0}) is None, "")
    _ok_stats = "ARIA has now filed 87 briefs. The latest average novelty score is 6.8 out of 10, a model reading of abstracts."
    check("postwriter stats post needs no paper title but still rejects invented numbers",
          pw.validate(_ok_stats, _stats, []) == [] and any("number" in x for x in pw.validate(_ok_stats + " That is up 12.", _stats, [])), "")
except Exception as e:
    check("postwriter checks run", False, repr(e))


from datetime import date, timedelta  # noqa: E402

# ── 11. Trend summary (ADR-018) ────────────────────────────────────────────────
try:
    import importlib.util as _ilu
    _sp = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts", "trend_summary.py")
    _spec = _ilu.spec_from_file_location("trend_summary", _sp)
    ts = _ilu.module_from_spec(_spec)
    _spec.loader.exec_module(ts)

    check("trend fields: AI and ML are separate, ML includes stat.ML",
          ts.field_flags(["cs.AI"]) == {"AI": True, "ML": False, "RO": False, "BIO": False}
          and ts.field_flags(["stat.ML"])["ML"] and ts.field_flags(["q-bio.GN"])["BIO"], "")
    _lab = ts.paper_labels(["cs.AI", "cs.LG"])
    check("trend labels: AI+ML overlap counts as multi-field, plain AI does not",
          _lab["AI&ML"] and _lab["multi"] and not ts.paper_labels(["cs.AI"])["multi"], "")
    check("trend stats: spearman is 1 for monotone data, interval needs 2+ runs",
          abs(ts.spearman([1, 2, 3, 4], [10, 20, 30, 40]) - 1) < 1e-9 and ts.interval([0.5])[1] != ts.interval([0.5])[1], "")

    def _mkrun(n_ai, n_ml, n=200):
        return [{"labels": ts.paper_labels((["cs.AI"] if i < n_ai else []) + (["cs.LG"] if i < n_ml else [])),
                 "nov": 7} for i in range(n)]
    _runs = {}
    for wk in range(10):
        for day in (6, 7, 8):  # three runs per week
            d = date(2026, 5, 4) + timedelta(days=7 * wk + day - 6)
            _runs[d.isoformat()] = _mkrun(100, 60)
    _runs["2026-09-01"] = _mkrun(10, 10, n=50)  # failed/partial run: excluded
    _res = ts.summarize(_runs)
    check("trend summary: weeks built, partial run excluded, shares correct",
          len(_res["weeks"]) == 10 and _res["runs_excluded"] == 1
          and abs(_res["weeks"][0]["shares"]["AI"]["share"] - 0.5) < 1e-9, str(len(_res["weeks"])))
    check("trend summary: every exploratory test is labelled with its family size",
          all(t["tests_in_family"] == 9 for t in _res["exploratory_tests"]) and len(_res["caveats"]) >= 5, "")
except Exception as e:
    check("trend summary checks run", False, repr(e))

# ── Summary ────────────────────────────────────────────────────────────────────
total = len(PASS) + len(FAIL)
print(f"\n{len(PASS)}/{total} checks passed")
if FAIL:
    print(f"FAILED: {', '.join(FAIL)}")
    sys.exit(1)
else:
    print("All checks passed.")
    sys.exit(0)
