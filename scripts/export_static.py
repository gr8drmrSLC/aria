"""
scripts/export_static.py
Generate a static snapshot of the ARIA dashboard for GitHub Pages.

Fetches rendered HTML from the live EC2 dashboard, rewrites internal links
to work as static files, and saves everything to docs/.

Usage:
  python scripts/export_static.py                         # uses ARIA_API env var
  ARIA_API=http://aria-agent.duckdns.org python scripts/export_static.py

Run automatically via GitHub Actions (.github/workflows/update-pages.yml).
Can also be run manually to force a refresh.
"""

import os
import re
import sys
from pathlib import Path

try:
    import requests
except ImportError:
    print("requests not installed. Run: pip install requests")
    sys.exit(1)

BASE = os.environ.get("ARIA_API", "http://aria-agent.duckdns.org").rstrip("/")
DOCS = Path(__file__).parent.parent / "docs"
TIMEOUT = 30


def fetch_html(path: str) -> str:
    url = f"{BASE}{path}"
    print(f"  GET {url}")
    r = requests.get(url, timeout=TIMEOUT)
    r.raise_for_status()
    return r.text


def rewrite_index(html: str) -> str:
    # /reports/N  ->  reports/N.html
    html = re.sub(r'href="/reports/(\d+)"', r'href="reports/\1.html"', html)
    # /reports (view-all link)  ->  index.html
    html = re.sub(r'href="/reports"', r'href="index.html"', html)
    return html


def rewrite_report(html: str) -> str:
    # href="/"  ->  ../index.html
    html = re.sub(r'href="/"', r'href="../index.html"', html)
    # /reports (breadcrumb/back links)  ->  ../index.html
    html = re.sub(r'href="/reports"', r'href="../index.html"', html)
    # /reports/N (cross-links between reports)  ->  N.html
    html = re.sub(r'href="/reports/(\d+)"', r'href="\1.html"', html)
    return html


def main():
    print(f"Exporting ARIA dashboard from {BASE}")

    DOCS.mkdir(exist_ok=True)
    (DOCS / "reports").mkdir(exist_ok=True)

    # ── Index page ────────────────────────────────────────────────
    print("\nIndex page:")
    html = fetch_html("/")
    html = rewrite_index(html)
    (DOCS / "index.html").write_text(html, encoding="utf-8")
    print("  Saved docs/index.html")

    # ── Report pages ──────────────────────────────────────────────
    try:
        reports = requests.get(f"{BASE}/api/reports?limit=50", timeout=TIMEOUT).json()
    except Exception as e:
        print(f"\nCould not fetch report list: {e}")
        reports = []

    if reports:
        print(f"\nReport pages ({len(reports)} reports):")
        for report in reports:
            rid = report.get("id")
            if rid is None:
                continue
            try:
                html = fetch_html(f"/reports/{rid}")
                html = rewrite_report(html)
                path = DOCS / "reports" / f"{rid}.html"
                path.write_text(html, encoding="utf-8")
                print(f"  Saved docs/reports/{rid}.html")
            except Exception as e:
                print(f"  WARN: could not fetch report {rid}: {e}")
    else:
        print("\nNo reports to export yet.")

    print(f"\nExport complete -> {DOCS}")


if __name__ == "__main__":
    main()
