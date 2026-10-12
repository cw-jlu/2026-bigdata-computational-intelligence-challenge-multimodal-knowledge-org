param(
 [Parameter(Mandatory=$true)][string]$Output,
 [string]$ProjectRoot=(Join-Path $PSScriptRoot 'inputs'),
 [string]$Python='C:/Users/Andy1/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe',
 [string]$Node='C:/Users/Andy1/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node.exe',
 [string]$Packages='C:/Users/Andy1/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules'
)
$ErrorActionPreference='Stop'
foreach($taskPath in @($Python,$Node,$Packages,$ProjectRoot)) {
 if(-not(Test-Path -LiteralPath $taskPath)){throw "Missing required runtime/input path: $taskPath"}
}
$taskOutput=[System.IO.Path]::GetFullPath($Output)
if(Test-Path -LiteralPath $taskOutput){throw 'Use a new output directory. Existing output is never replaced.'}
$taskModules=Join-Path $PSScriptRoot 'code/node_modules'
if(-not(Test-Path -LiteralPath $taskModules)){
 New-Item -ItemType Junction -Path $taskModules -Target ([System.IO.Path]::GetFullPath($Packages)) | Out-Null
}
$env:COMPETITION_PROJECT_ROOT=[System.IO.Path]::GetFullPath($ProjectRoot)
$env:PYTHONIOENCODING='utf-8'
& $Python (Join-Path $PSScriptRoot 'code/reproduce.py') --output $taskOutput --node $Node
if($LASTEXITCODE -ne 0){throw "Eight-node reproduction failed: $LASTEXITCODE"}
Write-Output "All eight nodes and full candidate submission ZIP reproduced at $taskOutput"
