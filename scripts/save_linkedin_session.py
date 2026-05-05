"""
scripts/save_linkedin_session.py
One-time interactive login to save a LinkedIn session for this project.

Run once from the project root:
  python scripts/save_linkedin_session.py

A Chromium window opens to linkedin.com/login. Log in normally.
When you land on the feed, press Enter. The session is saved to
scripts/linkedin_session.json and all future posts use it automatically.

Re-run any time the session expires (LinkedIn sessions last ~2 years
but can be invalidated by password changes or security events).
"""

import os
import sys

SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
SESSION_PATH = os.path.join(SCRIPTS_DIR, "linkedin_session.json")


def main():
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("playwright not installed. Run: pip install playwright && playwright install chromium")
        sys.exit(1)

    print(f"\nSaving LinkedIn session to: {SESSION_PATH}")
    print("A browser window will open. Log in to LinkedIn, then press Enter here.\n")

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=False,
            args=["--no-sandbox", "--disable-dev-shm-usage"],
        )
        context = browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/131.0.0.0 Safari/537.36"
            ),
            viewport={"width": 1280, "height": 900},
        )
        page = context.new_page()
        page.goto("https://www.linkedin.com/login", timeout=30000)

        input("Log in to LinkedIn in the browser, then press Enter here when on the feed... ")

        context.storage_state(path=SESSION_PATH)
        context.close()
        browser.close()

    print(f"\nSession saved to {SESSION_PATH}")
    print("You can now run: python scripts/update_linkedin.py")


if __name__ == "__main__":
    main()
