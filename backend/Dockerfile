# Backend image: runs the API (default), the ingest worker or migrations.
# Build: docker build -t satellite-tracker-backend backend/

FROM python:3.13-slim-bookworm AS build
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy UV_PYTHON_DOWNLOADS=never
RUN pip install --no-cache-dir uv==0.11.32
WORKDIR /app
COPY pyproject.toml uv.lock README.md ./
RUN uv sync --locked --no-dev --no-install-project
COPY src ./src
RUN uv sync --locked --no-dev

FROM python:3.13-slim-bookworm AS runtime
RUN useradd --system --uid 10001 --no-create-home sattrack
WORKDIR /app
COPY --from=build /app/.venv ./.venv
COPY --from=build /app/src ./src
COPY alembic.ini ./
COPY alembic ./alembic
ENV PATH="/app/.venv/bin:${PATH}" PYTHONUNBUFFERED=1
USER sattrack
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD ["python", "-c", "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/api/v1/health', timeout=4).status == 200 else 1)"]
CMD ["uvicorn", "sattrack.main:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers"]
