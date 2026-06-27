# Deploy on Arvan Cloud (VPS)

Dev locally stays the same:

```bash
cp docker-compose.example.yml docker-compose.yml
cp .env.example .env
docker compose up --build
```

Production uses a separate compose file and env — dev files are untouched.

---

## 1. Buy VPS (Abraak)

- Ubuntu 22.04 LTS
- Minimum: 2 vCPU / 4 GB RAM
- Open firewall ports: **22, 80, 443** (not 5432 / 6379)

## 2. Server setup

```bash
ssh root@YOUR_SERVER_IP

apt update && apt upgrade -y
apt install -y git curl ufw nginx certbot python3-certbot-nginx
curl -fsSL https://get.docker.com | sh
apt install -y docker-compose-plugin

ufw allow OpenSSH
ufw allow 80
ufw allow 443
ufw enable
```

## 3. Clone project

```bash
mkdir -p /var/www
cd /var/www
git clone https://github.com/avahmh/event-ticketing-api.git
cd event-ticketing-api
```

## 4. Production env

```bash
cp deploy/.env.production.example .env
nano .env
```

Set at least:

- `SECRET_KEY` — long random string
- `POSTGRES_PASSWORD` — strong password
- `DJANGO_ALLOWED_HOSTS` — domain + server IP
- `CSRF_TRUSTED_ORIGINS` — `https://your-domain.com`

## 5. Start stack

```bash
docker compose -f docker-compose.prod.yml up -d --build
docker compose -f docker-compose.prod.yml ps
docker compose -f docker-compose.prod.yml logs -f web
```

First boot runs `migrate` and `collectstatic` automatically.

## 6. Demo data + admin user

```bash
docker compose -f docker-compose.prod.yml exec web python manage.py seed_teatrshahr
docker compose -f docker-compose.prod.yml exec web python manage.py createsuperuser
```

## 7. Nginx

```bash
cp deploy/nginx.conf /etc/nginx/sites-available/ticketing
nano /etc/nginx/sites-available/ticketing   # fix server_name and paths
ln -s /etc/nginx/sites-available/ticketing /etc/nginx/sites-enabled/
nginx -t && systemctl reload nginx
```

## 8. HTTPS

```bash
certbot --nginx -d your-domain.com -d www.your-domain.com
```

## 9. DNS (Arvan panel)

```
A    @      YOUR_SERVER_IP
A    www    YOUR_SERVER_IP
```

## 10. Verify

| URL | What |
|-----|------|
| `/` | Frontend homepage |
| `/admin/` | Django admin |
| `/events/` | Events API |
| Reserve a seat | Redis + Celery must be running |

Check workers:

```bash
docker compose -f docker-compose.prod.yml logs celery
docker compose -f docker-compose.prod.yml logs celery_beat
```

## Update after code changes

```bash
cd /var/www/event-ticketing-api
git pull
docker compose -f docker-compose.prod.yml up -d --build
```

## File map

| File | Purpose |
|------|---------|
| `docker-compose.example.yml` | Local dev (runserver) |
| `docker-compose.debug.example.yml` | Local dev + debugpy |
| `docker-compose.prod.yml` | Production (gunicorn + Celery) |
| `Dockerfile.example` | Dev image |
| `Dockerfile.prod` | Production image |
| `deploy/.env.production.example` | Production env template |
| `deploy/nginx.conf` | Nginx reverse proxy |
| `deploy/docker-entrypoint.sh` | migrate + collectstatic on web start |

## Dev vs production

| | Dev | Production |
|--|-----|------------|
| Compose | `docker-compose.yml` (from example) | `docker-compose.prod.yml` |
| Server | `runserver` | `gunicorn` |
| DEBUG | `True` (default) | `False` in `.env` |
| Static | Django dev server | WhiteNoise + Nginx |
| Media | Django when DEBUG | Nginx `/media/` |
| DB/Redis ports | exposed on host | internal only |
