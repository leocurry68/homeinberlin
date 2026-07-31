from unittest.mock import Mock

from src.config import Settings
from src.main import main
from src.models import Listing, ScrapeResult


def test_notification_failure_does_not_write_seen(tmp_path, monkeypatch) -> None:
    listing = Listing(name="Friends Room", area="Berlin Wedding", max_occupancy="2", detail_url="https://example.com/a")
    monkeypatch.setattr(
        "src.main.load_settings",
        lambda: Settings("topic", "https://ntfy.sh", False, "INFO", 30, tmp_path),
    )
    monkeypatch.setattr("src.main.Scraper", lambda settings: Mock(scrape=lambda: ScrapeResult([listing])))
    monkeypatch.setattr("src.main.NtfyNotifier", lambda settings: Mock(send_listing=lambda item: False, send_error=lambda *args: True))
    assert main([]) == 1
    assert (tmp_path / "seen_listings.json").read_text(encoding="utf-8") == "{}\n"


def test_dry_run_does_not_write_active(tmp_path, monkeypatch) -> None:
    listing = Listing(name="Friends Room", area="Berlin Wedding", max_occupancy="2", detail_url="https://example.com/a")
    monkeypatch.setattr(
        "src.main.load_settings",
        lambda: Settings(None, "https://ntfy.sh", True, "INFO", 30, tmp_path),
    )
    monkeypatch.setattr("src.main.Scraper", lambda settings: Mock(scrape=lambda: ScrapeResult([listing])))
    assert main(["--dry-run"]) == 0
    assert (tmp_path / "active_listings.json").read_text(encoding="utf-8") == "{}\n"
