$ErrorActionPreference='Stop'
$taskRoot=Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$taskProject=Split-Path -Parent $taskRoot
$taskReference=Join-Path $taskProject '提交示例文件/日报/2025.10.20/2025.10.20日报.docx'
$taskDestination=Join-Path (Split-Path -Parent $PSScriptRoot) 'qa/sample_docx/report.pdf'
$taskWord=New-Object -ComObject Word.Application
$taskWord.Visible=$false
$taskWord.DisplayAlerts=0
try {
 $taskDoc=$taskWord.Documents.Open($taskReference,$false,$true)
 try {
  $taskDoc.ExportAsFixedFormat($taskDestination,17)
  @{renderer=$taskWord.Path;version=$taskWord.Version;source_sha256=(Get-FileHash -LiteralPath $taskReference -Algorithm SHA256).Hash;pages=$taskDoc.ComputeStatistics(2);packaged_renderer_failure='LibreOffice soffice.exe was not found on PATH';fallback='Word.Application COM full export'} | ConvertTo-Json | Set-Content -LiteralPath (Join-Path (Split-Path -Parent $PSScriptRoot) 'qa/sample_renderer.json') -Encoding utf8
 } finally {$taskDoc.Close(0)}
} finally {$taskWord.Quit()}
