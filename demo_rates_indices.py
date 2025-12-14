from datetime import date, timedelta
from src.data.market_data import MarketData
from src.data.baskets_rates import RATES_US_YIELD_IDX

end = date.today()
start = end - timedelta(days=180)

md = MarketData()

print("\n=== Rates (yield index) levels (tail) ===")
levels = md.rates_levels(RATES_US_YIELD_IDX, start, end)
print(levels.tail())

print("\n=== Rates (yield index) daily changes (bps) (tail) ===")

chg = md.rates_changes_bps(RATES_US_YIELD_IDX, start, end, quote_mode="cboe_x10")

print(chg.tail())
