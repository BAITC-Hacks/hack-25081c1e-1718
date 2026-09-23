[CmdletBinding()]
param([int]$Minutes = 4)

if ($Minutes -lt 1) { throw 'Minutes must be at least 1.' }
Write-Host "Checkpoint reminders every $Minutes minute(s). Stop with Ctrl+C."
while ($true) {
    Start-Sleep -Seconds ($Minutes * 60)
    $changes = git status --short
    if ($LASTEXITCODE -ne 0) { throw 'Cannot read Git status.' }
    if ($changes) {
        Write-Host 'Changes are present. Review your files, verify, and checkpoint with explicit -Paths.'
        $changes | Write-Host
    }
}
