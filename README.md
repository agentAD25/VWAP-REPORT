# VWAP Reports Gallery - Static Website

A static website project for hosting and browsing VWAP (Volume Weighted Average Price) analysis reports. This project provides a clean, modern interface to navigate reports by contract, timeframe, and date range.

## What This Project Is

This is a **static website** that displays VWAP report outputs (PNG images, HTML dashboards, and CSV downloads) in an organized, filterable gallery. It requires:

- ✅ **No database connections**
- ✅ **No API keys**
- ✅ **No environment variables**
- ✅ **No Supabase or external services**
- ✅ **No build process** - just plain HTML, CSS, and JavaScript

The website reads from a generated `manifest.json` file that catalogs all available reports, making it perfect for hosting on GitHub Pages or any static hosting service.

## Project Structure

```
website hosting/
├── README.md                    # This file
├── tools/
│   ├── sync_reports.py          # Copies reports from source to site/docs/reports/
│   └── generate_manifest.py     # Generates manifest.json from copied reports
└── site/
    └── docs/                    # GitHub Pages root directory
        ├── index.html           # Main HTML page
        ├── app.js               # Application logic
        ├── styles.css           # Styling
        ├── manifest.json        # Generated catalog (run generate_manifest.py)
        └── reports/             # Copied report files (run sync_reports.py)
            ├── NQU25_20250623-20250915_1m/
            ├── NQU25_20250623-20250915_5m/
            └── ...
```

## Setup Instructions

### 1. Sync Reports

Copy report files from the source directory to the website directory:

```bash
python tools\sync_reports.py
```

This script:
- Reads from: `D:\alphadrip database\supabase-opti-database\LOCAL DATABASE\out\vwap_reports`
- Copies to: `site\docs\reports\`
- Only copies `.png`, `.html`, and `.csv` files
- Skips unchanged files (compares size and modified time)
- **Never modifies or deletes** files in the source directory

### 2. Generate Manifest

Create the `manifest.json` file that catalogs all reports:

```bash
python tools\generate_manifest.py
```

This script:
- Scans `site\docs\reports\` for report folders
- Extracts metadata from folder names (contract, timeframe, date range)
- Organizes reports hierarchically: contract → timeframe → date_range
- Generates `site\docs\manifest.json`

### 3. Preview Locally

Test the website locally before publishing:

**For local access only (same computer):**
```bash
cd site\docs
python -m http.server 8000
```

Then open your browser to: `http://localhost:8000`

**For network access (from other computers on the same network):**
```bash
cd site\docs
python -m http.server 8080 --bind 0.0.0.0
```

Then access from:
- **Same computer:** `http://localhost:8080`
- **Other computers:** `http://<your-ip-address>:8080`

To find your IP address:
- **Windows:** Run `ipconfig` in Command Prompt and look for "IPv4 Address" under your active network adapter
- **Example:** If your IP is `192.168.1.100`, access from another computer at `http://192.168.1.100:8080`

**Note:** If port 8000 is already in use (e.g., by n8n, Docker, or another service), you can use a different port (e.g., 3000, 5000, 8080, 9000).

**Security Note:** When using `--bind 0.0.0.0`, the server is accessible to anyone on your local network. Only use this on trusted networks (e.g., home/office LAN).

## Publishing to GitHub Pages

### Quick Deploy (Recommended)

Use the automated deployment script:

```powershell
cd "D:\alphadrip database\supabase-opti-database\LOCAL DATABASE\out\vwap_reports\website hosting"
.\deploy.ps1
```

The script will:
1. Sync reports and generate manifest
2. Initialize git repository (if needed)
3. Commit changes
4. Set up GitHub remote
5. Push to GitHub

Then enable GitHub Pages:
1. Go to your repository on GitHub
2. **Settings** → **Pages**
3. **Source**: Branch `main`, Folder `/docs`
4. Click **Save**

### Manual Deploy

#### Step 1: Create GitHub Repository

