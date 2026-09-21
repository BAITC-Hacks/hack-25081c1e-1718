[CmdletBinding()]
param()

$ErrorActionPreference = 'Stop'
$ran = $false

function Run-Step([string]$Name, [scriptblock]$Action) {
    Write-Host "==> $Name"
    & $Action
    if ($LASTEXITCODE -ne 0) { throw "$Name failed with exit code $LASTEXITCODE" }
    $script:ran = $true
}

Write-Host '==> Secret scan'
$secretPattern = '(AKIA[0-9A-Z]{16}|sk-[A-Za-z0-9_-]{20,}|gh[pousr]_[A-Za-z0-9]{20,}|-----BEGIN [A-Z ]*PRIVATE KEY-----)'
$hits = & rg -n -I --hidden --glob '!.git/**' --glob '!node_modules/**' --glob '!dist/**' --glob '!build/**' --glob '!*.lock' --glob '!scripts/verify.ps1' --regexp $secretPattern . 2>$null
if ($LASTEXITCODE -eq 0) { Write-Error "Possible secret detected:`n$($hits -join "`n")" }
if ($LASTEXITCODE -gt 1) { throw 'Secret scan could not run.' }

$badEnv = git diff --cached --name-only --diff-filter=ACMR | Where-Object {
    $_ -match '(^|/|\\)\.env($|\.)' -and $_ -notmatch '\.env\.example$'
}
if ($badEnv) { throw "Refusing staged environment file(s): $($badEnv -join ', ')" }

if (Test-Path 'package.json') {
    $package = Get-Content -Raw 'package.json' | ConvertFrom-Json
    foreach ($name in @('lint', 'typecheck', 'test', 'build')) {
        if ($package.scripts.PSObject.Properties.Name -contains $name) {
            Run-Step "npm run $name" { npm run $name }
        }
    }
}

if (Test-Path 'pyproject.toml') {
    if (Get-Command ruff -ErrorAction SilentlyContinue) { Run-Step 'ruff check' { ruff check . } }
    if ((Test-Path 'tests') -and (Get-Command pytest -ErrorAction SilentlyContinue)) { Run-Step 'pytest' { pytest -q } }
}
if (Test-Path 'go.mod') { Run-Step 'go test' { go test ./... } }
if (Test-Path 'Cargo.toml') { Run-Step 'cargo test' { cargo test } }

if (-not $ran) { Write-Host 'nothing to verify' }
Write-Host 'Verification passed.'
