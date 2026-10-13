# Supabase Google OAuth (Sign in with Google)

How "Sign in with Google" works in Fuze and how to configure it: Google Cloud OAuth credentials, the Supabase Google provider, environment variables, local testing, and security notes.

---

**Overview**

Fuze uses Supabase Auth only as the Google OAuth broker. The flow implemented in the codebase is:

- The frontend (`frontend/src/services/oauth.js`) records that this browser started a Google sign-in (or a link), then redirects to the Supabase authorize URL (`provider=google`).
- Supabase performs OAuth with Google and redirects back to `/oauth/callback` with tokens in the URL fragment.
- The frontend accepts the redirect only if this browser started it in the last 10 minutes (otherwise a link carrying an attacker's token could sign the victim into the attacker's account). It reads `access_token` from the fragment and POSTs it to `/api/auth/supabase-oauth` (sign-in) or `/api/auth/link-oauth` (connect Google to the signed-in account).
- The backend verifies the token with Supabase (`GET /auth/v1/user`), requires a verified email, signs in the account **linked to that Google identity** (or creates a new one), and issues the application's own JWTs. It never joins an existing account by matching email.

The application's sessions, refresh-token rotation and revocation stay entirely in Fuze.

---

## Prerequisites

- A Supabase project (`https://<project-ref>.supabase.co`).
- A Google Cloud project with an OAuth client of type "Web application".
- Access to set environment variables for the backend and the frontend build.

---

## Step 1: Create the Google OAuth Client ID and Secret

1. Go to the Google Cloud Console: https://console.cloud.google.com/
2. Select or create a project.
3. Under "APIs & Services" → "OAuth consent screen", configure the consent screen (app name, authorized domains, scopes `openid`, `email`, `profile`).
4. Under "Credentials" → "Create Credentials" → "OAuth client ID", choose "Web application".
5. Add Supabase's callback as an authorized redirect URI:

   `https://<project-ref>.supabase.co/auth/v1/callback`

6. Save, and copy the **Client ID** and **Client Secret**.

---

## Step 2: Configure the Google provider in Supabase

1. Supabase Dashboard → your project → `Authentication` → `Providers` → `Google`.
2. Enable the provider and fill in:
   - **Client IDs**: the web client ID from Step 1.
   - **Client Secret**: the secret from Step 1.
   - **Callback URL**: Supabase shows `https://<project-ref>.supabase.co/auth/v1/callback`; it must match the redirect URI registered in Google Cloud.
3. Save.
4. Under `Authentication` → `URL Configuration`, add the app's callback to the allowed redirect URLs. The frontend sends users back to `<APP_ORIGIN>/oauth/callback`, for example `https://app.example.com/oauth/callback` and, for local work, `http://localhost:5173/oauth/callback`.

`Allow users without an email` has no effect on Fuze: the backend rejects identities without a verified email.

---

## Step 3: Environment variables

