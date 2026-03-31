"""
scripts/update_linkedin.py
Update the LinkedIn profile with ARIA content.

Uses the saved LinkedIn session from the job-search bot — no login automation,
no password required. Just loads the stored cookies and picks up the session.

Tasks:
  --about       Update the About section with the ARIA narrative
  --project     Add ARIA as a project in the Projects section
  --post        Take fresh dashboard screenshots, then publish the announcement post
  --all         Run all three tasks (default)
  --screenshots Take dashboard screenshots only, without posting

Usage:
  python scripts/update_linkedin.py --all
  python scripts/update_linkedin.py --post
  python scripts/update_linkedin.py --screenshots
  python scripts/update_linkedin.py --all --dry-run

Requires: playwright, playwright-stealth
Session file: ../job-search/data/sessions/linkedin_session.json
Dashboard:    http://localhost:5051  (must be running before --post or --screenshots)
"""

import argparse
import logging
import os
import random
import sys
import time

SESSION_PATH = os.path.normpath(os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "..", "job-search", "data", "sessions", "linkedin_session.json"
))

PROFILE_URL = "https://www.linkedin.com/in/stephenthoemmes/"
DASHBOARD_URL = "http://localhost:5051"
IMAGES_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "post_images")

# ── Content ───────────────────────────────────────────────────────────────────

ABOUT_TEXT = (
    "I'm not a software engineer. I don't write code from scratch. What I do is design "
    "systems — I identify a problem, map out what an automated solution should do, and use "
    "AI tools to build it. The result is usually something that keeps running on its own "
    "long after the initial build.\n\n"
    "ARIA is a good example. I wanted a way to monitor research across AI, machine learning, "
    "biology, and robotics without reading hundreds of papers a day. So I designed a system "
    "that does it automatically — it pulls every new submission from arXiv each morning, uses "
    "Claude AI to score each one for significance, and decides on its own whether what it "
    "found is worth writing a report about. No alerts telling it what to do. It just runs.\n\n"
    "The same underlying pattern — monitor a data source, apply AI analysis, make an autonomous "
    "decision, produce an output — is something I've applied to options trading and prediction "
    "markets as well. The domain changes. The structure doesn't.\n\n"
    "What I'm good at is seeing where that structure fits, defining what the system should "
    "decide and when, and building it in a way that doesn't require constant maintenance. "
    "The goal is always a tool that works while you're doing something else."
)

PROJECT_NAME = "ARIA — Autonomous Research Intelligence Agent"

PROJECT_DESCRIPTION = (
    "ARIA monitors the arXiv research database daily across artificial intelligence, machine "
    "learning, quantitative biology, and robotics. It uses the Claude API to score each new "
    "paper for novelty, tracks rolling baselines by category, and applies four independent "
    "anomaly triggers to decide autonomously whether the day's research activity is significant "
    "enough to publish an intelligence brief. When it decides yes, it writes one.\n\n"
    "Designed as a demonstration of a reusable pattern: any high-volume data source — research "
    "papers, market filings, pricing data, news feeds, job postings — can be monitored with "
    "the same architecture. The system ingests, analyzes, decides, and reports without ongoing "
    "human input.\n\n"
    "Built with Python, the Anthropic Claude API, arXiv API, SQLite, Flask, and APScheduler. "
    "Runs on a daily schedule on AWS EC2. "
    "Source: https://github.com/gr8drmrSLC/aria"
)

