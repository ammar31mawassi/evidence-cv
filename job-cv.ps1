[CmdletBinding()]
param(
    [Parameter(Position = 0)][string]$Url,
    [string]$Model,
    [switch]$Build,
    [switch]$Discover,
    [switch]$DigestStatus,
    [switch]$NoEmail,
    [string]$DescriptionFile,
    [int]$TimeoutMinutes = 30
)
$ErrorActionPreference = 'Stop'
$base = 'http://127.0.0.1:5681/webhook/job-cv'
try {
    if ($Url -and ($Discover -or $DigestStatus)) { throw 'Use either a job URL or a discovery command.' }
    if ($Url -and ($Url -notmatch '^https?://' -or -not [uri]::IsWellFormedUriString($Url, [UriKind]::Absolute))) { throw 'Provide one quoted http/https job URL.' }
    if ($DescriptionFile -and -not (Test-Path -LiteralPath $DescriptionFile -PathType Leaf)) { throw 'Description file does not exist.' }
    $startup=@{Build=$Build;SkipDiscoveryCatchup=($Discover -or $DigestStatus -or $NoEmail)}
    if ($Model) { $startup.Model=$Model }
    & (Join-Path $PSScriptRoot 'start.ps1') @startup | Out-Host
    if ($Discover -or $DigestStatus) {
        $line=Get-Content (Join-Path $PSScriptRoot '.env') | Where-Object {$_ -match '^DISCOVERY_TOKEN='} | Select-Object -First 1
        if (-not $line) { throw 'Configure private/search.json and DISCOVERY_TOKEN first.' }
        $headers=@{'X-Discovery-Token'=$line.Substring('DISCOVERY_TOKEN='.Length).Trim()}
        if ($DigestStatus) {
            Invoke-RestMethod 'http://127.0.0.1:8012/discovery/latest' -Headers $headers | ConvertTo-Json -Depth 12
        } else {
            $body=@{force=$true;send_email=(-not $NoEmail)} | ConvertTo-Json
            Invoke-RestMethod 'http://127.0.0.1:8012/discovery/run' -Method Post -Headers $headers -ContentType 'application/json' -Body $body | ConvertTo-Json
            Write-Host 'Discovery queued. Use job-cv -DigestStatus to read the result.'
        }
        return
    }
    if (-not $Url) { return }
    $payload = @{ url = $Url }
    if ($DescriptionFile) {
        $payload.description = Get-Content -LiteralPath $DescriptionFile -Raw -Encoding utf8
    }
    try {
        $job = Invoke-RestMethod -Uri $base -Method Post -ContentType 'application/json' -Body ($payload | ConvertTo-Json) -TimeoutSec 30
    } catch {
        throw "Could not submit to local n8n. Run ./import-workflows.ps1 in evidence-cv, then retry. $($_.Exception.Message)"
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
        if ($result.status -eq 'failed') {
            $diagnostics=Join-Path (Join-Path $PSScriptRoot 'state') $job.id
            throw "$($result.error) Job ID: $($job.id). Local diagnostics: $diagnostics"
        }
        if ($result.status -notin @('queued', 'running')) { throw 'The progress workflow returned an unexpected response.' }
        Write-Progress -Activity 'Producing tailored CV locally' -Status $result.stage
        Start-Sleep -Seconds 2
    }
    throw "Generation is still running. Job ID: $($job.id). Check http://localhost:8012/jobs/$($job.id)."
} finally {
    Write-Progress -Activity 'Producing tailored CV locally' -Completed
}
