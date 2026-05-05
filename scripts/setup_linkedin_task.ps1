# setup_linkedin_task.ps1
# Creates a Windows Task Scheduler task that posts ARIA findings to LinkedIn.
# Runs Tue-Sat at 9:00 AM local time (after ARIA pipeline + GitHub Pages export).
# Runs as soon as possible if the window was missed (machine was offline).
#
# Run once from a normal PowerShell prompt:
#   Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
#   .\scripts\setup_linkedin_task.ps1

$TaskName  = "LinkedInARIA"
$BatFile   = "C:\Users\V2Rst\aria\scripts\run_linkedin_post.bat"
$StartTime = "09:00"

if (Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue) {
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
    Write-Host "Removed existing task: $TaskName"
}

$Action = New-ScheduledTaskAction `
    -Execute "cmd.exe" `
    -Argument "/c `"$BatFile`""

# Tue-Sat (DaysOfWeek: Tuesday=4, Wednesday=8, Thursday=16, Friday=32, Saturday=64)
$Trigger = New-ScheduledTaskTrigger `
    -Weekly `
    -DaysOfWeek Tuesday, Wednesday, Thursday, Friday, Saturday `
    -At $StartTime

$Settings = New-ScheduledTaskSettingsSet `
    -StartWhenAvailable `
    -RunOnlyIfNetworkAvailable `
    -ExecutionTimeLimit (New-TimeSpan -Minutes 10) `
    -MultipleInstances IgnoreNew

Register-ScheduledTask `
    -TaskName $TaskName `
    -Action $Action `
    -Trigger $Trigger `
    -Settings $Settings `
    -RunLevel Limited | Out-Null

Write-Host "Task created: $TaskName"
Write-Host "  Schedule : Tue-Sat at $StartTime"
Write-Host "  Catch-up : Yes (StartWhenAvailable)"
Write-Host "  Network  : Required"
Write-Host ""
Write-Host "To verify:  schtasks /Query /TN '$TaskName' /FO LIST"
Write-Host "To run now: Start-ScheduledTask -TaskName '$TaskName'"
