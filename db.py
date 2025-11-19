"""Repository-level shim for the web-app database helpers."""
from __future__ import annotations

import sys
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from types import ModuleType

WEB_APP_DIR = Path(__file__).resolve().parent / "web-app"
_REAL_DB_PATH = WEB_APP_DIR / "db.py"

if str(WEB_APP_DIR) not in sys.path:
    sys.path.insert(0, str(WEB_APP_DIR))


def _load_real_db() -> ModuleType:
    """Load the real db.py module from the web-app directory."""
    spec = spec_from_file_location("_web_app_db_impl", _REAL_DB_PATH)
    if spec is None or spec.loader is None:
        raise ImportError(f"Could not load web-app db module from {_REAL_DB_PATH}")

    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_REAL_DB = _load_real_db()

get_db = getattr(_REAL_DB, "get_db")
get_collection = getattr(_REAL_DB, "get_collection")

__all__ = ["get_db", "get_collection"]
