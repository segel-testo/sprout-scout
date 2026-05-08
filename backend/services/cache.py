import hashlib
import json
import time
from pathlib import Path

CACHE_DIR = Path(__file__).parent.parent / ".cache"
CACHE_TTL = 60 * 60 * 24 * 7  # 1 week in seconds

CACHE_DIR.mkdir(exist_ok=True)


def _cache_path(key: str) -> Path:
    # Hash the full key so the on-disk filename can never escape CACHE_DIR
    # via "..", path separators, null bytes, etc., regardless of how trusted
    # the caller's input is.
    digest = hashlib.sha256(key.encode("utf-8")).hexdigest()
    return CACHE_DIR / f"{digest}.json"


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


def get_namespaced(namespace: str, key: str):
    return get_cached(f"{namespace}__{key}")


def set_namespaced(namespace: str, key: str, payload):
    set_cached(f"{namespace}__{key}", payload)
