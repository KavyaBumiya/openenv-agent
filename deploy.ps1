# HuggingFace Spaces Deployment Script
# Usage: powershell -ExecutionPolicy Bypass -File deploy.ps1

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Customer Support RL Env - HF Deployment" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Get HuggingFace username
$hf_username = Read-Host "Enter your HuggingFace username"
if ([string]::IsNullOrWhiteSpace($hf_username)) {
    Write-Host "Error: Username required" -ForegroundColor Red
    exit 1
}

$space_name = "customer-support-env"
$space_url = "https://huggingface.co/spaces/$hf_username/$space_name"
$clone_url = "https://huggingface.co/spaces/$hf_username/$space_name"

Write-Host ""
Write-Host "STEP 1: Creating temp directory..." -ForegroundColor Yellow
$temp_dir = "$env:TEMP\hf_deploy_$([System.DateTime]::Now.Ticks)"
New-Item -ItemType Directory -Path $temp_dir -Force | Out-Null
cd $temp_dir
Write-Host "✓ Created: $temp_dir" -ForegroundColor Green

Write-Host ""
Write-Host "STEP 2: Cloning HuggingFace Space repository..." -ForegroundColor Yellow
Write-Host "URL: $clone_url"
git clone $clone_url
if ($LASTEXITCODE -ne 0) {
    Write-Host "✗ Git clone failed! Ensure:" -ForegroundColor Red
    Write-Host "  1. Space exists at $space_url" -ForegroundColor Red
    Write-Host "  2. Git is installed and authenticated" -ForegroundColor Red
    exit 1
}
cd $space_name
Write-Host "✓ Repository cloned" -ForegroundColor Green

Write-Host ""
Write-Host "STEP 3: Copying project files..." -ForegroundColor Yellow

# Copy directories
@(
    @{"src" = "d:\Hackathon\customer_support_env"; "dst" = "customer_support_env"},
    @{"src" = "d:\Hackathon\tests"; "dst" = "tests"},
    @{"src" = "d:\Hackathon\evals"; "dst" = "evals"}
) | ForEach-Object {
    $src = $_.src
    $dst = $_.dst
    if (Test-Path $src) {
        Write-Host "  Copying $src..."
        Copy-Item -Path $src -Destination $dst -Recurse -Force
        Write-Host "  ✓ $dst copied"
    }
}

# Copy files
@(
    "Dockerfile",
    "requirements.txt",
    "README.md",
    "main.py",
    "run_official_benchmark.py",
    "pyrightconfig.json",
    "pytest.ini"
) | ForEach-Object {
    $file = $_
    if (Test-Path "d:\Hackathon\$file") {
        Write-Host "  Copying $file..."
        Copy-Item -Path "d:\Hackathon\$file" -Destination . -Force
        Write-Host "  ✓ $file copied"
    }
}

Write-Host "✓ All files copied" -ForegroundColor Green

Write-Host ""
Write-Host "STEP 4: Staging changes for git..." -ForegroundColor Yellow
git add .
Write-Host "✓ Files staged" -ForegroundColor Green

Write-Host ""
Write-Host "STEP 5: Committing changes..." -ForegroundColor Yellow
git commit -m "Initial deployment: Customer Support RL Environment" -q
if ($LASTEXITCODE -ne 0) {
    Write-Host "✗ Git commit failed" -ForegroundColor Red
    exit 1
}
Write-Host "✓ Changes committed" -ForegroundColor Green

Write-Host ""
Write-Host "STEP 6: Pushing to HuggingFace..." -ForegroundColor Yellow
git push origin main
if ($LASTEXITCODE -ne 0) {
    Write-Host "✗ Git push failed!" -ForegroundColor Red
    Write-Host "Check your HF authentication and try: git push origin main" -ForegroundColor Red
    exit 1
}
Write-Host "✓ Pushed successfully!" -ForegroundColor Green

Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "✓ DEPLOYMENT INITIATED!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Cyan
Write-Host "1. HuggingFace is now building your Space (3-5 minutes)" -ForegroundColor White
Write-Host "2. Monitor progress: $space_url" -ForegroundColor White
Write-Host ""
Write-Host "3. Once deployed, add environment variable:" -ForegroundColor Cyan
Write-Host "   - Go to: $space_url/settings" -ForegroundColor White
Write-Host "   - Click 'Repository secrets'" -ForegroundColor White
Write-Host "   - Add: GROQ_API_KEY = gsk_..." -ForegroundColor White
Write-Host "   - Restart the Space" -ForegroundColor White
Write-Host ""
Write-Host "4. Test deployment:" -ForegroundColor Cyan
Write-Host "   https://$hf_username-$space_name.hf.space/docs" -ForegroundColor White
Write-Host ""
Write-Host "Workspace location: $temp_dir" -ForegroundColor Gray