POST_TEXT = (
    "I built an agent that reads the entire arXiv AI, ML, biology, and robotics feed every "
    "morning and decides — without being asked — whether what it found is worth telling you about.\n\n"
    "It's called ARIA: Autonomous Research Intelligence Agent.\n\n"
    "Here's what it does on its own:\n\n"
    "Pulls every new paper from cs.AI, cs.LG, q-bio, and cs.RO via the arXiv API\n\n"
    "Asks Claude to score each paper for novelty on a scale of 0 to 10 and identify its core themes\n\n"
    "Runs four independent anomaly detectors against a rolling 30-day baseline:\n"
    "   Volume Spike: is today's submission count unusually high?\n"
    "   Cross-Domain Cluster: are AI and biology papers converging on the same idea?\n"
    "   Novelty Burst: is an unusual share of papers scoring high?\n"
    "   Significance Surge: is the average novelty score above baseline?\n\n"
    "When any detector fires, Claude drafts a full intelligence brief. "
    "Everything lands on a newspaper-style dashboard with a live paper feed and published reports.\n\n"
    "No daily prompt from me. No manual curation. ARIA runs at 07:00 UTC and decides.\n\n"
    "The interesting challenge was the decision layer. How do you give a system a principled "
    "standard for what counts as significant without hardcoding a fixed threshold? "
    "The answer is baseline-relative thresholds. ARIA learns what normal looks like for each "
    "category over 30 days and then flags meaningful deviations. The first month is bootstrapping. "
    "After that, it has its own sense of what is routine.\n\n"
    "Built with Python, the Anthropic Claude API, arXiv API, Flask, SQLite, and APScheduler.\n\n"
    "GitHub: https://github.com/gr8drmrSLC/aria"
)

# ── Logging ───────────────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-7s  %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)


def _delay(min_ms: int = 1000, max_ms: int = 2500):
    time.sleep(random.randint(min_ms, max_ms) / 1000)


def _screenshot(page, label: str):
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), f"screenshot_{label}.png")
    page.screenshot(path=path)
    log.info(f"Screenshot: {path}")


def _check_session(session_path: str):
    if not os.path.exists(session_path):
        log.error(f"LinkedIn session not found at: {session_path}")
        log.error("Run: cd job-search && python scripts/save_session.py  (choose LinkedIn)")
        sys.exit(1)
    log.info(f"Session: {session_path}")


def _build_context(playwright, session_path: str):
    """Launch headed Chromium with the saved LinkedIn session."""
    browser = playwright.chromium.launch(
        headless=False,
        args=["--no-sandbox", "--disable-dev-shm-usage"],
    )
    context = browser.new_context(
        storage_state=session_path,
        user_agent=(
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/131.0.0.0 Safari/537.36"
        ),
        viewport={"width": 1280, "height": 900},
    )
    page = context.new_page()
    try:
        from playwright_stealth import Stealth
        Stealth().apply_stealth_sync(page)
        log.info("Stealth patches applied")
    except ImportError:
        log.warning("playwright-stealth not installed — continuing without stealth")
    return browser, context, page


def _verify_login(page) -> bool:
    log.info("Verifying session...")
    page.goto("https://www.linkedin.com/feed/", timeout=20000)
    _delay(2000, 3500)
    url = page.url
    log.info(f"  Landed on: {url}")
    on_auth = any(s in url for s in ("login", "signup", "authwall", "checkpoint"))
    logged_in = "linkedin.com" in url and not on_auth
    if not logged_in:
        log.error("Session expired. Re-run: python job-search/scripts/save_session.py")
    return logged_in


def _click_link(page, href_fragment: str, label: str, timeout: int = 8000) -> bool:
    """Click an anchor link whose href contains href_fragment."""
    sel = f"a[href*='{href_fragment}']"
    try:
        el = page.wait_for_selector(sel, timeout=timeout, state="visible")
        if el:
            el.scroll_into_view_if_needed()
            _delay(400, 700)
            el.click()
            log.info(f"  Clicked {label}")
            return True
    except Exception as e:
        log.warning(f"  Link not found ({label}): {e}")
    return False


