[CmdletBinding()]
param([string]$PythonCommand = $env:ARPU_PYTHON, [switch]$Release)

$ErrorActionPreference = 'Stop'
Push-Location (Split-Path -Parent $PSScriptRoot)
try {
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

# Inspect what will actually be committed, including ignored files staged explicitly.
$stagedSecretPaths = & git grep --cached -I -l -E -e $secretPattern -- . ':!scripts/verify.ps1' 2>$null
if ($LASTEXITCODE -eq 0) { throw 'Possible secret in the staged Git snapshot. Values are not printed.' }
if ($LASTEXITCODE -gt 1) { throw 'Staged secret scan could not run.' }

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
    if (Test-Path 'scripts/test_quality_policy.py') {
        Run-Step 'quality policy, report and isolated benchmark checks' {
            & $PythonCommand -B -X utf8 -m unittest scripts.test_quality_policy scripts.test_quality_benchmark scripts.test_report_quality scripts.test_report_localization scripts.test_chat_language -q
        }
    }
    Run-Step 'official local_eval.py (UTF-8)' {
        $previousOffline = $env:ARPU_OFFLINE
        try {
            $env:ARPU_OFFLINE = '1'
            $evaluation = & $PythonCommand -X utf8 local_eval.py 2>&1
        } finally {
            if ($null -eq $previousOffline) { Remove-Item Env:ARPU_OFFLINE -ErrorAction SilentlyContinue }
            else { $env:ARPU_OFFLINE = $previousOffline }
        }
        $evaluation | ForEach-Object { Write-Host $_ }
        if ($LASTEXITCODE -ne 0) { throw 'Official evaluator failed.' }
        if (($evaluation -join "`n") -match 'Агент упал|Кампания .*отброшена|Агент не вернул') {
            throw 'Official evaluator reported an invalid agent/campaign.'
        }
    }
    if ($Release) {
        Run-Step 'official submission generation (offline)' {
            $previousOffline = $env:ARPU_OFFLINE
            try {
                $env:ARPU_OFFLINE = '1'
                & $PythonCommand -X utf8 make_submission.py
                if ($LASTEXITCODE -ne 0) { throw 'Official CSV generator failed.' }
            } finally {
                if ($null -eq $previousOffline) { Remove-Item Env:ARPU_OFFLINE -ErrorAction SilentlyContinue }
                else { $env:ARPU_OFFLINE = $previousOffline }
            }
            $rows = @(Import-Csv -LiteralPath 'submission.csv')
            if ($rows.Count -lt 1 -or $rows.Count -gt 10) { throw 'Submission must contain 1 through 10 campaigns.' }
            $expected = @('campaign_name','filter_arpu_segment','filter_data_segment','filter_call_segment','filter_current_tariff','target_tariff','channel')
            if (($rows[0].PSObject.Properties.Name -join ',') -ne ($expected -join ',')) { throw 'Unexpected submission columns.' }
            $tariffCodes = @(Import-Csv -LiteralPath 'tariff_dictionary.csv' | ForEach-Object { $_.tariff_plan_code })
            foreach ($row in $rows) {
                if ($row.target_tariff -notin $tariffCodes -or $row.channel -notin @('push','sms','digital_ads','call')) {
                    throw 'Submission has an unknown tariff or channel.'
                }
            }
        }
        Write-Host 'Release CSV regenerated and checked. Include submission.csv in the next checkpoint.'
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
} finally {
    Pop-Location
}
