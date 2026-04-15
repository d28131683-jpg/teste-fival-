from __future__ import annotations

import logging
from typing import Any

import httpx
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from app.core.config import get_settings

logger = logging.getLogger(__name__)


class BaseHttpClient:
    def __init__(self, base_url: str, headers: dict[str, str] | None = None, timeout: int | None = None) -> None:
        settings = get_settings()
        self.base_url = base_url.rstrip('/')
        self.headers = headers or {}
        self.timeout = timeout or settings.request_timeout_seconds
        self.max_retries = settings.http_max_retries

    @retry(
        retry=retry_if_exception_type((httpx.HTTPError, httpx.TimeoutException)),
        wait=wait_exponential(multiplier=1, min=1, max=5),
        stop=stop_after_attempt(3),
        reraise=True,
    )
    def get(self, path: str, params: dict[str, Any] | None = None) -> httpx.Response:
        url = f'{self.base_url}/{path.lstrip('/')}'
        with httpx.Client(timeout=self.timeout, headers=self.headers) as client:
            response = client.get(url, params=params)
            response.raise_for_status()
            return response
