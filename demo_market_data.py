from datetime import date, timedelta
from src.data.market_data import MarketData
from src.data.baskets import EQ_MEGA, FX_G10, INDEX_CORE

end = date.today()
start = end - timedelta(days=30)

md = MarketData()

print("\n=== EQ prices ===")
print(md.history_prices(EQ_MEGA, start, end).tail())

print("\n=== EQ returns ===")
print(md.returns(EQ_MEGA, start, end).tail())

print("\n=== FX returns ===")
print(md.fx_returns(FX_G10.rics, start, end).tail())

print("\n=== Index prices ===")
print(md.history_prices(INDEX_CORE, start, end).tail())
