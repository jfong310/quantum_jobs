from __future__ import annotations

from .lever_base import LeverPostingsSource


# If you encounter a Lever org that uses a different API host (region),
# you can pass api_root=... when creating the source.
# Example:
#   LeverPostingsSource(..., api_root="https://api.eu.lever.co/v0/postings")


def rigetti_source(**kwargs) -> LeverPostingsSource:
    # Hosted jobs page: https://jobs.lever.co/rigetti
    return LeverPostingsSource(company_slug="rigetti", company="Rigetti", **kwargs)


def atomcomputing_source(**kwargs) -> LeverPostingsSource:
    # Hosted jobs page: https://jobs.lever.co/atomcomputing
    return LeverPostingsSource(company_slug="atomcomputing", company="Atom Computing", **kwargs)


def quantinuum_source(**kwargs) -> LeverPostingsSource:
    return LeverPostingsSource(
        company_slug="quantinuum",
        company="Quantinuum",
        api_root="https://api.eu.lever.co/v0/postings",
        hosted_root="https://jobs.eu.lever.co",
        **kwargs
    )


def qctrl_source(**kwargs) -> LeverPostingsSource:
    # Slug may be "q-ctrl" (hyphenated) depending on how their Lever board is configured.
    # If you get 404s, try company_slug="q-ctrl" vs "qctrl".
    return LeverPostingsSource(company_slug="q-ctrl", company="Q-CTRL", **kwargs)