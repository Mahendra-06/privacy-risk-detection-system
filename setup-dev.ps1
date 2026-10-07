$ErrorActionPreference = "Stop"

Write-Host "== Privacy Risk Detection System - Local Setup ==" -ForegroundColor Cyan

if (-not (Get-Command node -ErrorAction SilentlyContinue)) {
    throw "Node.js is required. Install Node.js 20+ and run this script again."
}

if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    throw "Python is required. Install Python 3.11+ and run this script again."
}

Write-Host "Installing Node.js dependencies..." -ForegroundColor Yellow
npm install
npm --prefix apps/api install
npm --prefix apps/web install

Write-Host "Installing Python ML dependencies..." -ForegroundColor Yellow
python -m pip install -r services/ml/requirements.txt

Write-Host "`nSetup complete." -ForegroundColor Green
Write-Host "Make sure MongoDB is running locally on port 27017."
Write-Host "For OCR, install Tesseract OCR and ensure tesseract.exe is on PATH."
Write-Host "Then run: npm run dev" -ForegroundColor Cyan
