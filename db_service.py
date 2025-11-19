"""Repository-level shim for the web-app db_service helpers."""
from __future__ import annotations

import sys
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from types import ModuleType

WEB_APP_DIR = Path(__file__).resolve().parent / "web-app"
_REAL_DB_SERVICE_PATH = WEB_APP_DIR / "db_service.py"

if str(WEB_APP_DIR) not in sys.path:
    sys.path.insert(0, str(WEB_APP_DIR))


def _load_real_db_service() -> ModuleType:
    """Load the real db_service.py module from the web-app directory."""
    spec = spec_from_file_location("_web_app_db_service_impl", _REAL_DB_SERVICE_PATH)
    if spec is None or spec.loader is None:
        raise ImportError(
            f"Could not load web-app db_service module from {_REAL_DB_SERVICE_PATH}"
        )

    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_REAL_DB_SERVICE = _load_real_db_service()

create_mood_snapshot = getattr(_REAL_DB_SERVICE, "create_mood_snapshot")
get_snapshot_view = getattr(_REAL_DB_SERVICE, "get_snapshot_view")

__all__ = ["create_mood_snapshot", "get_snapshot_view"]
