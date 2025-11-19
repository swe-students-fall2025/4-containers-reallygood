"""Repository-level shim for the web application module.

This allows tooling (pylint, tests executed from the repo root, etc.)
to import ``app`` even though the real implementation lives inside the
``web-app`` subdirectory.
"""
from __future__ import annotations

from pathlib import Path
from types import ModuleType
import sys
from importlib.util import module_from_spec, spec_from_file_location

WEB_APP_DIR = Path(__file__).resolve().parent / "web-app"
_REAL_APP_PATH = WEB_APP_DIR / "app.py"

if str(WEB_APP_DIR) not in sys.path:
    sys.path.insert(0, str(WEB_APP_DIR))


def _load_real_app() -> ModuleType:
    """Load the web-app/app.py module under a unique module name."""
    spec = spec_from_file_location("_web_app_app_impl", _REAL_APP_PATH)
    if spec is None or spec.loader is None:
        raise ImportError(f"Could not load web-app module from {_REAL_APP_PATH}")

    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_REAL_APP = _load_real_app()

# Re-export the names the tests/linting expect to exist.
create_app = getattr(_REAL_APP, "create_app")
get_db = getattr(_REAL_APP, "get_db")
get_collection = getattr(_REAL_APP, "get_collection")
create_mood_snapshot = getattr(_REAL_APP, "create_mood_snapshot")
get_snapshot_view = getattr(_REAL_APP, "get_snapshot_view")

__all__ = [
    "create_app",
    "get_db",
    "get_collection",
    "create_mood_snapshot",
    "get_snapshot_view",
]
