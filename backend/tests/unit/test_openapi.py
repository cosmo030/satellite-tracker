from __future__ import annotations

import importlib.util
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "export_openapi.py"


def test_committed_openapi_spec_matches_the_application() -> None:
    spec = importlib.util.spec_from_file_location("export_openapi", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    committed = module.SPEC_PATH.read_text()

    assert committed == module.render_spec(), (
        "docs/openapi.json is out of date; run `make openapi` and commit the result"
    )
