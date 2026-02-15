# apartments_checker/suppliers/realt.py
from __future__ import annotations

from typing import Any, Dict, Sequence

import requests

from lib.models import Listing
from lib.suppliers.base import Supplier

# --- Minimal GraphQL payload (only the fields we need) ---
GQL_QUERY = """
query searchObjects($data: GetObjectsByAddressInput!) {
  searchObjects(data: $data) {
    body {
      results {
        uuid
        code
        createdAt
        updatedAt
        price
        priceCurrency
        rooms
        agencyName
        address
        location        # [lon, lat]
        images
      }
    }
  }
}
"""

# NOTE: We keep headers minimal (requests handles gzip by default).
HEADERS = {
    "Content-Type": "application/json",
    "Accept": "application/json",
    "Origin": "https://realt.by",
}

# Build the variables once; adjust to your bbox/price window as needed.
# priceType=840 means USD on Realt.by. priceNegotiable true to include negotiable.
DEFAULT_VARIABLES: Dict[str, Any] = {
    "data": {
        "where": {
            "priceFrom": "340",
            "priceTo": "600",
            "priceType": "840",
            "priceNegotiable": "true",
            "category": 2,  # Apartments (long-term rent)
            "addressV2": [
                {"metroStationUuid": "481c9f9e-7b00-11eb-8943-0cc47adabd66"},
                {"metroStationUuid": "481ca613-7b00-11eb-8943-0cc47adabd66"},
                {"metroStationUuid": "481caca1-7b00-11eb-8943-0cc47adabd66"},
                {"metroStationUuid": "481cb2fe-7b00-11eb-8943-0cc47adabd66"},
                {"metroStationUuid": "481cb3f0-7b00-11eb-8943-0cc47adabd66"},
                {"metroStationUuid": "481ca4ae-7b00-11eb-8943-0cc47adabd66"},
                {"metroStationUuid": "481ca9de-7b00-11eb-8943-0cc47adabd66"},
                {"metroStationUuid": "481caba5-7b00-11eb-8943-0cc47adabd66"},
                {"metroStationUuid": "481cada1-7b00-11eb-8943-0cc47adabd66"},
                {"metroStationUuid": "481cae9a-7b00-11eb-8943-0cc47adabd66"},
                {"metroStationUuid": "481cb081-7b00-11eb-8943-0cc47adabd66"},
                {"metroStationUuid": "481cb170-7b00-11eb-8943-0cc47adabd66"},
                {"metroStationUuid": "481ca729-7b00-11eb-8943-0cc47adabd66"},
                {"metroStationUuid": "481ca889-7b00-11eb-8943-0cc47adabd66"},
                {"metroStationUuid": "481caf96-7b00-11eb-8943-0cc47adabd66"},
            ],
        },
        "pagination": {"page": 1, "pageSize": 30},
        "sort": [{"by": "updatedAt", "order": "DESC"}],
        "extraFields": None,
        "isReactAdaptiveUA": False,
    }
}


def _rooms_to_rent_type(rooms: int | None) -> str:
    # Normalize to your bot’s format: "1_room" vs "2_rooms"
    if not rooms or rooms <= 0:
        return "unknown"
    return f"{rooms}_room" if rooms == 1 else f"{rooms}_rooms"


def _listing_url(code: int) -> str:
    return f"https://realt.by/rent-flat-for-long/object/{code}/"


class RealtSupplier(Supplier):
    def __init__(self, session: requests.Session | None = None):
        # Reuse a session for keep-alive + connection pooling
        self._session = session or requests.Session()

    @property
    def name(self) -> str:
        return "realt"

    def fetch(self) -> Sequence[Listing]:
        # GraphQL batch endpoint accepts a list of operations; we send one.
        payload = [{
            "operationName": "searchObjects",
            "variables": DEFAULT_VARIABLES,
            "query": GQL_QUERY,
        }]

        resp = self._session.post(
            "https://realt.by/bff/graphql",
            headers=HEADERS,
            json=payload,
            timeout=200,
        )
        resp.raise_for_status()
        data = resp.json()

        # Response is a list of operation results; take the first
        op = data[0]
        body = (
            op.get("data", {})
              .get("searchObjects", {})
              .get("body", {})
        )
        results = body.get("results", []) or []

        out: list[Listing] = []
        for it in results:
            # Filter only USD (840) just in case
            if it.get("priceCurrency") != 840:
                continue

            # Только 2-комнатные
            if it.get("rooms") != 2:
                continue
        
            # Только собственники
            if it.get("agencyName") is not None:
                continue

            images = it.get("images") or []
            lon, lat = None, None
            loc = it.get("location")
            if isinstance(loc, list) and len(loc) >= 2:
                lon, lat = float(loc[0]), float(loc[1])

            priceint = it.get("price", "")

            li = Listing(
                source=self.name,
                id=str(it["uuid"]),
                url=_listing_url(it.get("code")),
                photo=images[0] if images else None,
                rent_type=_rooms_to_rent_type(it.get("rooms")),
                # integer on Realt, keep as string
                price_usd=str(priceint),
                created_at=it["createdAt"],
                # best “bump” analogue
                last_time_up=it["updatedAt"],
                # no agency => owner
                owner=(it.get("agencyName") is None),
                user_address=it.get("address", ""),
                latitude=lat if lat is not None else 0.0,
                longitude=lon if lon is not None else 0.0,
            )

            out.append(li)

        # Newest-first is already requested via sort DESC, just return
        return out
