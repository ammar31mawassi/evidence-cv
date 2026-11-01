$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot 'compose-command.ps1')
Push-Location $PSScriptRoot
try {
    Invoke-CvCompose exec -T n8n n8n import:workflow --input=/workflow-import/job-cv.json
    if ($LASTEXITCODE -ne 0) { throw 'Could not import submission workflow.' }
    Invoke-CvCompose exec -T n8n n8n import:workflow --input=/workflow-import/job-cv-status.json
    if ($LASTEXITCODE -ne 0) { throw 'Could not import progress workflow.' }
    Invoke-CvCompose exec -T n8n n8n publish:workflow --id=localJobCvSubmit
    if ($LASTEXITCODE -ne 0) { throw 'Could not publish submission workflow.' }
    Invoke-CvCompose exec -T n8n n8n publish:workflow --id=localJobCvStatus
    if ($LASTEXITCODE -ne 0) { throw 'Could not publish progress workflow.' }
    if (Select-String -LiteralPath .env -Pattern '^DISCOVERY_TOKEN=.' -Quiet) {
        Invoke-CvCompose exec -T n8n n8n import:workflow --input=/workflow-import/job-discovery.json
        Invoke-CvCompose exec -T n8n n8n publish:workflow --id=localJobDiscovery
    }
    Invoke-CvCompose restart n8n
    if ($LASTEXITCODE -ne 0) { throw 'Could not restart n8n to register the webhooks.' }
} finally { Pop-Location }
