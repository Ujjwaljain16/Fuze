# Self-hosted deploy (free: Oracle Cloud Always Free)

Docker Compose runs the backend image (gunicorn + RQ workers via supervisord) behind Caddy, which
provides automatic HTTPS. Database stays on Supabase and Redis on Upstash.

## One-time setup

1. **Oracle Cloud** account, then create an Always Free VM: Ubuntu 22.04/24.04, shape
   `VM.Standard.A1.Flex` (ARM, 2 OCPU / 12 GB is plenty) or `VM.Standard.E2.1.Micro` (1 GB, too small).
   Add ingress rules for TCP 80 and 443 in the VCN security list. Save the SSH key.
2. **Free hostname:** create a name at duckdns.org and point it at the VM's public IP.
3. SSH in, then:
   ```bash
   git clone https://github.com/Ujjwaljain16/Fuze.git && cd Fuze
   cp deploy/.env.example deploy/.env   # fill it in; reuse the SAME SECRET_KEY / JWT_SECRET_KEY as before
   bash deploy/setup-vm.sh
   ```
   The first build takes 10-20 minutes (torch wheels).
4. **Vercel:** set `VITE_API_URL=https://<your-name>.duckdns.org`, redeploy the frontend.
5. Make sure `CORS_ORIGINS` in `deploy/.env` includes the Vercel domain.
6. Update the Chrome extension's default API URL (`background.js`, `popup/popup.js`).

## Update

```bash
cd Fuze && git pull && sudo docker compose -f deploy/docker-compose.yml up -d --build
```

## Check

```bash
curl -s https://<your-name>.duckdns.org/health/readiness
sudo docker compose -f deploy/docker-compose.yml logs -f app
```
