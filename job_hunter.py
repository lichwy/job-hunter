import json
import os
import smtplib
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

from jobspy import scrape_jobs

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
    """Normalized title+company key for cross-platform deduplication."""
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
    results = []
    for site in ("linkedin", "indeed"):
        try:
            df = scrape_jobs(
                site_name=[site],
                search_term=search["query"],
                location=search["location"],
                results_wanted=search["results_wanted"],
                hours_old=search["hours_old"],
            )
            if df is not None and not df.empty:
                results.extend(df.to_dict("records"))
                print(f"  {site}: 抓到 {len(df)} 条")
        except Exception as e:
            print(f"  {site}: 抓取失败 — {e}")
    return results


def build_html(jobs: list[dict]) -> str:
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

    return f"""
<html><body style="font-family:Arial,sans-serif;color:#333;">
<h2 style="color:#1a6fc4;">Seattle HRBP New Jobs · {datetime.now().strftime('%Y-%m-%d')}</h2>
<p><strong>{len(jobs)}</strong> new jobs found (LinkedIn + Indeed)</p>
<table border="1" cellpadding="0" cellspacing="0"
       style="border-collapse:collapse;width:100%;font-size:14px;">
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
</table>
<p style="color:#888;font-size:12px;margin-top:20px;">Sent by job_hunter · edit config.json to customize</p>
</body></html>"""


def send_email(jobs: list[dict], cfg: dict) -> None:
    password = os.environ.get("GMAIL_APP_PASSWORD", "")
    if not password:
        raise RuntimeError("GMAIL_APP_PASSWORD environment variable not set.")

    html = build_html(jobs)
    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"[Job Hunter] Seattle HRBP · {datetime.now().strftime('%Y-%m-%d')} · {len(jobs)} new"
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
    seen_keys_this_run = set()
    for j in all_jobs:
        if not j.get("job_url"):
            continue
        if is_blocked(j, blocklist):
            continue
        url = j["job_url"]
        key = job_key(j)
        # skip if seen before (by URL or by title+company across platforms)
        if url in seen or key in seen:
            continue
        # skip duplicates within this run (same title+company from two platforms)
        if key in seen_keys_this_run:
            continue
        new_jobs.append(j)
        seen_keys_this_run.add(key)

    blocked_count = sum(1 for j in all_jobs if is_blocked(j, blocklist))
    print(f"Total: {len(all_jobs)}, blocked: {blocked_count}, new: {len(new_jobs)}")

    # persist both URLs and title+company keys
    for j in all_jobs:
        if j.get("job_url"):
            seen.add(j["job_url"])
            seen.add(job_key(j))
    save_seen_urls(seen)

    if new_jobs:
        send_email(new_jobs, cfg)
    else:
        print("No new jobs, skipping email.")

    print("=== Done ===")


if __name__ == "__main__":
    main()
