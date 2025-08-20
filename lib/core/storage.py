import json
from pathlib import Path
from typing import Set

DATA_DIR = Path("./data")
SUBSCRIBERS_FILE = DATA_DIR / "subscribers.json"
SEEN_DIR = DATA_DIR / "seen"

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

def _seen_path_for(chat_id: str) -> Path:
    return SEEN_DIR / f"{chat_id}.json"

def load_seen_for(chat_id: str) -> Set[str]:
    path = _seen_path_for(chat_id)
    if not path.exists():
        return set()
    try:
        return set(json.loads(path.read_text(encoding="utf-8")))
    except Exception:
        return set()

def save_seen_for(chat_id: str, keys: Set[str]) -> None:
    p = _seen_path_for(chat_id)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(sorted(keys)), encoding="utf-8")

def make_seen_key(source: str, listing_id: str) -> str:
    # namespaced dedupe across all suppliers
    return f"{source}:{listing_id}"