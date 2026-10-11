"""Session cleanup so neatlogs does not log after pytest has closed its streams."""

import pytest


@pytest.fixture(scope="session", autouse=True)
def _close_tracing():
    yield
    try:
        import neatlogs

        neatlogs.shutdown()
    except Exception:
        pass
