# deploy.ps1
# PowerShell script to help deploy VWAP Reports Gallery to GitHub Pages
#
# -Contract: "all" (default) stages everything. Use one contract (e.g. "MGCQ25") to stage
#   only that contract's report folders + manifest + tools + deploy.ps1 for smaller pushes.
#   Helps avoid timeouts or failures on large git add/push.

param(
    [string]$GitHubUsername = "",
    [string]$RepositoryName = "vwap-reports-gallery",
    [string]$Contract = "all",
    [switch]$NoPush,
    [string]$CommitMessage = ""
)

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "VWAP Reports Gallery - GitHub Deploy" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Check if git is installed
try {
    $gitVersion = git --version
    Write-Host "[ok] Git found: $gitVersion" -ForegroundColor Green
} catch {
    Write-Host "[x] Git is not installed or not in PATH" -ForegroundColor Red
    Write-Host "Please install Git from https://git-scm.com/" -ForegroundColor Yellow
    exit 1
}

# Check if we're in the right directory
if (-not (Test-Path "site\docs\index.html")) {
    Write-Host "[x] Error: index.html not found in site\docs\" -ForegroundColor Red
    Write-Host "Please run this script from the 'website hosting' directory" -ForegroundColor Yellow
    exit 1
}

Write-Host "[ok] Found website files" -ForegroundColor Green
Write-Host ""

# Step 1: Sync reports
Write-Host "Step 1: Syncing reports from source..." -ForegroundColor Yellow
try {
    py tools\sync_reports.py
    if ($LASTEXITCODE -ne 0) {
        Write-Host "[x] Error syncing reports" -ForegroundColor Red
        exit 1
    }
    Write-Host "[ok] Reports synced" -ForegroundColor Green
} catch {
    Write-Host "[x] Error running sync script" -ForegroundColor Red
    Write-Host "Make sure Python is installed and in PATH" -ForegroundColor Yellow
    exit 1
}

# Step 1a2: MGCQ25 sync to match MGCZ24 (hold_fail, heatmap, mfe_mae, regime; remove cross-contamination in docs+site)
Write-Host "Step 1a2: MGCQ25 sync to match MGCZ24..." -ForegroundColor Yellow
try {
    py tools\sync_mgcq25_to_match_mgcz24.py
    if ($LASTEXITCODE -eq 0) { Write-Host "  [ok] MGCQ25 sync done" -ForegroundColor Green }
} catch { Write-Host "  [!] MGCQ25 sync skipped" -ForegroundColor Yellow }

Write-Host ""

# Step 1b: Apply visual updates (after sync to preserve our changes)
Write-Host "Step 1b: Applying visual updates..." -ForegroundColor Yellow
try {
    # Update hold_fail_rates styling
    py tools\update_hold_fail_rates_visual.py
    if ($LASTEXITCODE -ne 0) {
        Write-Host "[!] Warning: Error updating hold_fail_rates visual" -ForegroundColor Yellow
    } else {
        Write-Host "  [ok] Hold fail rates styling updated" -ForegroundColor Green
    }
    
    py tools\apply_visual_updates_to_webpage.py
    if ($LASTEXITCODE -ne 0) {
        Write-Host "[!] Warning: Error applying visual updates" -ForegroundColor Yellow
    } else {
        Write-Host "  [ok] Visual updates applied to webpage" -ForegroundColor Green
    }
    
    # Remove Downloads sections
    py tools\remove_downloads_sections.py
    if ($LASTEXITCODE -ne 0) {
        Write-Host "[!] Warning: Error removing Downloads sections" -ForegroundColor Yellow
    } else {
        Write-Host "  [ok] Downloads sections removed" -ForegroundColor Green
    }
    
    Write-Host "[ok] Visual updates applied" -ForegroundColor Green
} catch {
    Write-Host "[!] Warning: Error applying visual updates" -ForegroundColor Yellow
    Write-Host "Continuing with deployment..." -ForegroundColor Yellow
}

# Step 1b2: MGCZ24 root-from-dashboards (fix 0/NaN in daily_max_extensions, extension_tail_metrics, oos_by_month)
Write-Host "Step 1b2: MGCZ24 root-from-dashboards fix..." -ForegroundColor Yellow
try {
    py tools\fix_mgcz24_root_from_dashboards.py
    if ($LASTEXITCODE -eq 0) { Write-Host "  [ok] MGCZ24 root fix applied" -ForegroundColor Green }
} catch { Write-Host "  [!] MGCZ24 fix skipped" -ForegroundColor Yellow }

