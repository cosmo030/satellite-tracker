# sattrack (backend)

FastAPI API and CelesTrak ingest worker for Satellite Tracker. See the
[project README](../README.md) for setup and the [architecture](../docs/architecture.md)
for how the modules fit together.

| Entry point | Command |
|---|---|
| API | `uvicorn sattrack.main:create_app --factory` |
| Ingest worker | `python -m sattrack.ingest` (add `--once` for a single run) |
| Migrations | `alembic upgrade head` |
