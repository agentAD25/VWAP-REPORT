# Deployment Plan - VWAP Reports Gallery

## ⚠️ Important Note

The `sync_reports.py` script copies files from the source directory, which will **overwrite** our visual updates (centered charts, dashboard styling, removed Downloads sections). 

**Solution:** We must run our visual update scripts AFTER syncing to preserve our changes.

---

## 📋 Step-by-Step Deployment Plan

### ✅ Step 1: Verify Current State
**Status:** IN PROGRESS

Verify that our latest changes are currently in the deployment folder:
- [x] Check hold_fail_rates.html files have centered charts
- [x] Check Downloads sections are removed
- [x] Verify dashboard styling is applied

**Action:** Verifying files now...

---

### Step 2: Sync Reports from Source
**Status:** PENDING

Sync latest reports from source directory:
```powershell
cd "D:\alphadrip database\supabase-opti-database\LOCAL DATABASE\out\vwap_reports\website hosting_20260101"
py tools\sync_reports.py
```

**Note:** This will overwrite our visual updates, but we'll restore them in Step 3.

---

### Step 3: Apply Visual Updates
**Status:** PENDING

Restore our visual updates after sync:
```powershell
# Update hold_fail_rates styling
py tools\update_hold_fail_rates_visual.py
py tools\apply_visual_updates_to_webpage.py

# Remove Downloads sections
py tools\remove_downloads_sections.py
```

This ensures our latest changes are included in deployment.

---

### Step 4: Generate Manifest
**Status:** PENDING

Generate the manifest.json file:
```powershell
py tools\generate_manifest.py
```

---

### Step 5: Test Locally
**Status:** PENDING

Test the website locally before deploying:
```powershell
cd site\docs
py -m http.server 8080
```

Then visit: `http://localhost:8080`

**Verify:**
- [ ] Main page loads
- [ ] Reports are accessible
- [ ] Charts are centered
- [ ] Downloads sections are removed
- [ ] Dashboard styling is applied

---

### Step 6: Deploy to GitHub
**Status:** PENDING

Run the deployment script:
```powershell
cd "D:\alphadrip database\supabase-opti-database\LOCAL DATABASE\out\vwap_reports\website hosting_20260101"
.\deploy.ps1
```

**Note:** We may need to modify deploy.ps1 to include Step 3 (visual updates) automatically.

---

### Step 7: Enable GitHub Pages
**Status:** PENDING

1. Go to your GitHub repository
2. Settings → Pages
3. Branch: `main`, Folder: `/docs`
4. Click Save

---

### Step 8: Verify Deployment
**Status:** PENDING

Visit your site URL and verify everything works:
```
https://YOUR_USERNAME.github.io/vwap-reports-gallery/
```

---

## 🔧 Recommended: Update deploy.ps1

To automate the visual updates, we should modify `deploy.ps1` to include Step 3. This ensures our changes are always included in deployments.

---

## 📊 Current Status Summary

**Files with Latest Changes:**
- ✅ hold_fail_rates.html (all timeframes, all contracts) - Dashboard styling + centered charts
- ✅ All HTML reports - Downloads sections removed

**Ready for Deployment:** After completing Steps 2-3
