from __future__ import annotations

import logging
import time

from .config import Settings
from .http_client import HttpClient
from .matcher import is_in_wedding, is_suitable_for_two
from .models import Listing, ScrapeResult
from .parser import merge_detail, parse_listing_page

LOGGER = logging.getLogger(__name__)


class Scraper:
    def __init__(self, settings: Settings, client: HttpClient | None = None) -> None:
        self.settings = settings
        self.client = client or HttpClient(timeout=settings.request_timeout)

    def scrape(self) -> ScrapeResult:
        html = self.client.get(self.settings.listings_url)
        result = parse_listing_page(html, self.settings.listings_url)
        enriched: list[Listing] = []
        for listing in result.listings:
            if self._needs_detail(listing):
                time.sleep(1)
                try:
                    listing = merge_detail(listing, self.client.get(listing.detail_url))
                except Exception as exc:
                    LOGGER.warning("Could not enrich listing %s: %s", listing.detail_url, exc)
            enriched.append(listing)
        result.listings = enriched
        return result

    def _needs_detail(self, listing: Listing) -> bool:
        # Fetch only likely candidates: cards already showing Wedding or two-person evidence.
        return is_in_wedding(listing).matched or is_suitable_for_two(listing).matched
