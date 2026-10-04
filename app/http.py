import asyncio
import logging
from typing import Any

import aiohttp

log = logging.getLogger(__name__)

DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/139 Safari/537.36",
    "Accept": "application/json",
}


def _retryable(exc: Exception) -> bool:
    if isinstance(exc, aiohttp.ClientResponseError):
        return exc.status == 429 or exc.status >= 500
    return isinstance(exc, (aiohttp.ClientError, asyncio.TimeoutError))


async def request_json(
    session: aiohttp.ClientSession,
    method: str,
    url: str,
    *,
    retries: int = 2,
    timeout: float = 10.0,
    backoff: float = 0.5,
    label: str | None = None,
    **kwargs: Any,
) -> Any:
    """Request JSON with retries on network errors, 429 and 5xx (exponential backoff).

    `label` replaces the URL in logs (use it when the URL contains a secret).
    """
    for attempt in range(retries + 1):
        try:
            async with session.request(
                method, url, timeout=aiohttp.ClientTimeout(total=timeout), **kwargs
            ) as response:
                response.raise_for_status()
                return await response.json(content_type=None)
        except Exception as exc:
            if attempt >= retries or not _retryable(exc):
                raise
            delay = backoff * 2 ** attempt
            reason = getattr(exc, "status", None) or type(exc).__name__
            log.warning("%s %s failed (%s), retry in %.1fs", method, label or url, reason, delay)
            await asyncio.sleep(delay)
