[CmdletBinding()]
param([Parameter(Mandatory, Position = 0)][string]$Message)

$ErrorActionPreference = 'Stop'
if ($Message -notmatch '^(feat|fix|docs|chore|refactor|test)(\([^)]+\))?!?: .+') {
    throw 'Use a Conventional Commit message, for example: docs: add demo checklist'
}

& "$PSScriptRoot/verify.ps1"
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
git add -A
git diff --cached --quiet
if ($LASTEXITCODE -eq 0) { Write-Host 'No changes to checkpoint.'; exit 0 }
git commit -m $Message
git pull --rebase --autostash
git push
