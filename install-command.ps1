[CmdletBinding()]
param()
$ErrorActionPreference = 'Stop'
$scriptPath = Join-Path $PSScriptRoot 'job-cv.ps1'
$escapedPath = $scriptPath.Replace("'", "''")
$definition = "function global:job-cv { & '$escapedPath' @args }"
# All-host profiles cover both ConsoleHost and other PowerShell hosts.
$profilePaths = @(
    (Join-Path ([Environment]::GetFolderPath('MyDocuments')) 'PowerShell\profile.ps1'),
    (Join-Path ([Environment]::GetFolderPath('MyDocuments')) 'WindowsPowerShell\profile.ps1')
)
foreach ($profilePath in $profilePaths) {
    New-Item -ItemType Directory -Path (Split-Path $profilePath) -Force | Out-Null
    if (-not (Test-Path -LiteralPath $profilePath)) { New-Item -ItemType File -Path $profilePath | Out-Null }
    $content = Get-Content -LiteralPath $profilePath -Raw -ErrorAction SilentlyContinue
    $block = "# BEGIN Local Job CV`r`n$definition`r`n# END Local Job CV"
    if ($content -match '(?s)# BEGIN Local Job CV.*?# END Local Job CV') {
        $content = [regex]::Replace($content, '(?s)# BEGIN Local Job CV.*?# END Local Job CV', [System.Text.RegularExpressions.MatchEvaluator]{ param($m) $block })
    } else { $content = "$content`r`n$block`r`n" }
    Set-Content -LiteralPath $profilePath -Value $content -Encoding utf8
}
Invoke-Expression $definition
Write-Output 'Installed job-cv for PowerShell 7 and Windows PowerShell. New terminals load it automatically.'
