# Pre-Deployment Checklist
# Run this before deploy.ps1

Write-Host "HuggingFace Deployment - Pre-Check" -ForegroundColor Cyan
Write-Host "=================================" -ForegroundColor Cyan
Write-Host ""

# Check Git
Write-Host "Checking Git installation..." -ForegroundColor Yellow
try {
    $git_version = git --version 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✓ Git: $git_version" -ForegroundColor Green
    }
} catch {
    Write-Host "✗ Git not found! Install from https://git-scm.com" -ForegroundColor Red
    exit 1
}

# Check GitHub CLI or Git credentials
Write-Host ""
Write-Host "Checking HuggingFace authentication..." -ForegroundColor Yellow
$cred_config = git config --global credential.helper 2>&1
if ($cred_config) {
    Write-Host "✓ Credential helper configured" -ForegroundColor Green
} else {
    Write-Host "Create HF token at: https://huggingface.co/settings/tokens" -ForegroundColor Yellow
    Write-Host "Then run: git config --global credential.helper wincred" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "Prerequisites:" -ForegroundColor Cyan
Write-Host "1. HuggingFace account: https://huggingface.co/join" -ForegroundColor White
Write-Host "2. Space created with Docker SDK (free CPU tier)" -ForegroundColor White
Write-Host "3. Groq API key: https://console.groq.com" -ForegroundColor White
Write-Host ""
Write-Host "Ready? Run: powershell -ExecutionPolicy Bypass -File deploy.ps1" -ForegroundColor Green
