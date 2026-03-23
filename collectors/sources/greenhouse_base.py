from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any, Dict, Iterable, List, Optional
import time

import requests


@dataclass
class NormalizedJob:
    # Keep these aligned with your DB writer / snapshot schema
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


class GreenhouseBoardSource:
    """
    Reusable adapter for Greenhouse 'boards-api' endpoints.

    List endpoint:
      https://boards-api.greenhouse.io/v1/boards/{board_token}/jobs

    Detail endpoint (optional):
      https://boards-api.greenhouse.io/v1/boards/{board_token}/jobs/{job_id}

    Notes:
    - No auth required.
    - The list endpoint usually includes: id, title, absolute_url, updated_at, location, metadata.
    - Some fields (e.g. description) require the detail endpoint.
    """

    GH_ROOT = "https://boards-api.greenhouse.io/v1/boards"

    def __init__(
        self,
        *,
        board_token: str,
        company: str,
        source_name: str = "greenhouse",
        timeout_s: int = 30,
        use_detail_endpoint: bool = False,
        detail_rate_limit_s: float = 0.0,
        session: Optional[requests.Session] = None,
    ) -> None:
        self.board_token = board_token
        self.company = company
        self.source_name = source_name
        self.timeout_s = timeout_s
        self.use_detail_endpoint = use_detail_endpoint
        self.detail_rate_limit_s = detail_rate_limit_s
        self.session = session or requests.Session()

        self.list_url = f"{self.GH_ROOT}/{self.board_token}/jobs"

    def fetch(self) -> List[NormalizedJob]:
        payload = self._get_json(self.list_url)

        jobs = payload.get("jobs", [])
        if not isinstance(jobs, list):
            return []

        normalized: List[NormalizedJob] = []

        for j in jobs:
            if not isinstance(j, dict):
                continue

            job_id = j.get("id")
            if job_id is None:
                continue

            job_dict = j

            if self.use_detail_endpoint:
                # Pull richer fields, but guard for rate limits and individual failures.
                detail_url = f"{self.GH_ROOT}/{self.board_token}/jobs/{job_id}"
                try:
                    if self.detail_rate_limit_s > 0:
                        time.sleep(self.detail_rate_limit_s)
                    detail = self._get_json(detail_url)
                    if isinstance(detail, dict):
                        # Merge detail into list-level dict; detail wins on conflicts.
                        job_dict = {**j, **detail}
                except requests.RequestException:
                    # Don’t fail the entire run if one detail fetch fails.
                    job_dict = j

            nj = self._normalize(job_dict)
            if nj is not None:
                normalized.append(nj)

        return normalized

    def fetch_as_dicts(self) -> List[Dict[str, Any]]:
        """Convenience helper if your DB writer expects dicts."""
        return [asdict(j) for j in self.fetch()]

    # -------------------------
    # Normalization
    # -------------------------

    def _normalize(self, j: Dict[str, Any]) -> Optional[NormalizedJob]:
        job_id = j.get("id")
        if job_id is None:
            return None

        title = self._get_str(j, "title")
        apply_url = self._get_str(j, "absolute_url") or self._get_str(j, "url")
        last_modified = self._get_str(j, "updated_at")

        # location is usually {"name": "..."}
        location = None
        loc = j.get("location")
        if isinstance(loc, dict):
            location = self._get_str(loc, "name")
        elif isinstance(loc, str):
            location = loc

        # department often is in metadata list like [{"name":"Department","value":"Engineering"}]
        department = self._extract_metadata_value(j.get("metadata"), "Department")

        # modality is not always provided by Greenhouse; sometimes in metadata under "Workplace Type"
        modality = (
            self._extract_metadata_value(j.get("metadata"), "Workplace Type")
            or self._extract_metadata_value(j.get("metadata"), "Workplace type")
            or self._extract_metadata_value(j.get("metadata"), "Workplace")
            or None
        )

        requisition_id = (
            self._extract_metadata_value(j.get("metadata"), "Requisition ID")
            or self._extract_metadata_value(j.get("metadata"), "Requisition Id")
            or None
        )

        return NormalizedJob(
            company=self.company,
            source=self.source_name,
            api_url=self.list_url,
            job_id=str(job_id),
            title=title,
            department=department,
            location=location,
            modality=modality,
            apply_url=apply_url,
            last_modified=last_modified,
            requisition_id=requisition_id,
            raw_json=j,
        )

    def _extract_metadata_value(self, metadata: Any, name: str) -> Optional[str]:
        if not isinstance(metadata, list):
            return None
        for m in metadata:
            if not isinstance(m, dict):
                continue
            if m.get("name") == name:
                v = m.get("value")
                if isinstance(v, str) and v.strip():
                    return v.strip()
                if isinstance(v, (int, float)):
                    return str(v)
        return None

    def _get_str(self, d: Dict[str, Any], key: str) -> Optional[str]:
        v = d.get(key)
        if v is None:
            return None
        if isinstance(v, str):
            s = v.strip()
            return s if s else None
        if isinstance(v, (int, float)):
            return str(v)
        return None

    def _get_json(self, url: str) -> Dict[str, Any]:
        headers = {
            "Accept": "application/json",
            "User-Agent": "quantum-jobs-collector/1.0",
        }
        r = self.session.get(url, headers=headers, timeout=self.timeout_s)
        r.raise_for_status()
        data = r.json()
        # The list endpoint is always a dict with "jobs"
        return data if isinstance(data, dict) else {}