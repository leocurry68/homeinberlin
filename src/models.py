from __future__ import annotations

from dataclasses import asdict, dataclass, field
from hashlib import sha256

UNKNOWN = "未注明"


@dataclass(slots=True)
class Listing:
    name: str = UNKNOWN
    listing_type: str = UNKNOWN
    area: str = UNKNOWN
    address: str = UNKNOWN
    postal_code: str = UNKNOWN
    rooms: str = UNKNOWN
    max_occupancy: str = UNKNOWN
    size: str = UNKNOWN
    monthly_rent: str = UNKNOWN
    other_costs: str = UNKNOWN
    deposit: str = UNKNOWN
    available_from: str = UNKNOWN
    status: str = UNKNOWN
    detail_url: str = UNKNOWN
    two_person_reason: str = UNKNOWN
    wedding_reason: str = UNKNOWN
    raw_text: str = UNKNOWN

    def unique_id(self) -> str:
        if self.detail_url and self.detail_url != UNKNOWN:
            return self.detail_url.rstrip("/")
        stable = "|".join([self.name, self.address, self.monthly_rent, self.available_from])
        return sha256(stable.encode("utf-8")).hexdigest()

    def to_dict(self) -> dict[str, str]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> Listing:
        fields = cls.__dataclass_fields__
        return cls(**{k: str(data.get(k, UNKNOWN) or UNKNOWN) for k in fields})


@dataclass(slots=True)
class MatchResult:
    matched: bool
    reason: str


@dataclass(slots=True)
class ScrapeResult:
    listings: list[Listing] = field(default_factory=list)
    parsed_ok: bool = True
    warnings: list[str] = field(default_factory=list)

