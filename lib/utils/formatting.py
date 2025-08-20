from datetime import datetime
from telegram import InlineKeyboardMarkup, InlineKeyboardButton
from lib.models import Listing

def pretty_rent_type(rt: str) -> str:
    return rt.replace("_", " ")

def owner_label(is_owner: bool) -> str:
    return "Owner" if is_owner else "Agency"

def fmt_time(iso_str: str) -> str:
    dt = datetime.fromisoformat(iso_str)  # preserves offset; uses local format symbols
    return f'<b>{dt.strftime("%H:%M")}</b> {dt.strftime("%d.%m.%Y")}'

def format_caption(a: Listing) -> str:
    # Bold price + rooms, blank line after header, blank line after "Last up:"
    price = a.price_usd.rstrip("0").rstrip(".")
    header = f'<b>{price}$ {pretty_rent_type(a.rent_type)}</b> — {owner_label(a.owner)}'
    return "\n".join([
        header,
        "",
        f'🕒 Created: {fmt_time(a.created_at)}',
        f'🔁 Last up: {fmt_time(a.last_time_up)}',
        "",
        f'📍 {a.user_address}',
    ])

def build_keyboard(a: Listing) -> InlineKeyboardMarkup:
    # Pin on Yandex: pt=lon,lat; single row of 2 buttons
    pt = f"{a.longitude},{a.latitude}"
    yandex_url = f"https://yandex.ru/maps/?pt={pt}&z=18&l=map"
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("🗺️ Open in Yandex Maps", url=yandex_url),
        InlineKeyboardButton("🏢 Open on Onliner", url=a.url),
    ]])