def _save_modal(page) -> bool:
    """Click the Save button inside the currently open modal."""
    save_selectors = [
        "button[aria-label='Save']",
        "div[role='dialog'] button:has-text('Save')",
        "div.artdeco-modal button:has-text('Save')",
        "button.artdeco-button--primary:has-text('Save')",
    ]
    for sel in save_selectors:
        try:
            el = page.wait_for_selector(sel, timeout=5000, state="visible")
            if el:
                el.scroll_into_view_if_needed()
                el.click()
                log.info(f"  Saved via: {sel}")
                return True
        except Exception:
            continue
    log.error("  Save button not found")
    return False


def _close_modal(page):
    """Dismiss the current modal without saving."""
    for sel in ["button[aria-label='Dismiss']", "button:has-text('Cancel')"]:
        try:
            el = page.query_selector(sel)
            if el and el.is_visible():
                el.click()
                _delay(500, 1000)
                return
        except Exception:
            continue


# ── Dashboard screenshots ─────────────────────────────────────────────────────

def take_dashboard_screenshots() -> list[str]:
    """
    Capture fresh screenshots of the ARIA dashboard using a headless browser.
    Returns list of absolute paths to the saved images.
    The dashboard must be running at DASHBOARD_URL before calling this.
    """
    import urllib.request
    log.info("=== Taking dashboard screenshots ===")

    # Verify dashboard is up
    try:
        urllib.request.urlopen(DASHBOARD_URL, timeout=5)
    except Exception:
        log.error(f"Dashboard not reachable at {DASHBOARD_URL} — start it first:")
        log.error("  python dashboard/app.py")
        return []

    os.makedirs(IMAGES_DIR, exist_ok=True)

    from playwright.sync_api import sync_playwright

    paths = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(viewport={"width": 1400, "height": 900})
        page = ctx.new_page()

        # Screenshot 1 — Dashboard homepage
        log.info(f"  Loading {DASHBOARD_URL}/")
        page.goto(f"{DASHBOARD_URL}/", timeout=15000)
        _delay(2000, 3000)
        path1 = os.path.join(IMAGES_DIR, "1_dashboard.png")
        page.screenshot(path=path1, full_page=False)
        paths.append(path1)
        log.info(f"  Saved: {path1}")

        # Screenshot 2 — Most recent intelligence brief
        links = page.query_selector_all("a[href^='/reports/']")
        report_href = None
        for link in links:
            href = link.get_attribute("href") or ""
            if href and href != "/reports" and "/reports/" in href:
                report_href = href
                break

        if report_href:
            report_url = f"{DASHBOARD_URL}{report_href}"
            log.info(f"  Loading {report_url}")
            page.goto(report_url, timeout=15000)
            _delay(2000, 3000)
            path2 = os.path.join(IMAGES_DIR, "2_report.png")
            page.screenshot(path=path2, full_page=False)
            paths.append(path2)
            log.info(f"  Saved: {path2}")
        else:
            log.warning("  No report detail link found on dashboard — skipping report screenshot")

        browser.close()

    log.info(f"  {len(paths)} screenshot(s) ready")
    return paths


# ── Task: Update About section ────────────────────────────────────────────────

def update_about(page, dry_run: bool = False) -> bool:
    log.info("=== Updating About section ===")

    page.goto(PROFILE_URL, timeout=20000)
    _delay(2500, 4000)
    _screenshot(page, "01_profile")

    if not _click_link(page, "add-edit/SUMMARY", "About edit link"):
        _screenshot(page, "01_summary_link_not_found")
        log.error("Cannot find About/Summary edit link")
        return False

    _delay(1500, 2500)
    _screenshot(page, "02_about_modal")

    textarea_sel = "textarea[id*='SUMMARY']"
    try:
        ta = page.wait_for_selector(textarea_sel, timeout=8000, state="visible")
        if not ta:
            raise RuntimeError("textarea not found")
    except Exception:
        _screenshot(page, "02_summary_textarea_not_found")
        log.error("Summary textarea not found in modal")
        return False

    log.info(f"  Current length: {len(ta.input_value())} chars")

    if dry_run:
        log.info("[DRY RUN] Would replace About with:")
        log.info(f"  {ABOUT_TEXT[:120]}...")
        _close_modal(page)
        return True

    ta.scroll_into_view_if_needed()
    ta.click()
    _delay(300, 600)
    page.keyboard.press("Control+a")
    _delay(200, 400)
    ta.fill(ABOUT_TEXT)
    _delay(600, 1200)
    _screenshot(page, "03_about_filled")

    if not _save_modal(page):
        return False

    _delay(2000, 3500)
    _screenshot(page, "04_about_saved")
    log.info("  About section updated")
    return True


