[CmdletBinding()]
param([int]$Minutes = 20)

if ($Minutes -lt 1) { throw 'Minutes must be at least 1.' }
Write-Host "Autosave checks every $Minutes minute(s). Stop with Ctrl+C."
while ($true) {
    Start-Sleep -Seconds ($Minutes * 60)
    if (git status --porcelain) {
        $stamp = Get-Date -Format 'yyyy-MM-dd HH:mm'
        & "$PSScriptRoot/checkpoint.ps1" "chore: wip checkpoint $stamp"
    }
}
