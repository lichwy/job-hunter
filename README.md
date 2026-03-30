# Job Hunter

Scrapes Seattle HRBP jobs from LinkedIn and Indeed every morning and emails you the new ones.

---

## Step 1 — Download the project

### Option A: Download as ZIP (no Git needed, easiest)

1. Open this link in your browser: **https://github.com/lichwy/job-hunter**
2. Click the green **`<> Code`** button
3. Click **`Download ZIP`**
4. Unzip the downloaded file — you'll get a folder called `job-hunter-main`
5. Move that folder somewhere easy to find (e.g. your Desktop or Documents)

### Option B: Clone with Git (if you have Git installed)

**Mac** — open Terminal and run:
```bash
git clone https://github.com/lichwy/job-hunter.git
```

**Windows** — open PowerShell and run:
```powershell
git clone https://github.com/lichwy/job-hunter.git
```

---

## Step 2 — Install Python (if you don't have it)

1. Open **https://www.python.org/downloads/**
2. Click the big **Download Python** button
3. Run the installer
   - **Windows only:** make sure to check **"Add Python to PATH"** before clicking Install

To verify Python is installed, open Terminal (Mac) or PowerShell (Windows) and run:
```
python3 --version   # Mac
python --version    # Windows
```
You should see something like `Python 3.12.x`.

---

## Step 3 — Run the setup script

Open Terminal (Mac) or PowerShell (Windows), navigate to the project folder, then run the setup script. It will walk you through everything interactively.

### Mac

```bash
cd ~/Desktop/job-hunter-main   # adjust path to wherever you put the folder
bash setup.sh
```

### Windows

Right-click `setup.ps1` and choose **"Run with PowerShell"**.

If you see a permissions error, open PowerShell and run:
```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
cd C:\Users\YourName\Desktop\job-hunter-main   # adjust path
.\setup.ps1
```

The setup script will:
1. Install required Python packages
2. Ask for your Gmail App Password (see below)
3. Schedule the job to run every day at 08:00

---

## Gmail App Password

You need a **Gmail App Password** — this is different from your regular Gmail password.

1. Open **https://myaccount.google.com/apppasswords** and sign in with the Gmail account you want to send from
2. In the text box, type any name (e.g. `job-hunter`) and click **Create**
3. Copy the 16-character password that appears
4. Paste it when the setup script asks for it

> If you don't see the App Passwords page, make sure 2-Step Verification is enabled on your Google account.

---

## Run manually anytime

After setup, you can trigger a run whenever you want:

**Mac:**
```bash
bash /path/to/job-hunter/run_now.sh
```

**Windows (PowerShell):**
```powershell
python C:\path\to\job-hunter\job_hunter.py
```

---

## Customize

Edit **`config.json`** to change any settings — no coding needed.

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
    "companies": ["Amazon", "Amazon.com", "Amazon Web Services"],
    "title_keywords": ["Director", "VP", "Vice President", "SVP", "EVP", "Head of", "Chief", "Managing Director", "Principal"]
  },
  "schedule_time": "08:00"
}
```

| Setting | What it does |
|---------|-------------|
| `sender_email` | Gmail account used to send the email |
| `recipients` | Who gets the email — add as many addresses as you want |
| `search.query` | What to search for — change this to look for other job types |
| `search.location` | City or region to search in |
| `search.hours_old` | Only include jobs posted within this many hours |
| `blocklist.companies` | Companies to skip — just add the company name |
| `blocklist.title_keywords` | Job title words to skip — e.g. "Director" filters out all director-level roles |
| `schedule_time` | What time to run each day (24-hour format, e.g. `"08:00"`) |

---

## Files

| File | Description |
|------|-------------|
| `job_hunter.py` | Main script |
| `config.json` | All settings — edit this to customize |
| `setup.sh` | One-click setup for macOS |
| `setup.ps1` | One-click setup for Windows |
| `run_now.sh` | Run immediately on macOS |
| `seen_jobs.json` | Auto-created; remembers seen jobs so you only get new ones |
| `log.txt` | Auto-created; log output from scheduled runs |