# ── Task: Add ARIA project ────────────────────────────────────────────────────

def add_project(page, dry_run: bool = False) -> bool:
    log.info("=== Adding ARIA project ===")

    page.goto(PROFILE_URL, timeout=20000)
    _delay(2500, 4000)

    page.evaluate("window.scrollBy(0, 1200)")
    _delay(1000, 1800)
    _screenshot(page, "10_profile_scrolled")

    if not _click_link(page, "add-edit/PROJECT/", "Add project link"):
        _screenshot(page, "10_project_link_not_found")
        log.error("Cannot find Add project link")
        return False

    _delay(1500, 2500)
    _screenshot(page, "11_project_modal")

    if dry_run:
        log.info("[DRY RUN] Would fill:")
        log.info(f"  Name: {PROJECT_NAME}")
        log.info(f"  Desc: {PROJECT_DESCRIPTION[:80]}...")
        _close_modal(page)
        return True

    name_sel = "input[id*='PROJECT'][id*='single-line']"
    fallback_name_sel = "input[id*='PROJECT']:not([placeholder*='looking'])"
    try:
        name_el = page.wait_for_selector(name_sel, timeout=6000, state="visible")
        if not name_el:
            name_el = page.wait_for_selector(fallback_name_sel, timeout=4000, state="visible")
        name_el.fill(PROJECT_NAME)
        _delay(400, 700)
        log.info("  Project name filled")
    except Exception as e:
        log.error(f"  Project name field not found: {e}")
        _screenshot(page, "11_project_name_not_found")
        return False

    desc_sel = "textarea[id*='PROJECT']"
    try:
        desc_el = page.wait_for_selector(desc_sel, timeout=5000, state="visible")
        desc_el.fill(PROJECT_DESCRIPTION)
        _delay(500, 900)
        log.info("  Description filled")
    except Exception as e:
        log.warning(f"  Description field not found: {e}")

    try:
        month_sels = page.query_selector_all("select[name='month']")
        year_sels = page.query_selector_all("select[name='year']")
        visible_month = [s for s in month_sels if s.is_visible()]
        visible_year = [s for s in year_sels if s.is_visible()]
        if visible_month:
            visible_month[0].select_option(label="March")
            _delay(300, 500)
            log.info("  Start month: March")
        if visible_year:
            visible_year[0].select_option(label="2026")
            _delay(300, 500)
            log.info("  Start year: 2026")
    except Exception as e:
        log.warning(f"  Date fields: {e}")

    _screenshot(page, "12_project_filled")

    if not _save_modal(page):
        return False

    _delay(2500, 4000)
    _screenshot(page, "13_project_saved")
    log.info("  ARIA project added")
    return True


# ── Task: Create post with images ─────────────────────────────────────────────

def _focus_shadow_editor(page) -> bool:
    """
    LinkedIn's post composer is rendered inside a shadow DOM.
    This function walks all shadow roots to find the editor div and focuses it.
    Returns True if found and focused.
    """
    focused = page.evaluate("""
        () => {
            function findInShadow(root) {
                const walker = document.createTreeWalker(root, NodeFilter.SHOW_ELEMENT);
                let node;
                while (node = walker.nextNode()) {
                    if (node.contentEditable === 'true' &&
                        node.getAttribute('aria-label') === 'Text editor for creating content') {
                        node.focus();
                        node.click();
                        return true;
                    }
                    if (node.shadowRoot) {
                        if (findInShadow(node.shadowRoot)) return true;
                    }
                }
                return false;
            }
            return findInShadow(document);
        }
    """)
    return bool(focused)


