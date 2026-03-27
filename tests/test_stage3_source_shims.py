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


def test_legacy_and_package_greenhouse_factories_match() -> None:
    _install_requests_stub()

    from collectors.sources.greenhouse_companies import ionq_source as legacy_ionq_source
    from quantum_jobs.sources.greenhouse_companies import ionq_source as new_ionq_source

    legacy = legacy_ionq_source()
    new = new_ionq_source()

    assert legacy.board_token == new.board_token == "ionq"
    assert legacy.company == new.company == "IonQ"
    assert legacy.list_url == new.list_url


def test_legacy_and_package_lever_factories_match() -> None:
    _install_requests_stub()

    from collectors.sources.lever_companies import quantinuum_source as legacy_quantinuum_source
    from quantum_jobs.sources.lever_companies import quantinuum_source as new_quantinuum_source

    legacy = legacy_quantinuum_source()
    new = new_quantinuum_source()

    assert legacy.company_slug == new.company_slug == "quantinuum"
    assert legacy.api_root == new.api_root == "https://api.eu.lever.co/v0/postings"
    assert legacy.hosted_root == new.hosted_root == "https://jobs.eu.lever.co"


def test_legacy_class_aliases_new_class_definitions() -> None:
    _install_requests_stub()

    from collectors.sources.greenhouse_base import GreenhouseBoardSource as LegacyGreenhouseBoardSource
    from quantum_jobs.sources.greenhouse_base import GreenhouseBoardSource as NewGreenhouseBoardSource

    from collectors.sources.lever_base import LeverPostingsSource as LegacyLeverPostingsSource
    from quantum_jobs.sources.lever_base import LeverPostingsSource as NewLeverPostingsSource

    assert LegacyGreenhouseBoardSource is NewGreenhouseBoardSource
    assert LegacyLeverPostingsSource is NewLeverPostingsSource
