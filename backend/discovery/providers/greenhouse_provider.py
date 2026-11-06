"""
Greenhouse Job Board API Provider.
Fetches public job postings directly from Greenhouse Boards API.
Endpoint: https://boards-api.greenhouse.io/v1/boards/{board_token}/jobs?content=true
"""

from typing import Any, Dict, List, Optional

from discovery.discovery_logger import get_logger
from discovery.providers.base_provider import (
    BaseJobProvider,
    DiscoveredJobData,
    ProviderNotFoundError,
    ProviderAccessDeniedError,
    ProviderException,
)

logger = get_logger("greenhouse_provider")


class GreenhouseProvider(BaseJobProvider):
    """Integrates with the official Greenhouse Public Job Board API."""

    BASE_URL = "https://boards-api.greenhouse.io/v1/boards"

    def __init__(self, **kwargs):
        super().__init__(name="greenhouse", **kwargs)

    async def is_available(self) -> bool:
        # Greenhouse public API requires no authentication token
        return True

    async def discover_jobs(
        self,
        identifier: str,
        company_name: Optional[str] = None,
        source_url: Optional[str] = None,
    ) -> List[DiscoveredJobData]:
        """
        Discovers jobs for a given Greenhouse board token.
        :param identifier: Greenhouse board token (e.g. 'stripe', 'airbnb').
        :param company_name: Name of company for logging/context.
        :param source_url: Original career source URL.
        :return: List of standardized DiscoveredJobData.
        """
        board_token = identifier.strip().lower()
        if not board_token:
            return []

        url = f"{self.BASE_URL}/{board_token}/jobs"
        params = {"content": "true"}

        try:
            logger.info(
                f"[Greenhouse] Fetching jobs for board '{board_token}' (Company: {company_name or 'Unknown'})"
            )
            response = await self.execute_request_with_retry(url=url, params=params)
            data = response.json()

            jobs_raw = data.get("jobs", [])
            discovered_jobs: List[DiscoveredJobData] = []

            for item in jobs_raw:
                job_id = str(item.get("id", ""))
                title = item.get("title", "").strip()
                if not job_id or not title:
                    continue

                location_dict = item.get("location") or {}
                location_name = location_dict.get("name") if isinstance(location_dict, dict) else str(location_dict)

                departments = item.get("departments") or []
                department_name = departments[0].get("name") if departments and isinstance(departments[0], dict) else None

                job_url = item.get("absolute_url") or f"https://boards.greenhouse.io/{board_token}/jobs/{job_id}"

                discovered_jobs.append(
                    DiscoveredJobData(
                        provider="greenhouse",
                        external_job_id=job_id,
                        title=title,
                        location=location_name,
                        department=department_name,
                        job_url=job_url,
                        application_url=job_url,
                        source_url=source_url or url,
                        raw_payload=dict(item, board_token=board_token),
                        extra_metadata={
                            "board_token": board_token,
                            "company_name": company_name,
                        },
                    )
                )

            logger.info(
                f"[Greenhouse] Successfully retrieved {len(discovered_jobs)} jobs for board '{board_token}'"
            )
            return discovered_jobs

        except ProviderNotFoundError:
            logger.info(f"[Greenhouse] Board token '{board_token}' does not exist or has no active public board.")
            return []
        except ProviderAccessDeniedError:
            logger.warning(f"[Greenhouse] Access denied for board '{board_token}'.")
            return []
        except Exception as exc:
            logger.error(f"[Greenhouse] Error fetching jobs for '{board_token}': {exc}", exc_info=True)
            return []

