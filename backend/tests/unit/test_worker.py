from __future__ import annotations

import threading

from sattrack.ingest.celestrak import CelesTrakUnavailableError
from sattrack.ingest.service import IngestReport
from sattrack.ingest.worker import run_forever


class RecordingStop(threading.Event):
    """Records requested waits instead of sleeping; stops after a number of waits."""

    def __init__(self, stop_after: int) -> None:
        super().__init__()
        self.waits_seconds: list[float] = []
        self._stop_after = stop_after

    def wait(self, timeout: float | None = None) -> bool:
        self.waits_seconds.append(timeout or 0.0)
        if len(self.waits_seconds) >= self._stop_after:
            self.set()
        return self.is_set()


class ScriptedService:
    def __init__(self, outcomes: list[Exception | None]) -> None:
        self._outcomes = outcomes
        self.runs = 0

    def run_once(self) -> IngestReport:
        outcome = self._outcomes[self.runs]
        self.runs += 1
        if outcome is not None:
            raise outcome
        return IngestReport()


def unavailable() -> CelesTrakUnavailableError:
    return CelesTrakUnavailableError("https://celestrak.test", 503, "HTTP 503")


def test_worker_waits_two_hours_between_successful_runs() -> None:
    stop = RecordingStop(stop_after=2)
    run_forever(ScriptedService([None, None]), stop)
    assert stop.waits_seconds == [7200, 7200]


def test_worker_backs_off_after_failures_and_resets_after_success() -> None:
    stop = RecordingStop(stop_after=4)
    service = ScriptedService([unavailable(), unavailable(), None, unavailable()])

    run_forever(service, stop)

    assert service.runs == 4
    assert stop.waits_seconds == [7200, 14400, 7200, 7200]


def test_worker_does_not_run_when_already_stopped() -> None:
    stop = RecordingStop(stop_after=1)
    stop.set()
    service = ScriptedService([])

    run_forever(service, stop)

    assert service.runs == 0
