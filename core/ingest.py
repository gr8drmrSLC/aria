"""
ARIA Ingest Module
------------------
This module provides functionality to fetch and parse research papers from the
arXiv API, specifically targeting AI, Machine Learning, Robotics, and
Quantitative Biology categories.
"""

import logging
import time
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone

import feedparser

# Configure logger
logger = logging.getLogger('aria.ingest')

# Constants
ARXIV_API_BASE_URL = "https://export.arxiv.org/api/query"
DEFAULT_CATEGORIES = ["cs.AI", "cs.LG", "q-bio.*", "cs.RO"]
MAX_RETRIES = 4
INITIAL_BACKOFF = 15  # seconds — arXiv rate limits require longer waits

def get_categories() -> list[str]:
    """Returns the list of monitored arXiv categories."""
    return DEFAULT_CATEGORIES

def fetch_papers(categories=None, max_results=200, date_filter=True) -> list[dict]:
    """
    Fetches papers from arXiv based on categories and filters.

    Args:
        categories: List of arXiv categories (e.g., ['cs.AI']). Defaults to DEFAULT_CATEGORIES.
        max_results: Maximum number of results to fetch.
        date_filter: If True, only returns papers submitted in the last 24 hours.

    Returns:
        List of dictionaries containing paper metadata.
    """
    if categories is None:
        categories = DEFAULT_CATEGORIES

    # Construct search query (e.g., cat:cs.AI+OR+cat:cs.LG)
    query_parts = [f"cat:{cat}" for cat in categories]
    search_query = "+OR+".join(query_parts)

    params = {
        "search_query": search_query,
        "max_results": max_results,
        "sortBy": "submittedDate",
        "sortOrder": "descending"
    }

    # URL encode parameters, keeping special arXiv characters like '+' and ':'
    encoded_params = urllib.parse.urlencode(params, safe=':+')
    request_url = f"{ARXIV_API_BASE_URL}?{encoded_params}"

    response_data = None
    for attempt in range(MAX_RETRIES + 1):
        try:
            logger.debug(f"Fetching from arXiv (attempt {attempt + 1}): {request_url}")
            with urllib.request.urlopen(request_url, timeout=30) as response:
                if response.status == 200:
                    response_data = response.read()
                    break
                elif response.status == 503:
                    logger.warning("arXiv API rate limit hit (503). Retrying...")
                else:
                    logger.error(f"Unexpected API response status: {response.status}")
        except Exception as e:
            logger.error(f"Error fetching from arXiv: {e}")

        if attempt < MAX_RETRIES:
            sleep_time = INITIAL_BACKOFF * (2 ** attempt)
            time.sleep(sleep_time)
        else:
            logger.error("Max retries reached. Failed to fetch papers.")
            return []

    if not response_data:
        return []

    feed = feedparser.parse(response_data)
    papers = []

    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(hours=24)

    for entry in feed.entries:
        try:
            # arXiv uses UTC Zulu format: 2023-10-25T13:45:00Z
            published_dt = datetime.strptime(entry.published, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)

            if date_filter and published_dt < cutoff:
                continue

            paper = {
                "id": entry.id.split('/abs/')[-1],
                "title": entry.title.replace('\n', ' ').strip(),
                "abstract": entry.summary.replace('\n', ' ').strip(),
                "authors": [author.name for author in entry.authors],
                "categories": [tag.term for tag in entry.tags],
                "published": entry.published,
                "arxiv_url": entry.link
            }
            papers.append(paper)
        except Exception as e:
            logger.warning(f"Failed to parse entry: {e}")
            continue

    return papers

if __name__ == "__main__":
    # Basic logging setup for demonstration
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    print(f"Monitoring categories: {', '.join(get_categories())}")
    print("Fetching new papers (last 24 hours)...")

    results = fetch_papers(date_filter=True)

    print(f"\nSummary: Found {len(results)} new papers.")
    print("-" * 40)

    for i, p in enumerate(results, 1):
        print(f"{i}. {p['title']}")
        print(f"   ID: {p['id']} | Published: {p['published']}")
        print(f"   Authors: {', '.join(p['authors'][:3])}{'...' if len(p['authors']) > 3 else ''}")
        print(f"   URL: {p['arxiv_url']}\n")
