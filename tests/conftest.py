import sys
import types
from pathlib import Path

# Ensure the repository root is importable as a module path for tests
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


class _DummyResponse:
    def __init__(self, status_code: int = 200, payload: dict | None = None):
        self.status_code = status_code
        self._payload = payload or {}

    def json(self):  # pragma: no cover - not used in tests
        return self._payload

    def raise_for_status(self):
        if self.status_code >= 400:
            raise HTTPError(f"HTTP {self.status_code}")


class HTTPError(RuntimeError):
    """Minimal HTTPError replacement for tests."""


def _not_implemented(*args, **kwargs):  # pragma: no cover - sanity guard
    raise RuntimeError("Network calls are disabled in the test environment")


requests_stub = types.ModuleType("requests")
requests_stub.HTTPError = HTTPError
requests_stub.get = _not_implemented
requests_stub.post = _not_implemented
requests_stub.Response = _DummyResponse
sys.modules.setdefault("requests", requests_stub)

