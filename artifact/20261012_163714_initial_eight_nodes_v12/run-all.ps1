param(
 [string]$Python='',
 [string]$Node='',
 [string]$NodeModules='',
 [string]$Output='',
 [switch]$SkipNativeRender
)
$ErrorActionPreference='Stop'
$taskRuntime=Join-Path $env:USERPROFILE '.cache/codex-runtimes/codex-primary-runtime/dependencies'
if(!$Python){$Python=Join-Path $taskRuntime 'python/python.exe'}
if(!$Node){$Node=Join-Path $taskRuntime 'node/bin/node.exe'}
if(!$NodeModules){$NodeModules=Join-Path $taskRuntime 'node/node_modules'}
if(!(Test-Path -LiteralPath $Python)){throw 'Pass -Python with the interpreter containing requirements-lock.txt dependencies.'}
if(!(Test-Path -LiteralPath $Node)){throw 'Pass -Node with Node.js.'}
if(!(Test-Path -LiteralPath (Join-Path $NodeModules '@oai/artifact-tool/package.json'))){throw 'Pass -NodeModules with the Codex bundled artifact-tool runtime. It is not included as a vendored binary.'}
$taskModules=Join-Path $PSScriptRoot 'code/node_modules'
if(!(Test-Path -LiteralPath $taskModules)){New-Item -ItemType Junction -Path $taskModules -Target $NodeModules | Out-Null}
if(!$Output){$Output=Join-Path $PSScriptRoot ('reproduced_'+(Get-Date -Format 'yyyyMMdd_HHmmss'))}
$Output=[IO.Path]::GetFullPath($Output)
if(Test-Path -LiteralPath $Output){throw 'Output must be a new directory.'}
$env:PYTHONIOENCODING='utf-8'
$env:COMPETITION_PROJECT_ROOT=Join-Path $PSScriptRoot 'inputs'
& $Python (Join-Path $PSScriptRoot 'code/reproduce.py') --output $Output --node $Node
if($LASTEXITCODE -ne 0){throw 'Raw-input reproduction failed. See output/run.log.'}
if(!$SkipNativeRender){
 & (Join-Path $PSScriptRoot 'code/render_word.ps1') -Output $Output
 & (Join-Path $PSScriptRoot 'code/render_excel.ps1') -Output $Output
 & $Python (Join-Path $PSScriptRoot 'code/raster_qa.py') --output $Output
 if($LASTEXITCODE -ne 0){throw 'DOCX raster rendering failed.'}
 & $Python (Join-Path $PSScriptRoot 'code/raster_excel.py') --output $Output
 if($LASTEXITCODE -ne 0){throw 'XLSX raster rendering failed.'}
}
Write-Output "Reproduced all eight nodes and 48-file archive: $Output"
Write-Output 'Saved analysis is replayed, not newly authored by a model. New renders require visual review.'
