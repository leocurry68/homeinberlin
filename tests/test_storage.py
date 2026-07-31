from src.models import Listing
from src.storage import JsonStore


def test_missing_and_corrupt_json_recover(tmp_path) -> None:
    store = JsonStore(tmp_path)
    assert store.load_seen() == {}
    store.seen_path.write_text("{broken", encoding="utf-8")
    assert store.load_seen() == {}


def test_active_listing_prevents_duplicate_and_reappearing_is_new(tmp_path) -> None:
    store = JsonStore(tmp_path)
    listing = Listing(name="Apartment Friends", detail_url="https://example.com/a")
    assert store.new_or_reappeared([listing]) == [listing]
    store.save_active([listing])
    assert store.new_or_reappeared([listing]) == []
    store.save_active([])
    assert store.new_or_reappeared([listing]) == [listing]

def test_mark_notified_writes_seen(tmp_path) -> None:
    store = JsonStore(tmp_path)
    listing = Listing(name="Apartment Friends", detail_url="https://example.com/a")
    store.mark_notified(listing)
    assert listing.unique_id() in store.load_seen()

