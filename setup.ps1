# setup.ps1 — one-click setup for Windows (run in PowerShell as Administrator)
$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path

Write-Host "=== Job Hunter Setup (Windows) ===" -ForegroundColor Cyan

# 1. Install dependencies
Write-Host "[1/3] Installing Python dependencies..."
python -m pip install -r "$ScriptDir\requirements.txt" -q
Write-Host "  OK"

# 2. Gmail App Password
$existing = [System.Environment]::GetEnvironmentVariable("GMAIL_APP_PASSWORD", "User")
if (-not $existing) {
    Write-Host ""
    Write-Host "[2/3] Gmail App Password not set."
    Write-Host "  -> Go to: https://myaccount.google.com/apppasswords"
    Write-Host "  -> Create an app password for 'job-hunter'"
    Write-Host ""
    $app_password = Read-Host "Paste your 16-character app password"
    [System.Environment]::SetEnvironmentVariable("GMAIL_APP_PASSWORD", $app_password, "User")
    $env:GMAIL_APP_PASSWORD = $app_password
    Write-Host "  OK: Saved to user environment variables"
} else {
    Write-Host "[2/3] GMAIL_APP_PASSWORD already set, skipping."
}

# 3. Schedule Task Scheduler job
$config = Get-Content "$ScriptDir\config.json" | ConvertFrom-Json
$scheduleTime = $config.schedule_time
if (-not $scheduleTime) { $scheduleTime = "08:00" }

Write-Host "[3/3] Setting up daily Task Scheduler job at ${scheduleTime}..."
$taskName = "JobHunter"
$pythonPath = (Get-Command python).Source
$action = New-ScheduledTaskAction -Execute $pythonPath -Argument "$ScriptDir\job_hunter.py" -WorkingDirectory $ScriptDir
$trigger = New-ScheduledTaskTrigger -Daily -At $scheduleTime
$settings = New-ScheduledTaskSettingsSet -ExecutionTimeLimit (New-TimeSpan -Minutes 10) -RunOnlyIfNetworkAvailable

# Remove existing task if present
if (Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue) {
    Unregister-ScheduledTask -TaskName $taskName -Confirm:$false
}
Register-ScheduledTask -TaskName $taskName -Action $action -Trigger $trigger -Settings $settings -RunLevel Highest | Out-Null
Write-Host "  OK: Task '$taskName' scheduled at $scheduleTime daily"

Write-Host ""
Write-Host "=== Setup complete! ===" -ForegroundColor Green
Write-Host "Run manually anytime:  python $ScriptDir\job_hunter.py"
Write-Host "View logs:             Get-Content $ScriptDir\log.txt -Wait"
