# Supabase Google OAuth (Sign in with Google) — Setup and Documentation

This document explains how to enable "Sign in with Google" for your Fuze app using Supabase's Auth providers and Google Cloud OAuth credentials. It covers required settings in Google Cloud Console and Supabase Dashboard, environment variable changes, testing steps, and security considerations.

---

**Overview**

The application supports Supabase-hosted OAuth sign-in. The flow implemented in the codebase is:

- Frontend redirects the browser to Supabase OAuth authorize URL (provider=google).
- Supabase performs OAuth with Google and redirects back to `/oauth/callback` with tokens in the URL fragment.
- The frontend reads `access_token` from the URL fragment and POSTs it to the backend endpoint `/api/auth/supabase-oauth`.
- The backend verifies the token with Supabase (`/auth/v1/user`), finds or creates a local `User`, and issues the application's own JWTs.

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
- `SUPABASE_SERVICE_ROLE_KEY=<your-supabase-service-role-key>`  # Keep secret, used by backend to access Supabase admin endpoints if needed

(Optional — for advanced control if you prefer managing provider via env instead of Supabase UI):
- `SUPABASE_CLIENT_ID=<google-client-id>`
- `SUPABASE_CLIENT_SECRET=<google-client-secret>`

Add to frontend `.env` (Vite uses `VITE_` prefix):

- `VITE_SUPABASE_URL=https://xqfgfalwwfwtzvuuvroq.supabase.co`
- `VITE_API_URL=http://127.0.0.1:5000` (development) or your production API URL

Note: The Supabase provider configuration (Client IDs and Client Secret) is typically stored in the Supabase Dashboard. The backend only needs `SUPABASE_URL` and `SUPABASE_SERVICE_ROLE_KEY` to verify tokens server-side and to optionally manage Supabase programmatically.

---

## Step 4 — Code changes (already applied)

The repository already contains the minimal flow needed for Sign in with Google:

- Frontend:
  - Login page (`frontend/src/pages/Login.jsx`) has a "Sign in with Google" button that redirects to:
    `https://<SUPABASE_URL>/auth/v1/authorize?provider=google&redirect_to=<APP_ORIGIN>/oauth/callback`
  - `frontend/src/pages/OAuthCallback.jsx` extracts the `access_token` from the URL fragment and POSTs it to `/api/auth/supabase-oauth`.

- Backend:
  - `POST /api/auth/supabase-oauth` endpoint in `backend/blueprints/auth.py`:
    - Verifies the `access_token` by calling `GET https://<SUPABASE_URL>/auth/v1/user` with the Bearer token.
    - Finds or creates a local `User` in the database by email.
    - Issues local JWT tokens (access + refresh cookie) and returns an `access_token` to the frontend.

If you want stronger validation you can (optional):
- Verify the Google `id_token` audience (`aud`) matches your Google client ID.
- Verify `iss` (issuer) is `https://accounts.google.com` or `accounts.google.com`.
- Store provider name and provider user id (`sub`) in the `User` model for easier linking of accounts.

---

## Step 5 — Testing locally

1. Ensure `.env` contains `VITE_SUPABASE_URL` and `VITE_API_URL` and your backend environment has `SUPABASE_URL` and `SUPABASE_SERVICE_ROLE_KEY`.
2. Start the backend (from project root):

```powershell
# Activate venv (already active in your environment)
& .\venv\Scripts\Activate.ps1
pip install -r requirements.txt
# Run your Flask app (example)
python -m backend.run_production
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
- Check backend logs for errors from the `/auth/v1/user` call (network, timeout, or invalid token).

---

## Security considerations

- Protect `SUPABASE_SERVICE_ROLE_KEY`. It provides elevated privileges and must not be exposed to browsers or client code.
- `Skip nonce checks` weakens security. Only enable if you have a platform limitation that prevents using nonces.
- `Allow users without an email` can create non-unique user entries. If enabled, implement additional verification or a step to collect an email later.
- For production, always run under HTTPS and ensure all callback/redirect URIs use `https`.

---

## Optional improvements & recommendations

- Store provider metadata on `User` model:
  - Add columns `provider_name` (e.g., `google`) and `provider_user_id` (the provider-specific user id) for linking accounts.
- Add a migration script to create those columns and backfill from `user_metadata`.
- When creating user accounts without email, prompt the user to add an email address before allowing full account access.
- Validate `id_token` fields (`aud`, `iss`, `exp`) if you accept ID tokens directly.
- Consider rotating or limiting the service role key usage: the backend should use the access token (Bearer) to get user info; only use service role key for admin operations.

---

## Example env additions for `.env`

Add to backend `.env` (do not commit secrets):

```env
SUPABASE_URL=https://xqfgfalwwfwtzvuuvroq.supabase.co
SUPABASE_SERVICE_ROLE_KEY=eyJhbGciOiJI...   # Keep secret
```

Add to frontend `.env` (for Vite):

```env
VITE_SUPABASE_URL=https://xqfgfalwwfwtzvuuvroq.supabase.co
VITE_API_URL=http://127.0.0.1:5000
```

---

If you'd like, I can:
- Add database migration code to store `provider_name` and `provider_user_id` on `User` and wire it into the OAuth creation flow.
- Add audience (`aud`) validation using the Google `id_token` if you prefer additional checks.
- Add README section or inline comments in code to indicate where to toggle the "Skip nonce checks" and "Allow users without email" settings.

Tell me which of the optional improvements you want next and I'll implement them.