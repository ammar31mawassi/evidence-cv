[CmdletBinding()]
param([switch]$Build, [string]$Model, [switch]$SkipCareerCheck, [switch]$SkipDiscoveryCatchup)
$ErrorActionPreference='Stop'
. (Join-Path $PSScriptRoot 'compose-command.ps1')
if (-not (Get-Command docker -ErrorAction SilentlyContinue)) { throw 'Install Docker Desktop and retry.' }
$engineReady = Test-CvDockerEngine
if (-not $engineReady) {
    $desktop=Join-Path $env:ProgramFiles 'Docker/Docker/Docker Desktop.exe'
    if (-not (Test-Path $desktop)) { throw 'Start Docker Desktop and retry.' }
    Write-Host 'Starting Docker Desktop...'
    Start-Process -FilePath $desktop -WindowStyle Hidden
    $deadline=(Get-Date).AddMinutes(3)
    while ((Get-Date) -lt $deadline) {
        $engineReady=Test-CvDockerEngine
        if ($engineReady) { break }
        Start-Sleep -Seconds 3
    }
    if (-not $engineReady) { throw 'Docker Desktop did not become ready. Check its WSL/engine status and retry.' }
}
Push-Location $PSScriptRoot
try {
    if (-not (Test-Path '.env')) {
        $outputPath=Join-Path $PSScriptRoot 'output'
        Set-Content .env "JOB_CV_OUTPUT_DIR=$outputPath" -Encoding utf8
    }
    if ($Model) {
        if ($Model -notmatch '^[a-zA-Z0-9][a-zA-Z0-9._:-]*$' -or $Model -match '(?i)cloud') { throw 'Choose a local library tag, e.g. qwen3.5:4b or deepseek-r1:8b.' }
        $settings=Get-Content .env -Raw
        if ($settings -match '(?m)^OLLAMA_MODEL=') { $settings=[regex]::Replace($settings,'(?m)^OLLAMA_MODEL=.*$',"OLLAMA_MODEL=$Model") }
        else { $settings+="`nOLLAMA_MODEL=$Model`n" }
        Set-Content .env $settings -Encoding utf8
        $env:OLLAMA_MODEL=$Model
    }
    $arguments=@('up','-d')
    if ($Build) { $arguments+='--build' }
    Invoke-CvCompose @arguments | Out-Host
    $health=Wait-CvEndpoint 'http://127.0.0.1:8012/health'
    $tags=Wait-CvEndpoint 'http://127.0.0.1:11436/api/tags'
    $selectedModel=$health.model
    if ($selectedModel -match '(?i)cloud|/') { throw 'Cloud/remote models are not permitted.' }
    if ($selectedModel -notin @($tags.models | ForEach-Object { $_.name })) {
        Write-Host "Downloading $selectedModel (first use only)..."
        Invoke-CvCompose exec -T ollama ollama pull $selectedModel | Out-Host
    }
    Write-Host "Checking local inference with $selectedModel..."
    $body=@{model=$selectedModel;stream=$false;think=$false;format='json';messages=@(@{role='user';content='Return only this JSON object: {"ready":true}'});options=@{temperature=0;num_predict=64}} | ConvertTo-Json -Depth 6
    $reply=Invoke-RestMethod 'http://127.0.0.1:11436/api/chat' -Method Post -ContentType 'application/json' -Body $body -TimeoutSec 300
    if (-not ($reply.message.content | ConvertFrom-Json).ready) { throw 'The model failed the local JSON inference check.' }
    $null=Wait-CvEndpoint 'http://127.0.0.1:5681/healthz'
    New-Item -ItemType Directory -Force state | Out-Null
    $hash=(Get-FileHash n8n/job-cv.json).Hash+(Get-FileHash n8n/job-cv-status.json).Hash
    if (Test-Path private/search.json) { $hash+=(Get-FileHash n8n/job-discovery.json).Hash }
    if (-not (Test-Path state/workflows.sha256) -or (Get-Content state/workflows.sha256 -Raw).Trim() -ne $hash) {
        & ./import-workflows.ps1 | Out-Host
        $null=Wait-CvEndpoint 'http://127.0.0.1:5681/healthz'
        Set-Content state/workflows.sha256 $hash
    }
    if (-not $SkipCareerCheck) {
        Invoke-CvCompose exec -T worker python check-career.py | Out-Host
    }
    if (-not $SkipDiscoveryCatchup -and (Test-Path private/search.json) -and (Select-String -LiteralPath .env -Pattern '^DISCOVERY_TOKEN=.' -Quiet) -and (Get-Content private/search.json -Raw | ConvertFrom-Json).enabled) {
        $tokenLine=(Get-Content .env | Where-Object {$_ -match '^DISCOVERY_TOKEN='} | Select-Object -First 1)
        $discoverySecret=$tokenLine.Substring('DISCOVERY_TOKEN='.Length).Trim()
        $null=Invoke-RestMethod 'http://127.0.0.1:8012/discovery/run' -Method Post -Headers @{'X-Discovery-Token'=$discoverySecret} -ContentType 'application/json' -Body '{"force":false,"send_email":true}' -TimeoutSec 10
        Write-Host 'Daily job digest enabled; queued a check for any missed run after 13:00.'
    }
    Write-Host "Ready. Model: $selectedModel | n8n: http://127.0.0.1:5681"
} finally { Pop-Location }
