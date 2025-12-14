from src.data.market_data import Basket

# Rates proxies that are entitled on your account:
# .IRX (13-week), .TNX (10Y), .TYX (30Y) – yield indices
RATES_US_YIELD_IDX = Basket(
    name="RATES_US_YIELD_IDX",
    asset_class="RATES",
    rics=[".IRX", ".TNX", ".TYX"],
    history_field="TR.PriceClose",
)
