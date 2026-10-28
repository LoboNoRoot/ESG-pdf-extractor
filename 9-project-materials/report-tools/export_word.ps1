$ErrorActionPreference = 'Stop'
$docx = (Resolve-Path -LiteralPath 'C:\Users\Lenovo\Desktop\省一改\项目报告书-智析万卷：面向ESG报告的自适应布局分析与要素提取-专业团队ProMax-国赛专项修订版.docx').Path
$pdf = 'C:\Users\Lenovo\Desktop\省一改\项目报告书-智析万卷：面向ESG报告的自适应布局分析与要素提取-专业团队ProMax-国赛专项修订版.pdf'
$word = $null
$doc = $null
try {
    $word = New-Object -ComObject Word.Application
    $word.Visible = $false
    $word.DisplayAlerts = 0
    $word.Options.UpdateFieldsAtPrint = $true
    $doc = $word.Documents.Open($docx)
    $null = $doc.Fields.Update()
    foreach ($toc in $doc.TablesOfContents) { $toc.Update() }
    foreach ($tof in $doc.TablesOfFigures) { $tof.Update() }
    $doc.Repaginate()
    $pages = $doc.ComputeStatistics(2)
    $doc.Save()
    $doc.ExportAsFixedFormat($pdf, 17)
    Write-Output "DOCX=$docx"
    Write-Output "PDF=$pdf"
    Write-Output "PAGES=$pages"
}
finally {
    if ($doc -ne $null) { $doc.Close($false) }
    if ($word -ne $null) { $word.Quit() }
    [GC]::Collect()
    [GC]::WaitForPendingFinalizers()
}
