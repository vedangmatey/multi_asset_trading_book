print(">>> Script Started")

from datetime import date
from src.instruments.equity import EquityOption
from src.pricing.equity_pricing import black_scholes_price
from src.risk.greeks import black_scholes_greeks

print(">>> Modules imported successfully")

opt = EquityOption(
    id="OPT1",
    currency="USD",
    underlying="AAPL",
    strike=180,
    expiry=date(2026, 6, 19),
    option_type="call"
)

print(">>> Option Created:", opt.describe())

spot = 185.0
rate = 0.03
vol = 0.25
ttm = 0.5  # 6 months

price = black_scholes_price(spot, opt.strike, rate, vol, ttm, opt.option_type)
greeks = black_scholes_greeks(spot, opt.strike, rate, vol, ttm, opt.option_type)

print("\nRESULTS")
print("Price:", price)
print("Greeks:", greeks)
print("\n>>> Script Completed")
