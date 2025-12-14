from datetime import date, timedelta
from src.data.market_data import MarketData
from src.data.baskets import RATES_UST

end = date.today()
start = end - timedelta(days=60)

md = MarketData()

print("\n=== UST yield levels (tail) ===")
y = md.rates_level_series(RATES_UST, start, end)
print(y.tail())

print("\n=== UST daily changes (bps) (tail) ===")
dy = md.rate_changes_bps(RATES_UST, start, end, input_units="percent")
print(dy.tail())
