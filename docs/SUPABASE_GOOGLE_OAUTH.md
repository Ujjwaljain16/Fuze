# Supabase Google OAuth (Sign in with Google) — Setup and Documentation

This document explains how to enable "Sign in with Google" for your Fuze app using Supabase's Auth providers and Google Cloud OAuth credentials. It covers required settings in Google Cloud Console and Supabase Dashboard, environment variable changes, testing steps, and security considerations.

---

**Overview**

The application supports Supabase-hosted OAuth sign-in. The flow implemented in the codebase is:

- Frontend (`frontend/src/services/oauth.js`) records that this browser started a Google sign-in (or a link), then redirects to the Supabase OAuth authorize URL (provider=google).
- Supabase performs OAuth with Google and redirects back to `/oauth/callback` with tokens in the URL fragment.
- The frontend accepts the redirect only if this browser started it in the last 10 minutes (otherwise a link carrying an attacker's token could sign the victim into the attacker's account), reads `access_token` from the fragment and POSTs it to `/api/auth/supabase-oauth` (sign-in) or `/api/auth/link-oauth` (connect Google to the signed-in account).
- The backend verifies the token with Supabase (`/auth/v1/user`), requires a verified email, signs in the account **linked to that Google identity** (or creates a new one), and issues the application's own JWTs. It never joins an existing account by matching email.

This enables single sign-on while keeping the application session management under your control.

---

## Prerequisites

- A Supabase project (you already have one: `https://xqfgfalwwfwtzvuuvroq.supabase.co`).
- A Google Cloud project with OAuth credentials for "Web application" (or other client types you need: Android, Chrome extension, One Tap).
- Access to your repository and `.env` to set environment variables on local and production environments.

---

## Step 1 — Create Google OAuth Client ID & Client Secret

1. Go to Google Cloud Console: https://console.cloud.google.com/
2. Select your project (or create a new one).
3. In the left menu, go to "APIs & Services" → "OAuth consent screen" and configure the consent screen (set the app name, authorized domains, add scopes `openid`, `email`, `profile` as needed).
4. Go to "Credentials" → "Create Credentials" → "OAuth client ID".
   - Choose "Web application" (or other type for Android/Chrome extension/One Tap as needed).
   - For the authorized redirect URIs add Supabase's callback URI:

      `https://xqfgfalwwfwtzvuuvroq.supabase.co/auth/v1/callback`

   - For local development you may add (if needed):

      `http://localhost:5173` (or your local frontend URL)

   - Save and copy the **Client ID** and **Client Secret**.

Notes:
- If you plan to use Google One Tap or Chrome extension sign-ins, register the corresponding client IDs (Chrome extension client id format starts with `chrome-extension://<EXT_ID>`). You can provide multiple client IDs (comma-separated) in Supabase's UI.

---

## Step 2 — Configure Google provider in Supabase Dashboard

1. Open Supabase Dashboard → Your project → `Authentication` → `Providers` → `Google`.
2. Fill in the fields:
   - **Client IDs**: paste one or more client IDs (comma-separated) — include the web client ID and any other client IDs you want to allow (Android/Chrome extension/One Tap).
   - **Client Secret**: paste the client secret you obtained from Google Cloud.
   - **Callback URL**: ensure it is `https://xqfgfalwwfwtzvuuvroq.supabase.co/auth/v1/callback` (Supabase shows this; register it in Google Cloud as well).
3. Options (toggle as necessary):
   - **Skip nonce checks**: enable only if you cannot supply nonce values for the OIDC id_token (less secure but sometimes required for some platforms). Avoid enabling this unless necessary.
   - **Allow users without an email**: enable only if you want to allow provider accounts that do not return an email address. If enabled, the backend must handle missing email (account creation without email or prompt user to add email later).
4. Save changes.

---

## Step 3 — Environment variables and repo changes

The repository already contains environment handling. To enable OAuth in the app, make sure the following environment variables are set for your backend and frontend environments.

Add to backend `.env` (or set in your host environment):

- `SUPABASE_URL=https://xqfgfalwwfwtzvuuvroq.supabase.co`
- `SUPABASE_ANON_KEY=<your-supabase-anon-key>`  # sent as the `apikey` header when verifying tokens

Add to frontend `.env` (Vite uses `VITE_` prefix):

- `VITE_SUPABASE_URL=https://xqfgfalwwfwtzvuuvroq.supabase.co`
- `VITE_API_URL=http://127.0.0.1:5000` (development) or your production API URL

Note: The Supabase provider configuration (Client IDs and Client Secret) is stored in the Supabase Dashboard. The backend only needs `SUPABASE_URL` and `SUPABASE_ANON_KEY` to verify tokens server-side; it does not read a service role key.

