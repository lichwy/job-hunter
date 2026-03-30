#!/bin/bash
# setup.sh — one-click setup for macOS
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo ""
echo "========================================"
echo "   Job Hunter Setup — macOS"
echo "========================================"
echo ""

# ── Check Python ──────────────────────────────────────────
PYTHON=$(command -v python3 2>/dev/null || true)
if [ -z "$PYTHON" ]; then
  echo "Python 3 is not installed. Opening the download page in your browser..."
  open "https://www.python.org/downloads/"
  echo ""
  echo "  1. Download and install Python from the page that just opened"
  echo "  2. Re-run this script"
  exit 1
fi
echo "✓ Python found: $($PYTHON --version)"

# ── Step 1: Install dependencies ─────────────────────────
echo ""
echo "Step 1/3 — Installing dependencies..."
"$PYTHON" -m pip install -r "$SCRIPT_DIR/requirements.txt" --break-system-packages -q 2>/dev/null \
  || "$$PYTHON" -m pip install -r "$SCRIPT_DIR/requirements.txt" -q
echo "✓ Done"

# ── Step 2: Gmail App Password ────────────────────────────
echo ""
echo "Step 2/3 — Gmail App Password"

if [ -n "$GMAIL_APP_PASSWORD" ]; then
  echo "✓ Already configured, skipping"
else
  echo ""
  echo "You need a Gmail App Password to send emails."
  echo "It is different from your regular Gmail password."
  echo ""
  echo "How to get one:"
  echo "  1. Open this link in your browser:"
  echo "     https://myaccount.google.com/apppasswords"
  echo "  2. Sign in with the Gmail account you want to send from"
  echo "  3. Type any name (e.g. job-hunter) and click 'Create'"
  echo "  4. Copy the 16-character password shown"
  echo ""
  read -rp "Paste the password here and press Enter: " app_password
  if [ -z "$app_password" ]; then
    echo "ERROR: No password entered. Exiting."
    exit 1
  fi

  # Save to shell config
  SHELL_RC="$HOME/.zshrc"
  echo "" >> "$SHELL_RC"
  echo "export GMAIL_APP_PASSWORD=\"$app_password\"" >> "$SHELL_RC"
  export GMAIL_APP_PASSWORD="$app_password"
  echo "✓ Password saved"
fi

# ── Step 3: Schedule daily cron job ──────────────────────
echo ""
echo "Step 3/3 — Scheduling daily job..."

SCHEDULE_TIME=$("$PYTHON" -c "import json; c=json.load(open('$SCRIPT_DIR/config.json')); print(c.get('schedule_time','08:00'))")
HOUR="${SCHEDULE_TIME%%:*}"
MINUTE="${SCHEDULE_TIME##*:}"
CRON_LINE="$MINUTE $HOUR * * * source \$HOME/.zshrc && $PYTHON $SCRIPT_DIR/job_hunter.py >> $SCRIPT_DIR/log.txt 2>&1"

( crontab -l 2>/dev/null | grep -v "job_hunter.py"; echo "$CRON_LINE" ) | crontab -
echo "✓ Scheduled to run daily at $SCHEDULE_TIME"

# ── Done ──────────────────────────────────────────────────
echo ""
echo "========================================"
echo "   Setup complete!"
echo "========================================"
echo ""
echo "The script will run automatically every day at $SCHEDULE_TIME."
echo "Results will be emailed to you."
echo ""
echo "To run it right now:"
echo "  bash $SCRIPT_DIR/run_now.sh"
echo ""
echo "To view past logs:"
echo "  cat $SCRIPT_DIR/log.txt"
echo ""
