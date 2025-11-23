# PowerShell script to automatically sync backend files to Hugging Face Space
# Usage: .\scripts\sync_to_hf_space.ps1

$ErrorActionPreference = "Stop"

# Configuration
$ProjectRoot = Split-Path -Parent $PSScriptRoot
$HFSpacePath = "$env:USERPROFILE\OneDrive\Desktop\fuze-backend"

# Check if HF Space exists
if (-not (Test-Path $HFSpacePath)) {
    Write-Host "❌ Hugging Face Space not found at: $HFSpacePath" -ForegroundColor Red
    Write-Host "📝 Please clone it first:" -ForegroundColor Yellow
    Write-Host "   git clone https://huggingface.co/spaces/Ujjwaljain16/fuze-backend $HFSpacePath" -ForegroundColor Cyan
    exit 1
}

Write-Host "🔄 Syncing backend files to Hugging Face Space..." -ForegroundColor Cyan
Write-Host "   Source: $ProjectRoot" -ForegroundColor Gray
Write-Host "   Target: $HFSpacePath" -ForegroundColor Gray
Write-Host ""

# Files to sync
$FilesToSync = @(
    @{Source = "backend\init_db.py"; Target = "backend\init_db.py"},
    @{Source = "backend\run_production.py"; Target = "backend\run_production.py"},
    @{Source = "backend\services\task_queue.py"; Target = "backend\services\task_queue.py"},
    @{Source = "backend\utils\database_security_migration.py"; Target = "backend\utils\database_security_migration.py"},
    @{Source = "requirements.txt"; Target = "requirements.txt"},
    @{Source = "Dockerfile"; Target = "Dockerfile"},
    @{Source = "app.py"; Target = "app.py"},
    @{Source = "wsgi.py"; Target = "wsgi.py"},
    @{Source = "start.sh"; Target = "start.sh"}
)

# Sync files
$SyncedCount = 0
foreach ($file in $FilesToSync) {
    $sourcePath = Join-Path $ProjectRoot $file.Source
    $targetPath = Join-Path $HFSpacePath $file.Target
    
    if (Test-Path $sourcePath) {
        # Create target directory if needed
        $targetDir = Split-Path -Parent $targetPath
        if (-not (Test-Path $targetDir)) {
            New-Item -ItemType Directory -Path $targetDir -Force | Out-Null
        }
        
        Copy-Item $sourcePath $targetPath -Force
        Write-Host "✅ Synced: $($file.Source)" -ForegroundColor Green
        $SyncedCount++
    } else {
        Write-Host "⚠️  Not found: $($file.Source)" -ForegroundColor Yellow
    }
}

Write-Host ""
Write-Host "📦 Synced $SyncedCount files" -ForegroundColor Cyan
Write-Host ""

# Ask if user wants to commit and push
$commit = Read-Host "Commit and push to Hugging Face? (y/n)"
if ($commit -eq 'y' -or $commit -eq 'Y') {
    Push-Location $HFSpacePath
    
    try {
        Write-Host "📝 Committing changes..." -ForegroundColor Cyan
        git add .
        
        $commitMessage = Read-Host "Enter commit message (or press Enter for default)"
        if ([string]::IsNullOrWhiteSpace($commitMessage)) {
            $commitMessage = "chore: sync backend files from main repo"
        }
        
        git commit -m $commitMessage
        
        Write-Host "🚀 Pushing to Hugging Face..." -ForegroundColor Cyan
        git push
        
        Write-Host ""
        Write-Host "✅ Successfully synced and pushed to Hugging Face Space!" -ForegroundColor Green
    } catch {
        Write-Host "❌ Error: $_" -ForegroundColor Red
    } finally {
        Pop-Location
    }
} else {
    Write-Host "📝 Files synced. Run these commands in $HFSpacePath to commit:" -ForegroundColor Yellow
    Write-Host "   git add ." -ForegroundColor Cyan
    Write-Host "   git commit -m 'chore: sync backend files'" -ForegroundColor Cyan
    Write-Host "   git push" -ForegroundColor Cyan
}

