"""Helpers to keep pylint happy when optional deps are missing."""
from __future__ import annotations

import sys
from importlib import import_module
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Tuple

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def get_pytest():
    """Return pytest if available, otherwise a minimal stub."""

    class _PytestStub(SimpleNamespace):  # pylint: disable=too-few-public-methods
        """Provides a fixture decorator that returns the original function."""

        def fixture(self, func=None, **_kwargs):  # pragma: no cover
            """Return identity decorator used by pylintrc fallback."""

            def decorator(fn):
                return fn

            if func is None:
                return decorator
            return decorator(func)

    try:
        import pytest  # pylint: disable=import-outside-toplevel

        return pytest
    except ImportError:  # pragma: no cover
        return _PytestStub()


def _import_with_stub(module_name: str) -> Any:
    """Import module or return stub namespace."""

    class _Stub(SimpleNamespace):  # pylint: disable=too-few-public-methods
        """Fallback object raising runtime errors when accessed."""

        def __getattr__(self, name):  # pragma: no cover
            raise RuntimeError(f"Stub for {module_name} lacks attribute '{name}'")

    try:
        return import_module(module_name)
    except ImportError:  # pragma: no cover
        return _Stub()


def import_app_modules() -> Tuple[Any, Any]:
    """Return ``(app_module, create_app)`` with stub fallback."""

    module = _import_with_stub("app")

    def _create_app_stub():  # pragma: no cover
        raise RuntimeError("create_app stub used")

    create_app = getattr(module, "create_app", _create_app_stub)
    return module, create_app


def import_db_module():
    """Return db module with stub fallback."""

    return _import_with_stub("db")


def import_db_service_module():
    """Return db_service module with stub fallback."""

    return _import_with_stub("db_service")