def create_post(page, image_paths: list[str], dry_run: bool = False) -> bool:
    log.info("=== Creating ARIA announcement post ===")

    valid_images = [p for p in image_paths if os.path.isfile(p)]
    if valid_images:
        log.info(f"  Attaching {len(valid_images)} image(s): {[os.path.basename(p) for p in valid_images]}")
    else:
        log.warning("  No images found — post will be text only")

    page.goto("https://www.linkedin.com/feed/", timeout=20000)
    _delay(2500, 4000)
    _screenshot(page, "20_feed")

    if dry_run:
        # Just verify the Photo button and composer are accessible
        try:
            page.get_by_role("button", name="Photo").wait_for(state="visible", timeout=6000)
            log.info("[DRY RUN] Would attach images and post:")
            log.info(f"  Images: {[os.path.basename(p) for p in valid_images]}")
            log.info(f"  Text: {POST_TEXT[:120]}...")
        except Exception:
            log.info("[DRY RUN] Photo button not found on feed — post would proceed text-only")
        return True

    if valid_images:
        # ── Photo-first flow: opens media editor then text composer ────────────
        # Step 1: Click "Photo" on the feed header — opens the media editor modal
        try:
            photo_btn = page.get_by_role("button", name="Photo")
            photo_btn.wait_for(state="visible", timeout=8000)
            photo_btn.click()
            log.info("  Photo button clicked")
        except Exception as e:
            log.warning(f"  Photo button not found ({e}) — falling back to text-only flow")
            valid_images = []

    if valid_images:
        _delay(1500, 2500)
        _screenshot(page, "21_media_editor")

        # Step 2: Upload images via hidden file input (no native dialog needed)
        file_input = page.query_selector("input[type='file']")
        if file_input:
            file_input.set_input_files(valid_images)
            log.info(f"  Files uploaded: {[os.path.basename(p) for p in valid_images]}")
            _delay(3000, 5000)
            _screenshot(page, "22_files_set")
        else:
            log.warning("  File input not found — continuing without images")
            valid_images = []

        if valid_images:
            # Step 3: Click Next to advance to the text composer
            # exact=True avoids matching "Go to next page of document" pagination button
            try:
                next_btn = page.get_by_role("button", name="Next", exact=True)
                next_btn.wait_for(state="visible", timeout=8000)
                next_btn.click()
                log.info("  Clicked Next — advancing to text composer")
                _delay(2000, 3000)
                _screenshot(page, "23_text_composer")
            except Exception as e:
                log.error(f"  Next button not found: {e}")
                return False

    else:
        # ── Text-only flow ─────────────────────────────────────────────────────
        try:
            page.locator("text=Start a post").first.wait_for(state="visible", timeout=8000)
            page.locator("text=Start a post").first.click()
            log.info("  Opened text-only composer")
            _delay(2000, 3000)
            _screenshot(page, "21_text_composer")
        except Exception as e:
            _screenshot(page, "21_composer_not_opened")
            log.error(f"  Could not open composer: {e}")
            return False

    # ── Type text — editor is in shadow DOM ────────────────────────────────────
    focused = False
    for attempt in range(5):
        if _focus_shadow_editor(page):
            focused = True
            log.info("  Editor focused via shadow DOM")
            break
        _delay(800, 1200)

    if not focused:
        _screenshot(page, "24_editor_not_found")
        log.error("  Could not focus the shadow DOM editor")
        return False

    _delay(400, 700)
    page.keyboard.type(POST_TEXT, delay=random.randint(15, 35))
    log.info("  Post text typed")
    _delay(1000, 1500)
    _screenshot(page, "25_post_ready")

    # ── Publish ────────────────────────────────────────────────────────────────
    # Post button may also be in shadow DOM; try DOM walk first, then direct selectors
    posted = page.evaluate("""
        () => {
            function findPostBtn(root) {
                const walker = document.createTreeWalker(root, NodeFilter.SHOW_ELEMENT);
                let node;
                while (node = walker.nextNode()) {
                    const tag = node.tagName;
                    const text = (node.innerText || '').trim();
                    const label = node.getAttribute('aria-label') || '';
                    if (tag === 'BUTTON' && (text === 'Post' || label === 'Post')) {
                        node.click();
                        return true;
                    }
                    if (node.shadowRoot) {
                        if (findPostBtn(node.shadowRoot)) return true;
                    }
                }
                return false;
            }
            return findPostBtn(document);
        }
    """)

    if not posted:
        # Fallback to direct selectors
        for sel in ["button.share-actions__primary-action", "button[aria-label='Post']",
                    "button:has-text('Post')"]:
            try:
                el = page.wait_for_selector(sel, timeout=4000, state="visible")
                if el:
                    el.click()
                    posted = True
                    log.info(f"  Post button clicked via: {sel}")
                    break
            except Exception:
                continue

    if not posted:
        _screenshot(page, "25_post_btn_not_found")
        log.error("  Post button not found")
        return False

    _delay(3000, 5000)
    _screenshot(page, "26_posted")
    log.info("  Post published")
    return True


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Update LinkedIn profile with ARIA content")
    parser.add_argument("--about", action="store_true", help="Update About section")
    parser.add_argument("--project", action="store_true", help="Add ARIA project")
    parser.add_argument("--post", action="store_true", help="Take screenshots and publish post")
    parser.add_argument("--screenshots", action="store_true", help="Take dashboard screenshots only")
    parser.add_argument("--all", dest="run_all", action="store_true", help="Run all tasks (default)")
    parser.add_argument("--dry-run", action="store_true", help="Navigate forms but do not save")
    args = parser.parse_args()

    if not any([args.about, args.project, args.post, args.screenshots, args.run_all]):
        args.run_all = True

    if args.run_all:
        args.about = args.project = args.post = True

    if args.dry_run:
        log.info("DRY RUN — forms will be inspected but not saved")

    # Screenshots happen before LinkedIn session is needed
    image_paths = []
    if args.post or args.screenshots:
        image_paths = take_dashboard_screenshots()
        if args.screenshots:
            log.info(f"Screenshots saved to: {IMAGES_DIR}")
            return

    if not args.about and not args.project and not args.post:
        return

    _check_session(SESSION_PATH)

    from playwright.sync_api import sync_playwright

    with sync_playwright() as playwright:
        browser, context, page = _build_context(playwright, SESSION_PATH)
        try:
            if not _verify_login(page):
                log.error("Aborting — session invalid")
                sys.exit(1)

            results = {}

            if args.about:
                try:
                    results["about"] = update_about(page, dry_run=args.dry_run)
                except Exception as e:
                    log.error(f"About failed: {e}")
                    _screenshot(page, "err_about")
                    results["about"] = False

            if args.project:
                try:
                    results["project"] = add_project(page, dry_run=args.dry_run)
                except Exception as e:
                    log.error(f"Project failed: {e}")
                    _screenshot(page, "err_project")
                    results["project"] = False

            if args.post:
                try:
                    results["post"] = create_post(page, image_paths, dry_run=args.dry_run)
                except Exception as e:
                    log.error(f"Post failed: {e}")
                    _screenshot(page, "err_post")
                    results["post"] = False

            log.info("=== Results ===")
            all_ok = True
            for task, ok in results.items():
                status = "OK" if ok else "FAILED"
                if not ok:
                    all_ok = False
                log.info(f"  {task:12s}  {status}")

            sys.exit(0 if all_ok else 1)

        finally:
            browser.close()


if __name__ == "__main__":
    main()
