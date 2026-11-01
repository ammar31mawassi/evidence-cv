function Invoke-CvCompose {
    $composeArgs = @('compose', '--project-directory', $PSScriptRoot, '-f', (Join-Path $PSScriptRoot 'compose.yaml'))
    if (Test-Path (Join-Path $PSScriptRoot 'compose.local.yaml')) { $composeArgs += @('-f', (Join-Path $PSScriptRoot 'compose.local.yaml')) }
    & docker @composeArgs @args
    if ($LASTEXITCODE -ne 0) { throw "Docker Compose failed: $args" }
}
function Test-CvDockerEngine {
    # Docker's CLI can itself hang while Desktop is starting. Bound each probe.
    $info=New-Object System.Diagnostics.ProcessStartInfo
    $info.FileName=(Get-Command docker -ErrorAction Stop).Source
    $info.Arguments='info --format {{.ServerVersion}}'
    $info.UseShellExecute=$false
    $info.CreateNoWindow=$true
    $info.RedirectStandardOutput=$true
    $info.RedirectStandardError=$true
    $probe=New-Object System.Diagnostics.Process
    $probe.StartInfo=$info
    try {
        $null=$probe.Start()
        if (-not $probe.WaitForExit(5000)) { $probe.Kill(); return $false }
        return $probe.ExitCode -eq 0
    } finally { $probe.Dispose() }
}
function Wait-CvEndpoint([string]$Uri, [int]$Seconds = 180) {
    $deadline = (Get-Date).AddSeconds($Seconds)
    while ((Get-Date) -lt $deadline) {
        try { return (Invoke-RestMethod -Uri $Uri -TimeoutSec 3) } catch { Start-Sleep -Seconds 2 }
    }
    throw "Timed out waiting for $Uri. Inspect Docker Compose logs."
}
