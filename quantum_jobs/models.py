from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional


@dataclass
class NormalizedJob:
    """
    Canonical internal job model used across all source adapters.

    Identity:
    - The logical job identity is (company, job_id).

    Required fields:
    - company, source, api_url, job_id

    Optional fields:
    - title, department, location, modality, apply_url, last_modified,
      requisition_id, raw_json

    Notes:
    - `raw_json` stores the source payload for traceability.
    - Change detection compares: title, department, location, modality,
      apply_url, last_modified.
    """

    company: str
    source: str
    api_url: str
    job_id: str

    title: Optional[str] = None
    department: Optional[str] = None
    location: Optional[str] = None
    modality: Optional[str] = None
    apply_url: Optional[str] = None
    last_modified: Optional[str] = None
    requisition_id: Optional[str] = None

    raw_json: Optional[Dict[str, Any]] = None
