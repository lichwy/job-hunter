"""
LinkedIn auto-commenter: finds recent posts for new jobs and leaves a comment.
Run standalone:  LINKEDIN_PASSWORD=xxx python3 linkedin_commenter.py
Or imported by job_hunter.py after scraping new jobs.
"""

import json
import os
import time
import random
from pathlib import Path

from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout

BASE_DIR = Path(__file__).parent
COMMENTED_FILE = BASE_DIR / "commented_posts.json"

COMMENT_TEMPLATE = (
    "Hi there! I noticed {company} is hiring for a {title} role — "
    "this aligns closely with my background in HRBP and HR Business Partnering. "
    "Would love to connect and learn more about the opportunity!"
)


def load_commented() -> set:
    if COMMENTED_FILE.exists():
        with open(COMMENTED_FILE, encoding="utf-8") as f:
            return set(json.load(f))
    return set()


def save_commented(commented: set) -> None:
    with open(COMMENTED_FILE, "w", encoding="utf-8") as f:
        json.dump(sorted(commented), f)


def _random_delay(lo=1.5, hi=3.5):
    time.sleep(random.uniform(lo, hi))


def _login(page, email: str, password: str) -> bool:
    print("  Logging in to LinkedIn...")
    page.goto("https://www.linkedin.com/login", wait_until="domcontentloaded")
    _random_delay()
    page.fill('input[name="session_key"]', email)
    page.fill('input[name="session_password"]', password)
    _random_delay(0.5, 1.2)
    page.click('button[type="submit"]')
    try:
        page.wait_for_url("**/feed/**", timeout=15000)
        print("  Login successful.")
        return True
    except PlaywrightTimeout:
        print("  Login failed or unexpected redirect.")
        return False


def _search_posts(page, company: str, title: str) -> list[str]:
    """Search LinkedIn for recent posts mentioning this job and return post URLs."""
    query = f"{company} {title}"
    encoded = query.replace(" ", "%20")
    url = f"https://www.linkedin.com/search/results/content/?keywords={encoded}&sortBy=date_posted"
    page.goto(url, wait_until="domcontentloaded")
    _random_delay(2, 4)

    # Collect post URNs from search results
    post_links = page.eval_on_selector_all(
        'a[href*="/posts/"]',
        "els => els.map(e => e.href)"
    )
    # Deduplicate and filter to actual post URLs
    seen = set()
    results = []
    for link in post_links:
        # Normalize: strip query params
        base = link.split("?")[0]
        if base not in seen and "/posts/" in base:
            seen.add(base)
            results.append(base)
        if len(results) >= 3:
            break
    return results


def _post_comment(page, post_url: str, comment: str) -> bool:
    """Navigate to a post and leave a comment. Returns True on success."""
    try:
        page.goto(post_url, wait_until="domcontentloaded")
        _random_delay(2, 3)

        # Click the comment button/input area
        comment_btn = page.locator(
            'button:has-text("Comment"), '
            '[placeholder*="comment" i], '
            '.comments-comment-box__form button'
        ).first
        comment_btn.click(timeout=8000)
        _random_delay(0.8, 1.5)

        # Type into the active editor
        editor = page.locator('.ql-editor, [contenteditable="true"]').first
        editor.click()
        editor.type(comment, delay=40)
        _random_delay(1, 2)

        # Submit
        submit = page.locator(
            'button.comments-comment-box__submit-button, '
            'button:has-text("Post comment"), '
            'button[type="submit"]'
        ).first
        submit.click(timeout=8000)
        _random_delay(1.5, 2.5)
        print(f"    Commented on: {post_url}")
        return True
    except Exception as e:
        print(f"    Failed to comment on {post_url}: {e}")
        return False


def comment_on_new_jobs(new_jobs: list[dict], cfg: dict) -> None:
    email = cfg.get("linkedin_email", "")
    password = os.environ.get("LINKEDIN_PASSWORD", "")

    if not email:
        print("[LinkedIn] linkedin_email not set in config.json, skipping.")
        return
    if not password:
        print("[LinkedIn] LINKEDIN_PASSWORD env var not set, skipping.")
        return
    if not new_jobs:
        print("[LinkedIn] No new jobs, nothing to comment on.")
        return

    commented = load_commented()

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/122.0.0.0 Safari/537.36"
            )
        )
        page = context.new_page()

        if not _login(page, email, password):
            browser.close()
            return

        for job in new_jobs:
            company = (job.get("company") or "").strip()
            title = (job.get("title") or "").strip()
            if not company or not title:
                continue

            print(f"  Searching posts for: {company} — {title}")
            try:
                post_urls = _search_posts(page, company, title)
            except Exception as e:
                print(f"    Search failed: {e}")
                continue

            if not post_urls:
                print(f"    No posts found.")
                continue

            comment = COMMENT_TEMPLATE.format(company=company, title=title)
            commented_this_job = False

            for post_url in post_urls:
                if post_url in commented:
                    print(f"    Already commented: {post_url}")
                    continue
                success = _post_comment(page, post_url, comment)
                if success:
                    commented.add(post_url)
                    save_commented(commented)
                    commented_this_job = True
                    break  # one comment per job is enough
                _random_delay(2, 4)

            if not commented_this_job:
                print(f"    Could not comment for {company} — {title}")

            _random_delay(3, 6)  # pace between jobs

        browser.close()

    print("[LinkedIn] Done commenting.")


if __name__ == "__main__":
    import sys
    sys.path.insert(0, str(BASE_DIR))
    from job_hunter import load_config, load_seen_urls, scrape, is_blocked, job_key

    cfg = load_config()
    seen = load_seen_urls()
    all_jobs = scrape(cfg)
    blocklist = cfg.get("blocklist", {})
    seen_keys = set()
    new_jobs = []
    for j in all_jobs:
        if not j.get("job_url") or is_blocked(j, blocklist):
            continue
        key = job_key(j)
        if key in seen_keys or j["job_url"] in seen or key in seen:
            continue
        seen_keys.add(key)
        new_jobs.append(j)

    print(f"Found {len(new_jobs)} new jobs to comment on.")
    comment_on_new_jobs(new_jobs, cfg)
