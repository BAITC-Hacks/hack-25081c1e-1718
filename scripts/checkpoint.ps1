[CmdletBinding()]
param(
    [Parameter(Mandatory, Position = 0)][string]$Message,
    [string[]]$Paths = @()
)

$ErrorActionPreference = 'Stop'
Push-Location (Split-Path -Parent $PSScriptRoot)
try {
if ($Message -notmatch '^(feat|fix|docs|chore|refactor|test)(\([^)]+\))?!?: .+') {
    throw 'Use a Conventional Commit message, for example: docs: add demo checklist'
}

function Invoke-GitChecked([string[]]$Arguments) {
    & git @Arguments
    if ($LASTEXITCODE -ne 0) { throw "git $($Arguments -join ' ') failed ($LASTEXITCODE)." }
}

$conflicts = & git diff --name-only --diff-filter=U
if ($LASTEXITCODE -ne 0) { throw 'Cannot inspect Git conflicts.' }
if ($conflicts) { throw 'Resolve merge conflicts before checkpoint.' }

# Explicit paths only. Without -Paths, checkpoint commits the already reviewed index.
if ($Paths.Count -gt 0) {
    $staged = & git diff --cached --name-only
    if ($LASTEXITCODE -ne 0) { throw 'Cannot inspect the Git index.' }
    if ($staged) { throw 'Index already contains staged changes. Review them and checkpoint without -Paths, or unstage them first.' }
    Invoke-GitChecked -Arguments (@('add', '--') + $Paths)
}
& git diff --cached --quiet
if ($LASTEXITCODE -eq 0) { Write-Host 'No staged changes. Use -Paths with the files you own.'; exit 0 }
if ($LASTEXITCODE -ne 1) { throw 'Cannot inspect staged diff.' }

& pwsh -NoProfile -File "$PSScriptRoot/verify.ps1"
if ($LASTEXITCODE -ne 0) { throw 'Verification failed; nothing committed.' }
Invoke-GitChecked -Arguments @('commit', '-m', $Message)
Invoke-GitChecked -Arguments @('pull', '--rebase', '--autostash')
& pwsh -NoProfile -File "$PSScriptRoot/verify.ps1"
if ($LASTEXITCODE -ne 0) { throw 'Verification after synchronization failed; local commit retained, nothing pushed.' }
Invoke-GitChecked -Arguments @('push')
} finally {
    Pop-Location
}
