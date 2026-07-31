from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse
from zoneinfo import ZoneInfo

BERLIN_TZ = ZoneInfo("Europe/Berlin")
BASE_URL = "https://home-in-berlin.de"
LISTINGS_URL = "https://home-in-berlin.de/en/immobilien/"


def _bool_env(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def normalize_ntfy_topic(value: str | None) -> str | None:
    if not value:
        return None
    topic = value.strip()
    if not topic:
        return None
    if topic.startswith(("http://", "https://")):
        parsed = urlparse(topic)
        parts = [part for part in parsed.path.split("/") if part]
        return parts[0] if parts else None
    return topic.strip("/")


@dataclass(slots=True)
class Settings:
    ntfy_topic: str | None
    ntfy_server: str
    dry_run: bool
    log_level: str
    request_timeout: int
    data_dir: Path
    listings_url: str = LISTINGS_URL

    @property
    def ntfy_url(self) -> str | None:
        if not self.ntfy_topic:
            return None
        return f"{self.ntfy_server.rstrip('/')}/{self.ntfy_topic}"


def load_settings(data_dir: Path | None = None) -> Settings:
    topic = normalize_ntfy_topic(os.getenv("NTFY_TOPIC"))
    dry_run = _bool_env("DRY_RUN", False) or topic is None
    return Settings(
        ntfy_topic=topic,
        ntfy_server=os.getenv("NTFY_SERVER", "https://ntfy.sh"),
        dry_run=dry_run,
        log_level=os.getenv("LOG_LEVEL", "INFO").upper(),
        request_timeout=int(os.getenv("REQUEST_TIMEOUT", "30")),
        data_dir=data_dir or Path("data"),
    )


class BerlinFormatter(logging.Formatter):
    converter = None

    def formatTime(self, record: logging.LogRecord, datefmt: str | None = None) -> str:
        from datetime import datetime

        dt = datetime.fromtimestamp(record.created, BERLIN_TZ)
        return dt.strftime(datefmt or "%Y-%m-%d %H:%M:%S %Z")


def configure_logging(level: str) -> None:
    handler = logging.StreamHandler()
    handler.setFormatter(BerlinFormatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(level)
