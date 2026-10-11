param([string]$Reports,[string]$Output)
$ErrorActionPreference='Stop'
$reportRoot=(Resolve-Path -LiteralPath $Reports).Path
New-Item -ItemType Directory -Path $Output -Force | Out-Null
$qaRoot=(Resolve-Path -LiteralPath $Output).Path
$excelApp=New-Object -ComObject Excel.Application
$excelApp.Visible=$false
$excelApp.DisplayAlerts=$false
$excelApp.ScreenUpdating=$false
$log=@()
try {
    foreach($inputBook in (Get-ChildItem -LiteralPath $reportRoot -Filter '*.xlsx' -Recurse | Sort-Object FullName)) {
        $day=$inputBook.Directory.Name
        $book=$excelApp.Workbooks.Open($inputBook.FullName,0,$true)
        try {
            foreach($sheet in $book.Worksheets) {
                $last=if($sheet.Name -eq '飞机'){'P'}else{'K'}
                $rowCount=[Math]::Min(5,$sheet.UsedRange.Rows.Count)
                $sheet.PageSetup.PrintArea='$A$1:$'+$last+'$'+$rowCount
                $sheet.PageSetup.Orientation=2
                $sheet.PageSetup.PaperSize=8
                $sheet.PageSetup.Zoom=$false
                $sheet.PageSetup.FitToPagesWide=1
                $sheet.PageSetup.FitToPagesTall=1
                $pdfPath=Join-Path $qaRoot ($day+'_'+$sheet.Name+'.pdf')
                $sheet.ExportAsFixedFormat(0,$pdfPath)
                $log+=@{date=$day;sheet=$sheet.Name;xlsx_sha256=(Get-FileHash -LiteralPath $inputBook.FullName -Algorithm SHA256).Hash.ToLower();pdf=$pdfPath;cell_A2_display=$sheet.Range('A2').Text;cell_A2_serial=$sheet.Range('A2').Value2;cell_A2_format=$sheet.Range('A2').NumberFormat;engine='Microsoft Excel native';read_only=$true}
            }
            Write-Output "$day Excel sheets rendered"
        } finally {$book.Close($false)}
    }
} finally {
    $excelApp.Quit()
    [System.Runtime.InteropServices.Marshal]::FinalReleaseComObject($excelApp) | Out-Null
}
$log | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath (Join-Path $qaRoot 'native_excel_log.json') -Encoding utf8
