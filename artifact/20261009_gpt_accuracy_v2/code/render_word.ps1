param([string]$Reports,[string]$Output)
$ErrorActionPreference='Stop'
$reportRoot=(Resolve-Path -LiteralPath $Reports).Path
New-Item -ItemType Directory -Path $Output -Force | Out-Null
$qaRoot=(Resolve-Path -LiteralPath $Output).Path
$wordApp=New-Object -ComObject Word.Application
$wordApp.Visible=$false
$wordApp.DisplayAlerts=0
$wordApp.ScreenUpdating=$false
$log=@()
try {
    foreach($inputDoc in (Get-ChildItem -LiteralPath $reportRoot -Filter '*.docx' -Recurse | Sort-Object FullName)) {
        $day=$inputDoc.Directory.Name
        $qaFolder=Join-Path $qaRoot $day
        New-Item -ItemType Directory -Path $qaFolder -Force | Out-Null
        $pdfPath=Join-Path $qaFolder 'report.pdf'
        $doc=$wordApp.Documents.Open($inputDoc.FullName,$false,$true,$false)
        try {
            $doc.Repaginate()
            $pages=$doc.ComputeStatistics(2)
            $doc.ExportAsFixedFormat($pdfPath,17,$false)
            $log+=@{date=$day;docx=$inputDoc.FullName;docx_sha256=(Get-FileHash -LiteralPath $inputDoc.FullName -Algorithm SHA256).Hash.ToLower();pdf=$pdfPath;pages=$pages;engine='Microsoft Word native ExportAsFixedFormat';read_only=$true}
            Write-Output "$day rendered $pages pages"
        } finally {$doc.Close(0)}
    }
} finally {
    $wordApp.Quit(0)
    [System.Runtime.InteropServices.Marshal]::FinalReleaseComObject($wordApp) | Out-Null
}
$log | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath (Join-Path $qaRoot 'render_log.json') -Encoding utf8
