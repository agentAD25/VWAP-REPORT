# Deploy one contract (chunked) to avoid push timeouts

If `git push` fails (timeout, large buffer, or API error), use **one contract at a time**:

```powershell
.\deploy.ps1 -Contract MGCQ25
.\deploy.ps1 -Contract MGCZ24
.\deploy.ps1 -Contract MGCZ25
# ... then other contracts, or
.\deploy.ps1 -Contract all   # to push any remaining changes
```

- **`-Contract NAME`**  
  - Only stages: `docs/reports/NAME_*`, `site/docs/reports/NAME_*`, `docs/manifest.json`, `tools/`, `deploy.ps1`.  
  - Commit and push are unchanged; each push is smaller.

- **`-Contract all`** (default)  
  - `git add .` (full tree). Use when most changes are already pushed or the repo is small.

- **`-NoPush`**  
  - Run sync, visual, manifest, `git add`, `git commit`, but **skip** `git push`.  
  - Then run `git push -u origin main` yourself (or retry).  
  - Useful when the failure is only on push (e.g. GitHub API / Request ID errors).

Examples:

```powershell
# One contract, then push
.\deploy.ps1 -Contract MGCQ25

# Do everything except push; you push manually
.\deploy.ps1 -Contract MGCQ25 -NoPush
git push -u origin main

# Full deploy (all contracts)
.\deploy.ps1
```

`.gitignore` excludes `docs/reports_visual_update/` and `site/docs/reports_visual_update/` to keep `git add .` smaller.
