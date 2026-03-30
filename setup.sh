#!/bin/bash
# setup.sh — one-click setup for macOS
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PYTHON=$(command -v python3)

echo "=== Job Hunter Setup (macOS) ==="

# 1. Install dependencies
echo "[1/3] Installing Python dependencies..."
"$PYTHON" -m pip install -r "$SCRIPT_DIR/requirements.txt" --break-system-packages -q \
  || "$PYTHON" -m pip install -r "$SCRIPT_DIR/requirements.txt" -q

# 2. Gmail App Password
if [ -z "$GMAIL_APP_PASSWORD" ]; then
  echo ""
  echo "[2/3] Gmail App Password not set."
  echo "  → Go to: https://myaccount.google.com/apppasswords"
  echo "  → Create an app password for 'job-hunter'"
  echo ""
  read -rp "Paste your 16-character app password: " app_password
  shell_rc="$HOME/.zshrc"
  [ -f "$HOME/.bashrc" ] && shell_rc="$HOME/.bashrc"
  echo "export GMAIL_APP_PASSWORD=\"$app_password\"" >> "$shell_rc"
  export GMAIL_APP_PASSWORD="$app_password"
  echo "  ✓ Saved to $shell_rc"
else
  echo "[2/3] GMAIL_APP_PASSWORD already set, skipping."
fi

# 3. Schedule daily cron job at time from config.json
SCHEDULE_TIME=$(python3 -c "import json; c=json.load(open('$SCRIPT_DIR/config.json')); print(c.get('schedule_time','08:00'))")
HOUR="${SCHEDULE_TIME%%:*}"
MINUTE="${SCHEDULE_TIME##*:}"
CRON_LINE="$MINUTE $HOUR * * * source ~/.zshrc && $PYTHON $SCRIPT_DIR/job_hunter.py >> $SCRIPT_DIR/log.txt 2>&1"

echo "[3/3] Setting up daily cron job at ${SCHEDULE_TIME}..."
( crontab -l 2>/dev/null | grep -v "job_hunter.py"; echo "$CRON_LINE" ) | crontab -
echo "  ✓ Cron job set"

echo ""
echo "=== Setup complete! ==="
echo "Run manually anytime:  bash $SCRIPT_DIR/run_now.sh"
echo "View logs:             tail -f $SCRIPT_DIR/log.txt"