# Step 1b3: Hold fail rates NQ-format (all contracts/timeframes: CSS, subtitle, insights-table, chart 400px, remove Downloads, title casing)
Write-Host "Step 1b3: Hold fail rates NQ-format (all contracts/timeframes)..." -ForegroundColor Yellow
try {
    py tools\apply_hold_fail_nq_format_all.py
    if ($LASTEXITCODE -eq 0) { Write-Host "  [ok] Hold fail rates NQ-format applied" -ForegroundColor Green }
} catch { Write-Host "  [!] Hold fail rates NQ-format skipped" -ForegroundColor Yellow }

Write-Host ""

# Step 1c: Generate manifest
Write-Host "Step 1c: Generating manifest..." -ForegroundColor Yellow
try {
    py tools\generate_manifest.py
    if ($LASTEXITCODE -ne 0) {
        Write-Host "[x] Error generating manifest" -ForegroundColor Red
        exit 1
    }
    Write-Host "[ok] Manifest generated" -ForegroundColor Green
} catch {
    Write-Host "[x] Error generating manifest" -ForegroundColor Red
    Write-Host "Make sure Python is installed and in PATH" -ForegroundColor Yellow
    exit 1
}

Write-Host ""

# Step 2: Initialize git if needed
if (-not (Test-Path ".git")) {
    Write-Host "Step 2: Initializing git repository..." -ForegroundColor Yellow
    git init
    Write-Host "[ok] Git repository initialized" -ForegroundColor Green
} else {
    Write-Host "Step 2: Git repository already exists" -ForegroundColor Green
}

Write-Host ""

# Step 3: Add files (chunk by contract if -Contract is set to reduce push size)
Write-Host "Step 3: Staging files..." -ForegroundColor Yellow
if ($Contract -and $Contract -ne "all") {
    if (Test-Path "docs/reports") {
        Get-ChildItem -Path "docs/reports" -Directory -Filter "$($Contract)_*" -ErrorAction SilentlyContinue | ForEach-Object { git add "docs/reports/$($_.Name)" }
    }
    if (Test-Path "site/docs/reports") {
        Get-ChildItem -Path "site/docs/reports" -Directory -Filter "$($Contract)_*" -ErrorAction SilentlyContinue | ForEach-Object { git add "site/docs/reports/$($_.Name)" }
    }
    @("docs/manifest.json", "tools", "deploy.ps1", ".gitignore", "DEPLOY_ONE_CONTRACT.md") | Where-Object { Test-Path $_ } | ForEach-Object { git add $_ }
    Write-Host "  Staged contract: $Contract (+ manifest, tools, deploy.ps1)" -ForegroundColor Cyan
} else {
    git add .
}
Write-Host "[ok] Files staged" -ForegroundColor Green
Write-Host ""

# Step 4: Check for uncommitted changes
$status = git status --porcelain
if ($status) {
    Write-Host "Step 4: Committing changes..." -ForegroundColor Yellow
    
    if (-not $GitHubUsername) {
        $GitHubUsername = Read-Host "Enter your GitHub username"
    }
    
    if ([string]::IsNullOrWhiteSpace($CommitMessage)) {
        $commitMessage = Read-Host "Enter commit message (or press Enter for default)"
    } else {
        $commitMessage = $CommitMessage
    }
    if ([string]::IsNullOrWhiteSpace($commitMessage)) {
        $commitMessage = "Update VWAP reports"
    }
    
    git commit -m $commitMessage
    Write-Host "[ok] Changes committed" -ForegroundColor Green
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

# Push to GitHub (skip if -NoPush: run everything then push manually)
if ($NoPush) {
    Write-Host "Skipping push (-NoPush). Run: git push -u origin main" -ForegroundColor Yellow
} else {
    Write-Host "Pushing to GitHub..." -ForegroundColor Cyan
    git push -u origin main
}

if ($NoPush -or $LASTEXITCODE -eq 0) {
    if ($NoPush) { Write-Host "[ok] Staging and commit done. Run: git push -u origin main" -ForegroundColor Green }
    else { Write-Host "[ok] Successfully pushed to GitHub!" -ForegroundColor Green }
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
    Write-Host "[x] Error pushing to GitHub" -ForegroundColor Red
    Write-Host "Make sure:" -ForegroundColor Yellow
    Write-Host "  - Repository exists on GitHub" -ForegroundColor White
    Write-Host "  - You have push access" -ForegroundColor White
    Write-Host "  - You're authenticated (use GitHub CLI or SSH keys)" -ForegroundColor White
    Write-Host ""
    Write-Host "If the push is too large or times out, try one contract:" -ForegroundColor Yellow
    Write-Host "  .\deploy.ps1 -Contract MGCQ25" -ForegroundColor Cyan
    Write-Host "  .\deploy.ps1 -Contract MGCZ24" -ForegroundColor Cyan
    Write-Host "  (Then run again for other contracts, or -Contract all for the rest)" -ForegroundColor Gray
}

Write-Host "========================================" -ForegroundColor Cyan
