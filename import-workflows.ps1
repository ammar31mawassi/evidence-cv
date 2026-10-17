$ErrorActionPreference = 'Stop'
Push-Location $PSScriptRoot
try {
    & docker compose exec -T n8n n8n import:workflow --input=/workflow-import/job-cv.json
    if ($LASTEXITCODE -ne 0) { throw 'Could not import submission workflow.' }
    & docker compose exec -T n8n n8n import:workflow --input=/workflow-import/job-cv-status.json
    if ($LASTEXITCODE -ne 0) { throw 'Could not import progress workflow.' }
    & docker compose exec -T n8n n8n publish:workflow --id=localJobCvSubmit
    if ($LASTEXITCODE -ne 0) { throw 'Could not publish submission workflow.' }
    & docker compose exec -T n8n n8n publish:workflow --id=localJobCvStatus
    if ($LASTEXITCODE -ne 0) { throw 'Could not publish progress workflow.' }
    & docker compose restart n8n
    if ($LASTEXITCODE -ne 0) { throw 'Could not restart n8n to register the webhooks.' }
} finally { Pop-Location }
