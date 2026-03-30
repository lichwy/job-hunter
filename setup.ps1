# setup.ps1 — one-click setup for Windows
# Right-click this file and choose "Run with PowerShell"
$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "   Job Hunter Setup -- Windows"          -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# ── Check Python ──────────────────────────────────────────
try {
    $pyVersion = python --version 2>&1
    Write-Host "OK: $pyVersion found"
} catch {
    Write-Host "ERROR: Python is not installed." -ForegroundColor Red
    Write-Host ""
    Write-Host "Please install it first:"
    Write-Host "  1. Open: https://www.python.org/downloads/"
    Write-Host "  2. Download and run the installer"
    Write-Host "  3. IMPORTANT: check 'Add Python to PATH' during install"
    Write-Host "  4. Re-run this script"
    Read-Host "Press Enter to exit"
    exit 1
}

# ── Step 1: Install dependencies ─────────────────────────
Write-Host ""
Write-Host "Step 1/3 -- Installing dependencies..."
python -m pip install -r "$ScriptDir\requirements.txt" -q
Write-Host "OK"

# ── Step 2: Gmail App Password ────────────────────────────
Write-Host ""
Write-Host "Step 2/3 -- Gmail App Password"

$existing = [System.Environment]::GetEnvironmentVariable("GMAIL_APP_PASSWORD", "User")
if ($existing) {
    Write-Host "OK: Already configured, skipping"
} else {
    Write-Host ""
    Write-Host "You need a Gmail App Password to send emails."
    Write-Host "It is different from your regular Gmail password."
    Write-Host ""
    Write-Host "How to get one:"
    Write-Host "  1. Open this link in your browser:"
    Write-Host "     https://myaccount.google.com/apppasswords" -ForegroundColor Yellow
    Write-Host "  2. Sign in with the Gmail account you want to send from"
    Write-Host "  3. Type any name (e.g. job-hunter) and click 'Create'"
    Write-Host "  4. Copy the 16-character password shown"
    Write-Host ""
    $app_password = Read-Host "Paste the password here and press Enter"
    if (-not $app_password) {
        Write-Host "ERROR: No password entered. Exiting." -ForegroundColor Red
        Read-Host "Press Enter to exit"
        exit 1
    }
    [System.Environment]::SetEnvironmentVariable("GMAIL_APP_PASSWORD", $app_password, "User")
    $env:GMAIL_APP_PASSWORD = $app_password
    Write-Host "OK: Password saved"
}

# ── Step 3: Schedule Task Scheduler job ──────────────────
Write-Host ""
Write-Host "Step 3/3 -- Scheduling daily job..."

$config = Get-Content "$ScriptDir\config.json" | ConvertFrom-Json
$scheduleTime = if ($config.schedule_time) { $config.schedule_time } else { "08:00" }

$taskName = "JobHunter"
$pythonPath = (Get-Command python).Source
$action = New-ScheduledTaskAction `
    -Execute $pythonPath `
    -Argument "$ScriptDir\job_hunter.py" `
    -WorkingDirectory $ScriptDir
$trigger  = New-ScheduledTaskTrigger -Daily -At $scheduleTime
$settings = New-ScheduledTaskSettingsSet `
    -ExecutionTimeLimit (New-TimeSpan -Minutes 10) `
    -RunOnlyIfNetworkAvailable

if (Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue) {
    Unregister-ScheduledTask -TaskName $taskName -Confirm:$false
}
Register-ScheduledTask -TaskName $taskName -Action $action -Trigger $trigger -Settings $settings -RunLevel Highest | Out-Null
Write-Host "OK: Scheduled to run daily at $scheduleTime"

# ── Done ──────────────────────────────────────────────────
Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "   Setup complete!"                       -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "The script will run automatically every day at $scheduleTime."
Write-Host "Results will be emailed to you."
Write-Host ""
Write-Host "To run it right now, open PowerShell and type:"
Write-Host "  python $ScriptDir\job_hunter.py" -ForegroundColor Yellow
Write-Host ""
Read-Host "Press Enter to close"
