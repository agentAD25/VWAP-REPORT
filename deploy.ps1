# deploy.ps1
# PowerShell script to help deploy VWAP Reports Gallery to GitHub Pages

param(
    [string]$GitHubUsername = "",
    [string]$RepositoryName = "vwap-reports-gallery"
)

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "VWAP Reports Gallery - GitHub Deploy" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Check if git is installed
try {
    $gitVersion = git --version
    Write-Host "✓ Git found: $gitVersion" -ForegroundColor Green
} catch {
    Write-Host "✗ Git is not installed or not in PATH" -ForegroundColor Red
    Write-Host "Please install Git from https://git-scm.com/" -ForegroundColor Yellow
    exit 1
}

# Check if we're in the right directory
if (-not (Test-Path "site\docs\index.html")) {
    Write-Host "✗ Error: index.html not found in site\docs\" -ForegroundColor Red
    Write-Host "Please run this script from the 'website hosting' directory" -ForegroundColor Yellow
    exit 1
}

Write-Host "✓ Found website files" -ForegroundColor Green
Write-Host ""

# Step 1: Sync reports
Write-Host "Step 1: Syncing reports from source..." -ForegroundColor Yellow
try {
    py tools\sync_reports.py
    if ($LASTEXITCODE -ne 0) {
        Write-Host "✗ Error syncing reports" -ForegroundColor Red
        exit 1
    }
    Write-Host "✓ Reports synced" -ForegroundColor Green
} catch {
    Write-Host "✗ Error running sync script" -ForegroundColor Red
    Write-Host "Make sure Python is installed and in PATH" -ForegroundColor Yellow
    exit 1
}

Write-Host ""

# Step 1b: Apply visual updates (after sync to preserve our changes)
Write-Host "Step 1b: Applying visual updates..." -ForegroundColor Yellow
try {
    # Update hold_fail_rates styling
    py tools\update_hold_fail_rates_visual.py
    if ($LASTEXITCODE -ne 0) {
        Write-Host "⚠ Warning: Error updating hold_fail_rates visual" -ForegroundColor Yellow
    } else {
        Write-Host "  ✓ Hold fail rates styling updated" -ForegroundColor Green
    }
    
    py tools\apply_visual_updates_to_webpage.py
    if ($LASTEXITCODE -ne 0) {
        Write-Host "⚠ Warning: Error applying visual updates" -ForegroundColor Yellow
    } else {
        Write-Host "  ✓ Visual updates applied to webpage" -ForegroundColor Green
    }
    
    # Remove Downloads sections
    py tools\remove_downloads_sections.py
    if ($LASTEXITCODE -ne 0) {
        Write-Host "⚠ Warning: Error removing Downloads sections" -ForegroundColor Yellow
    } else {
        Write-Host "  ✓ Downloads sections removed" -ForegroundColor Green
    }
    
    Write-Host "✓ Visual updates applied" -ForegroundColor Green
} catch {
    Write-Host "⚠ Warning: Error applying visual updates" -ForegroundColor Yellow
    Write-Host "Continuing with deployment..." -ForegroundColor Yellow
}

Write-Host ""

# Step 1c: Generate manifest
Write-Host "Step 1c: Generating manifest..." -ForegroundColor Yellow
try {
    py tools\generate_manifest.py
    if ($LASTEXITCODE -ne 0) {
        Write-Host "✗ Error generating manifest" -ForegroundColor Red
        exit 1
    }
    Write-Host "✓ Manifest generated" -ForegroundColor Green
} catch {
    Write-Host "✗ Error generating manifest" -ForegroundColor Red
    Write-Host "Make sure Python is installed and in PATH" -ForegroundColor Yellow
    exit 1
}

Write-Host ""

# Step 2: Initialize git if needed
if (-not (Test-Path ".git")) {
    Write-Host "Step 2: Initializing git repository..." -ForegroundColor Yellow
    git init
    Write-Host "✓ Git repository initialized" -ForegroundColor Green
} else {
    Write-Host "Step 2: Git repository already exists" -ForegroundColor Green
}

Write-Host ""

# Step 3: Add files
Write-Host "Step 3: Staging files..." -ForegroundColor Yellow
git add .
Write-Host "✓ Files staged" -ForegroundColor Green
Write-Host ""

# Step 4: Check for uncommitted changes
$status = git status --porcelain
if ($status) {
    Write-Host "Step 4: Committing changes..." -ForegroundColor Yellow
    
    if (-not $GitHubUsername) {
        $GitHubUsername = Read-Host "Enter your GitHub username"
    }
    
    $commitMessage = Read-Host "Enter commit message (or press Enter for default)"
    if ([string]::IsNullOrWhiteSpace($commitMessage)) {
        $commitMessage = "Update VWAP reports"
    }
    
    git commit -m $commitMessage
    Write-Host "✓ Changes committed" -ForegroundColor Green
} else {
    Write-Host "Step 4: No changes to commit" -ForegroundColor Green
}

Write-Host ""

# Step 5: Set up remote and push
Write-Host "Step 5: Setting up remote and pushing..." -ForegroundColor Yellow

# Check if remote exists
$remote = git remote get-url origin 2>$null
if ($LASTEXITCODE -ne 0) {
    # No remote set up
    if (-not $GitHubUsername) {
        $GitHubUsername = Read-Host "Enter your GitHub username"
    }
    
    $repoName = Read-Host "Enter repository name (or press Enter for '$RepositoryName')"
    if ([string]::IsNullOrWhiteSpace($repoName)) {
        $repoName = $RepositoryName
    }
    
    $remoteUrl = "https://github.com/$GitHubUsername/$repoName.git"
    Write-Host "Adding remote: $remoteUrl" -ForegroundColor Cyan
    git remote add origin $remoteUrl
    
    # Set main branch
    git branch -M main 2>$null
}

# Push to GitHub
Write-Host "Pushing to GitHub..." -ForegroundColor Cyan
git push -u origin main

if ($LASTEXITCODE -eq 0) {
    Write-Host "✓ Successfully pushed to GitHub!" -ForegroundColor Green
    Write-Host ""
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host "Next Steps:" -ForegroundColor Yellow
    Write-Host "1. Go to your repository on GitHub" -ForegroundColor White
    Write-Host "2. Settings → Pages" -ForegroundColor White
    Write-Host "3. Source: Branch 'main', Folder '/docs'" -ForegroundColor White
    Write-Host "4. Click Save" -ForegroundColor White
    Write-Host ""
    $remote = git remote get-url origin
    if ($remote) {
        $repoUrl = $remote -replace '\.git$', ''
        Write-Host "Your site will be available at:" -ForegroundColor Cyan
        $repoName = ($repoUrl -split '/')[-1]
        $username = ($repoUrl -split '/')[-2]
        Write-Host "https://$username.github.io/$repoName/" -ForegroundColor Green
    }
} else {
    Write-Host "✗ Error pushing to GitHub" -ForegroundColor Red
    Write-Host "Make sure:" -ForegroundColor Yellow
    Write-Host "  - Repository exists on GitHub" -ForegroundColor White
    Write-Host "  - You have push access" -ForegroundColor White
    Write-Host "  - You're authenticated (use GitHub CLI or SSH keys)" -ForegroundColor White
}

Write-Host "========================================" -ForegroundColor Cyan
