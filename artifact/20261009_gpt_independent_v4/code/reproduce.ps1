param(
    [string]$Python = 'python',
    [string]$Node = "$env:USERPROFILE/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node.exe",
    [string]$DocPython = "$env:USERPROFILE/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe",
    [string]$Output = ''
)
$ErrorActionPreference = 'Stop'
$versionRoot = Split-Path $PSScriptRoot -Parent
$repoRoot = Split-Path (Split-Path $versionRoot -Parent) -Parent
if (-not $Output) { $Output = Join-Path $versionRoot 'reproduced/output' }
$env:PYTHONIOENCODING = 'utf-8'
& $Python (Join-Path $PSScriptRoot 'run.py') --input (Join-Path $repoRoot '赛题2-初赛/数据') --output $Output --node $Node --doc-python $DocPython
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
& $Python (Join-Path $PSScriptRoot 'check_cases.py') --events (Join-Path $Output 'evidence/all_events.jsonl') --cases (Join-Path $versionRoot 'audit/gold_cases.json') --output (Join-Path $Output 'case_check.json')
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