Backend (`.env` or the host's environment):

- `SUPABASE_URL=https://<project-ref>.supabase.co`
- `SUPABASE_ANON_KEY=<supabase-anon-key>` (sent as the `apikey` header when verifying tokens)

Frontend (Vite reads `VITE_` variables at build time):

- `VITE_SUPABASE_URL=https://<project-ref>.supabase.co`
- `VITE_API_URL=http://127.0.0.1:5000` for development, or the production API URL

The Google client ID and secret live only in the Supabase Dashboard. The backend needs just `SUPABASE_URL` and `SUPABASE_ANON_KEY` to verify tokens (`backend/blueprints/auth.py`); it does not read a service role key. Without `SUPABASE_URL` the endpoints return `503 auth_provider_unavailable`.

---

## How it is implemented

- Frontend:
  - `frontend/src/services/oauth.js` is the one OAuth module. `startGoogleOAuth()` stores a pending marker (mode `signin` or `link`, timestamp) in `localStorage` and redirects to:
    `<VITE_SUPABASE_URL>/auth/v1/authorize?provider=google&redirect_to=<APP_ORIGIN>/oauth/callback`
  - `frontend/src/pages/OAuthCallback.jsx` finishes the flow: tokens are read from the URL fragment only, and only if a pending marker from this browser is under 10 minutes old. Other routes forward a stray fragment to `/oauth/callback` instead of handling it.
  - On `409 account_link_required` the callback explains what to do instead of failing.
  - The Profile page has a **Connect Google** card that starts the flow in `link` mode; `/api/profile` reports `google_connected`.

- Backend (`backend/blueprints/auth.py`, `backend/services/auth_service.py`):
  - `POST /api/auth/supabase-oauth`:
    - Verifies the `access_token` by calling `GET <SUPABASE_URL>/auth/v1/user` with the bearer token. A rejected token is `401 invalid_oauth_token`; a Supabase outage, timeout or rate limit is `503 auth_provider_unavailable`, so clients retry.
    - Rejects identities whose email isn't verified (`403`).
    - Signs in the user whose `provider_name='google'` and `provider_user_id` match the identity. If none exists and **an account with that email already exists**, it returns `409 account_link_required`: `/register` does not prove email ownership, so joining by email would let whoever registered the address first keep a password into the real owner's account.
    - Otherwise creates a new user with a random, unusable password and issues local JWT tokens (access and refresh, in cookies and in the response body).
  - `POST /api/auth/link-oauth` (requires a signed-in user) connects the Google identity to the caller's own account. The Google email must match the account's email, and the identity must not already belong to another account.
  - A Google-created account can set its first password only after a sign-in in the last 15 minutes (it has no current password to confirm).

---

## Testing locally

1. Set `VITE_SUPABASE_URL` and `VITE_API_URL` for the frontend, and `SUPABASE_URL` and `SUPABASE_ANON_KEY` for the backend.
2. Start the backend from the project root:

```powershell
# Activate the virtual environment
& .\venv\Scripts\Activate.ps1
pip install -r requirements.txt
# Local work needs APP_ENV=development (unset means production, which refuses default secrets)
cd backend
python run_production.py
```

3. Start the frontend from `frontend/`:

```bash
npm install
npm run dev
```

4. Open `/login` and click "Sign in with Google". Complete the Google consent flow.
5. Supabase redirects back to `<origin>/oauth/callback` with an `access_token` in the URL fragment. The frontend exchanges it with the backend and then redirects to `/dashboard`.

Troubleshooting:
- If the redirect fails or you get `Invalid Supabase token`, check that the Supabase callback is registered as a redirect URI in Google Cloud and that the app's `/oauth/callback` is in Supabase's allowed redirect URLs.
- If `access_token` is missing in the redirect, check that the authorize URL built by the frontend uses the right Supabase URL and that the Google provider is enabled.
- If the callback says the sign-in wasn't started from this browser, start it again from the same browser within 10 minutes.
- `account_link_required`: an account with that email exists. Sign in with its password, then use **Connect Google** on the Profile page.
- Check the backend logs for failures of the `/auth/v1/user` call (network, timeout, or invalid token).

---

## Security considerations

- Keep Supabase service-role keys out of this deployment: the backend doesn't need one, and it must never reach browsers or client code.
- The anon key is public by design (it is sent as `apikey`); the access token is what proves identity, and the backend checks it with Supabase on every exchange.
- Tokens travel in the URL fragment only, never the query string, so they are not sent to servers or leaked through `Referer`.
- Run production under HTTPS and register only `https` callback and redirect URIs.

---

## Example env additions

Backend `.env` (do not commit secrets):

```env
SUPABASE_URL=https://<project-ref>.supabase.co
SUPABASE_ANON_KEY=<supabase-anon-key>
```

Frontend `.env`:

```env
VITE_SUPABASE_URL=https://<project-ref>.supabase.co
VITE_API_URL=http://127.0.0.1:5000
```
