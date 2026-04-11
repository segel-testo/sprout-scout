import json
import time
from pathlib import Path

CACHE_DIR = Path(__file__).parent.parent / ".cache"
CACHE_TTL = 60 * 60 * 24 * 7  # 1 week in seconds

CACHE_DIR.mkdir(exist_ok=True)


def _cache_path(key: str) -> Path:
    safe_key = key.replace("/", "_").replace(":", "_")
    return CACHE_DIR / f"{safe_key}.json"


def get_cached(key: str):
    path = _cache_path(key)
    if not path.exists():
        return None
    data = json.loads(path.read_text())
    if time.time() - data["timestamp"] > CACHE_TTL:
        path.unlink()
        return None
    return data["payload"]


def set_cached(key: str, payload):
    path = _cache_path(key)
    path.write_text(json.dumps({"timestamp": time.time(), "payload": payload}))
