[CmdletBinding()]
param(
    [Parameter(Mandatory = $true, Position = 0)][string]$Url,
    [string]$DescriptionFile,
    [int]$TimeoutMinutes = 30
)
$ErrorActionPreference = 'Stop'
$base = 'http://127.0.0.1:5681/webhook/job-cv'
try {
    try {
        $null = Invoke-RestMethod -Uri 'http://127.0.0.1:5681/healthz' -TimeoutSec 5
    } catch {
        Write-Progress -Activity 'Producing tailored CV locally' -Status 'Starting local Docker services'
        & (Join-Path $PSScriptRoot 'start.ps1') | Out-Host
        $ready = $false
        for ($attempt = 0; $attempt -lt 30; $attempt++) {
            try {
                $null = Invoke-RestMethod -Uri 'http://127.0.0.1:5681/healthz' -TimeoutSec 5
                $ready = $true
                break
            } catch { Start-Sleep -Seconds 2 }
        }
        if (-not $ready) { throw 'Local n8n did not start. Confirm Docker Desktop is running.' }
    }
    $payload = @{ url = $Url }
    if ($DescriptionFile) {
        $payload.description = Get-Content -LiteralPath $DescriptionFile -Raw -Encoding utf8
    }
    try {
        $job = Invoke-RestMethod -Uri $base -Method Post -ContentType 'application/json' -Body ($payload | ConvertTo-Json) -TimeoutSec 30
    } catch {
        throw "Could not submit to local n8n. Run the setup/start script in job-cv-local, then retry. $($_.Exception.Message)"
    }
    if (-not $job.id) { throw 'n8n did not return a job ID.' }
    $deadline = (Get-Date).AddMinutes($TimeoutMinutes)
    while ((Get-Date) -lt $deadline) {
        $result = Invoke-RestMethod -Uri "$base/status?id=$($job.id)" -TimeoutSec 30
        if ($result.status -eq 'completed') {
            if (-not (Test-Path -LiteralPath $result.path -PathType Leaf)) {
                throw "The service returned a PDF path that is not accessible on Windows: $($result.path)"
            }
            Write-Progress -Activity 'Producing tailored CV locally' -Completed
            Write-Output $result.path
            return
        }
        if ($result.status -eq 'failed') { throw $result.error }
        if ($result.status -notin @('queued', 'running')) { throw 'The progress workflow returned an unexpected response.' }
        Write-Progress -Activity 'Producing tailored CV locally' -Status $result.stage
        Start-Sleep -Seconds 2
    }
    throw "Generation is still running. Job ID: $($job.id). Check http://localhost:8012/jobs/$($job.id)."
} finally {
    Write-Progress -Activity 'Producing tailored CV locally' -Completed
}
