from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field

import requests

LOGGER = logging.getLogger(__name__)
RETRY_STATUS_CODES = {403, 429, 500, 502, 503, 504}


class FetchError(RuntimeError):
    def __init__(self, url: str, message: str) -> None:
        super().__init__(message)
        self.url = url
        self.message = message


@dataclass(slots=True)
class HttpClient:
    timeout: int = 30
    session: requests.Session = field(default_factory=requests.Session)
    cache: dict[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.session.headers.update(
            {
                "User-Agent": (
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"
                ),
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "en,de;q=0.8",
            }
        )

    def get(self, url: str) -> str:
        if url in self.cache:
            return self.cache[url]
        last_error = ""
        for attempt in range(1, 4):
            try:
                response = self.session.get(url, timeout=self.timeout)
                if response.status_code == 404:
                    raise FetchError(url, "404 Not Found")
                if response.status_code in RETRY_STATUS_CODES:
                    retry_after = response.headers.get("Retry-After")
                    wait = int(retry_after) if response.status_code == 429 and retry_after and retry_after.isdigit() else 2**attempt
                    last_error = f"HTTP {response.status_code}"
                    LOGGER.warning("Request failed for %s with %s; retrying in %ss", url, last_error, wait)
                    time.sleep(wait)
                    continue
                response.raise_for_status()
                self.cache[url] = response.text
                return response.text
            except requests.RequestException as exc:
                last_error = str(exc)
                wait = 2**attempt
                LOGGER.warning("Request failed for %s: %s; retrying in %ss", url, exc, wait)
                time.sleep(wait)
        raise FetchError(url, f"Failed after retries: {last_error}")

