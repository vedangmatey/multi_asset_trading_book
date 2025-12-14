from datetime import date
from src.instruments.equity import EquityOption
from src.pricing.equity_pricing import black_scholes_price
from src.risk.greeks import black_scholes_greeks
from src.portfolio.portfolio import Portfolio
from src.portfolio.positions import Position

print("\n=== Portfolio Risk Test ===")

# Two option positions
opt1 = EquityOption(id="OPT1", currency="USD", underlying="AAPL", strike=180, expiry=date(2026,6,19), option_type="call")
opt2 = EquityOption(id="OPT2", currency="USD", underlying="AAPL", strike=200, expiry=date(2026,6,19), option_type="put")

spot = 185.0
rate = 0.03
vol = 0.25
ttm = 0.5

# Calculate Greeks
g1 = black_scholes_greeks(spot, opt1.strike, rate, vol, ttm, "call")
g2 = black_scholes_greeks(spot, opt2.strike, rate, vol, ttm, "put")

# Create portfolio
p = Portfolio()
p.add(Position("OPT1", quantity=5))   # long 5 calls
p.add(Position("OPT2", quantity=-3))  # short 3 puts

# Aggregate
combined = p.total_greeks({"OPT1": g1, "OPT2": g2})

print("\nPortfolio Combined Greeks:")
for k, v in combined.items():
    print(f"{k}: {v}")



combined = p.total_greeks({"OPT1": g1, "OPT2": g2})

print("\nDEBUG:", combined)  # <- should print a dictionary, NOT {}

print("\nPortfolio Combined Greeks:")
for k, v in combined.items():
    print(f"{k}: {v}")
