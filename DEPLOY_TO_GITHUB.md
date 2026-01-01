# Deploy VWAP Reports to GitHub Pages

Step-by-step guide to deploy your VWAP Reports Gallery to GitHub Pages.

## Prerequisites

- GitHub account
- Git installed on your computer
- Python installed (for syncing reports)

## Quick Start

### Option 1: Deploy from `site/docs` folder (Recommended)

This is the simplest approach - GitHub Pages will serve directly from the `/docs` folder.

#### Step 1: Create GitHub Repository

1. Go to [GitHub](https://github.com) and sign in
2. Click the **+** icon → **New repository**
3. Repository name: `vwap-reports-gallery` (or your preferred name)
4. Description: "VWAP Reports Gallery - Static Website"
5. Choose **Public** (required for free GitHub Pages)
6. **Do NOT** check "Initialize with README"
7. Click **Create repository**

#### Step 2: Initialize Git and Push

Open PowerShell or Command Prompt in the `website hosting` directory:

```powershell
# Navigate to website hosting directory
cd "D:\alphadrip database\supabase-opti-database\LOCAL DATABASE\out\vwap_reports\website hosting"

# Initialize git repository
git init

# Add all files
git add .

# Create initial commit
git commit -m "Initial commit: VWAP Reports Gallery"

# Add GitHub remote (replace YOUR_USERNAME and REPO_NAME)
git remote add origin https://github.com/YOUR_USERNAME/vwap-reports-gallery.git

# Push to GitHub
git branch -M main
git push -u origin main
```

**Important:** Replace `YOUR_USERNAME` and `vwap-reports-gallery` with your actual GitHub username and repository name.

#### Step 3: Enable GitHub Pages

1. Go to your repository on GitHub
2. Click **Settings** (top menu)
3. Scroll down to **Pages** (left sidebar)
4. Under **Source**:
   - **Branch**: Select `main`
   - **Folder**: Select `/docs`
5. Click **Save**

#### Step 4: Access Your Site

Your site will be live at:
```
https://YOUR_USERNAME.github.io/vwap-reports-gallery/
```

**Note:** It may take 1-2 minutes for the site to be available after enabling Pages.

---

### Option 2: Deploy from root (Alternative)

If you prefer to have the website files in the repository root:

#### Step 1: Create GitHub Repository

Same as Option 1, Step 1.

#### Step 2: Copy Files to Root

```powershell
# Navigate to website hosting directory
cd "D:\alphadrip database\supabase-opti-database\LOCAL DATABASE\out\vwap_reports\website hosting"

# Copy site/docs contents to a temporary location, then to repo root
# (You'll need to clone the repo first, then copy files)
```

Then:
1. Clone your repository
2. Copy all files from `site\docs\` to the repository root
3. Commit and push

#### Step 3: Enable GitHub Pages

1. Go to **Settings** → **Pages**
2. Under **Source**:
   - **Branch**: `main`
   - **Folder**: `/` (root)
3. Click **Save**

---

## Updating Reports

When you have new reports to add:

### Step 1: Sync and Generate

```powershell
cd "D:\alphadrip database\supabase-opti-database\LOCAL DATABASE\out\vwap_reports\website hosting"

# Sync new reports
py tools\sync_reports.py

# Regenerate manifest
py tools\generate_manifest.py
```

### Step 2: Commit and Push

```powershell
# Add changes
git add site/docs/

# Commit
git commit -m "Update VWAP reports"

# Push to GitHub
git push
```

GitHub Pages will automatically update within 1-2 minutes.

---

## Troubleshooting

### Site Not Loading

1. **Check repository settings:**
   - Repository must be **Public** (for free GitHub Pages)
   - Or upgrade to GitHub Pro for private repos with Pages

2. **Verify Pages is enabled:**
   - Go to Settings → Pages
   - Ensure source branch and folder are set correctly

3. **Check file structure:**
   - `index.html` must be in the root of the selected folder
   - For `/docs` folder: `site/docs/index.html` should exist
   - For root: `index.html` should be in repo root

4. **Wait a few minutes:**
   - GitHub Pages can take 1-2 minutes to build and deploy

### 404 Errors

- Ensure `manifest.json` exists in the same directory as `index.html`
- Check that file paths in `manifest.json` are relative (start with `reports/`)
- Verify all report files were copied correctly

### Images/Dashboards Not Loading

- Check browser console for 404 errors
- Verify file paths in `manifest.json` are correct
- Ensure all files were committed and pushed to GitHub

---

## Custom Domain (Optional)

To use a custom domain:

1. Add a `CNAME` file in your `site/docs/` folder with your domain:
   ```
   reports.yourdomain.com
   ```

2. Configure DNS:
   - Add a CNAME record pointing to `YOUR_USERNAME.github.io`

3. Update GitHub Pages settings:
   - Settings → Pages → Custom domain
   - Enter your domain

---

## Repository Structure

After deployment, your repository should look like:

```
vwap-reports-gallery/
├── .gitignore
├── README.md
├── DEPLOY_TO_GITHUB.md
├── tools/
│   ├── sync_reports.py
│   └── generate_manifest.py
└── site/
    └── docs/              # This is what GitHub Pages serves
        ├── index.html
        ├── app.js
        ├── styles.css
        ├── manifest.json
        └── reports/
            └── ...
```

---

## Security Reminder

⚠️ **Everything in your repository will be publicly accessible!**

- Do not commit API keys
- Do not commit database credentials
- Do not commit personal information
- Only commit the static website files

---

## Need Help?

- [GitHub Pages Documentation](https://docs.github.com/en/pages)
- [GitHub Pages Troubleshooting](https://docs.github.com/en/pages/getting-started-with-github-pages/creating-a-github-pages-site#troubleshooting)
