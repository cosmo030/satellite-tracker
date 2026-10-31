"""Write the API's OpenAPI specification to docs/openapi.json (run via `make openapi`)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

from sattrack.config import Settings
from sattrack.main import create_app

SPEC_PATH = Path(__file__).resolve().parents[2] / "docs" / "openapi.json"
# Building the app does not connect to the database; any syntactically valid URL works.
PLACEHOLDER_DATABASE_URL = "postgresql+psycopg://user:password-not-real@localhost:5432/unused"


def render_spec() -> str:
    settings = Settings(database_url=PLACEHOLDER_DATABASE_URL)
    return json.dumps(create_app(settings).openapi(), indent=2, sort_keys=True) + "\n"


def main() -> int:
    SPEC_PATH.write_text(render_spec())
    sys.stdout.write(f"Wrote {SPEC_PATH}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
