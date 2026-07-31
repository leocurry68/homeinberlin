from __future__ import annotations

import re

from .models import Listing, MatchResult

TWO_PERSON_KEYWORDS = [
    "Couple",
    "Couple Room",
    "Couples",
    "Friends",
    "Friends Room",
    "Doppelzimmer",
    "Zweibettzimmer",
    "2 Personen",
    "zwei Personen",
    "für 2 Personen",
    "two people",
    "two persons",
    "suitable for two",
    "suitable for 2",
    "2 Zimmer",
    "2-Zimmer",
    "two-room",
    "2 room apartment",
]
WEDDING_POSTAL_CODES = {"13347", "13349", "13351", "13353", "13355", "13357", "13359"}
NEGATIVE_AREAS = {"moabit", "tiergarten", "prenzlauer berg", "friedrichshain", "lichtenberg"}


def _haystack(listing: Listing) -> str:
    return " ".join(
        [
            listing.name,
            listing.listing_type,
            listing.area,
            listing.address,
            listing.postal_code,
            listing.rooms,
            listing.max_occupancy,
            listing.raw_text,
        ]
    )


def is_suitable_for_two(listing: Listing) -> MatchResult:
    if re.fullmatch(r"\s*[1-9]\d*\s*", listing.max_occupancy):
        people = int(listing.max_occupancy.strip())
        return MatchResult(people >= 2, f"最大入住人数为 {people}" if people >= 2 else f"最大入住人数仅为 {people}")

    occupancy_text = f"{listing.max_occupancy} {_haystack(listing)}"
    occupancy_match = re.search(
        r"(?:maximum occupancy|occupancy|max(?:imum)?|persons?|tenants?|residents?)\D{0,20}([1-9]\d*)",
        occupancy_text,
        re.I,
    )
    if occupancy_match:
        people = int(occupancy_match.group(1))
        return MatchResult(people >= 2, f"最大入住人数为 {people}" if people >= 2 else f"最大入住人数仅为 {people}")

    room_match = re.search(r"\b([2-9])\s*(?:Room|Rooms|Zimmer)\b|\b([2-9])-Zimmer\b", _haystack(listing), re.I)
    if room_match:
        rooms = room_match.group(1) or room_match.group(2)
        return MatchResult(True, f"页面明确显示 {rooms} 个房间")

    text = _haystack(listing)
    for keyword in TWO_PERSON_KEYWORDS:
        if re.search(rf"\b{re.escape(keyword)}\b", text, re.I):
            return MatchResult(True, f"命中双人入住关键词：{keyword}")

    return MatchResult(False, "没有明确双人入住、两人入住或至少两个房间的信息")


def is_in_wedding(listing: Listing) -> MatchResult:
    text = _haystack(listing)
    lower = text.lower()
    if re.search(r"\b(?:berlin[-\s])?wedding\b|\bortsteil wedding\b", text, re.I):
        return MatchResult(True, "页面明确写明 Berlin-Wedding/Wedding")
    if listing.postal_code in WEDDING_POSTAL_CODES or any(code in text for code in WEDDING_POSTAL_CODES):
        for area in NEGATIVE_AREAS:
            if area in lower:
                return MatchResult(False, f"出现非 Wedding 区域：{area}")
        if re.search(r"\bmitte\b", lower) and not re.search(r"\bwedding\b", lower):
            return MatchResult(False, "仅出现 Mitte，未明确 Wedding")
        code = (
            listing.postal_code
            if listing.postal_code in WEDDING_POSTAL_CODES
            else next(code for code in WEDDING_POSTAL_CODES if code in text)
        )
        return MatchResult(True, f"邮编 {code} 属于 Wedding 辅助匹配范围")
    return MatchResult(False, "没有明确 Wedding 区域或 Wedding 邮编")


def apply_match_reasons(listing: Listing) -> tuple[bool, Listing]:
    two = is_suitable_for_two(listing)
    wedding = is_in_wedding(listing)
    listing.two_person_reason = two.reason
    listing.wedding_reason = wedding.reason
    return two.matched and wedding.matched, listing
