# PWA Testing Checklist

## ✅ Pre-Testing Setup

### 1. Verify Service Worker is Enabled
- [ ] Check `frontend/src/main.jsx` - service worker registration should be active
- [ ] Service worker should NOT be commented out
- [ ] No unregister code should be running

### 2. Verify Files Exist
- [ ] `frontend/public/sw.js` exists
- [ ] `public/manifest.json` exists (or `frontend/public/manifest.json`)
- [ ] Icons exist in `frontend/public/icons/` directory

### 3. Build and Deploy
- [ ] Frontend is built: `npm run build`
- [ ] Deployed to Vercel
- [ ] Service worker file is accessible at `https://itsfuze.vercel.app/sw.js`

---

## 🧪 Testing Checklist

### Test 1: Service Worker Registration

**Steps:**
1. Open `https://itsfuze.vercel.app` in Chrome
2. Open DevTools → Application tab → Service Workers
3. Check if service worker is registered

**Expected:**
- ✅ Service worker shows as "activated and is running"
- ✅ Scope: `https://itsfuze.vercel.app/`
- ✅ No errors in console

**If not working:**
- Check browser console for errors
- Verify `/sw.js` is accessible (try opening directly in browser)
- Check Network tab - should see `sw.js` loaded with 200 status

---

### Test 2: Service Worker Not Blocking API Calls

**Steps:**
1. Open DevTools → Network tab
2. Log in to the app
3. Navigate to Dashboard
4. Check API calls to `*.hf.space`

**Expected:**
- ✅ All API calls go directly to `*.hf.space` (not intercepted)
- ✅ API calls complete successfully (200 status)
- ✅ No "Failed to fetch" errors
- ✅ SSE streams work correctly

**If API calls are blocked:**
- Check service worker code - should have bypass logic for external requests
- Check service worker code - should bypass all `/api/` requests
- Verify service worker is not caching API responses

---

### Test 3: PWA Installation (Desktop)

**Steps:**
1. Open `https://itsfuze.vercel.app` in Chrome
2. Look for install button in address bar (or menu)
3. Click "Install" or "Add to Home Screen"

**Expected:**
- ✅ Install prompt appears
- ✅ App installs successfully
- ✅ App opens in standalone window (no browser UI)
- ✅ App icon appears in applications/taskbar

**If install prompt doesn't appear:**
- Check manifest.json is valid (DevTools → Application → Manifest)
- Verify all required manifest fields are present
- Check if app is already installed
- Try in incognito mode

---

### Test 4: PWA Installation (Mobile - Android)

**Steps:**
1. Open `https://itsfuze.vercel.app` in Chrome on Android
2. Tap menu (3 dots) → "Add to Home screen" or "Install app"
3. Confirm installation

**Expected:**
- ✅ Install prompt appears
- ✅ App icon added to home screen
- ✅ App opens in standalone mode (no browser UI)
- ✅ App works offline (cached pages)

---

### Test 5: PWA Installation (Mobile - iOS)

**Steps:**
1. Open `https://itsfuze.vercel.app` in Safari on iOS
2. Tap Share button
3. Tap "Add to Home Screen"
4. Confirm

**Expected:**
- ✅ App icon added to home screen
- ✅ App opens in standalone mode
- ✅ Status bar styling matches theme-color

---

### Test 6: PWA Share Target (Mobile)

**Steps:**
1. Install PWA on mobile device
2. Open a LinkedIn post in browser
3. Tap Share button
4. Look for "Fuze" in share options
5. Select "Fuze"
6. App should open with shared URL

**Expected:**
- ✅ "Fuze" appears in share menu
- ✅ App opens to `/share` route
- ✅ URL is extracted from share
- ✅ User can save the bookmark

**If share target doesn't work:**
- Verify `share_target` is in manifest.json
- Check manifest.json is served with correct MIME type
- Verify `/share` route exists in app
- Test on Android (iOS has limited share target support)

---

### Test 7: Offline Functionality

**Steps:**
1. Install PWA
2. Open app and navigate to different pages
3. Turn off internet/WiFi
4. Try to navigate within the app

**Expected:**
- ✅ Cached pages still load
- ✅ App doesn't show "No internet" error immediately
- ✅ Navigation between cached pages works
- ✅ API calls fail gracefully (show error message)

