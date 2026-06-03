"""
Apollo.io API integration for company and people data enrichment.

Docs: https://apolloio.github.io/apollo-api-docs/
"""
import logging
from typing import Optional

import httpx

from ..config import settings

logger = logging.getLogger(__name__)

APOLLO_BASE_URL = "https://api.apollo.io/v1"


async def _post(endpoint: str, payload: dict) -> Optional[dict]:
    if not settings.APOLLO_API_KEY:
        logger.warning("APOLLO_API_KEY not configured — skipping Apollo call")
        return None

    headers = {
        "Content-Type": "application/json",
        "Cache-Control": "no-cache",
        "X-Api-Key": settings.APOLLO_API_KEY,
    }
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                f"{APOLLO_BASE_URL}/{endpoint}", json=payload, headers=headers
            )
            resp.raise_for_status()
            return resp.json()
    except httpx.HTTPStatusError as e:
        logger.error(f"Apollo API HTTP error [{endpoint}]: {e.response.status_code} {e.response.text}")
    except Exception as e:
        logger.error(f"Apollo API error [{endpoint}]: {e}")
    return None


async def _get(endpoint: str, params: dict) -> Optional[dict]:
    if not settings.APOLLO_API_KEY:
        logger.warning("APOLLO_API_KEY not configured — skipping Apollo call")
        return None

    headers = {
        "Content-Type": "application/json",
        "Cache-Control": "no-cache",
        "X-Api-Key": settings.APOLLO_API_KEY,
    }
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(
                f"{APOLLO_BASE_URL}/{endpoint}", params=params, headers=headers
            )
            resp.raise_for_status()
            return resp.json()
    except httpx.HTTPStatusError as e:
        logger.error(f"Apollo API HTTP error [{endpoint}]: {e.response.status_code} {e.response.text}")
    except Exception as e:
        logger.error(f"Apollo API error [{endpoint}]: {e}")
    return None


async def enrich_organization(domain: str) -> Optional[dict]:
    """Get enriched company data from Apollo by domain."""
    data = await _get("organizations/enrich", {"domain": domain})
    if data and "organization" in data:
        return data["organization"]
    return None


async def search_people_at_company(
    org_name: str,
    org_domain: Optional[str] = None,
    page: int = 1,
    per_page: int = 25,
) -> Optional[dict]:
    """Search for people at a specific company."""
    payload: dict = {
        "page": page,
        "per_page": per_page,
        "organization_ids": [],
        "q_organization_name": org_name,
    }
    if org_domain:
        payload["q_organization_domains"] = [org_domain]

    return await _post("people/search", payload)


async def get_recent_hires(
    org_name: str,
    org_domain: Optional[str] = None,
    days_back: int = 30,
) -> list[dict]:
    """Get people who recently joined the company (new hires detected by title/start date)."""
    data = await search_people_at_company(org_name, org_domain, per_page=50)
    if not data:
        return []

    people = data.get("people", [])
    recent = []
    for person in people:
        # Apollo includes employment_history; check most recent job
        history = person.get("employment_history", [])
        if history:
            current = next((h for h in history if h.get("current", False)), None)
            if current and current.get("organization_name", "").lower() in org_name.lower():
                recent.append({
                    "name": person.get("name", ""),
                    "title": person.get("title", ""),
                    "linkedin_url": person.get("linkedin_url", ""),
                    "start_date": current.get("start_date", ""),
                    "organization_name": org_name,
                })
    return recent


async def search_company_by_name(name: str) -> Optional[dict]:
    """Search for an organization by name."""
    payload = {
        "q_organization_name": name,
        "page": 1,
        "per_page": 1,
    }
    data = await _post("mixed_companies/search", payload)
    if data and data.get("organizations"):
        return data["organizations"][0]
    return None
