"""Fixtures compartidas por toda la suite de tests del backend."""

from __future__ import annotations

import pytest

from designfabric.core.progress import ProgressEvent


class FakeProgressReporter:
    """Reporter de progreso que solo acumula eventos, para poder hacer `assert` sobre ellos."""

    def __init__(self) -> None:
        self.events: list[ProgressEvent] = []

    def emit(self, event: ProgressEvent) -> None:
        self.events.append(event)


@pytest.fixture
def fake_reporter() -> FakeProgressReporter:
    return FakeProgressReporter()