1. Go to [GitHub](https://github.com) and create a new repository
2. Name it `vwap-reports-gallery` (or your preferred name)
3. Choose **Public** (required for free GitHub Pages)
4. **Do not initialize** with README, .gitignore, or license

#### Step 2: Initialize Git and Push

```powershell
cd "D:\alphadrip database\supabase-opti-database\LOCAL DATABASE\out\vwap_reports\website hosting"

# Initialize git
git init
git add .
git commit -m "Initial commit: VWAP Reports Gallery"

# Add remote (replace YOUR_USERNAME and REPO_NAME)
git remote add origin https://github.com/YOUR_USERNAME/vwap-reports-gallery.git

# Push to GitHub
git branch -M main
git push -u origin main
```

#### Step 3: Enable GitHub Pages

1. Go to your repository on GitHub
2. Navigate to **Settings** → **Pages**
3. Under **Source**, select:
   - **Branch**: `main` (or your default branch)
   - **Folder**: `/docs`
4. Click **Save**

#### Step 4: Access Your Site

Your site will be available at:
```
https://<your-username>.github.io/<repository-name>/
```

For example: `https://username.github.io/vwap-reports-gallery/`

**Note:** It may take 1-2 minutes for the site to be available after enabling Pages.

For detailed instructions, see [DEPLOY_TO_GITHUB.md](DEPLOY_TO_GITHUB.md)

## Updating Reports

When you have new reports to add:

1. **Sync new reports:**
   ```bash
   python tools\sync_reports.py
   ```

2. **Regenerate manifest:**
   ```bash
   python tools\generate_manifest.py
   ```

3. **Commit and push:**
   ```bash
   git add .
   git commit -m "Update reports"
   git push
   ```

GitHub Pages will automatically update within a few minutes.

## URL Parameters

The website supports URL parameters for direct linking to specific reports:

```
?contract=NQU25&tf=15m&range=20250623-20250915
```

Parameters:
- `contract`: Contract symbol (e.g., `NQU25`)
- `tf`: Timeframe (e.g., `1m`, `5m`, `15m`, `30m`)
- `range`: Date range in format `YYYYMMDD-YYYYMMDD` (e.g., `20250623-20250915`)

Example full URL:
```
https://username.github.io/vwap-reports-gallery/?contract=NQU25&tf=15m&range=20250623-20250915
```

## Report Folder Format

Reports must follow this naming convention:

```
<CONTRACT>_<START_DATE>-<END_DATE>_<TIMEFRAME>
```

Where:
- `CONTRACT`: Contract symbol (e.g., `NQU25`, `NQZ25`)
- `START_DATE`: Start date as `YYYYMMDD` (e.g., `20250623`)
- `END_DATE`: End date as `YYYYMMDD` (e.g., `20250915`)
- `TIMEFRAME`: Timeframe as `1m`, `5m`, `15m`, or `30m`

Examples:
- `NQU25_20250623-20250915_1m`
- `NQZ25_20250915-20251215_15m`

## Important Notes

### ⚠️ Public Content Warning

**Everything in the `site\docs\` directory (or your GitHub Pages root) will be publicly accessible once hosted.** Do not include:

- API keys
- Database credentials
- Personal information
- Sensitive data

### Non-Destructive Operations

- The `sync_reports.py` script **never modifies or deletes** files in the source directory
- It only **copies** files to the website directory
- Source reports remain untouched

### File Extensions

Only the following file types are copied:
- `.png` - Report images (primary display)
- `.html` - Dashboard files (opened in new tab)
- `.csv` - Data downloads

## Troubleshooting

### Manifest Not Found

If you see "Failed to load manifest.json":
1. Run `python tools\generate_manifest.py`
2. Ensure `manifest.json` exists in `site\docs\`

### No Reports Showing

If reports don't appear:
1. Run `python tools\sync_reports.py` to copy reports
2. Run `python tools\generate_manifest.py` to regenerate manifest
3. Check browser console for errors

### Images Not Loading

If images don't load:
1. Verify files were copied to `site\docs\reports\`
2. Check file paths in `manifest.json` are relative (start with `reports/`)
3. Ensure GitHub Pages is serving from the correct directory

## Browser Compatibility

This website uses modern JavaScript features and should work in:
- Chrome/Edge (latest)
- Firefox (latest)
- Safari (latest)

For older browsers, consider using a polyfill for `fetch()` if needed.

## License

This project is provided as-is for hosting VWAP reports. Modify as needed for your use case.
