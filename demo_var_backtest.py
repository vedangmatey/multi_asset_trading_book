import math
import random
from datetime import date

from src.instruments.equity import EquityOption
from src.pricing.equity_pricing import black_scholes_price
from src.portfolio.portfolio import Portfolio
from src.portfolio.positions import Position
from src.risk.var import historical_var

print("\n=== VaR Backtest Demo ===")

# ---------- 1. Set up portfolio (same structure as before) ----------
opt1 = EquityOption(
    id="OPT1",
    currency="USD",
    underlying="AAPL",
    strike=180,
    expiry=date(2026, 6, 19),
    option_type="call",
)

opt2 = EquityOption(
    id="OPT2",
    currency="USD",
    underlying="AAPL",
    strike=200,
    expiry=date(2026, 6, 19),
    option_type="put",
)

portfolio = Portfolio()
portfolio.add(Position("OPT1", quantity=5))    # long 5 calls
portfolio.add(Position("OPT2", quantity=-3))   # short 3 puts

# ---------- 2. Simulate underlying price path ----------
n_days = 100
spot0 = 185.0
rate = 0.03
vol = 0.25  # annual vol
T0 = 0.5    # 6 months to maturity at start

dt = T0 / n_days
spots = [spot0]

for _ in range(n_days):
    # simple GBM-ish step
    z = random.gauss(0.0, 1.0)
    spot_next = spots[-1] * math.exp((rate - 0.5 * vol ** 2) * dt + vol * math.sqrt(dt) * z)
    spots.append(spot_next)

# ---------- 3. Revalue portfolio each day, compute PnL ----------
portfolio_values = []
for i, s in enumerate(spots):
    ttm = max(T0 - i * dt, 0.0001)  # avoid zero
    price1 = black_scholes_price(s, opt1.strike, rate, vol, ttm, "call")
    price2 = black_scholes_price(s, opt2.strike, rate, vol, ttm, "put")

    # Map instrument -> price
    prices = {
        "OPT1": price1,
        "OPT2": price2,
    }

    # Compute portfolio value as sum(position * price)
    pv = 0.0
    for pos in portfolio.positions:
        pv += pos.value(prices[pos.instrument_id])

    portfolio_values.append(pv)

# PnL: day-to-day changes
pnls = []
for i in range(1, len(portfolio_values)):
    pnls.append(portfolio_values[i] - portfolio_values[i - 1])

print(f"\nSimulated {len(pnls)} daily PnL observations.")
print("First 5 PnL values:", pnls[:5])

# ---------- 4. Compute historical VaR ----------
var_95 = historical_var(pnls, confidence=0.95)
var_99 = historical_var(pnls, confidence=0.99)

print(f"\nHistorical 95% VaR: {var_95:.4f}")
print(f"Historical 99% VaR: {var_99:.4f}")