---

## Step 4 — Code changes (already applied)

The repository already contains the flow for Sign in with Google:

- Frontend:
  - `frontend/src/services/oauth.js` is the one OAuth module. `startGoogleOAuth()` stores a pending marker (mode `signin` or `link`, timestamp) and redirects to:
    `https://<SUPABASE_URL>/auth/v1/authorize?provider=google&redirect_to=<APP_ORIGIN>/oauth/callback`
  - `frontend/src/pages/OAuthCallback.jsx` finishes the flow: tokens are read from the URL fragment only, and only if a pending marker from this browser is under 10 minutes old. Other routes forward a stray fragment to `/oauth/callback` instead of handling it.
  - On `409 account_link_required` the callback explains what to do instead of failing.
  - The Profile page has a **Connect Google** card that starts the flow in `link` mode; `/api/profile` reports `google_connected`.

- Backend (`backend/blueprints/auth.py`, `backend/services/auth_service.py`):
  - `POST /api/auth/supabase-oauth`:
    - Verifies the `access_token` by calling `GET https://<SUPABASE_URL>/auth/v1/user` with the Bearer token.
    - Rejects identities whose email isn't verified (`403`).
    - Signs in the user whose `provider_name='google'` / `provider_user_id` match the identity. If none exists and **an account with that email already exists**, it returns `409 account_link_required`: `/register` does not prove email ownership, so joining by email would let whoever registered the address first keep a password into the real owner's account.
    - Otherwise creates a new user with a random, unusable password and issues local JWT tokens (access + refresh, in cookies and in the response body).
  - `POST /api/auth/link-oauth` (requires a signed-in user): connects the Google identity to the caller's own account. The Google email must match the account's email, and the identity must not already belong to another account.
  - A Google-created account can set its first password only after a sign-in in the last 15 minutes (it has no current password to confirm).

If you want stronger validation you can (optional):
- Verify the Google `id_token` audience (`aud`) matches your Google client ID.
- Verify `iss` (issuer) is `https://accounts.google.com` or `accounts.google.com`.

---

## Step 5 — Testing locally

1. Ensure `.env` contains `VITE_SUPABASE_URL` and `VITE_API_URL` and your backend environment has `SUPABASE_URL` and `SUPABASE_SERVICE_ROLE_KEY`.
2. Start the backend (from project root):

```powershell
# Activate venv (already active in your environment)
& .\venv\Scripts\Activate.ps1
pip install -r requirements.txt
# Local work needs APP_ENV=development (unset means production, which refuses default secrets)
cd backend
python run_production.py
```

3. Start the frontend (from `frontend/`):

```bash
npm install
npm run dev
```

4. In the browser go to `/login` and click "Sign in with Google". Complete the Google consent flow.
5. Supabase will redirect back to `https://<your-origin>/oauth/callback` with an `access_token` in the URL fragment. The frontend will exchange that token with your backend and then redirect to `/dashboard` on success.

Troubleshooting tips:
- If the redirect fails or you get `Invalid Supabase token`, ensure the callback URL is registered in Google Cloud and matches exactly the value registered in Supabase.
- If `access_token` is missing in the redirect, check that the Supabase `authorize` URL used in the frontend is correct and that the provider is enabled in Supabase Dashboard.
- If the callback says the sign-in wasn't started from this browser, start it again from the same browser within 10 minutes.
- `account_link_required`: an account with that email exists. Sign in with its password, then use **Connect Google** on the Profile page.
- Check backend logs for errors from the `/auth/v1/user` call (network, timeout, or invalid token).

---

## Security considerations

- If you keep a `SUPABASE_SERVICE_ROLE_KEY` anywhere, protect it: it provides elevated privileges and must not be exposed to browsers or client code. The backend doesn't need it.
- `Skip nonce checks` weakens security. Only enable if you have a platform limitation that prevents using nonces.
- `Allow users without an email` has no effect on Fuze: the backend rejects identities without a verified email.
- For production, always run under HTTPS and ensure all callback/redirect URIs use `https`.

---

## Optional improvements & recommendations

- Validate `id_token` fields (`aud`, `iss`, `exp`) if you accept ID tokens directly.

---

## Example env additions for `.env`

Add to backend `.env` (do not commit secrets):

```env
SUPABASE_URL=https://xqfgfalwwfwtzvuuvroq.supabase.co
SUPABASE_ANON_KEY=eyJhbGciOiJI...
```

Add to frontend `.env` (for Vite):

```env
VITE_SUPABASE_URL=https://xqfgfalwwfwtzvuuvroq.supabase.co
VITE_API_URL=http://127.0.0.1:5000
```