"""
Scrapes jobs directly from company career pages.
Supports: Workday, Greenhouse, Built In.
"""
import re

import requests
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json",
}
TIMEOUT = 15


def _keyword_match(text: str, keywords: list[str]) -> bool:
    text = text.lower()
    return any(kw.lower() in text for kw in keywords)


def _location_match(text: str, locations) -> bool:
    """Match against a single location string or a list of them."""
    if isinstance(locations, str):
        locations = [locations]
    text = text.lower()
    cities = [loc.split(",")[0].strip().lower() for loc in locations]
    return any(city in text for city in cities)


# ── Greenhouse ────────────────────────────────────────────────────────────────

def scrape_greenhouse(entry: dict, keywords: list[str], locations) -> list[dict]:
    board = entry["board"]
    company = entry["company"]
    resp = requests.get(
        f"https://boards-api.greenhouse.io/v1/boards/{board}/jobs?content=true",
        headers=HEADERS, timeout=TIMEOUT,
    )
    resp.raise_for_status()
    jobs = []
    for job in resp.json().get("jobs", []):
        title = job.get("title", "")
        if not _keyword_match(title, keywords):
            continue
        loc = job.get("location", {}).get("name", "") or ""
        if not _location_match(loc, locations):
            continue
        jobs.append({
            "title": title,
            "company": company,
            "location": loc,
            "job_url": job.get("absolute_url", ""),
            "site": "greenhouse",
            "date_posted": (job.get("updated_at") or "")[:10],
        })
    return jobs


# ── Workday ───────────────────────────────────────────────────────────────────

def scrape_workday(entry: dict, keywords: list[str], locations) -> list[dict]:
    tenant = entry["tenant"]
    instance = entry.get("instance", "wd1")
    site = entry["site"]
    company = entry["company"]

    url = f"https://{tenant}.{instance}.myworkdayjobs.com/wday/cxs/{tenant}/{site}/jobs"
    body = {
        "searchText": " ".join(keywords),
        "limit": 20,
        "offset": 0,
        "appliedFacets": {},
    }
    resp = requests.post(url, json=body, headers=HEADERS, timeout=TIMEOUT)
    resp.raise_for_status()

    jobs = []
    for job in resp.json().get("jobPostings", []):
        title = job.get("title", "")
        if not _keyword_match(title, keywords):
            continue
        loc = job.get("locationsText", "") or ""
        if not _location_match(loc, locations):
            continue
        path = job.get("externalPath", "")
        jobs.append({
            "title": title,
            "company": company,
            "location": loc,
            "job_url": f"https://{tenant}.{instance}.myworkdayjobs.com/en-US/{site}{path}",
            "site": "workday",
            "date_posted": (job.get("postedOn") or "")[:10],
        })
    return jobs


# ── Built In ─────────────────────────────────────────────────────────────────

def scrape_builtin(entry: dict, keywords: list[str], locations) -> list[dict]:
    """Scrape Built In job search. Config entry fields:
        city  – URL slug, e.g. "seattle" (default "seattle")
        pages – how many pages to fetch (default 2)
    """
    city = entry.get("city", "seattle")
    max_pages = entry.get("pages", 2)
    jobs = []

    for kw in keywords:
        for page in range(1, max_pages + 1):
            url = f"https://builtin.com/jobs/{city}?search={requests.utils.quote(kw)}&page={page}"
            resp = requests.get(url, headers={**HEADERS, "Accept": "text/html"}, timeout=TIMEOUT)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "html.parser")
            cards = soup.find_all("div", attrs={"data-id": "job-card"})
            if not cards:
                break

            for card in cards:
                title_a = card.find("a", attrs={"data-id": "job-card-title"})
                co_a = card.find("a", attrs={"data-id": "company-title"})
                if not title_a:
                    continue
                title = title_a.get_text(strip=True)
                company = co_a.get_text(strip=True) if co_a else ""
                href = title_a.get("href", "")
                job_url = f"https://builtin.com{href}" if href.startswith("/") else href

                # Extract location, salary, date from spans
                loc, salary, date_posted = "", "", ""
                for span in card.find_all("span"):
                    txt = span.get_text(strip=True)
                    if not txt:
                        continue
                    parent_cls = span.parent.get("class", []) if span.parent else []
                    # Location: classless parent span with state/country abbreviation
                    if not parent_cls and re.search(r"\b[A-Z]{2}\b", txt):
                        loc = txt
                    # Salary: contains K and Annually/Hourly
                    elif "Annually" in txt or "Hourly" in txt:
                        if not salary:
                            salary = txt
                    # Date: contains "Ago"
                    elif "Ago" in txt and "bg-gray-01" in span.get("class", []):
                        date_posted = txt

                if not _keyword_match(title, keywords):
                    continue
                if not _location_match(loc, locations):
                    continue

                jobs.append({
                    "title": title,
                    "company": company,
                    "location": loc,
                    "job_url": job_url,
                    "site": "builtin",
                    "date_posted": date_posted,
                    "salary_text": salary,
                })

    # Deduplicate by URL
    seen = set()
    unique = []
    for j in jobs:
        if j["job_url"] not in seen:
            seen.add(j["job_url"])
            unique.append(j)
    return unique


# ── Router ────────────────────────────────────────────────────────────────────

_SCRAPERS = {
    "greenhouse": scrape_greenhouse,
    "workday": scrape_workday,
    "builtin": scrape_builtin,
}


def scrape_watchlist(watchlist: list[dict], keywords: list[str], locations) -> list[dict]:
    all_jobs = []
    for entry in watchlist:
        if entry.get("enabled") is False:
            note = entry.get("note", "disabled in config")
            print(f"  [watchlist] {entry.get('company')}: skipped ({note})")
            continue
        ats = entry.get("ats", "")
        scraper = _SCRAPERS.get(ats)
        if not scraper:
            print(f"  [watchlist] {entry.get('company')}: unknown ATS '{ats}', skipping")
            continue
        try:
            jobs = scraper(entry, keywords, locations)
            print(f"  [watchlist] {entry['company']}: {len(jobs)} jobs")
            all_jobs.extend(jobs)
        except Exception as e:
            print(f"  [watchlist] {entry['company']}: failed — {e}")
    return all_jobs
