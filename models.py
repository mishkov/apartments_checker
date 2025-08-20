from dataclasses import dataclass

@dataclass(frozen=True)
class Listing:
    source: str                # e.g. "onliner"
    id: str                    # unique per source
    url: str
    photo: str | None
    rent_type: str            # "1_room", "2_rooms", etc.
    price_usd: str            # "450.00"
    created_at: str           # ISO 8601 string
    last_time_up: str         # ISO 8601 string
    owner: bool               # True=Owner, False=Agency
    user_address: str
    latitude: float
    longitude: float