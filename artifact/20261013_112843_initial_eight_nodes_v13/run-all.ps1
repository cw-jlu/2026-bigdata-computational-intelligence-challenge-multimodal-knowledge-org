param([string]$Output='',[string]$Python='',[string]$Node='',[string]$NodeModules='',[switch]$SkipNativeRender)
$ErrorActionPreference='Stop'
$taskRuntime=Join-Path $env:USERPROFILE '.cache/codex-runtimes/codex-primary-runtime/dependencies'
if(!$Python){$Python=Join-Path $taskRuntime 'python/python.exe'}
if(!$Node){$Node=Join-Path $taskRuntime 'node/bin/node.exe'}
if(!$NodeModules){$NodeModules=Join-Path $taskRuntime 'node/node_modules'}
if(!(Test-Path -LiteralPath $Python)){throw 'Pass -Python with the dependencies in requirements-lock.txt'}
if(!(Test-Path -LiteralPath (Join-Path $NodeModules '@oai/artifact-tool/package.json'))){throw 'Pass -NodeModules with bundled artifact-tool; runtime binaries are not included'}
$taskModules=Join-Path $PSScriptRoot 'code/node_modules'
if(!(Test-Path -LiteralPath $taskModules)){New-Item -ItemType Junction -Path $taskModules -Target $NodeModules | Out-Null}
if(!$Output){$Output=Join-Path $PSScriptRoot ('reproduced_'+(Get-Date -Format 'yyyyMMdd_HHmmss'))}
$Output=[IO.Path]::GetFullPath($Output)
if(Test-Path -LiteralPath $Output){throw 'Output must be a new directory'}
$env:PYTHONIOENCODING='utf-8'
$env:COMPETITION_PROJECT_ROOT=Join-Path $PSScriptRoot 'inputs'
& $Python -X utf8 (Join-Path $PSScriptRoot 'code/reproduce.py') --output $Output --node $Node
if($LASTEXITCODE -ne 0){throw 'Raw-input reproduction failed; see run.log'}
if(!$SkipNativeRender){
 & (Join-Path $PSScriptRoot 'code/render_word.ps1') -Output $Output
 & (Join-Path $PSScriptRoot 'code/render_excel.ps1') -Output $Output
 & $Python (Join-Path $PSScriptRoot 'code/raster_qa.py') --output $Output
 & $Python (Join-Path $PSScriptRoot 'code/raster_excel.py') --output $Output
}
Write-Output "Completed raw facts + reviewed analysis replay and 48 files: $Output"
Write-Output 'Fresh reasoning is not executed; new renders need human visual review.'
