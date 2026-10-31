# 0001. Initial stack and repository structure

- **Status:** Proposed
- **Date:** 2026-10-31
- **Deciders:** cosmo030 (owner); drafted by an AI coding agent at the owner's request

## Context

The MVP needs a web UI with a 3D globe, a scheduled download of public orbital data, a
small read-only API and a database. It is a solo, open-source learning project, so the stack
should be mainstream, well documented and cheap to host on one small server.

## Decision

We will use a monorepo with two deployables:

- `backend/`: Python 3.13, FastAPI, SQLAlchemy 2.1, Alembic and PostgreSQL 16, managed with
  uv. One package, `sattrack`, organised by feature module (`catalog`, `ingest`, `health`)
  with `shared` for database and logging helpers.
- `frontend/`: React 19, TypeScript and Vite, with CesiumJS for the globe and satellite.js
  for SGP4, managed with npm.

Tooling: Ruff (format, lint, security rules), mypy strict, pytest; Prettier, ESLint
(typescript-eslint strict), Vitest. One `make check` runs everything, locally and in CI.
Deployment is Docker Compose with Caddy in front.

## Alternatives Considered

| Option | Pros | Cons | Why not chosen |
|---|---|---|---|
| Node.js backend (Fastify) | One language | Weaker orbital-maths ecosystem (Skyfield, sgp4 are Python) | Pass predictions in phase 2 need Python libraries |
| SQLite | Zero setup | Weak concurrency for worker + API; no `DISTINCT ON`, JSONB | PostgreSQL is free and runs in Compose |
| three.js / globe.gl | Smaller bundle | No geospatial frames, time or imagery out of the box | CesiumJS is built for exactly this |
| Separate repositories | Independent releases | Two pipelines, harder for contributors | Unnecessary for one maintainer |

## Consequences

- **Positive:** Mature, popular tools; strong typing on both sides; one command to verify.
- **Negative:** CesiumJS adds about 1.1 MB (gzipped) to the frontend bundle.
- **Follow-up:** Revisit hosting when traffic grows; add PostGIS only if spatial queries appear.

## Security and Data Considerations

Only public orbital data is stored. No user accounts or personal data.
