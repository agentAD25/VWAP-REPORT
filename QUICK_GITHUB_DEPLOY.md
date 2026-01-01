# Quick GitHub Pages Deployment Guide

## 📍 Project Location

Your website project is located at:
```
D:\alphadrip database\supabase-opti-database\LOCAL DATABASE\out\vwap_reports\website hosting_20260101\
```

## 🚀 Quick Deploy (3 Steps)

### Step 1: Create GitHub Repository

1. Go to [GitHub.com](https://github.com) and sign in
2. Click **+** → **New repository**
3. Repository name: `vwap-reports-gallery` (or your choice)
4. Description: "VWAP Reports Gallery - Static Website"
5. Choose **Public** (required for free GitHub Pages)
6. **Do NOT** check "Initialize with README"
7. Click **Create repository**

### Step 2: Run Deployment Script

Open PowerShell in the project directory:

```powershell
cd "D:\alphadrip database\supabase-opti-database\LOCAL DATABASE\out\vwap_reports\website hosting_20260101"
.\deploy.ps1
```

The script will:
- ✅ Sync reports and generate manifest
- ✅ Initialize git (if needed)
- ✅ Commit all files
- ✅ Set up GitHub remote
- ✅ Push to GitHub

**When prompted:**
- Enter your GitHub username
- Enter repository name (or press Enter for default: `vwap-reports-gallery`)
- Enter commit message (or press Enter for default)

### Step 3: Enable GitHub Pages

1. Go to your repository on GitHub
2. Click **Settings** (top menu)
3. Scroll to **Pages** (left sidebar)
4. Under **Source**:
   - **Branch**: `main`
   - **Folder**: `/docs`
5. Click **Save**

## 🌐 Your Site URL

After enabling Pages, your site will be available at:
```
https://YOUR_USERNAME.github.io/vwap-reports-gallery/
```

**Example:** If your username is `AlphaDrip`, the URL would be:
```
https://alphadrip.github.io/vwap-reports-gallery/
```

⏱️ **Note:** It may take 1-2 minutes for the site to be available after enabling Pages.

---

## 📝 Manual Deploy (Alternative)

If you prefer to do it manually:

### 1. Navigate to Project
```powershell
cd "D:\alphadrip database\supabase-opti-database\LOCAL DATABASE\out\vwap_reports\website hosting_20260101"
```

### 2. Sync Reports & Generate Manifest
```powershell
py tools\sync_reports.py
py tools\generate_manifest.py
```

### 3. Initialize Git
```powershell
git init
git add .
git commit -m "Initial commit: VWAP Reports Gallery"
```

### 4. Add GitHub Remote
```powershell
git remote add origin https://github.com/YOUR_USERNAME/vwap-reports-gallery.git
git branch -M main
git push -u origin main
```

**Replace `YOUR_USERNAME` with your actual GitHub username.**

### 5. Enable GitHub Pages
- Go to repository → **Settings** → **Pages**
- **Branch**: `main`, **Folder**: `/docs`
- Click **Save**

---

## 🔄 Updating Reports

When you have new reports to add:

```powershell
cd "D:\alphadrip database\supabase-opti-database\LOCAL DATABASE\out\vwap_reports\website hosting_20260101"

# Sync new reports
py tools\sync_reports.py

# Regenerate manifest
py tools\generate_manifest.py

# Commit and push
git add site/docs/
git commit -m "Update VWAP reports"
git push
```

GitHub Pages will automatically update within 1-2 minutes.

---

## 📚 Additional Resources

- **Detailed Guide:** See [DEPLOY_TO_GITHUB.md](DEPLOY_TO_GITHUB.md)
- **Project README:** See [README.md](README.md)
- **Deployment Script:** See [deploy.ps1](deploy.ps1)

---

## ⚠️ Important Notes

1. **Public Repository Required:** Free GitHub Pages requires a public repository
2. **Folder Structure:** GitHub Pages serves from `site/docs/` folder
3. **File Size:** Large report files may take time to upload
4. **Security:** Everything in the repository will be publicly accessible

---

## 🐛 Troubleshooting

### Site Not Loading
- Check repository is **Public**
- Verify Pages is enabled: **Settings** → **Pages**
- Wait 1-2 minutes for deployment

### 404 Errors
- Ensure `manifest.json` exists in `site/docs/`
- Check file paths are relative (start with `reports/`)

### Push Errors
- Verify repository exists on GitHub
- Check you're authenticated (GitHub CLI or SSH keys)
- Ensure you have push access to the repository

---

## 📂 Repository Structure

After deployment, your GitHub repository will have:

```
vwap-reports-gallery/
├── .gitignore
├── README.md
├── DEPLOY_TO_GITHUB.md
├── QUICK_GITHUB_DEPLOY.md (this file)
├── deploy.ps1
├── tools/
│   ├── sync_reports.py
│   ├── generate_manifest.py
│   └── ...
└── site/
    └── docs/              ← GitHub Pages serves from here
        ├── index.html
        ├── app.js
        ├── styles.css
        ├── manifest.json
        └── reports/
            └── ...
```

---

**Ready to deploy?** Run `.\deploy.ps1` and follow the prompts!
