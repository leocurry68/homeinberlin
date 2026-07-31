from pathlib import Path

from src.parser import merge_detail, parse_listing_page

FIXTURES = Path(__file__).parent / "fixtures"


def test_parse_listing_page_deduplicates_links() -> None:
    result = parse_listing_page((FIXTURES / "listings.html").read_text())
    assert result.parsed_ok
    assert len(result.listings) == 2
    assert result.listings[0].rooms == "2 Room"


def test_merge_detail_handles_missing_fields() -> None:
    listing = parse_listing_page((FIXTURES / "listings.html").read_text()).listings[0]
    merged = merge_detail(listing, (FIXTURES / "listing_detail.html").read_text())
    assert merged.max_occupancy == "2"
    assert merged.monthly_rent == "949,00 € / Month"
    assert merged.deposit == "1.898,00 €"


def test_empty_page_flags_possible_parser_failure() -> None:
    result = parse_listing_page((FIXTURES / "empty_page.html").read_text())
    assert result.listings == []
    assert not result.parsed_ok

