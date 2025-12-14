import hashlib
import os
import pickle
from pathlib import Path
from typing import Any

CACHE_DIR = Path(".cache_refinitiv")
CACHE_DIR.mkdir(exist_ok=True)

def _key_to_path(key: str) -> Path:
    h = hashlib.sha256(key.encode("utf-8")).hexdigest()
    return CACHE_DIR / f"{h}.pkl"

def cache_get(key: str) -> Any | None:
    p = _key_to_path(key)
    if p.exists():
        with open(p, "rb") as f:
            return pickle.load(f)
    return None

def cache_set(key: str, obj: Any) -> None:
    p = _key_to_path(key)
    with open(p, "wb") as f:
        pickle.dump(obj, f)
