from __future__ import annotations

import argparse
import logging
import sys

from .config import configure_logging, load_settings
from .http_client import FetchError
from .matcher import apply_match_reasons, is_in_wedding, is_suitable_for_two
from .notifier import NtfyNotifier
from .scraper import Scraper
from .storage import JsonStore

LOGGER = logging.getLogger(__name__)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Monitor Home in Berlin listings")
    parser.add_argument("--dry-run", action="store_true", help="Do not send notifications or write notified state")
    parser.add_argument("--test-notification", action="store_true", help="Send one ntfy test notification")
    parser.add_argument("--show-all", action="store_true", help="Show all scraped listings and match results")
    parser.add_argument("--reset-state", action="store_true", help="Clear local state after interactive confirmation")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    settings = load_settings()
    if args.dry_run:
        settings.dry_run = True
    configure_logging(settings.log_level)
    store = JsonStore(settings.data_dir)
    notifier = NtfyNotifier(settings)

    if args.reset_state:
        if not sys.stdin.isatty():
            LOGGER.error("--reset-state requires an interactive terminal")
            return 2
        confirm = input("Type RESET to clear seen, active, and error state: ")
        if confirm != "RESET":
            LOGGER.info("Reset cancelled")
            return 1
        store.reset()
        LOGGER.info("State reset")
        return 0

    if args.test_notification:
        return 0 if notifier.send_test() else 1

    try:
        scrape_result = Scraper(settings).scrape()
    except FetchError as exc:
        _send_rate_limited_error(store, notifier, "list_page_fetch_failed", exc.message, exc.url)
        return 1
    except Exception as exc:
        LOGGER.exception("Unexpected monitor failure")
        _send_rate_limited_error(store, notifier, "unexpected_failure", str(exc), settings.listings_url)
        return 1

    if not scrape_result.parsed_ok:
        _send_rate_limited_error(store, notifier, "parser_zero_results", "; ".join(scrape_result.warnings), settings.listings_url)

    matched = []
    for listing in scrape_result.listings:
        ok, listing = apply_match_reasons(listing)
        if args.show_all:
            two = is_suitable_for_two(listing)
            wedding = is_in_wedding(listing)
            LOGGER.info(
                "Listing: %s | two=%s (%s) | wedding=%s (%s) | %s",
                listing.name,
                two.matched,
                two.reason,
                wedding.matched,
                wedding.reason,
                listing.detail_url,
            )
        if ok:
            matched.append(listing)

    new_listings = store.new_or_reappeared(matched)
    failures = 0
    for listing in new_listings:
        sent = notifier.send_listing(listing)
        if sent:
            if not settings.dry_run:
                store.mark_notified(listing)
        else:
            failures += 1
            LOGGER.error("Notification failed for %s", listing.detail_url)

    if not settings.dry_run:
        store.save_active(matched)
    else:
        LOGGER.info("Dry-run: state files were not modified")

    if new_listings and failures == len(new_listings):
        _send_rate_limited_error(store, notifier, "all_notifications_failed", "所有新房源通知都发送失败", settings.listings_url)
        return 1
    LOGGER.info("Scraped %s listings, matched %s, new/reappeared %s", len(scrape_result.listings), len(matched), len(new_listings))
    return 0


def _send_rate_limited_error(store: JsonStore, notifier: NtfyNotifier, error_type: str, message: str, page_url: str) -> None:
    if store.error_allowed(error_type):
        if notifier.send_error(error_type, message, page_url):
            store.mark_error_sent(error_type)
    else:
        LOGGER.warning("Suppressed repeated error notification for %s", error_type)


if __name__ == "__main__":
    raise SystemExit(main())