**Note:** Full offline functionality requires more caching - this is basic offline support.

---

### Test 8: Service Worker Updates

**Steps:**
1. Make a change to `sw.js`
2. Deploy new version
3. Open app in browser
4. Check service worker update

**Expected:**
- ✅ New service worker installs in background
- ✅ Old service worker continues serving until new one activates
- ✅ After refresh, new service worker is active
- ✅ Old cache is cleaned up

---

### Test 9: Manifest Validation

**Steps:**
1. Open DevTools → Application → Manifest
2. Check all fields

**Expected:**
- ✅ No errors or warnings
- ✅ All icons load correctly
- ✅ Theme color is correct
- ✅ Display mode is "standalone"
- ✅ Start URL is "/"

---

### Test 10: API Calls with Service Worker Active

**Critical Test - This was the main issue before**

**Steps:**
1. Ensure service worker is active
2. Open Dashboard
3. Check Network tab
4. Verify all API calls work

**Expected:**
- ✅ `/api/auth/csrf-token` - 200 OK
- ✅ `/api/profile` - 200 OK
- ✅ `/api/bookmarks` - 200 OK
- ✅ `/api/projects` - 200 OK
- ✅ `/api/bookmarks/dashboard/stats` - 200 OK
- ✅ SSE stream `/api/bookmarks/progress/stream` - 200 OK (EventSource)
- ✅ No requests are canceled
- ✅ No "Failed to fetch" errors

**If API calls fail:**
- Check service worker fetch handler - should bypass all `/api/` requests
- Check service worker fetch handler - should bypass all external requests
- Verify service worker is not caching API responses

---

## 🐛 Common Issues & Fixes

### Issue 1: Service Worker Not Registering

**Symptoms:**
- No service worker in DevTools → Application → Service Workers
- Console shows "Service worker file not found"

**Fixes:**
- Verify `sw.js` exists in `frontend/public/` directory
- Check Vercel build includes `sw.js` in output
- Verify `sw.js` is accessible at `/sw.js` URL
- Check file permissions

---

### Issue 2: API Calls Blocked by Service Worker

**Symptoms:**
- API calls show as "canceled" or "failed"
- Network tab shows requests intercepted by service worker
- SSE streams don't work

**Fixes:**
- Verify service worker fetch handler bypasses `/api/` requests
- Verify service worker fetch handler bypasses external requests
- Check service worker code for proper `return;` statements
- Unregister service worker and re-register

---

### Issue 3: Install Prompt Not Appearing

**Symptoms:**
- No install button in browser
- "Add to Home Screen" not available

**Fixes:**
- Verify manifest.json is valid
- Check all required manifest fields are present
- Ensure app is served over HTTPS
- Check if app is already installed
- Try in incognito/private mode

---

### Issue 4: Share Target Not Working

**Symptoms:**
- "Fuze" doesn't appear in share menu
- Share opens app but doesn't extract URL

**Fixes:**
- Verify `share_target` is in manifest.json
- Check manifest.json MIME type (should be `application/manifest+json`)
- Verify `/share` route exists in app
- Test on Android (iOS has limited support)
- Check share handler component logic

---

## ✅ Success Criteria

All tests should pass:
- ✅ Service worker registers and activates
- ✅ API calls work with service worker active
- ✅ SSE streams work with service worker active
- ✅ PWA installs on desktop
- ✅ PWA installs on mobile (Android & iOS)
- ✅ Share target works (Android)
- ✅ Basic offline functionality works
- ✅ No console errors
- ✅ No network errors

---

## 📝 Testing Notes

- **Test on HTTPS**: PWAs require HTTPS (Vercel provides this)
- **Test on Real Devices**: Mobile testing should be on actual devices
- **Clear Cache**: Use "Clear storage" in DevTools if testing updates
- **Check Console**: Always check browser console for errors
- **Network Tab**: Monitor Network tab for any blocked requests

---

## 🚀 After Testing

If all tests pass:
1. ✅ PWA is fully functional
2. ✅ Service worker is working correctly
3. ✅ API calls are not blocked
4. ✅ Ready for production use

If any tests fail:
1. Document the issue
2. Check the "Common Issues & Fixes" section
3. Fix the issue
4. Re-test

