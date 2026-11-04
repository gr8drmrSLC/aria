"""
arxiv_counts.py - monthly arXiv category and cross-listing COUNTS from arXiv's own API (ADR-019).

Why: ARIA's daily sample covers about 9 hours of submissions, so it cannot say how big a field is or
how fast it grows. arXiv's API reports the total number of matching papers (opensearch:totalResults)
for any query, so counts for every month can be pulled with no sampling and no Claude cost.

What the numbers are: counts of papers by arXiv category TAG (primary or cross-listed, as chosen by
authors and moderators), by month of first submission. Nothing here measures content, quality,
performance or demand.

Politeness and safety: read-only GET requests, one at a time, at least 3.5 s apart (arXiv asks for
one request every 3 s), retries with backoff, identifies itself in the User-Agent. Results are cached
in a JSON file after every query, so a stopped run resumes where it left off and finished cells are
never fetched again.

Usage:  python scripts/arxiv_counts.py [--start 2020-01] [--end 2026-10] [--cache data/arxiv_counts.json]
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone

API = "https://export.arxiv.org/api/query"
MIN_GAP_SECONDS = 3.5
RETRIES = 4
USER_AGENT = "ARIA-research-monitor/1.0 (monthly category counts; read-only; github.com/gr8drmrSLC/aria)"

# Field definitions match scripts/trend_summary.py.
AI = "cat:cs.AI"
ML = "(cat:cs.LG OR cat:stat.ML)"
RO = "cat:cs.RO"
BIO = "cat:q-bio.*"
AI_OR_ML = "(cat:cs.AI OR cat:cs.LG OR cat:stat.ML)"

# name -> category clause (None = no category filter, i.e. all of arXiv)
SERIES = {
    "total": None,
    "AI": AI,
    "ML": ML,
    "RO": RO,
    "BIO": BIO,
    "AI&ML": f"{AI} AND {ML}",
    "RO&AI": f"{RO} AND {AI}",
    "RO&ML": f"{RO} AND {ML}",
    "RO&(AI|ML)": f"{RO} AND {AI_OR_ML}",
    "BIO&AI": f"{BIO} AND {AI}",
    "BIO&ML": f"{BIO} AND {ML}",
    "BIO&(AI|ML)": f"{BIO} AND {AI_OR_ML}",
    "BIO&RO": f"{BIO} AND {RO}",
}


def months(start: str, end: str) -> list[str]:
    """['2020-01', ...] inclusive."""
    y, m = map(int, start.split("-"))
    ey, em = map(int, end.split("-"))
    out = []
    while (y, m) <= (ey, em):
        out.append(f"{y}-{m:02d}")
        y, m = (y, m + 1) if m < 12 else (y + 1, 1)
    return out


def build_query(clause: str | None, month: str) -> str:
    y, m = map(int, month.split("-"))
    ny, nm = (y, m + 1) if m < 12 else (y + 1, 1)
    window = f"submittedDate:[{y}{m:02d}010000 TO {ny}{nm:02d}010000]"
    return window if clause is None else f"{clause} AND {window}"


def parse_total(xml: str) -> int | None:
    m = re.search(r"<opensearch:totalResults[^>]*>(\d+)<", xml)
    return int(m.group(1)) if m else None


def fetch_total(query: str) -> int | None:
    url = API + "?" + urllib.parse.urlencode({"search_query": query, "max_results": 1})
    delay = 10
    for attempt in range(RETRIES):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(req, timeout=60) as r:
                total = parse_total(r.read().decode("utf-8", "replace"))
            if total is not None:
                return total
        except Exception as exc:  # network error, 429, 503: back off and retry
            print(f"  retry {attempt + 1}/{RETRIES}: {exc}", file=sys.stderr)
        time.sleep(delay)
        delay *= 2
    return None


def load_cache(path: str) -> dict:
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict) and isinstance(data.get("counts"), dict):
            return data
    except FileNotFoundError:
        pass
    return {"counts": {}, "meta": {}}


def save_cache(path: str, data: dict) -> None:
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=1, sort_keys=True)
    os.replace(tmp, path)


def run(start: str, end: str, cache_path: str, sleep=time.sleep, fetch=fetch_total) -> dict:
    data = load_cache(cache_path)
    data["meta"] = {
        "source": "arXiv API opensearch:totalResults",
        "note": "Counts of papers by category tag (primary or cross-list) by month of first submission. Not a measure of content, quality or demand.",
        "series": {k: (v or "all arXiv") for k, v in SERIES.items()},
        "last_run": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
    todo = [(mo, name) for mo in months(start, end) for name in SERIES if f"{mo}|{name}" not in data["counts"]]
    print(f"{len(todo)} queries to fetch ({len(data['counts'])} already cached)")
    failed = []
    for i, (mo, name) in enumerate(todo, 1):
        total = fetch(build_query(SERIES[name], mo))
        if total is None:
            failed.append(f"{mo}|{name}")
        else:
            data["counts"][f"{mo}|{name}"] = total
            save_cache(cache_path, data)
        if i % 25 == 0:
            print(f"  {i}/{len(todo)} done, {len(failed)} failed")
        sleep(MIN_GAP_SECONDS)
    data["meta"]["failed_last_run"] = failed
    save_cache(cache_path, data)
    print(f"done. {len(data['counts'])} cells cached, {len(failed)} failed (rerun to retry them)")
    return data


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--start", default="2020-01")
    ap.add_argument("--end", default="2026-10")
    ap.add_argument("--cache", default=os.path.join("data", "arxiv_counts.json"))
    args = ap.parse_args(argv)
    run(args.start, args.end, args.cache)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
