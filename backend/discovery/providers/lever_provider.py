"""
Lever Postings API Provider.
Fetches public job postings directly from Lever API.
Endpoint: https://api.lever.co/v0/postings/{site}?mode=json
"""

from typing import Any, Dict, List, Optional

from discovery.discovery_logger import get_logger
from discovery.providers.base_provider import (
    BaseJobProvider,
    DiscoveredJobData,
    ProviderNotFoundError,
    ProviderAccessDeniedError,
)

logger = get_logger("lever_provider")


class LeverProvider(BaseJobProvider):
    """Integrates with the official Lever Public Postings API."""

    BASE_URL = "https://api.lever.co/v0/postings"

    def __init__(self, **kwargs):
        super().__init__(name="lever", **kwargs)

    async def is_available(self) -> bool:
        # Lever public postings API requires no auth token
        return True

    async def discover_jobs(
        self,
        identifier: str,
        company_name: Optional[str] = None,
        source_url: Optional[str] = None,
    ) -> List[DiscoveredJobData]:
        """
        Discovers jobs for a given Lever site identifier.
        :param identifier: Lever site slug (e.g. 'netflix', 'atlassian').
        :param company_name: Name of company.
        :param source_url: Original career source URL.
        :return: List of standardized DiscoveredJobData.
        """
        site = identifier.strip().lower()
        if not site:
            return []

        url = f"{self.BASE_URL}/{site}"
        params = {"mode": "json"}

        try:
            logger.info(
                f"[Lever] Fetching postings for site '{site}' (Company: {company_name or 'Unknown'})"
            )
            response = await self.execute_request_with_retry(url=url, params=params)
            data = response.json()

            # Lever returns a list of postings directly
            if not isinstance(data, list):
                logger.warning(f"[Lever] Expected list of postings from {url}, got {type(data)}")
                return []

            discovered_jobs: List[DiscoveredJobData] = []

            for item in data:
                if not isinstance(item, dict):
                    continue

                job_id = str(item.get("id", ""))
                title = item.get("text", "").strip()
                if not job_id or not title:
                    continue

                categories = item.get("categories") or {}
                location_name = categories.get("location") or categories.get("workplaceType")
                department_name = categories.get("department") or categories.get("team")

                hosted_url = item.get("hostedUrl") or f"https://jobs.lever.co/{site}/{job_id}"
                apply_url = item.get("applyUrl") or hosted_url

                discovered_jobs.append(
                    DiscoveredJobData(
                        provider="lever",
                        external_job_id=job_id,
                        title=title,
                        location=location_name,
                        department=department_name,
                        job_url=hosted_url,
                        application_url=apply_url,
                        source_url=source_url or url,
                        raw_payload=dict(item, site=site),
                        extra_metadata={
                            "site": site,
                            "company_name": company_name,
                        },
                    )
                )

            logger.info(
                f"[Lever] Successfully retrieved {len(discovered_jobs)} postings for site '{site}'"
            )
            return discovered_jobs

        except ProviderNotFoundError:
            logger.info(f"[Lever] Site '{site}' not found or has no active public postings.")
            return []
        except ProviderAccessDeniedError:
            logger.warning(f"[Lever] Access denied for site '{site}'.")
            return []
        except Exception as exc:
            logger.error(f"[Lever] Error fetching postings for site '{site}': {exc}", exc_info=True)
            return []

