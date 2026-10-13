param(
 [Parameter(Mandatory=$true)][ValidateSet('fresh','frozen')][string]$Mode,
 [Parameter(Mandatory=$true)][string]$Output,
 [string]$Python,
 [string]$Node,
 [string]$Modules,
 [string]$Codex,
 [switch]$Render
)
$ErrorActionPreference='Stop'
$taskDependencies=Join-Path $env:USERPROFILE '.cache/codex-runtimes/codex-primary-runtime/dependencies'
if(-not $Python){$Python=Join-Path $taskDependencies 'python/python.exe'}
if(-not $Node){$Node=Join-Path $taskDependencies 'node/bin/node.exe'}
if(-not $Modules){$Modules=Join-Path $taskDependencies 'node/node_modules'}
if($Mode -eq 'fresh' -and -not $Codex){
 $taskCodexCommand=Get-Command codex -ErrorAction SilentlyContinue
 if($taskCodexCommand){$Codex=$taskCodexCommand.Source}
 else {
  $taskCodexRoot=Join-Path $env:LOCALAPPDATA 'OpenAI/Codex/bin'
  $taskCodexCandidates=Get-ChildItem -LiteralPath $taskCodexRoot -Filter codex.exe -Recurse | Sort-Object LastWriteTime -Descending
  foreach($taskCandidate in $taskCodexCandidates){if((& $taskCandidate.FullName --version) -eq 'codex-cli 0.162.0-alpha.17.2'){$Codex=$taskCandidate.FullName;break}}
 }
 if(-not $Codex){throw 'Required Codex CLI version unavailable; provide -Codex with the reviewed executable.'}
}
foreach($taskPath in @($Python,$Node,$Modules)){if(-not(Test-Path -LiteralPath $taskPath)){throw "Missing dependency: $taskPath"}}
$env:PYTHONIOENCODING='utf-8'
$taskArgs=@((Join-Path $PSScriptRoot 'code/reproduce.py'),'--mode',$Mode,'--output',$Output,'--node',$Node,'--modules',$Modules)
if($Codex){$taskArgs+=@('--codex',$Codex)}
if($Render){$taskArgs+='--render'}
& $Python @taskArgs
if($LASTEXITCODE -ne 0){throw "v14 generation failed with exit code $LASTEXITCODE"}
