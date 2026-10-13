param([string]$Output=(Split-Path -Parent $PSScriptRoot))
$ErrorActionPreference='Stop'
$taskDates=@('2025.5.10','2025.5.18','2025.5.30','2025.6.9','2025.6.17','2025.6.29','2025.7.9','2025.7.17')
$taskRecords=@()
foreach($taskDate in $taskDates){
 $taskWord=New-Object -ComObject Word.Application
 $taskWord.Visible=$false
 $taskWord.DisplayAlerts=0
 $taskRenderer=if($taskWord.Path -match 'Kingsoft|WPS'){'WPS Office through Word.Application COM'}else{'Word.Application COM: '+$taskWord.Name}
 $taskSource=Join-Path $Output "official/$taskDate/$($taskDate)日报.docx"
 $taskFolder=Join-Path $Output "qa/docx/$taskDate"
 New-Item -ItemType Directory -Path $taskFolder -Force | Out-Null
 try {
  $taskDoc=$taskWord.Documents.Open($taskSource,$false,$true)
  try {$taskDoc.ExportAsFixedFormat((Join-Path $taskFolder 'report.pdf'),17)
   $taskRecords+=@{node=$taskDate;source=$taskSource;source_sha256=(Get-FileHash -LiteralPath $taskSource -Algorithm SHA256).Hash;renderer=$taskRenderer;application_path=$taskWord.Path;version=$taskWord.Version;status='exported_full_document';pages=$taskDoc.ComputeStatistics(2)}
  } finally {$taskDoc.Close(0)}
 } finally {try {$taskWord.Quit()} catch {Write-Output "Word closed after export $taskDate"}}
 Write-Output "Rendered $taskDate"
}
$taskRecords | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath (Join-Path $Output 'word_render.json') -Encoding utf8
