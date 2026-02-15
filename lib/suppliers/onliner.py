import requests
from typing import Sequence
from lib.models import Listing
from lib.suppliers.base import Supplier

API_URL = (
    "https://r.onliner.by/sdapi/ak.api/search/apartments?"
    "metro%5B%5D=blue_line&"
    "price%5Bmin%5D=50&"
    "price%5Bmax%5D=620&"
    "currency=usd&"
    "bounds%5Blb%5D%5Blat%5D=53.740183247571835&"
    "bounds%5Blb%5D%5Blong%5D=27.31475830078125&"
    "bounds%5Brt%5D%5Blat%5D=54.0553574501532&"
    "bounds%5Brt%5D%5Blong%5D=27.809143066406254&"
    "page=1&"
    "v=0.1633072619118714&"
    "order=created_at%3Adesc"
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
        resp = requests.get(API_URL, headers=HEADERS, timeout=200)
        resp.raise_for_status()
        data = resp.json()

        out: list[Listing] = []
        for it in data.get("apartments", []):
        
            # Только собственники
            if not it.get("contact", {}).get("owner", False):
                continue
    
            # Только 2-комнатные
            if it.get("rent_type") not in ("2_rooms", "2_room"):
                continue
    
            # Только нужный диапазон цены
            price = float(it["price"]["amount"])
            if not (340 <= price <= 540):
                continue
            
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
