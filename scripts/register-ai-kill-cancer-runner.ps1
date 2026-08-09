param(
    [string]$RunnerRoot = "$env:SystemDrive\github-runners\AI-Kill-Cancer",
    [string]$RunnerName = "$env:COMPUTERNAME-ai-kill-cancer",
    [string]$Labels = "ai-ci",
    [switch]$ForceRepair
)

$ErrorActionPreference = 'Stop'
$Repo = 'liuxb99/AI-Kill-Cancer'
$RepoUrl = "https://github.com/$Repo"
$CacheDir = "$env:SystemDrive\github-runner-cache"

function Assert-Admin {
    $identity = [Security.Principal.WindowsIdentity]::GetCurrent()
    $principal = New-Object Security.Principal.WindowsPrincipal($identity)
    if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
        throw 'Please run PowerShell as Administrator.'
    }
}

function Assert-Gh {
    if (-not (Get-Command gh -ErrorAction SilentlyContinue)) {
        throw 'GitHub CLI (gh) is required. Install it with: winget install --id GitHub.cli'
    }

    & gh auth status *> $null
    if ($LASTEXITCODE -ne 0) {
        throw 'GitHub CLI is not authenticated. Run: gh auth login'
    }

    & gh api "repos/$Repo" --silent *> $null
    if ($LASTEXITCODE -ne 0) {
        throw "The current gh login cannot access $Repo."
    }
}

function Get-ApiToken([string]$Endpoint) {
    $token = (& gh api --method POST $Endpoint --jq '.token').Trim()
    if (-not $token) {
        throw "Could not obtain token from $Endpoint"
    }
    return $token
}

function Get-RunnerService {
    if (Test-Path (Join-Path $RunnerRoot '.service')) {
        $serviceName = (Get-Content (Join-Path $RunnerRoot '.service') -Raw).Trim()
        if ($serviceName) {
            return Get-Service -Name $serviceName -ErrorAction SilentlyContinue
        }
    }

    return Get-CimInstance Win32_Service -ErrorAction SilentlyContinue |
        Where-Object {
            $_.Name -like 'actions.runner.*' -and
            $_.PathName -like "*$($RunnerRoot.Replace('\','*'))*"
        } |
        Select-Object -First 1
}

function Ensure-RunnerPackage {
    New-Item -ItemType Directory -Path $RunnerRoot -Force | Out-Null
    New-Item -ItemType Directory -Path $CacheDir -Force | Out-Null

    $configCmd = Join-Path $RunnerRoot 'config.cmd'
    if (Test-Path $configCmd) {
        return
    }

    Write-Host '[1] Detecting latest GitHub Actions Runner version...'
    $tag = (& gh api repos/actions/runner/releases/latest --jq '.tag_name').Trim()
    if (-not $tag) {
        throw 'Could not detect the latest GitHub Actions Runner version.'
    }

    $version = $tag.TrimStart('v')
    $zipName = "actions-runner-win-x64-$version.zip"
    $zipPath = Join-Path $CacheDir $zipName
    $url = "https://github.com/actions/runner/releases/download/v$version/$zipName"

    if (-not (Test-Path $zipPath)) {
        Write-Host "[2] Downloading GitHub Actions Runner $version..."
        Invoke-WebRequest -Uri $url -OutFile $zipPath
    }
    else {
        Write-Host "[2] Using cached runner package: $zipPath"
    }

    Write-Host '[3] Extracting runner package...'
    Expand-Archive -Path $zipPath -DestinationPath $RunnerRoot -Force

    if (-not (Test-Path $configCmd)) {
        throw "config.cmd is missing after extraction into $RunnerRoot"
    }
}

function Get-ConfiguredUrl {
    $runnerFile = Join-Path $RunnerRoot '.runner'
    if (-not (Test-Path $runnerFile)) {
        return $null
    }

    try {
        $runner = Get-Content $runnerFile -Raw | ConvertFrom-Json
        if ($runner.gitHubUrl) { return [string]$runner.gitHubUrl }
        if ($runner.serverUrl) { return [string]$runner.serverUrl }
    }
    catch {
        Write-Warning "Could not parse existing .runner file: $($_.Exception.Message)"
    }

    return $null
}

