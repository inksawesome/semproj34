# Open a .docx in Word, optionally refresh the contents / lists of figures and tables / page numbers,
# save, and export a PDF.
#   powershell -ExecutionPolicy Bypass -File docs\tools\docx2pdf.ps1 -In <abs.docx> -Out <abs.pdf> -UpdateFields
param([string]$In, [string]$Out, [switch]$UpdateFields)
$word = New-Object -ComObject Word.Application
$word.Visible = $false
$word.DisplayAlerts = 0
try {
    $doc = $word.Documents.Open($In, $false, $false)
    if ($UpdateFields) {
        foreach ($t in $doc.TablesOfContents) { $t.Update() }
        foreach ($t in $doc.TablesOfFigures) { $t.Update() }
        $doc.Fields.Update() | Out-Null
        foreach ($t in $doc.TablesOfContents) { $t.Update() }
        foreach ($t in $doc.TablesOfFigures) { $t.Update() }
        $doc.Save()
    }
    $doc.ExportAsFixedFormat($Out, 17)
    Write-Output "pages=$($doc.ComputeStatistics(2))"
    $doc.Close($false)
} finally {
    $word.Quit()
}
