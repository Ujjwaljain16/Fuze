# PowerShell script to package Fuze Web Clipper extension for distribution
# This creates a zip file ready for manual installation

$ErrorActionPreference = "Stop"

# Get script directory
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Split-Path -Parent $ScriptDir
$ExtensionDir = Join-Path $ProjectRoot "BookmarkExtension"
$OutputDir = Join-Path $ProjectRoot "dist"
$ZipFile = Join-Path $OutputDir "fuze-web-clipper.zip"

Write-Host "📦 Packaging Fuze Web Clipper Extension..." -ForegroundColor Cyan

# Check if extension directory exists
if (-not (Test-Path $ExtensionDir)) {
    Write-Host "❌ Extension directory not found: $ExtensionDir" -ForegroundColor Red
    exit 1
}

# Create output directory
if (-not (Test-Path $OutputDir)) {
    New-Item -ItemType Directory -Path $OutputDir -Force | Out-Null
    Write-Host "✅ Created output directory: $OutputDir" -ForegroundColor Green
}

# Remove old zip if exists
if (Test-Path $ZipFile) {
    Remove-Item $ZipFile -Force
    Write-Host "🗑️  Removed old zip file" -ForegroundColor Yellow
}

# Create temporary directory for packaging
$TempDir = Join-Path $env:TEMP "fuze-web-clipper-$(Get-Date -Format 'yyyyMMdd-HHmmss')"
New-Item -ItemType Directory -Path $TempDir -Force | Out-Null

try {
    Write-Host "📋 Copying extension files..." -ForegroundColor Cyan
    
    # Copy all extension files
    Copy-Item -Path "$ExtensionDir\*" -Destination $TempDir -Recurse -Force
    
    # Verify manifest exists
    $ManifestPath = Join-Path $TempDir "MANIFEST.JSON"
    if (-not (Test-Path $ManifestPath)) {
        throw "MANIFEST.JSON not found in extension directory"
    }
    
    Write-Host "✅ Files copied successfully" -ForegroundColor Green
    
    # Create zip file
    Write-Host "📦 Creating zip archive..." -ForegroundColor Cyan
    
    # Use .NET compression (available in PowerShell 5+)
    Add-Type -AssemblyName System.IO.Compression.FileSystem
    [System.IO.Compression.ZipFile]::CreateFromDirectory($TempDir, $ZipFile)
    
    $ZipSize = (Get-Item $ZipFile).Length / 1KB
    Write-Host "✅ Zip file created: $ZipFile ($([math]::Round($ZipSize, 2)) KB)" -ForegroundColor Green
    
    Write-Host ""
    Write-Host "🎉 Extension packaged successfully!" -ForegroundColor Green
    Write-Host "📁 Location: $ZipFile" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "📝 Next steps:" -ForegroundColor Yellow
    Write-Host "   1. Upload the zip file to your hosting/CDN" -ForegroundColor White
    Write-Host "   2. Update ExtensionDownload.jsx with the download URL" -ForegroundColor White
    Write-Host "   3. Users can download and extract the zip" -ForegroundColor White
    Write-Host "   4. Load unpacked extension in Chrome" -ForegroundColor White
    
} catch {
    Write-Host "❌ Error packaging extension: $_" -ForegroundColor Red
    exit 1
} finally {
    # Clean up temp directory
    if (Test-Path $TempDir) {
        Remove-Item $TempDir -Recurse -Force
    }
}

