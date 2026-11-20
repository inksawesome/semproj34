# Export a .pptx to PDF with PowerPoint (for visual checks of the deck).
#   powershell -ExecutionPolicy Bypass -File docs\tools\pptx2pdf.ps1 -In <abs.pptx> -Out <abs.pdf>
param([string]$In, [string]$Out)
$pp = New-Object -ComObject PowerPoint.Application
try {
    $p = $pp.Presentations.Open($In, $true, $false, $false)
    $p.SaveAs($Out, 32)
    Write-Output "slides=$($p.Slides.Count)"
    $p.Close()
} finally {
    $pp.Quit()
}
