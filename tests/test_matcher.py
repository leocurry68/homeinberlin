from src.matcher import apply_match_reasons, is_in_wedding, is_suitable_for_two
from src.models import Listing


def test_couple_room_in_wedding_matches() -> None:
    listing = Listing(name="Couple Room", area="Berlin Wedding")
    assert is_suitable_for_two(listing).matched
    assert is_in_wedding(listing).matched
    assert apply_match_reasons(listing)[0]


def test_two_person_postal_code_matches() -> None:
    listing = Listing(name="Nice room", max_occupancy="2", postal_code="13347")
    assert apply_match_reasons(listing)[0]


def test_studio_without_occupancy_does_not_match_two() -> None:
    assert not is_suitable_for_two(Listing(name="Studio Classic Single")).matched


def test_apartment_without_evidence_does_not_match_two() -> None:
    assert not is_suitable_for_two(Listing(name="Apartment Classic")).matched


def test_mitte_double_room_not_wedding() -> None:
    listing = Listing(name="Couple Room", area="Berlin Mitte")
    assert is_suitable_for_two(listing).matched
    assert not is_in_wedding(listing).matched


def test_moabit_double_room_not_wedding() -> None:
    listing = Listing(name="Friends Room", area="Berlin Moabit")
    assert not is_in_wedding(listing).matched


def test_wedding_single_occupancy_not_two() -> None:
    listing = Listing(name="Room Single", area="Berlin Wedding", max_occupancy="1")
    assert is_in_wedding(listing).matched
    assert not is_suitable_for_two(listing).matched

