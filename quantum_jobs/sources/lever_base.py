from __future__ import annotations

from dataclasses import asdict
from typing import Any, Dict, List, Optional
from urllib.parse import urlencode

import requests
from quantum_jobs.models import NormalizedJob


class LeverPostingsSource:
    """
    Reusable adapter for Lever's public Postings API (unauthenticated).

    Typical list endpoint:
      https://api.lever.co/v0/postings/{company_slug}?mode=json

    Some orgs may use a different Lever region host; this class lets you override api_root.

    Notes:
    - This is for *public postings* (what shows on jobs.lever.co), not Lever's authenticated core API.
    - Payload shape is generally a JSON list of postings (dicts).
    """

    DEFAULT_API_ROOT = "https://api.lever.co/v0/postings"
    DEFAULT_HOSTED_ROOT = "https://jobs.lever.co"

    def __init__(
        self,
        *,
        company_slug: str,
        company: str,
        source_name: str = "lever",
        timeout_s: int = 30,
        api_root: str = DEFAULT_API_ROOT,
        hosted_root: str = DEFAULT_HOSTED_ROOT,
        session: Optional[requests.Session] = None,
        mode_json: bool = True,
    ) -> None:
        self.company_slug = company_slug
        self.company = company
        self.source_name = source_name
        self.timeout_s = timeout_s
        self.api_root = api_root.rstrip("/")
        self.hosted_root = hosted_root.rstrip("/")
        self.session = session or requests.Session()
        self.mode_json = mode_json

        base = f"{self.api_root}/{self.company_slug}"
        if self.mode_json:
            self.list_url = f"{base}?{urlencode({'mode': 'json'})}"
        else:
            self.list_url = base

    def fetch(self) -> List[NormalizedJob]:
        payload = self._get_json(self.list_url)

        if not isinstance(payload, list):
            # Defensive: some misconfigured endpoints might return dict; treat as empty.
            return []

        out: List[NormalizedJob] = []
        for p in payload:
            if not isinstance(p, dict):
                continue
            nj = self._normalize(p)
            if nj is not None:
                out.append(nj)
        return out

    def fetch_as_dicts(self) -> List[Dict[str, Any]]:
        """Convenience helper if your DB writer expects dicts."""
        return [asdict(j) for j in self.fetch()]

    # -------------------------
    # Normalization
    # -------------------------

    def _normalize(self, p: Dict[str, Any]) -> Optional[NormalizedJob]:
        # Lever postings almost always have 'id'
        job_id = p.get("id") or p.get("postingId") or p.get("posting_id")
        if job_id is None:
            return None

        title = self._get_str(p, "text") or self._get_str(p, "title")

        # Lever uses categories for many fields: team, location, commitment, department, etc.
        categories = p.get("categories")
        dept = None
        loc = None
        modality = None  # Lever doesn't have a consistent "remote/hybrid/onsite" field across orgs

        if isinstance(categories, dict):
            # Common: team, location, commitment
            dept = self._get_str(categories, "team") or self._get_str(categories, "department")
            loc = self._get_str(categories, "location")

            # Some orgs encode workplace type / remote-ness in custom category names;
            # you can extend this later if you observe consistent keys.
            modality = (
                self._get_str(categories, "workplaceType")
                or self._get_str(categories, "workplace_type")
                or self._get_str(categories, "workplace")
            )

        # Apply URL: some payloads include hostedUrl; otherwise construct the standard one.
        apply_url = (
            self._get_str(p, "hostedUrl")
            or self._get_str(p, "hosted_url")
            or f"{self.hosted_root}/{self.company_slug}/{job_id}"
        )

        # Updated time varies; keep as string if present (could be epoch ms or ISO).
        # You can standardize later if desired.
        last_modified = (
            self._to_time_str(p.get("updatedAt"))
            or self._to_time_str(p.get("updated_at"))
            or self._to_time_str(p.get("lastModified"))
            or self._to_time_str(p.get("last_modified"))
        )

        # Requisition IDs are not consistently present in public postings; sometimes in customFields.
        requisition_id = None
        custom_fields = p.get("customFields") or p.get("custom_fields")
        if isinstance(custom_fields, dict):
            # Try a few likely keys. Adjust if you observe a standard in your dataset.
            for k in ("requisitionId", "requisition_id", "reqId", "req_id", "requisition"):
                if k in custom_fields:
                    requisition_id = self._get_str(custom_fields, k)
                    if requisition_id:
                        break

        return NormalizedJob(
            company=self.company,
            source=self.source_name,
            api_url=self.list_url,
            job_id=str(job_id),
            title=title,
            department=dept,
            location=loc,
            modality=modality,
            apply_url=apply_url,
            last_modified=last_modified,
            requisition_id=requisition_id,
            raw_json=p,
        )

    # -------------------------
    # Helpers
    # -------------------------

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

    def _to_time_str(self, v: Any) -> Optional[str]:
        # Keep it simple: preserve ISO strings; stringify ints (epoch millis) as-is.
        if v is None:
            return None
        if isinstance(v, str):
            s = v.strip()
            return s if s else None
        if isinstance(v, (int, float)):
            # Likely epoch millis; keeping as string maintains fidelity w/out forcing a timezone choice.
            return str(int(v))
        return None

    def _get_json(self, url: str) -> Any:
        headers = {
            "Accept": "application/json",
            "User-Agent": "quantum-jobs-collector/1.0",
        }
        r = self.session.get(url, headers=headers, timeout=self.timeout_s)
        r.raise_for_status()
        return r.json()
