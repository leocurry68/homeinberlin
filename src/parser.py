from __future__ import annotations

import json
import re
from urllib.parse import urljoin

from bs4 import BeautifulSoup, Tag

from .config import BASE_URL
from .models import UNKNOWN, Listing, ScrapeResult


def clean_text(value: str | None) -> str:
    if not value:
        return UNKNOWN
    text = re.sub(r"\s+", " ", value).strip()
    return text or UNKNOWN


def _json_ld_objects(soup: BeautifulSoup) -> list[dict[str, object]]:
    objects: list[dict[str, object]] = []
    for script in soup.select('script[type="application/ld+json"]'):
        raw = script.string or script.get_text()
        if not raw:
            continue
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            continue
        stack = data if isinstance(data, list) else [data]
        for item in stack:
            if isinstance(item, dict):
                objects.append(item)
    return objects


def _extract_postal_code(text: str) -> str:
    match = re.search(r"\b(1[0-4]\d{3})\b", text)
    return match.group(1) if match else UNKNOWN


def _extract_rooms(text: str) -> str:
    match = re.search(r"\b(\d+(?:[.,]\d+)?)\s*(Room|Rooms|Zimmer)\b|\b(\d+)-Zimmer\b", text, re.I)
    if not match:
        return UNKNOWN
    return clean_text(match.group(0))


def _extract_size(text: str) -> str:
    match = re.search(r"\b(\d+(?:[.,]\d+)?)\s*(?:m²|qm|sq\.?\s*m)\b", text, re.I)
    return clean_text(match.group(0)) if match else UNKNOWN


def _extract_available(text: str) -> str:
    match = re.search(r"available from\s*:?\s*([0-3]?\d\.\s*[A-Za-z]{3,}\s*\d{4})", text, re.I)
    return clean_text(match.group(1)) if match else UNKNOWN


def _extract_occupancy(text: str) -> str:
    match = re.search(r"(?:maximum occupancy|occupancy|max(?:imum)? persons?)\s*:?\s*(\d+)", text, re.I)
    return match.group(1) if match else UNKNOWN


def _extract_money_after(label: str, text: str) -> str:
    pattern = rf"{label}\s*:?\s*(?:<[^>]+>|\s)*([0-9.]+,[0-9]{{2}}\s*€(?:\s*/\s*Month)?)"
    match = re.search(pattern, text, re.I)
    return clean_text(match.group(1)) if match else UNKNOWN


def _first_link(card: Tag) -> str:
    for link in card.select("a[href]"):
        href = str(link.get("href"))
        if "/estate/" in href:
            return urljoin(BASE_URL, href)
    return UNKNOWN


def _title_from_card(card: Tag) -> str:
    for selector in ["h2", "h3", ".news-item-title", ".item-title"]:
        node = card.select_one(selector)
        if node:
            text = clean_text(node.get_text(" "))
            if text != UNKNOWN:
                return text
    link = card.select_one("a[href*='/estate/']")
    return clean_text(link.get_text(" ") if link else None)


def _area_from_card(card: Tag) -> str:
    for line in card.get_text("\n").splitlines():
        text = clean_text(line)
        if text != UNKNOWN and "Berlin" in text and "|" in text:
            return text
    return UNKNOWN


def parse_listing_page(html: str, page_url: str = BASE_URL) -> ScrapeResult:
    soup = BeautifulSoup(html, "html.parser")
    _json_ld_objects(soup)
    cards = soup.select(".estate-card, article, .block-news-item")
    listings: list[Listing] = []
    seen: set[str] = set()
    for card in cards:
        if not isinstance(card, Tag):
            continue
        link = _first_link(card)
        if link == UNKNOWN or link in seen:
            continue
        seen.add(link)
        text = clean_text(card.get_text(" "))
        title = _title_from_card(card)
        facts = UNKNOWN
        strong = card.select_one(".estate-item-button-inner strong, strong")
        if strong:
            facts = clean_text(strong.get_text(" "))
        area = _area_from_card(card)
        listings.append(
            Listing(
                name=title,
                listing_type=title.split()[0] if title != UNKNOWN else UNKNOWN,
                area=area,
                address=area,
                postal_code=_extract_postal_code(text),
                rooms=_extract_rooms(facts if facts != UNKNOWN else text),
                size=_extract_size(facts if facts != UNKNOWN else text),
                available_from=_extract_available(facts if facts != UNKNOWN else text),
                status="online",
                detail_url=link,
                raw_text=text,
            )
        )
    warnings: list[str] = []
    parsed_ok = True
    if not listings:
        page_text = clean_text(soup.get_text(" "))
        if re.search(r"available|rooms|apartments|Zimmer|Wohnungen|estate", page_text, re.I):
            parsed_ok = False
            warnings.append("页面似乎包含房源相关内容，但解析结果为零，可能结构已变化")
    return ScrapeResult(listings=listings, parsed_ok=parsed_ok, warnings=warnings)


def merge_detail(base: Listing, html: str) -> Listing:
    soup = BeautifulSoup(html, "html.parser")
    text = clean_text(soup.get_text(" "))
    h1 = soup.select_one("h1")
    if h1:
        base.name = clean_text(h1.get_text(" "))
    pre_titles = [clean_text(node.get_text(" ")) for node in soup.select(".estate-pre-title")]
    if pre_titles:
        base.rooms = _extract_rooms(pre_titles[0])
        base.size = _extract_size(pre_titles[0])
        base.available_from = _extract_available(pre_titles[0])
    if len(pre_titles) > 1:
        base.area = pre_titles[1]
        base.address = pre_titles[1]
    meta_desc = soup.select_one('meta[name="description"], meta[property="og:description"]')
    if meta_desc and (base.area == UNKNOWN or base.address == UNKNOWN):
        content = clean_text(str(meta_desc.get("content", "")))
        parts = [clean_text(part) for part in content.split("|")]
        if len(parts) >= 4:
            base.area = parts[3]
            base.address = parts[3]
    base.max_occupancy = _extract_occupancy(text)
    base.postal_code = _extract_postal_code(text)
    base.monthly_rent = _extract_money_after("Total rent including utilities", str(soup)) or UNKNOWN
    base.deposit = _extract_money_after("Total deposit", str(soup)) or UNKNOWN
    if base.monthly_rent == UNKNOWN:
        rent_match = re.search(r"\b[0-9.]+,[0-9]{2}\s*€\b", text)
        base.monthly_rent = rent_match.group(0) if rent_match else UNKNOWN
    base.other_costs = "包含在总租金中" if base.monthly_rent != UNKNOWN else UNKNOWN
    base.status = "online"
    base.raw_text = f"{base.raw_text}\n{text}"
    return base

