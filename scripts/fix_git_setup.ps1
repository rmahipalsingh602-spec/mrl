[CmdletBinding()]
param(
    [string]$OriginUrl,
    [string]$CommitMessage = "Launch MRL 3.1 with counted loops, boolean logic, and site refresh",
    [switch]$ForceRemote
)

$ErrorActionPreference = "Stop"

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
Set-Location $repoRoot
$gitRepoRoot = $repoRoot -replace "\\", "/"

function Write-Step {
    param([string]$Message)
    Write-Host ""
    Write-Host "==> $Message" -ForegroundColor Cyan
}

function Get-GitOutput {
    param(
        [Parameter(Mandatory = $true)]
        [string[]]$Arguments
    )

    $result = & git @Arguments 2>$null
    return @($result)
}

Write-Step "Preparing Git for $repoRoot"

$safeDirectories = @(Get-GitOutput -Arguments @("config", "--global", "--get-all", "safe.directory"))
$normalizedSafeDirectories = @($safeDirectories | ForEach-Object { ($_ -replace "\\", "/").Trim() })
if ($normalizedSafeDirectories -notcontains $gitRepoRoot) {
    try {
        & git config --global --add safe.directory $gitRepoRoot *> $null
        if ($LASTEXITCODE -eq 0) {
            Write-Host "Added safe.directory: $gitRepoRoot" -ForegroundColor Green
        } else {
            Write-Host "Could not update global gitconfig automatically. Run this once in your own terminal:" -ForegroundColor Yellow
            Write-Host "git config --global --add safe.directory $gitRepoRoot"
        }
    } catch {
        Write-Host "Could not update global gitconfig automatically. Run this once in your own terminal:" -ForegroundColor Yellow
        Write-Host "git config --global --add safe.directory $gitRepoRoot"
    }
} else {
    Write-Host "safe.directory already present for this repo" -ForegroundColor Green
}

$gitOwner = (Get-Acl (Join-Path $repoRoot ".git")).Owner
$currentUser = "$env:COMPUTERNAME\$env:USERNAME"
Write-Host "Current Windows user : $currentUser"
Write-Host ".git owner           : $gitOwner"
if ($gitOwner -ne $currentUser) {
    Write-Host "Using Git safe.directory workaround because the .git owner is different." -ForegroundColor Yellow
}

$branch = (Get-GitOutput -Arguments @("branch", "--show-current")) | Select-Object -First 1
if (-not $branch) {
    $branch = "main"
}
Write-Host "Active branch        : $branch"

$remoteName = "origin"
$remoteUrl = (& git config --get "remote.$remoteName.url" 2>$null | Select-Object -First 1)
$remoteExists = $LASTEXITCODE -eq 0 -and $remoteUrl

if ($OriginUrl) {
    if ($remoteExists) {
        if ($ForceRemote) {
            & git remote set-url $remoteName $OriginUrl
            $remoteUrl = $OriginUrl
            Write-Host "Updated origin remote: $OriginUrl" -ForegroundColor Green
        } else {
            Write-Host "Origin already exists. Use -ForceRemote to replace it." -ForegroundColor Yellow
        }
    } else {
        & git remote add $remoteName $OriginUrl
        $remoteUrl = $OriginUrl
        $remoteExists = $true
        Write-Host "Added origin remote  : $OriginUrl" -ForegroundColor Green
    }
} elseif ($remoteExists) {
    Write-Host "Origin remote        : $remoteUrl"
} else {
    Write-Host "Origin remote        : not set" -ForegroundColor Yellow
}

$hasCommit = $true
$branchRef = Join-Path $repoRoot ".git\refs\heads\$branch"
if (-not (Test-Path $branchRef)) {
    $hasCommit = $false
}

Write-Step "Next commands"
Write-Host "git add ."
if ($hasCommit) {
    Write-Host "git commit -m `"$CommitMessage`""
} else {
    Write-Host "git commit -m `"$CommitMessage`""
}

if ($remoteExists) {
    Write-Host "git push -u origin $branch"
} else {
    Write-Host "Run this to link GitHub first:" -ForegroundColor Yellow
    Write-Host "powershell -ExecutionPolicy Bypass -File scripts/fix_git_setup.ps1 -OriginUrl https://github.com/YOUR_USERNAME/YOUR_REPO.git"
}

Write-Step "Remote status"
& git remote -v
