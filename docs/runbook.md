# Runbook

How to deploy, check, back up and roll back Satellite Tracker. There is no staging
environment; releases are verified with `make check` in CI, a local `docker compose up`,
and the post-deployment checks below.

## Where It Runs

A single Linux host (for example a small VPS) with Docker Compose runs five services:
`db` (PostgreSQL 16), `migrate` (one-off), `api`, `ingest` and `web` (Caddy). Only `web`
is published (port 8080, or 80/443 with a domain). Logs: `docker compose logs -f <service>`.

## Deploy

1. On the host, fetch the release: `git fetch --tags && git checkout vX.Y.Z`.
2. Make sure `.env` exists with a strong `POSTGRES_PASSWORD` (never the example value).
   For HTTPS, set `SITE_ADDRESS=your.domain` and publish ports 80 and 443 for `web`
   in a `docker-compose.override.yml` instead of 8080.
3. Build and start: `docker compose up -d --build`. The `migrate` service applies database
   migrations before `api` and `ingest` start; check it with `docker compose logs migrate`.
4. Run the post-deployment checks below.

## Post-Deployment Checks

- `curl -fsS http://localhost:8080/api/v1/health` returns `"status": "ok"`.
- Within a few minutes of the first start, `data_state` becomes `ok`.
- The web page loads and shows satellites on the globe.

## Scheduled Job: Ingest Worker

`ingest` runs continuously and refreshes data every 2 hours (CelesTrak's update cycle);
SATCAT metadata refreshes daily.

| Symptom | First response |
|---|---|
| `data_state` is `stale` | `docker compose logs ingest`. "CelesTrak unavailable" means the worker is backing off (2 h, 4 h, ... up to 24 h) after a non-200 response. Do not restart it in a loop: repeated requests after errors can get the host's IP blocked by CelesTrak. Check `https://celestrak.org` from the host. |
| HTTP 403 in the log | CelesTrak is refusing the IP, often from overuse. Stop `ingest`, review `fetch_log` for request frequency, and contact CelesTrak if needed. |
| "Skipping group after unusable response" | A configured group slug is probably wrong or renamed. Fix `SATTRACK_INGEST_GROUPS`. |

Inspect recent requests:

```bash
docker compose exec db psql -U sattrack -d sattrack -c \
  "SELECT started_at, source, group_slug, status_code, succeeded FROM fetch_log ORDER BY id DESC LIMIT 20;"
```

## Restart

`docker compose restart api` or `docker compose restart ingest` is safe at any time; the
worker skips groups that were fetched less than 2 hours ago.

## Backup and Restore

All data can be downloaded again from CelesTrak except the element-set history. Back up
if you need the history:

```bash
docker compose exec db pg_dump -U sattrack -Fc sattrack > sattrack-$(date +%F).dump
docker compose exec -T db pg_restore -U sattrack -d sattrack --clean < sattrack-YYYY-MM-DD.dump
```

## Roll Back

1. `git checkout <previous tag>` and `docker compose up -d --build`.
2. If the release you are leaving added a migration, downgrade first with the new code still
   checked out: `docker compose run --rm migrate alembic downgrade -1`. Migration
   `0001` is the initial schema; downgrading it deletes all data.
