from datetime import date, timedelta

from src.data.market_data import MarketData
from src.data.baskets_rates import RATES_UST_FUTURES

end = date.today()
start = end - timedelta(days=60)

md = MarketData()

print("\n=== Rates (Treasury futures) prices (tail) ===")
px = md.rates_prices(RATES_UST_FUTURES, start, end)
print(px.tail())

print("\n=== Rates (Treasury futures) returns (tail) ===")
rets = md.rates_returns(RATES_UST_FUTURES, start, end, method="log")
print(rets.tail())

print("\n=== Rates DV01-scaled returns (tail) ===")
scaled = md.rates_dv01_scaled_returns(RATES_UST_FUTURES, start, end)
print(scaled.tail())
