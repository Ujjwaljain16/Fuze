# PWA Share Functionality - Testing Guide

## Overview
This guide covers testing the PWA share functionality, which allows users to share LinkedIn posts (or any URLs) from their mobile phone to the Fuze PWA.

## Prerequisites

1. **HTTPS Required**: PWAs require HTTPS (except localhost)
2. **PWA Installation**: The app must be installed as a PWA
3. **Mobile Device**: Testing requires a mobile device (Android/iOS)

## Testing Steps

### 1. Install PWA on Mobile Device

#### Android (Chrome)
1. Open Chrome browser on Android
2. Navigate to your Fuze app URL (must be HTTPS)
3. Tap the menu (3 dots) → "Add to Home screen" or "Install app"
4. Confirm installation
5. The app icon should appear on your home screen

#### iOS (Safari)
1. Open Safari on iOS
2. Navigate to your Fuze app URL (must be HTTPS)
3. Tap the Share button
4. Select "Add to Home Screen"
5. Confirm installation

### 2. Test Share Functionality

#### From LinkedIn App (Android)
1. Open LinkedIn app on Android
2. Find a post you want to share
3. Tap the Share button on the post
4. Select "Fuze" from the share menu
5. The Fuze app should open with the shared URL
6. Verify the preview is shown correctly
7. Tap "Save Bookmark"
8. Verify it redirects to bookmarks page
9. Check that the bookmark appears in your bookmarks list

#### From Browser (Android/iOS)
1. Open any browser on your mobile device
2. Navigate to a LinkedIn post URL
3. Use the browser's share function
4. Select "Fuze" from the share menu
5. Follow the same verification steps as above

#### Manual Testing (Development)
1. Open the PWA
2. Navigate to: `https://your-domain.com/share?url=https://www.linkedin.com/posts/example-post&title=Test%20Post`
3. Verify the share handler page loads
4. Verify URL extraction works
5. Verify preview extraction works
6. Test save functionality

### 3. Test Edge Cases

#### No URL Provided
- Navigate to `/share` without URL parameter
- Should show error message
- Should provide option to go to dashboard

#### Invalid URL
- Share a malformed URL
- Should handle gracefully
- Should still allow saving (may have limited preview)

#### Not Authenticated
- Share while logged out
- Should redirect to login
- Should preserve share URL in redirect
- After login, should return to share handler

#### Network Issues
- Test with poor/no connectivity
- Should show appropriate error messages
- Should allow retry

### 4. Verify Content Extraction

#### LinkedIn Posts
- Share a LinkedIn post URL
- Verify content is extracted correctly
- Verify title, description, and text are captured
- Verify quality score is calculated

#### Other URLs
- Share a regular website URL
- Verify basic extraction works
- Verify fallback to URL-only save works

### 5. Test PWA Features

#### Offline Support
1. Install PWA
2. Enable airplane mode
3. Open PWA
4. Verify it loads from cache
5. Share functionality may be limited offline

#### App Updates
1. Make changes to the app
2. Reload the PWA
3. Verify service worker updates
4. Verify share functionality still works

## Browser Compatibility

### Full Support
- ✅ Chrome (Android) - Full Web Share Target API support
- ✅ Edge (Android) - Full support
- ✅ Samsung Internet - Full support

### Limited Support
- ⚠️ Safari (iOS) - Limited Web Share Target API support
  - Users may need to use "Add to Home Screen" first
  - Share may not appear in all share menus

### No Support
- ❌ Firefox (Android) - No Web Share Target API support
- ❌ Opera (Android) - Limited support

## Debugging

### Check Service Worker
1. Open Chrome DevTools
2. Go to Application tab
3. Check Service Workers section
4. Verify service worker is active
5. Check for errors

### Check Manifest
1. Open Chrome DevTools
2. Go to Application tab
3. Check Manifest section
4. Verify `share_target` is present
5. Verify all required fields are set

### Check Console
1. Open Chrome DevTools
2. Go to Console tab
3. Look for errors related to:
   - Service worker registration
   - Share handler navigation
   - API calls

### Test Share Target
1. Use Chrome DevTools
2. Go to Application tab
3. Click "Manifest" in left sidebar
4. Look for "Share Target" section
5. Verify configuration is correct

## Common Issues

### Share Option Not Appearing
- **Cause**: PWA not installed or manifest not configured
- **Solution**: Reinstall PWA, verify manifest.json is accessible

### URL Not Extracted
- **Cause**: URL parameter not passed correctly
- **Solution**: Check share_target configuration in manifest

### Authentication Issues
- **Cause**: User not logged in when sharing
- **Solution**: Implement redirect to login with return URL

### Content Not Extracting
- **Cause**: Backend extraction service failing
- **Solution**: Check backend logs, verify API endpoint works

## Production Checklist

Before deploying to production:

- [ ] Manifest.json is accessible at `/manifest.json`
- [ ] Service worker is registered and active
- [ ] Share target is configured correctly
- [ ] Share handler page exists and works
- [ ] Authentication flow works with share
- [ ] Content extraction works for LinkedIn URLs
- [ ] Error handling is implemented
- [ ] Mobile UI is responsive
- [ ] Icons are properly sized and accessible
- [ ] HTTPS is enabled (required for PWA)

## Testing Tools

### Chrome DevTools
- Application tab for PWA inspection
- Network tab for API debugging
- Console for error checking

### Lighthouse
- Run PWA audit
- Check for PWA requirements
- Verify share target configuration

### Real Device Testing
- Essential for share functionality
- Use Android device for best results
- Test on multiple browsers

