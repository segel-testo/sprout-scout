# Deploy the production build to Codeberg Pages.
#
# See README "Deployment → Frontend → Codeberg Pages → One-time setup"
# for the full first-time checklist (Codeberg account, SSH key, .domains,
# DNS records, CODEBERG_REMOTE env var).
#
# Usage:
#   cd frontend
#   .\scripts\deploy-codeberg.ps1
#   .\scripts\deploy-codeberg.ps1 -Remote git@codeberg.org:your-user/sprout-scout.git

param(
    [string]$Remote = $env:CODEBERG_REMOTE,
    [string]$Branch = "pages"
)

$ErrorActionPreference = "Stop"

if (-not $Remote) {
    Write-Error "No remote provided. Set `$env:CODEBERG_REMOTE or pass -Remote git@codeberg.org:user/repo.git"
    exit 1
}

$frontendDir = Split-Path -Parent $PSScriptRoot
$buildDir = Join-Path $frontendDir "dist\frontend\browser"

Write-Host "Building production bundle..." -ForegroundColor Cyan
Push-Location $frontendDir
try {
    & npx ng build --configuration production
    if ($LASTEXITCODE -ne 0) { throw "ng build failed" }
} finally {
    Pop-Location
}

if (-not (Test-Path $buildDir)) {
    Write-Error "Expected build output at $buildDir but it does not exist."
    exit 1
}

Write-Host "Pushing $buildDir to $Remote ($Branch branch)..." -ForegroundColor Cyan
Push-Location $buildDir
try {
    if (Test-Path ".git") {
        Remove-Item -Recurse -Force ".git"
    }
    & git init -b $Branch | Out-Null
    & git add .
    & git -c user.email=deploy@local -c user.name=deploy commit -m "deploy" | Out-Null
    & git remote add origin $Remote
    & git push -f origin $Branch
    if ($LASTEXITCODE -ne 0) { throw "git push failed" }
} finally {
    Pop-Location
}

Write-Host "Deployed." -ForegroundColor Green
