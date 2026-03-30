# Job Hunter

Scrapes Seattle HRBP jobs from LinkedIn and Indeed every morning and emails you the new ones.

## Quick Setup

### macOS
```bash
bash setup.sh
```

### Windows
Run PowerShell as Administrator, then:
```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\setup.ps1
```

The setup script will:
1. Install Python dependencies
2. Prompt for your Gmail App Password (if not already set)
3. Schedule the job to run daily at the time set in `config.json` (default 08:00)

---

## Gmail App Password

You need a Gmail [App Password](https://myaccount.google.com/apppasswords) — **not** your regular Gmail password.

1. Go to [myaccount.google.com/apppasswords](https://myaccount.google.com/apppasswords)
2. Create a new app password (name it anything, e.g. "job-hunter")
3. Copy the 16-character password — the setup script will ask for it

---

## Configuration

Edit `config.json` to customize behavior:

```json
{
  "sender_email": "you@gmail.com",
  "recipients": ["you@gmail.com", "friend@gmail.com"],
  "search": {
    "query": "HRBP OR \"HR Business Partner\"",
    "location": "Seattle, WA",
    "results_wanted": 50,
    "hours_old": 48
  },
  "blocklist": {
    "companies": ["Amazon", "Amazon.com", "Amazon Web Services"]
  },
  "schedule_time": "08:00"
}
```

| Field | Description |
|-------|-------------|
| `sender_email` | Gmail account used to send the email |
| `recipients` | List of email addresses to notify |
| `search.query` | Job search keywords |
| `search.location` | Target city/region |
| `search.hours_old` | Only scrape jobs posted within this many hours |
| `blocklist.companies` | Companies to exclude (case-insensitive) |
| `schedule_time` | Daily run time in `HH:MM` 24h format |

---

## Run Manually

```bash
# macOS / Linux
bash run_now.sh

# Windows
python job_hunter.py
```

---

## Files

| File | Description |
|------|-------------|
| `job_hunter.py` | Main script |
| `config.json` | All user-configurable settings |
| `setup.sh` | One-click setup for macOS |
| `setup.ps1` | One-click setup for Windows |
| `run_now.sh` | Run immediately on macOS |
| `seen_jobs.json` | Auto-generated; tracks seen job URLs to avoid duplicates |
| `log.txt` | Auto-generated; output log from scheduled runs |
