import json
import os
import smtplib
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

from jobspy import scrape_jobs

from watchlist_scraper import scrape_watchlist

BASE_DIR = Path(__file__).parent
CONFIG_FILE = BASE_DIR / "config.json"
SEEN_JOBS_FILE = BASE_DIR / "seen_jobs.json"


def load_config() -> dict:
    with open(CONFIG_FILE, encoding="utf-8") as f:
        return json.load(f)


def load_seen_urls() -> set:
    if SEEN_JOBS_FILE.exists():
        with open(SEEN_JOBS_FILE, encoding="utf-8") as f:
            return set(json.load(f))
    return set()


def save_seen_urls(seen: set) -> None:
    with open(SEEN_JOBS_FILE, "w", encoding="utf-8") as f:
        json.dump(sorted(seen), f)


def job_key(job: dict) -> str:
    title = (job.get("title") or "").strip().lower()
    company = (job.get("company") or "").strip().lower()
    return f"{title}||{company}"


def is_blocked(job: dict, blocklist: dict) -> bool:
    company = (job.get("company") or "").strip().lower()
    if company in [c.lower() for c in blocklist.get("companies", [])]:
        return True
    title = (job.get("title") or "").lower()
    if any(kw.lower() in title for kw in blocklist.get("title_keywords", [])):
        return True
    return False


def scrape(cfg: dict) -> list[dict]:
    search = cfg["search"]
    locations = search.get("locations") or [search.get("location", "Seattle, WA")]
    results = []

    for site in search.get("sites", ["linkedin", "indeed"]):
        site_total = 0
        for location in locations:
            try:
                df = scrape_jobs(
                    site_name=[site],
                    search_term=search["query"],
                    location=location,
                    results_wanted=search["results_wanted"],
                    hours_old=search["hours_old"],
                )
                if df is not None and not df.empty:
                    results.extend(df.to_dict("records"))
                    site_total += len(df)
            except Exception as e:
                print(f"  {site} ({location}): failed — {e}")
        if site_total:
            print(f"  {site}: {site_total} jobs across {len(locations)} cities")

    watchlist = cfg.get("watchlist", [])
    if watchlist:
        keywords = search.get("keywords", ["HRBP", "HR Business Partner"])
        results.extend(scrape_watchlist(watchlist, keywords, locations))

    return results


def _job_table(jobs: list[dict], total: int, cap: int) -> str:
    rows = ""
    for j in jobs:
        title = j.get("title") or "N/A"
        company = j.get("company") or "N/A"
        location = j.get("location") or "N/A"
        url = j.get("job_url") or ""
        site = (j.get("site") or "").capitalize()
        date_posted = j.get("date_posted") or ""
        title_cell = f'<a href="{url}" style="color:#1a6fc4;">{title}</a>' if url else title
        rows += f"""
        <tr>
          <td style="padding:8px 12px;">{title_cell}</td>
          <td style="padding:8px 12px;">{company}</td>
          <td style="padding:8px 12px;">{location}</td>
          <td style="padding:8px 12px;">{site}</td>
          <td style="padding:8px 12px;">{date_posted}</td>
        </tr>"""

    cap_note = (
        f'<p style="color:#e07000;margin:4px 0;">Showing {cap} of {total} — '
        f'{total - cap} more omitted (raise <code>max_email_jobs</code> in config.json to see all)</p>'
        if total > cap else ""
    )
    return f"""{cap_note}
<table border="1" cellpadding="0" cellspacing="0"
       style="border-collapse:collapse;width:100%;font-size:14px;margin-bottom:32px;">
  <thead style="background:#f5f5f5;">
    <tr>
      <th style="padding:8px 12px;text-align:left;">Title</th>
      <th style="padding:8px 12px;text-align:left;">Company</th>
      <th style="padding:8px 12px;text-align:left;">Location</th>
      <th style="padding:8px 12px;text-align:left;">Source</th>
      <th style="padding:8px 12px;text-align:left;">Posted</th>
    </tr>
  </thead>
  <tbody>{rows}
  </tbody>
</table>"""


