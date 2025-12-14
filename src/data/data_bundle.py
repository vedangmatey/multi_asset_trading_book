from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, List
from datetime import date

import pandas as pd
from src.data.market_data import MarketData, Basket, DateLike

@dataclass
class DataBundle:
    snapshots: Dict[str, pd.DataFrame]
    prices: Dict[str, pd.DataFrame]
    returns: Dict[str, pd.DataFrame]

def fetch_bundle(
    baskets: List[Basket],
    start: DateLike,
    end: DateLike,
) -> DataBundle:
    md = MarketData()
    snaps, px, rets = {}, {}, {}

    for b in baskets:
        snaps[b.name] = md.snapshot(b)
        px[b.name] = md.history_prices(b, start=start, end=end)
        rets[b.name] = md.returns(b, start=start, end=end)

    return DataBundle(snapshots=snaps, prices=px, returns=rets)
