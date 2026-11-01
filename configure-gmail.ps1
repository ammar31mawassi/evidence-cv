[CmdletBinding()]
param([string]$Email,[string]$Recipient)
$ErrorActionPreference='Stop'
if (-not $Email) { $Email=Read-Host 'Gmail address to send from' }
if (-not $Recipient) { $Recipient=$Email }
if ($Email -notmatch '^[^\s@]+@[^\s@]+\.[^\s@]+$' -or $Recipient -notmatch '^[^\s@]+@[^\s@]+\.[^\s@]+$') { throw 'Enter valid email addresses.' }
Write-Host 'Create a Gmail App Password for Evidence CV at https://myaccount.google.com/apppasswords'
Write-Host 'Enter it here only. It will be stored under ignored private/mail-secrets.'
$secret=Read-Host 'Gmail App Password (hidden)' -AsSecureString
$pointer=[Runtime.InteropServices.Marshal]::SecureStringToBSTR($secret)
try {
    $password=[Runtime.InteropServices.Marshal]::PtrToStringBSTR($pointer).Replace(' ','')
    if ($password -notmatch '^[a-zA-Z]{16}$') { throw 'Expected a 16-letter Google App Password, not your normal account password.' }
    $directory=Join-Path $PSScriptRoot 'private/mail-secrets'
    New-Item -ItemType Directory -Force $directory | Out-Null
    [IO.File]::WriteAllText((Join-Path $directory 'smtp.json'),(@{username=$Email;password=$password} | ConvertTo-Json),[Text.UTF8Encoding]::new($false))
    $configPath=Join-Path $PSScriptRoot 'private/search.json'
    $config=Get-Content -LiteralPath $configPath -Raw | ConvertFrom-Json
    $config.mail.mode='smtp';$config.mail.sender=$Email;$config.mail.recipient=$Recipient
    [IO.File]::WriteAllText($configPath,($config | ConvertTo-Json -Depth 12),[Text.UTF8Encoding]::new($false))
    Write-Host 'Gmail App Password saved locally. Return to the CV setup to test delivery and enable the schedule.'
} finally {
    [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($pointer)
    $password=$null;$secret=$null
}
