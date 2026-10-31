# Configuration Reference

All configuration comes from environment variables. The backend validates them at startup
and exits with an error naming the variable when one is missing or invalid. Locally, the
Makefile and `docker compose` load them from `.env` (copy [.env.example](../.env.example)).

## Backend

| Name | Purpose | Required | Default | Example | Secret |
|---|---|---|---|---|---|
| `SATTRACK_DATABASE_URL` | PostgreSQL URL for the API, worker and migrations | Yes | — | `postgresql+psycopg://sattrack:<password>@localhost:5432/sattrack` | Yes (contains the password) |
| `SATTRACK_LOG_LEVEL` | `DEBUG`, `INFO`, `WARNING` or `ERROR` | No | `INFO` | `DEBUG` | No |
| `SATTRACK_INGEST_GROUPS` | Comma-separated CelesTrak group slugs to ingest | No | `stations,visual,gps-ops,galileo,weather,science` | `stations,starlink` | No |
| `SATTRACK_HTTP_TIMEOUT_SECONDS` | Timeout per CelesTrak request, seconds (0–300) | No | `30` | `10` | No |
| `SATTRACK_CELESTRAK_BASE_URL` | CelesTrak base URL; must use `https://` | No | `https://celestrak.org` | `https://celestrak.org` | No |
| `SATTRACK_CORS_ALLOWED_ORIGINS` | Comma-separated origins allowed to call the API from a browser | No | none (same origin only) | `https://tracker.example.com` | No |
| `SATTRACK_TEST_DATABASE_URL` | Disposable database for integration tests; tables are emptied | Tests only | — (tests skipped) | `postgresql+psycopg://sattrack:<password>@localhost:5432/sattrack_test` | Yes |

Large groups such as `active` and `starlink` work but are big downloads; CelesTrak enforces
limits on them, so add them deliberately.

## Docker Compose

| Name | Purpose | Required | Default | Example | Secret |
|---|---|---|---|---|---|
| `POSTGRES_PASSWORD` | Password of the `sattrack` database user; also used to build the containers' database URL | Yes | — | `<CHOOSE_A_LOCAL_PASSWORD>` | Yes |
| `SITE_ADDRESS` | Address Caddy serves on. A domain name enables automatic HTTPS (publish ports 80/443) | No | `:8080` | `tracker.example.com` | No |

## Frontend

| Name | Purpose | Required | Default | Example | Secret |
|---|---|---|---|---|---|
| `SATTRACK_API_PROXY_TARGET` | Where `npm run dev` forwards `/api` | No | `http://localhost:8000` | `http://localhost:8001` | No |

The built frontend has no runtime configuration: it always calls `/api/v1` on its own origin.
