"""
Base Job Provider Module.
Defines the standard data structures, base provider class, rate limiter,
and exception types for all job discovery providers.
"""

import asyncio
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
import httpx

from discovery.discovery_config import discovery_settings
from discovery.discovery_logger import get_logger

logger = get_logger("base_provider")


@dataclass
class DiscoveredJobData:
    """Standardized job representation across all discovery sources."""
    provider: str
    external_job_id: str
    title: str
    location: Optional[str] = None
    department: Optional[str] = None
    job_url: str = ""
    application_url: Optional[str] = None
    source_url: str = ""
    raw_payload: Optional[Dict[str, Any]] = field(default_factory=dict)
    extra_metadata: Optional[Dict[str, Any]] = field(default_factory=dict)


class ProviderException(Exception):
    """Base exception for provider errors."""
    pass


class ProviderNotFoundError(ProviderException):
    """HTTP 404: Board/Site not found or disabled."""
    pass


class ProviderAccessDeniedError(ProviderException):
    """HTTP 403: Forbidden or bot-blocked."""
    pass


class ProviderRateLimitError(ProviderException):
    """HTTP 429: Too many requests."""
    pass


class ProviderServerError(ProviderException):
    """HTTP 5xx: Target server error."""
    pass


class TokenBucketRateLimiter:
    """Asynchronous rate limiter based on leaky/token bucket algorithm."""

    def __init__(self, rate: float):
        """
        :param rate: Allowed requests per second (e.g. 5.0 = 5 req/sec).
        """
        self.rate = max(0.1, rate)
        self.interval = 1.0 / self.rate
        self.last_check = 0.0
        self._lock: Optional[asyncio.Lock] = None

    async def acquire(self):
        if self._lock is None:
            self._lock = asyncio.Lock()
        async with self._lock:
            now = time.monotonic()
            if self.last_check > 0.0:
                elapsed = now - self.last_check
                if elapsed < self.interval:
                    await asyncio.sleep(self.interval - elapsed)
            self.last_check = time.monotonic()


class BaseJobProvider(ABC):
    """
    Abstract base provider providing retry logic, concurrency control,
    rate limiting, and standardized error handling.
    """

    def __init__(
        self,
        name: str,
        rate_limit: Optional[float] = None,
        max_concurrency: Optional[int] = None,
        timeout: Optional[float] = None,
        retry_limit: Optional[int] = None,
    ):
        self.name = name
        self.rate_limit = rate_limit or discovery_settings.DISCOVERY_RATE_LIMIT
        self.max_concurrency = max_concurrency or discovery_settings.DISCOVERY_MAX_CONCURRENCY
        self.timeout = timeout or discovery_settings.DISCOVERY_REQUEST_TIMEOUT
        self.retry_limit = retry_limit or discovery_settings.DISCOVERY_RETRY_LIMIT

        self._rate_limiter = TokenBucketRateLimiter(self.rate_limit)
        self._semaphore: Optional[asyncio.Semaphore] = None
        self._client: Optional[httpx.AsyncClient] = None

    @property
    def semaphore(self) -> asyncio.Semaphore:
        if self._semaphore is None:
            self._semaphore = asyncio.Semaphore(self.max_concurrency)
        return self._semaphore

    async def get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            headers = {
                "User-Agent": discovery_settings.DISCOVERY_USER_AGENT,
                "Accept": "application/json, text/plain, */*",
            }
            self._client = httpx.AsyncClient(
                headers=headers,
                timeout=httpx.Timeout(self.timeout, connect=10.0),
                follow_redirects=True,
            )
        return self._client

    async def close(self):
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None

    async def execute_request_with_retry(
        self,
        url: str,
        method: str = "GET",
        headers: Optional[Dict[str, str]] = None,
        params: Optional[Dict[str, Any]] = None,
        json_data: Optional[Dict[str, Any]] = None,
    ) -> httpx.Response:
        """
        Executes HTTP requests under semaphore and rate-limiter with exponential backoff retries.
        Distinguishes 403, 404, 429, and 5xx.
        """
        client = await self.get_client()

        for attempt in range(1, self.retry_limit + 1):
            async with self.semaphore:
                await self._rate_limiter.acquire()
                try:
                    logger.debug(
                        f"[{self.name}] HTTP {method} {url} (attempt {attempt}/{self.retry_limit})"
                    )
                    response = await client.request(
                        method=method,
                        url=url,
                        headers=headers,
                        params=params,
                        json=json_data,
                    )

                    # Distinct HTTP status checks
                    if response.status_code == 200:
                        return response
                    elif response.status_code == 404:
                        logger.warning(f"[{self.name}] HTTP 404 Not Found: {url}")
                        raise ProviderNotFoundError(f"Resource not found at {url}")
                    elif response.status_code == 403:
                        logger.warning(f"[{self.name}] HTTP 403 Forbidden: {url}")
                        raise ProviderAccessDeniedError(f"Access forbidden at {url}")
                    elif response.status_code == 429:
                        retry_after = float(response.headers.get("Retry-After", 2.0 * attempt))
                        logger.warning(
                            f"[{self.name}] HTTP 429 Rate Limited: {url}. Backing off for {retry_after}s"
                        )
                        if attempt == self.retry_limit:
                            raise ProviderRateLimitError(f"Rate limited after {attempt} attempts: {url}")
                        await asyncio.sleep(retry_after)
                        continue
                    elif response.status_code >= 500:
                        logger.warning(
                            f"[{self.name}] HTTP {response.status_code} Server Error on {url}"
                        )
                        if attempt == self.retry_limit:
                            raise ProviderServerError(
                                f"Server error {response.status_code} at {url} after {attempt} attempts"
                            )
                        backoff = 1.5 ** attempt
                        await asyncio.sleep(backoff)
                        continue
                    else:
                        response.raise_for_status()
                        return response

                except (httpx.TimeoutException, httpx.NetworkError) as err:
                    logger.warning(
                        f"[{self.name}] Network/Timeout on {url} (attempt {attempt}/{self.retry_limit}): {err}"
                    )
                    if attempt == self.retry_limit:
                        raise ProviderException(f"Connection failed after {attempt} attempts: {err}")
                    await asyncio.sleep(1.5 ** attempt)

        raise ProviderException(f"Failed to fetch {url} after {self.retry_limit} attempts")

    @abstractmethod
    async def is_available(self) -> bool:
        """Returns True if provider is properly configured and operational."""
        pass

    @abstractmethod
    async def discover_jobs(
        self,
        identifier: str,
        company_name: Optional[str] = None,
        source_url: Optional[str] = None,
    ) -> List[DiscoveredJobData]:
        """Discovers jobs for a given identifier (board token, site, or URL)."""
        pass
