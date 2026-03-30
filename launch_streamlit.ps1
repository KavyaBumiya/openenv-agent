# Streamlit launcher script for Windows PowerShell
# Usage: .\launch_streamlit.ps1
# Usage (with debug): .\launch_streamlit.ps1 -Debug

param(
    [switch]$Debug = $false,
    [switch]$Install = $false
)

Write-Host "🎫 Customer Support RL Environment - Streamlit UI Launcher" -ForegroundColor Cyan
Write-Host "================================================================" -ForegroundColor Cyan

# Check if in correct directory
$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $projectRoot
Write-Host "📍 Project root: $projectRoot" -ForegroundColor Green

# Check Python installation
try {
    $pythonVersion = python --version 2>&1
    Write-Host "✓ Python found: $pythonVersion" -ForegroundColor Green
}
catch {
    Write-Host "❌ Python not found in PATH!" -ForegroundColor Red
    Write-Host "Please install Python 3.8+ and add it to your PATH."
    exit 1
}

# Check/install requirements
if ($Install) {
    Write-Host "`n📦 Installing requirements..." -ForegroundColor Yellow
    pip install -r requirements.txt
    if ($LASTEXITCODE -ne 0) {
        Write-Host "❌ Failed to install requirements!" -ForegroundColor Red
        exit 1
    }
    Write-Host "✓ Requirements installed" -ForegroundColor Green
}

# Check if Streamlit is installed
try {
    python -m streamlit --version > $null 2>&1
    $streamlitCheck = $true
}
catch {
    $streamlitCheck = $false
}

if (-not $streamlitCheck) {
    Write-Host "❌ Streamlit is not installed!" -ForegroundColor Red
    Write-Host "Install with: pip install -r requirements.txt" -ForegroundColor Yellow
    Write-Host "Or run: .\launch_streamlit.ps1 -Install" -ForegroundColor Yellow
    exit 1
}

Write-Host "✓ Streamlit is installed" -ForegroundColor Green

# Build command
$cmd = @("streamlit", "run", "streamlit_app.py")

if ($Debug) {
    Write-Host "`n🔧 Running in development mode..." -ForegroundColor Yellow
    $cmd += "--logger.level=debug"
    $cmd += "--client.toolbarMode=developer"
}

Write-Host "`n🚀 Starting Streamlit UI..." -ForegroundColor Cyan
Write-Host "🌐 App will be available at: http://localhost:8501" -ForegroundColor Cyan
Write-Host "Press Ctrl+C to stop`n" -ForegroundColor Yellow

# Run Streamlit
python -m @cmd
