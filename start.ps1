[CmdletBinding()]
param([switch]$Build)
$ErrorActionPreference='Stop'
Push-Location $PSScriptRoot
try {
    if (-not (Test-Path '.env')) {
        $outputPath=Join-Path $PSScriptRoot 'output'
        Set-Content .env "JOB_CV_OUTPUT_DIR=$outputPath" -Encoding utf8
    }
    $arguments=@('compose','-f','compose.yaml')
    if (Test-Path 'compose.local.yaml') { $arguments+=@('-f','compose.local.yaml') }
    $arguments+=@('up','-d')
    if ($Build) { $arguments+='--build' }
    & docker @arguments
    if ($LASTEXITCODE -ne 0) { throw 'Start Docker Desktop and retry.' }
    Write-Host 'Evidence CV services: http://127.0.0.1:5681'
} finally { Pop-Location }
