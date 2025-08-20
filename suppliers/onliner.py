import requests
from typing import Sequence
from models import Listing
from suppliers.base import Supplier

API_URL = (
    "https://r.onliner.by/sdapi/ak.api/search/apartments"
    "?bounds%5Blb%5D%5Blat%5D=53.856627313959706"
    "&bounds%5Blb%5D%5Blong%5D=27.525730133056644"
    "&bounds%5Brt%5D%5Blat%5D=53.87634056593514"
    "&bounds%5Brt%5D%5Blong%5D=27.556629180908207"
    "&page=1&order=created_at%3Adesc&v=0.2166729371863111"
)

HEADERS = {
    "Accept": "application/json, text/plain, */*",
    "Referer": "https://r.onliner.by/ak/",
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/19.0 Safari/605.1.15",
    # let requests negotiate encoding or force gzip/deflate only:
    # "Accept-Encoding": "gzip, deflate",
}

class OnlinerSupplier(Supplier):
    @property
    def name(self) -> str:
        return "onliner"

    def fetch(self) -> Sequence[Listing]:
        resp = requests.get(API_URL, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        data = resp.json()

        out: list[Listing] = []
        for it in data.get("apartments", []):
            out.append(Listing(
                source=self.name,
                id=str(it["id"]),
                url=it["url"],
                photo=it.get("photo"),
                rent_type=it["rent_type"],
                price_usd=it["price"]["amount"],
                created_at=it["created_at"],
                last_time_up=it["last_time_up"],
                owner=it["contact"]["owner"],
                user_address=it["location"]["user_address"],
                latitude=it["location"]["latitude"],
                longitude=it["location"]["longitude"],
            ))
        return out