function Remove-ExistingRunner {
    if (-not (Test-Path (Join-Path $RunnerRoot '.runner'))) {
        return
    }

    Write-Host '[4] Removing stale/wrong runner registration...'
    Push-Location $RunnerRoot
    try {
        if (Test-Path '.\svc.cmd') {
            & .\svc.cmd stop *> $null
            & .\svc.cmd uninstall *> $null
        }

        try {
            $removeToken = Get-ApiToken "repos/$Repo/actions/runners/remove-token"
            & .\config.cmd remove --token $removeToken
            if ($LASTEXITCODE -ne 0) {
                throw "config.cmd remove returned $LASTEXITCODE"
            }
        }
        catch {
            Write-Warning "GitHub deregistration failed; cleaning local runner state: $($_.Exception.Message)"
            foreach ($name in '.runner', '.credentials', '.credentials_rsaparams', '.service') {
                Remove-Item $name -Force -ErrorAction SilentlyContinue
            }
        }
    }
    finally {
        Pop-Location
    }
}

function Register-Runner {
    Write-Host '[5] Requesting repository registration token...'
    $registrationToken = Get-ApiToken "repos/$Repo/actions/runners/registration-token"

    Write-Host '[6] Registering repository runner as a Windows service...'
    Push-Location $RunnerRoot
    try {
        & .\config.cmd `
            --url $RepoUrl `
            --token $registrationToken `
            --name $RunnerName `
            --labels $Labels `
            --work '_work' `
            --unattended `
            --replace `
            --runasservice

        if ($LASTEXITCODE -ne 0) {
            throw "Runner configuration failed with exit code $LASTEXITCODE"
        }
    }
    finally {
        Pop-Location
    }

    if (-not (Test-Path (Join-Path $RunnerRoot '.runner'))) {
        throw 'Runner registration did not create .runner.'
    }
}

function Ensure-ServiceRunning {
    Push-Location $RunnerRoot
    try {
        if (-not (Test-Path '.\svc.cmd')) {
            throw 'svc.cmd is missing from the official Windows x64 runner package.'
        }

        $service = Get-RunnerService
        if (-not $service) {
            Write-Host '[7] Installing runner Windows service...'
            & .\svc.cmd install
            if ($LASTEXITCODE -ne 0) {
                throw "svc.cmd install failed with exit code $LASTEXITCODE"
            }
        }

        Write-Host '[8] Starting runner Windows service...'
        & .\svc.cmd start
        if ($LASTEXITCODE -ne 0) {
            throw "svc.cmd start failed with exit code $LASTEXITCODE"
        }
    }
    finally {
        Pop-Location
    }

    Start-Sleep -Seconds 2
    $service = Get-RunnerService
    if (-not $service) {
        throw 'Runner Windows service was not found after installation.'
    }

    $status = if ($service.PSObject.Properties.Name -contains 'Status') { [string]$service.Status } else { [string]$service.State }
    if ($status -ne 'Running') {
        throw "Runner Windows service is not Running (status: $status)."
    }
}

Assert-Admin
Assert-Gh
Ensure-RunnerPackage

$existingUrl = Get-ConfiguredUrl
$normalizedExisting = if ($existingUrl) { $existingUrl.TrimEnd('/').ToLowerInvariant() } else { $null }
$normalizedTarget = $RepoUrl.TrimEnd('/').ToLowerInvariant()

if ((Test-Path (Join-Path $RunnerRoot '.runner')) -and ($ForceRepair -or $normalizedExisting -ne $normalizedTarget)) {
    if ($normalizedExisting -ne $normalizedTarget) {
        Write-Warning "Existing runner targets '$existingUrl', expected '$RepoUrl'."
    }
    Remove-ExistingRunner
}

if (-not (Test-Path (Join-Path $RunnerRoot '.runner'))) {
    Register-Runner
}
else {
    Write-Host '[OK] Existing runner registration targets this repository; keeping it.'
}

Ensure-ServiceRunning

Write-Host ''
Write-Host '============================================================'
Write-Host '[OK] AI-Kill-Cancer local GitHub Actions runner is ready.'
Write-Host "Repository : $RepoUrl"
Write-Host "Runner     : $RunnerName"
Write-Host "Labels     : self-hosted, Windows, X64, $Labels"
Write-Host "Root       : $RunnerRoot"
Write-Host '============================================================'
Write-Host 'Queued Local Verification Gate jobs can now be picked up automatically.'
Write-Host ''
Write-Host 'NOTE: The shared V8 organization runner belongs to liuxb99-ai.'
Write-Host 'Until this repository is transferred to liuxb99-ai, this repository-level'
Write-Host 'runner is required. After transfer, use the organization V8 runner instead.'
