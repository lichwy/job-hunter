import json
import os
import smtplib
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

from jobspy import scrape_jobs

# ── 配置 ────────────────────────────────────────────────
SENDER_EMAIL = "lichwy1024@gmail.com"
SENDER_APP_PASSWORD = os.environ.get("GMAIL_APP_PASSWORD", "")
RECIPIENTS = ["lichwy1024@gmail.com", "gracewang028@gmail.com"]
SEEN_JOBS_FILE = Path(__file__).parent / "seen_jobs.json"
# ────────────────────────────────────────────────────────


def load_seen_urls() -> set:
    if SEEN_JOBS_FILE.exists():
        with open(SEEN_JOBS_FILE, encoding="utf-8") as f:
            return set(json.load(f))
    return set()


def save_seen_urls(seen: set) -> None:
    with open(SEEN_JOBS_FILE, "w", encoding="utf-8") as f:
        json.dump(sorted(seen), f)


def scrape() -> list[dict]:
    """抓取 LinkedIn + Indeed 西雅图 HRBP 职位，返回标准化的 dict 列表。"""
    results = []
    for site in ("linkedin", "indeed"):
        try:
            df = scrape_jobs(
                site_name=[site],
                search_term='HRBP OR "HR Business Partner"',
                location="Seattle, WA",
                results_wanted=50,
                hours_old=48,  # 抓最近 48h，防止早上跑时漏掉昨晚发的
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
<h2 style="color:#1a6fc4;">🗺 西雅图 HRBP 新职位 · {datetime.now().strftime('%Y-%m-%d')}</h2>
<p>共 <strong>{len(jobs)}</strong> 个新职位（来源：LinkedIn + Indeed）</p>
<table border="1" cellpadding="0" cellspacing="0"
       style="border-collapse:collapse;width:100%;font-size:14px;">
  <thead style="background:#f5f5f5;">
    <tr>
      <th style="padding:8px 12px;text-align:left;">职位</th>
      <th style="padding:8px 12px;text-align:left;">公司</th>
      <th style="padding:8px 12px;text-align:left;">地点</th>
      <th style="padding:8px 12px;text-align:left;">来源</th>
      <th style="padding:8px 12px;text-align:left;">发布时间</th>
    </tr>
  </thead>
  <tbody>{rows}
  </tbody>
</table>
<p style="color:#888;font-size:12px;margin-top:20px;">由 job_hunter.py 自动发送</p>
</body></html>"""


def send_email(jobs: list[dict]) -> None:
    if not SENDER_APP_PASSWORD:
        raise RuntimeError("未设置 GMAIL_APP_PASSWORD 环境变量，请先配置。")

    html = build_html(jobs)
    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"[求职] 西雅图 HRBP 新职位 {datetime.now().strftime('%Y-%m-%d')} · {len(jobs)} 个"
    msg["From"] = SENDER_EMAIL
    msg["To"] = ", ".join(RECIPIENTS)
    msg.attach(MIMEText(html, "html", "utf-8"))

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(SENDER_EMAIL, SENDER_APP_PASSWORD)
        server.sendmail(SENDER_EMAIL, RECIPIENTS, msg.as_string())

    print(f"邮件已发送给 {RECIPIENTS}")


def main() -> None:
    print(f"=== job_hunter 启动 {datetime.now().strftime('%Y-%m-%d %H:%M')} ===")

    seen = load_seen_urls()
    all_jobs = scrape()

    if not all_jobs:
        print("未抓到任何职位，退出。")
        return

    # 去重：以 job_url 为唯一键
    new_jobs = [j for j in all_jobs if j.get("job_url") and j["job_url"] not in seen]
    print(f"共 {len(all_jobs)} 条，其中新职位 {len(new_jobs)} 条")

    if new_jobs:
        send_email(new_jobs)
        # 发送成功后才更新已见记录
        seen.update(j["job_url"] for j in all_jobs if j.get("job_url"))
        save_seen_urls(seen)
    else:
        # 没有新职位时也更新，防止重复检查
        seen.update(j["job_url"] for j in all_jobs if j.get("job_url"))
        save_seen_urls(seen)
        print("没有新职位，不发送邮件。")

    print("=== 完成 ===")


if __name__ == "__main__":
    main()
