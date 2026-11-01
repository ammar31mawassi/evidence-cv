# Host-only contract tests: no Docker or model required.
$ErrorActionPreference='Stop'
$sandbox=Join-Path ([IO.Path]::GetTempPath()) ('cv-launcher-'+[guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory $sandbox | Out-Null
Copy-Item (Join-Path $PSScriptRoot '../job-cv.ps1') (Join-Path $sandbox 'job-cv.ps1')
Set-Content (Join-Path $sandbox 'start.ps1') 'param([switch]$Build,[string]$Model); if ($Model -eq "fail") { throw "startup failed" }; $global:cvBoots++'
$global:cvBoots=0
$global:cvSubmittedUrl=''
$global:cvFakePdf=Join-Path $sandbox 'fixture.pdf'
Set-Content $global:cvFakePdf 'fixture, not a generated CV'
function Invoke-RestMethod {
    param($Uri,$Method,$ContentType,$Body,$TimeoutSec)
    if ($Method -eq 'Post') { $global:cvSubmittedUrl=($Body | ConvertFrom-Json).url; return @{id='fixture'} }
    return @{status='completed';path=$global:cvFakePdf}
}
try {
    $launcher=Join-Path $sandbox 'job-cv.ps1'
    $result=& $launcher
    if ($global:cvBoots -ne 1 -or $result) { throw 'Bare command must boot and return without submitting.' }
    $result=& $launcher 'https://example.com/job?a=1&b=2'
    if ($global:cvSubmittedUrl -ne 'https://example.com/job?a=1&b=2' -or $result -ne $global:cvFakePdf) { throw 'Single-quoted URL or output path failed.' }
    $result=& $launcher "https://example.com/job?a=3&b=4"
    if ($global:cvSubmittedUrl -ne 'https://example.com/job?a=3&b=4' -or $result -ne $global:cvFakePdf) { throw 'Double-quoted URL or output path failed.' }
    $before=$global:cvBoots
    $rejected=$false
    try { & $launcher 'not-a-url' } catch { $rejected=$true }
    if (-not $rejected -or $before -ne $global:cvBoots) { throw 'Bad URLs must fail before startup.' }
    $rejected=$false
    try { & $launcher -Model fail } catch { $rejected=$true }
    if (-not $rejected) { throw 'Startup failure must propagate.' }
    Write-Host 'PASS: bare command, both quote styles with query strings, path output, invalid URL, startup failure.'
} finally {
    Remove-Item -LiteralPath (Join-Path $sandbox 'job-cv.ps1'),(Join-Path $sandbox 'start.ps1'),$global:cvFakePdf
    Remove-Item -LiteralPath $sandbox
    Remove-Variable cvBoots,cvSubmittedUrl,cvFakePdf -Scope Global
}
