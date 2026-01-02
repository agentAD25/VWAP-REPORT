# Enable GitHub Pages - Step-by-Step Instructions

## ⚠️ Manual Action Required

GitHub Pages must be enabled through the GitHub web interface. Follow these steps:

---

## 📋 Step-by-Step Instructions

### Step 1: Navigate to Repository Settings
1. Go to: **https://github.com/agentAD25/VWAP-REPORT**
2. Click on **Settings** (in the repository navigation bar at the top)

### Step 2: Access Pages Settings
1. In the left sidebar, scroll down and click **Pages**
2. You'll see the "GitHub Pages" configuration section

### Step 3: Configure Pages Source
1. Under **Source**, you'll see a dropdown
2. Select:
   - **Branch:** `main`
   - **Folder:** `/docs` (NOT `/ (root)`)
3. Click **Save**

### Step 4: Wait for Deployment
- GitHub will show a message: "Your site is ready to be published..."
- Wait 1-2 minutes for the initial deployment
- You'll see a green checkmark when it's ready
- Your site URL will be displayed: `https://agentad25.github.io/VWAP-REPORT/`

---

## ✅ Verification

Once enabled, verify the site is working:

1. **Visit the site:** https://agentad25.github.io/VWAP-REPORT/
2. **Check main page loads** correctly
3. **Test navigation:**
   - Select a contract (NQU25 or NQZ25)
   - Select a timeframe (1m, 5m, 15m, 30m)
   - Verify reports list appears
4. **Test a report:**
   - Click on a `hold_fail_rates.html` report
   - Verify chart is centered
   - Verify no Downloads section appears
5. **Check browser console** for any errors

---

## 🔗 Important URLs

- **Repository:** https://github.com/agentAD25/VWAP-REPORT
- **Pages Settings:** https://github.com/agentAD25/VWAP-REPORT/settings/pages
- **Live Site (after enabling):** https://agentad25.github.io/VWAP-REPORT/

---

## ⚠️ Common Issues

### Issue: "Site not found" after enabling
- **Solution:** Wait 2-3 minutes for GitHub to build and deploy the site
- **Check:** Go to Settings → Pages to see deployment status

### Issue: Wrong folder selected
- **Solution:** Make sure you selected `/docs` folder, NOT `/ (root)`
- **Why:** Our website files are in the `site/docs/` directory

### Issue: Site shows 404 errors
- **Solution:** Verify the `site/docs/index.html` file exists in the repository
- **Check:** Browse the repository to confirm files are present

---

## 📊 Expected Result

After enabling GitHub Pages, you should see:
- ✅ Main page loads at https://agentad25.github.io/VWAP-REPORT/
- ✅ Contract and timeframe dropdowns work
- ✅ Reports are accessible
- ✅ Charts are centered in hold_fail_rates reports
- ✅ No Downloads sections appear
- ✅ All visual updates are live

---

**Last Updated:** 2026-01-01
