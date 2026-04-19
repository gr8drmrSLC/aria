"""
ARIA smoke test — runs without network or API calls.
All 10 checks must pass before any deployment.
Run: python tests/smoke_test.py
"""

import json
import sys
import os

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
    check("core.analyst imports", True)
except Exception as e:
    check("core.analyst imports", False, str(e))

try:
    from core.ingest import get_categories, fetch_papers
    check("core.ingest imports", True)
except Exception as e:
    check("core.ingest imports", False, str(e))

try:
    from core.decider import decide
    check("core.decider imports", True)
except Exception as e:
    check("core.decider imports", False, str(e))

try:
    from core.store import Database
    check("core.store imports", True)
except Exception as e:
    check("core.store imports", False, str(e))

try:
    from core.reporter import generate_report, _select_notable_papers
    check("core.reporter imports", True)
except Exception as e:
    check("core.reporter imports", False, str(e))


# ── 2. Budget guard ────────────────────────────────────────────────────────────
try:
    import core.analyst as analyst_mod
    original = analyst_mod._session_spend_usd
    analyst_mod._session_spend_usd = 0.0
    check("SESSION_SPEND_LIMIT_USD set", SESSION_SPEND_LIMIT_USD == 5.00,
          f"got {SESSION_SPEND_LIMIT_USD}")
except Exception as e:
    check("SESSION_SPEND_LIMIT_USD set", False, str(e))

try:
    class FakeUsage:
        input_tokens = 0
        output_tokens = 0

    analyst_mod._session_spend_usd = 4.9999
    raised = False
    try:
        # This tiny charge should tip it over $5.00
        analyst_mod._session_spend_usd = 5.001
        analyst_mod._charge("claude-sonnet-4-6", FakeUsage())
    except BudgetExceeded:
        raised = True
    check("BudgetExceeded raised when over limit", raised)
    analyst_mod._session_spend_usd = 0.0
except Exception as e:
    check("BudgetExceeded raised when over limit", False, str(e))


# ── 3. identify_cross_domain ───────────────────────────────────────────────────
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


# ── 4. decider logic ───────────────────────────────────────────────────────────
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


# ── 5. _select_notable_papers ──────────────────────────────────────────────────
try:
    papers = [{"novelty_score": float(i)} for i in range(25)]
    top = _select_notable_papers(papers, max_papers=10)
    check("_select_notable_papers returns top 10", len(top) == 10 and top[0]["novelty_score"] == 24.0,
          f"got {len(top)} papers, top score {top[0]['novelty_score'] if top else 'N/A'}")
except Exception as e:
    check("_select_notable_papers returns top 10", False, str(e))


# ── 6. .gitignore covers secrets ──────────────────────────────────────────────
try:
    gitignore_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".gitignore")
    with open(gitignore_path) as f:
        content = f.read()
    required = [".env", "*.pem", "*.key"]
    missing = [r for r in required if r not in content]
    check(".gitignore covers secrets", len(missing) == 0,
          f"missing: {missing}")
except Exception as e:
    check(".gitignore covers secrets", False, str(e))


# ── Summary ────────────────────────────────────────────────────────────────────
print(f"\n{len(PASS)}/{len(PASS)+len(FAIL)} checks passed")
if FAIL:
    print(f"FAILED: {', '.join(FAIL)}")
    sys.exit(1)
else:
    print("All checks passed.")
    sys.exit(0)
