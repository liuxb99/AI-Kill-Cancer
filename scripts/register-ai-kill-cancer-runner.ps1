param(
    [Parameter(Mandatory = $true)]
    [string]$RunnerToken,

    [string]$RunnerRoot = "$env:SystemDrive\actions-runner-ai-kill-cancer",
    [string]$RunnerName = "$env:COMPUTERNAME-ai-kill-cancer",
    [string]$Labels = "ai-ci",
    [switch]$Replace
)

$ErrorActionPreference = 'Stop'
$RepoUrl = 'https://github.com/liuxb99/AI-Kill-Cancer'

function Assert-Admin {
    $identity = [Security.Principal.WindowsIdentity]::GetCurrent()
    $principal = New-Object Security.Principal.WindowsPrincipal($identity)
    if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
        throw 'Please run PowerShell as Administrator.'
    }
}

Assert-Admin

if (-not (Test-Path $RunnerRoot)) {
    New-Item -ItemType Directory -Path $RunnerRoot -Force | Out-Null
}

$cfg = Join-Path $RunnerRoot 'config.cmd'
if (-not (Test-Path $cfg)) {
    throw "GitHub Actions runner is not installed in $RunnerRoot. Install/copy the official Windows x64 runner files there first."
}

Push-Location $RunnerRoot
try {
    if (Test-Path '.runner') {
        if (-not $Replace) {
            Write-Host 'Runner is already configured. Use -Replace to remove and reconfigure it.'
            exit 0
        }

        if (Test-Path '.service') {
            & .\svc.cmd stop 2>$null
            & .\svc.cmd uninstall 2>$null
        }
        & .\config.cmd remove --token $RunnerToken
    }

    & .\config.cmd `
        --unattended `
        --url $RepoUrl `
        --token $RunnerToken `
        --name $RunnerName `
        --labels $Labels `
        --work '_work' `
        --replace

    if (-not (Test-Path '.runner')) {
        throw 'Runner registration did not create .runner.'
    }

    if (-not (Test-Path '.\svc.cmd')) {
        throw 'svc.cmd is missing. Use the official Windows x64 GitHub Actions runner package.'
    }

    & .\svc.cmd install
    & .\svc.cmd start

    Write-Host ''
    Write-Host '[OK] AI-Kill-Cancer self-hosted runner registered and service started.'
    Write-Host "Repository: $RepoUrl"
    Write-Host "Runner:     $RunnerName"
    Write-Host "Labels:     self-hosted, Windows, X64, $Labels"
    Write-Host ''
    Write-Host 'The queued Local Verification Gate should be picked up automatically.'
}
finally {
    Pop-Location
}
