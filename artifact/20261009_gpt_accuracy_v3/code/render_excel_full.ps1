param([string]$Reports,[string]$Output)
$ErrorActionPreference='Stop'
$reportRoot=(Resolve-Path -LiteralPath $Reports).Path
New-Item -ItemType Directory -Path $Output -Force | Out-Null
$qaRoot=(Resolve-Path -LiteralPath $Output).Path
$excelApp=New-Object -ComObject Excel.Application
$excelApp.Visible=$false; $excelApp.DisplayAlerts=$false; $excelApp.ScreenUpdating=$false
$log=@()
try {
  foreach($inputBook in (Get-ChildItem -LiteralPath $reportRoot -Filter '*.xlsx' -Recurse | Sort-Object FullName)) {
    $day=$inputBook.Directory.Name
    $book=$excelApp.Workbooks.Open($inputBook.FullName,0,$true)
    try {
      foreach($sheet in $book.Worksheets) {
        $last=if($sheet.Name -eq '飞机'){'P'}else{'K'}
        $rowCount=$sheet.UsedRange.Rows.Count
        $sheet.PageSetup.PrintArea='$A$1:$'+$last+'$'+$rowCount
        $sheet.PageSetup.PrintTitleRows='$1:$1'
        $sheet.PageSetup.Orientation=2; $sheet.PageSetup.PaperSize=8
        $sheet.PageSetup.Zoom=$false; $sheet.PageSetup.FitToPagesWide=1; $sheet.PageSetup.FitToPagesTall=$false
        $pdfPath=Join-Path $qaRoot ($day+'_'+$sheet.Name+'.pdf')
        # Render the delivered row heights before any read-only measurement.
        $sheet.ExportAsFixedFormat(0,$pdfPath)
        $heightChecks=@()
        for($row=2;$row -le $rowCount;$row++) {
          $originalHeight=$sheet.Rows.Item($row).RowHeight
          $sheet.Rows.Item($row).AutoFit() | Out-Null
          $requiredHeight=$sheet.Rows.Item($row).RowHeight
          $heightChecks+=@{row=$row;delivered_height=$originalHeight;excel_autofit_height=$requiredHeight;may_clip=($requiredHeight -gt ($originalHeight+1))}
          $sheet.Rows.Item($row).RowHeight=$originalHeight
        }
        $log+=@{date=$day;sheet=$sheet.Name;range=('A1:'+$last+$rowCount);row_count=$rowCount;column_count=$sheet.UsedRange.Columns.Count;xlsx_sha256=(Get-FileHash -LiteralPath $inputBook.FullName -Algorithm SHA256).Hash.ToLower();pdf=$pdfPath;cell_A2_display=$sheet.Range('A2').Text;cell_A2_serial=$sheet.Range('A2').Value2;engine='Microsoft Excel full used range native export';read_only=$true;row_height_checks=$heightChecks}
      }
      Write-Output "$day complete Excel ranges rendered"
    } finally {$book.Close($false)}
  }
} finally {$excelApp.Quit(); [System.Runtime.InteropServices.Marshal]::FinalReleaseComObject($excelApp) | Out-Null}
$log | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath (Join-Path $qaRoot 'native_excel_log.json') -Encoding utf8
