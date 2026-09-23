[CmdletBinding()]
param([string]$PythonCommand = $env:ARPU_PYTHON)

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
if ($LASTEXITCODE -eq 0) { throw 'Possible secret detected. Remove it before committing; matched values are not printed.' }
if ($LASTEXITCODE -gt 1) { throw 'Secret scan could not run.' }

$badEnv = git diff --cached --name-only --diff-filter=ACMR | Where-Object {
    $_ -match '(^|/|\\)\.env($|\.)' -and $_ -notmatch '\.env\.example$'
}
if ($badEnv) { throw "Refusing staged environment file(s): $($badEnv -join ', ')" }

if (Test-Path 'agent.py') {
    if (-not $PythonCommand) {
        foreach ($candidate in @('.venv/Scripts/python.exe', '.venv/bin/python')) {
            if (Test-Path $candidate) { $PythonCommand = (Resolve-Path $candidate).Path; break }
        }
    }
    if (-not $PythonCommand) {
        $python = Get-Command python -ErrorAction SilentlyContinue
        if ($python) { $PythonCommand = $python.Source }
    }
    if (-not $PythonCommand) { throw 'Python is missing. Activate .venv or set ARPU_PYTHON to your Python executable.' }
    Run-Step 'official local_eval.py (UTF-8)' {
        $evaluation = & $PythonCommand -X utf8 local_eval.py 2>&1
        $evaluation | ForEach-Object { Write-Host $_ }
        if ($LASTEXITCODE -ne 0) { throw 'Official evaluator failed.' }
        if (($evaluation -join "`n") -match 'Агент упал|Кампания .*отброшена|Агент не вернул') {
            throw 'Official evaluator reported an invalid agent/campaign.'
        }
    }
}

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
Write-Host 'Technical verification passed. Economic quality is evaluated separately; see docs/BASELINE.md.'
