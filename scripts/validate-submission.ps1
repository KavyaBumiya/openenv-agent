param(
  [Parameter(Mandatory = $true)]
  [string]$PingUrl,

  [Parameter(Mandatory = $false)]
  [string]$RepoDir = "."
)

$ErrorActionPreference = "Stop"

function Write-Pass([string]$message) {
  Write-Host "PASSED -- $message" -ForegroundColor Green
}

function Write-Fail([string]$message) {
  Write-Host "FAILED -- $message" -ForegroundColor Red
}

function Stop-At([string]$step) {
  Write-Host "Validation stopped at $step. Fix the above before continuing." -ForegroundColor Red
  exit 1
}

$PingUrl = $PingUrl.TrimEnd("/")
$RepoPath = Resolve-Path $RepoDir

Write-Host "========================================"
Write-Host "  OpenEnv Submission Validator (Windows)"
Write-Host "========================================"
Write-Host "Repo:     $RepoPath"
Write-Host "Ping URL: $PingUrl"
Write-Host ""

# Step 1: Ping HF Space /reset
Write-Host "Step 1/3: Pinging HF Space ($PingUrl/reset) ..."
try {
  $resp = Invoke-WebRequest -Uri "$PingUrl/reset" -Method POST -ContentType "application/json" -Body "{}" -TimeoutSec 30 -UseBasicParsing
  if ($resp.StatusCode -eq 200) {
    Write-Pass "HF Space is live and responds to /reset"
  }
  else {
    Write-Fail "HF Space /reset returned HTTP $($resp.StatusCode) (expected 200)"
    Stop-At "Step 1"
  }
}
catch {
  $status = $null
  if ($_.Exception.Response) {
    $status = [int]$_.Exception.Response.StatusCode.value__
  }

  if ($status) {
    Write-Fail "HF Space /reset returned HTTP $status (expected 200)"
  }
  else {
    Write-Fail "HF Space not reachable (connection failed or timed out)"
  }
  Stop-At "Step 1"
}

# Step 2: Docker build
Write-Host "Step 2/3: Running docker build ..."
$docker = Get-Command docker -ErrorAction SilentlyContinue
if (-not $docker) {
  Write-Fail "docker command not found"
  Stop-At "Step 2"
}

$dockerfileRoot = Join-Path $RepoPath "Dockerfile"
$dockerfileServer = Join-Path $RepoPath "server/Dockerfile"

if (Test-Path $dockerfileRoot) {
  $dockerContext = $RepoPath
}
elseif (Test-Path $dockerfileServer) {
  $dockerContext = Join-Path $RepoPath "server"
}
else {
  Write-Fail "No Dockerfile found in repo root or server/ directory"
  Stop-At "Step 2"
}

Write-Host "  Found Dockerfile in $dockerContext"

& docker build "$dockerContext"
if ($LASTEXITCODE -ne 0) {
  Write-Fail "Docker build failed"
  Stop-At "Step 2"
}
Write-Pass "Docker build succeeded"

# Step 3: openenv validate
Write-Host "Step 3/3: Running openenv validate ..."
Push-Location $RepoPath
try {
  $openenv = Get-Command openenv -ErrorAction SilentlyContinue
  if (-not $openenv) {
    Write-Fail "openenv command not found"
    Stop-At "Step 3"
  }

  & openenv validate
  if ($LASTEXITCODE -ne 0) {
    Write-Fail "openenv validate failed"
    Stop-At "Step 3"
  }

  Write-Pass "openenv validate passed"
}
finally {
  Pop-Location
}

Write-Host ""
Write-Host "========================================"
Write-Host "  All 3/3 checks passed!" -ForegroundColor Green
Write-Host "  Your submission is ready to submit." -ForegroundColor Green
Write-Host "========================================"
exit 0
