# Self-hosted deploy (Oracle Cloud Always Free)

Docker Compose runs the backend image (gunicorn + RQ workers via supervisord) behind Caddy, which
provides automatic HTTPS. The database (Postgres + pgvector) and Redis are external services
referenced by `DATABASE_URL` and `REDIS_URL`.

## One-time setup

1. **Oracle Cloud** account, then create an Always Free VM: Ubuntu 22.04/24.04, shape
   `VM.Standard.A1.Flex` (ARM, 2 OCPU / 12 GB is plenty) or `VM.Standard.E2.1.Micro` (1 GB, too small).
   Add ingress rules for TCP 80 and 443 in the VCN security list. Save the SSH key.
2. **Hostname:** create a name (for example a free one at duckdns.org) and point it at the VM's
   public IP. It becomes `DOMAIN` below.
3. SSH in, then:
   ```bash
   git clone <repository-url> fuze && cd fuze
   cp deploy/.env.example deploy/.env   # fill it in
   bash deploy/setup-vm.sh
   ```
   When migrating an existing deployment, reuse its `SECRET_KEY` and `JWT_SECRET_KEY` (and
   `API_KEY_ENCRYPTION_KEY` if set), otherwise stored per-user API keys can't be decrypted and
   sessions end. The first build takes 10-20 minutes (torch wheels).
4. **Frontend:** build it with `VITE_API_URL=https://<DOMAIN>` and redeploy.
5. Make sure `CORS_ORIGINS` in `deploy/.env` includes the frontend's origin.
6. **Browser extension:** the default API address is `DEFAULT_API_BASE` in
   `BookmarkExtension/lib/config.js`. To use a self-hosted API without rebuilding, open the
   extension's options page and set **API URL** to `https://<DOMAIN>` (https only, no path); the
   extension asks for permission to reach that origin. The web app's sign-in handover to the
   extension is limited to `FUZE_WEB_ORIGIN` in the same file (and the matching
   `content_scripts` entry in `BookmarkExtension/manifest.json`), so a frontend served from
   another origin needs both changed in a custom build.

## Environment

`deploy/.env.example` lists every variable the compose file passes to the container
(`env_file: .env`); `DOMAIN` is also read by Caddy. Required: `DOMAIN`, `SECRET_KEY`,
`JWT_SECRET_KEY`, `DATABASE_URL` and `REDIS_URL`. Without `APP_ENV` the process runs as
production. The `LLM_*` variables switch every LLM call to an OpenAI-compatible provider; see
[`docs/OPERATIONS.md`](../docs/OPERATIONS.md).

## Update

```bash
cd fuze && git pull && sudo docker compose -f deploy/docker-compose.yml up -d --build
```

## Check

```bash
curl -s https://<DOMAIN>/health/readiness
sudo docker compose -f deploy/docker-compose.yml logs -f app
```
