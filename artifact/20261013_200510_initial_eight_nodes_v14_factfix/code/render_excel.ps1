param([string]$Output=(Split-Path -Parent $PSScriptRoot))
$ErrorActionPreference='Stop'
$taskDates=@('2025.5.10','2025.5.18','2025.5.30','2025.6.9','2025.6.17','2025.6.29','2025.7.9','2025.7.17')
$taskExcel=New-Object -ComObject Excel.Application
$taskExcel.Visible=$false
$taskExcel.DisplayAlerts=$false
 $taskRenderer=if($taskExcel.Path -match 'Kingsoft|WPS'){'WPS Office through Excel.Application COM'}else{'Excel.Application COM: '+$taskExcel.Name}
$taskRecords=@()
try {
 foreach($taskDate in $taskDates){
  $taskSource=Join-Path $Output "official/$taskDate/$($taskDate)机舰活动明细.xlsx"
  $taskFolder=Join-Path $Output "qa/xlsx_native/$taskDate"
  New-Item -ItemType Directory -Path $taskFolder -Force | Out-Null
  $taskBook=$taskExcel.Workbooks.Open($taskSource,0,$true)
  try {
   foreach($taskName in @('飞机','舰艇')){
    $taskSheet=$taskBook.Worksheets.Item($taskName)
    $taskRows=$taskSheet.UsedRange.Rows.Count
    $taskBands=if($taskName -eq '飞机'){@('A:H','I:P')}else{@('A:F','G:K')}
    for($taskIndex=0;$taskIndex -lt $taskBands.Length;$taskIndex++){
     $taskPair=$taskBands[$taskIndex].Split(':')
     $taskRange="$($taskPair[0])1:$($taskPair[1])$taskRows"
     $taskSheet.PageSetup.PrintArea=$taskRange
     $taskSheet.PageSetup.Orientation=2
     $taskSheet.PageSetup.PaperSize=8
     $taskSheet.PageSetup.Zoom=$false
     $taskSheet.PageSetup.FitToPagesWide=1
     $taskSheet.PageSetup.FitToPagesTall=1
     $taskSheet.PageSetup.LeftMargin=18
     $taskSheet.PageSetup.RightMargin=18
     $taskSheet.PageSetup.TopMargin=24
     $taskSheet.PageSetup.BottomMargin=24
     $taskPdf=Join-Path $taskFolder "$($taskName)_$($taskIndex+1).pdf"
     $taskSheet.ExportAsFixedFormat(0,$taskPdf)
     $taskRecords+=@{node=$taskDate;sheet=$taskName;range=$taskRange;renderer=$taskRenderer;application_path=$taskExcel.Path;version=$taskExcel.Version;output=$taskPdf;status='exported';source_sha256=(Get-FileHash -LiteralPath $taskSource -Algorithm SHA256).Hash}
    }
   }
  } finally {$taskBook.Close($false)}
  Write-Output "Excel rendered all cells $taskDate"
 }
} finally {try {$taskExcel.Quit()}catch {Write-Output 'Excel closed after exports'}}
$taskRecords | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath (Join-Path $Output 'excel_render.json') -Encoding utf8