def build_html(new_jobs: list[dict], old_jobs: list[dict], cap: int) -> str:
    date_str = datetime.now().strftime("%Y-%m-%d")

    new_section = ""
    if new_jobs:
        display = new_jobs[:cap]
        new_section = f"""
<h2 style="color:#1a6fc4;margin-top:0;">🆕 New Jobs · {len(new_jobs)} found</h2>
{_job_table(display, len(new_jobs), cap)}"""
    else:
        new_section = '<h2 style="color:#1a6fc4;margin-top:0;">🆕 New Jobs</h2><p style="color:#888;">No new jobs today.</p>'

    old_section = ""
    if old_jobs:
        display = old_jobs[:cap]
        old_section = f"""
<h2 style="color:#555;border-top:2px solid #eee;padding-top:24px;">📋 Still Active · {len(old_jobs)} previously seen</h2>
<p style="color:#888;font-size:13px;margin-top:-8px;">These jobs appeared in today's search but were already sent before.</p>
{_job_table(display, len(old_jobs), cap)}"""

    return f"""
<html><body style="font-family:Arial,sans-serif;color:#333;max-width:900px;">
<p style="color:#888;font-size:13px;margin-bottom:24px;">{date_str} · Seattle area HRBP · job_hunter</p>
{new_section}
{old_section}
</body></html>"""


def send_email(new_jobs: list[dict], old_jobs: list[dict], cfg: dict) -> None:
    password = os.environ.get("GMAIL_APP_PASSWORD", "")
    if not password:
        raise RuntimeError("GMAIL_APP_PASSWORD environment variable not set.")

    cap = cfg.get("max_email_jobs", 100)
    html = build_html(new_jobs, old_jobs, cap)

    new_count = len(new_jobs)
    old_count = len(old_jobs)
    subject_parts = []
    if new_count:
        subject_parts.append(f"{new_count} new")
    if old_count:
        subject_parts.append(f"{old_count} still active")
    subject = f"[Job Hunter] Seattle HRBP · {datetime.now().strftime('%Y-%m-%d')} · {', '.join(subject_parts)}"

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = cfg["sender_email"]
    msg["To"] = ", ".join(cfg["recipients"])
    msg.attach(MIMEText(html, "html", "utf-8"))

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(cfg["sender_email"], password)
        server.sendmail(cfg["sender_email"], cfg["recipients"], msg.as_string())

    print(f"Email sent to {cfg['recipients']}")


def main() -> None:
    print(f"=== job_hunter started {datetime.now().strftime('%Y-%m-%d %H:%M')} ===")

    cfg = load_config()
    seen = load_seen_urls()
    all_jobs = scrape(cfg)

    if not all_jobs:
        print("No jobs scraped, exiting.")
        return

    blocklist = cfg.get("blocklist", {})
    new_jobs = []
    old_jobs = []
    seen_keys_this_run = set()

    for j in all_jobs:
        if not j.get("job_url") or is_blocked(j, blocklist):
            continue
        url = j["job_url"]
        key = job_key(j)
        if key in seen_keys_this_run:
            continue  # cross-platform duplicate within this run
        seen_keys_this_run.add(key)
        if url in seen or key in seen:
            old_jobs.append(j)
        else:
            new_jobs.append(j)

    blocked_count = sum(1 for j in all_jobs if is_blocked(j, blocklist))
    print(f"Total: {len(all_jobs)}, blocked: {blocked_count}, new: {len(new_jobs)}, still active: {len(old_jobs)}")

    # Persist after sorting so new jobs are marked seen next time
    for j in all_jobs:
        if j.get("job_url"):
            seen.add(j["job_url"])
            seen.add(job_key(j))
    save_seen_urls(seen)

    if new_jobs or old_jobs:
        send_email(new_jobs, old_jobs, cfg)
    else:
        print("Nothing to send.")

    print("=== Done ===")


if __name__ == "__main__":
    main()
