import json
from pathlib import Path
from typing import Set

DATA_DIR = Path("./data")
SUBSCRIBERS_FILE = DATA_DIR / "subscribers.json"
SEEN_FILE = DATA_DIR / "seen_ids.json"

def load_json_set(path: Path) -> Set[str]:
    if not path.exists():
        return set()
    try:
        return set(json.loads(path.read_text(encoding="utf-8")))
    except Exception:
        return set()

def save_json_set(path: Path, values: Set[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(sorted(values)), encoding="utf-8")

def load_subscribers() -> Set[str]:
    return load_json_set(SUBSCRIBERS_FILE)

def save_subscribers(ids: Set[str]) -> None:
    save_json_set(SUBSCRIBERS_FILE, ids)

def load_seen() -> Set[str]:
    return load_json_set(SEEN_FILE)

def save_seen(ids: Set[str]) -> None:
    save_json_set(SEEN_FILE, ids)

def make_seen_key(source: str, listing_id: str) -> str:
    # namespaced dedupe across all suppliers
    return f"{source}:{listing_id}"