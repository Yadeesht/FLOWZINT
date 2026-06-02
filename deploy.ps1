param (
    [Parameter(Mandatory=$true)]
    [string]$IPAddress,
    
    [Parameter(Mandatory=$true)]
    [string]$PemPath,
    
    [string]$User = "azureuser"
)

$ErrorActionPreference = "Stop"

Write-Host "📦 Creating deployment archive..." -ForegroundColor Cyan
$archiveName = "flowzint-deploy.zip"
if (Test-Path $archiveName) { Remove-Item $archiveName }

# Compress necessary folders, excluding dependencies, virtual environments, build artifacts, and logs
Compress-Archive -Path backend, frontend, whatsapp-bot, ecosystem.config.js, nginx.conf -DestinationPath $archiveName

Write-Host "🚀 Uploading archive to VM at $IPAddress via SCP..." -ForegroundColor Cyan
scp -i $PemPath $archiveName "${User}@${IPAddress}:/home/${User}/"

Write-Host "🧹 Cleaning up local archive..." -ForegroundColor Cyan
Remove-Item $archiveName

Write-Host "✅ Upload completed successfully!" -ForegroundColor Green
Write-Host "Now SSH into your VM using:" -ForegroundColor Yellow
Write-Host "ssh -i $PemPath ${User}@${IPAddress}" -ForegroundColor Yellow
