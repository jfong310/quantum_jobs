from __future__ import annotations

import sys
import types


def _install_requests_stub() -> None:
    if "requests" in sys.modules:
        return

    class _DummyResponse:
        def raise_for_status(self) -> None:
            return None

        def json(self):
            return {}

    class Session:
        def get(self, *args, **kwargs):
            return _DummyResponse()

    def get(*args, **kwargs):
        return _DummyResponse()

    mod = types.ModuleType("requests")
    mod.RequestException = Exception
    mod.Session = Session
    mod.get = get
    sys.modules["requests"] = mod


def test_source_modules_share_one_normalized_job_model() -> None:
    _install_requests_stub()

    from quantum_jobs.models import NormalizedJob
    from quantum_jobs.sources.greenhouse_base import NormalizedJob as GHNormalizedJob
    from quantum_jobs.sources.lever_base import NormalizedJob as LeverNormalizedJob

    assert GHNormalizedJob is NormalizedJob
    assert LeverNormalizedJob is NormalizedJob


def test_normalized_job_identity_fields_are_explicit() -> None:
    from quantum_jobs.models import NormalizedJob

    job = NormalizedJob(
        company="IonQ",
        source="greenhouse",
        api_url="https://boards-api.greenhouse.io/v1/boards/ionq/jobs",
        job_id="123",
    )

    assert (job.company, job.job_id) == ("IonQ", "123")
    assert job.title is None
