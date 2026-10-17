$ErrorActionPreference='Stop'
Push-Location $PSScriptRoot
try {
    & ./start.ps1 -Build
    & docker compose exec -T ollama ollama pull qwen3.5:4b
    if ($LASTEXITCODE -ne 0) { throw 'Local model download failed.' }
    & ./import-workflows.ps1
    & ./install-command.ps1
    Write-Host 'Next: ask your agent to follow AGENTS.md and finish private onboarding before generating a real CV.'
} finally { Pop-Location }
