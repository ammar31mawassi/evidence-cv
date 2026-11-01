$ErrorActionPreference='Stop'
Push-Location $PSScriptRoot
try {
    & ./start.ps1 -Build -SkipCareerCheck
    & ./install-command.ps1
    Write-Host 'Next: ask your agent to follow AGENTS.md and finish private onboarding before generating a real CV.'
} finally { Pop-Location }
