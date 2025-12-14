from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Protocol
import pandas as pd


class MarketDataSource(Protocol):
    """Interface that MarketData uses (Refinitiv, cache, csv, etc)."""

    def get_history(self, rics: list[str], fields: list[str], start: str, end: str, interval: str = "daily") -> pd.DataFrame:
        ...

    def get_snapshot(self, rics: list[str], fields: list[str]) -> pd.DataFrame:
        ...


@dataclass
class SourceConfig:
    mode: str  # "refinitiv" | "cache"
    cache_dir: str = "data/cache"  # relative path
    allow_write_cache: bool = True
    verbose: bool = False
