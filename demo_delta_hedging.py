import math
import random
from datetime import date

from src.instruments.equity import EquityOption
from src.pricing.equity_pricing import black_scholes_price
from src.risk.greeks import black_scholes_greeks
from src.portfolio.portfolio import Portfolio
from src.portfolio.positions import Position

print("\n=== Delta Hedging Backtest Demo ===")

# ---------- 1. Set up option portfolio ----------
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

opt_portfolio = Portfolio()
opt_portfolio.add(Position("OPT1", quantity=5))    # long 5 calls
opt_portfolio.add(Position("OPT2", quantity=-3))   # short 3 puts

# ---------- 2. Simulate price path ----------
n_days = 100
spot0 = 185.0
rate = 0.03
vol = 0.25
T0 = 0.5  # years

dt = T0 / n_days
spots = [spot0]
for _ in range(n_days):
    z = random.gauss(0.0, 1.0)
    s_next = spots[-1] * math.exp((rate - 0.5 * vol**2) * dt + vol * math.sqrt(dt) * z)
    spots.append(s_next)

# ---------- 3. Run unhedged vs delta-hedged PnL ----------
unhedged_values = []
hedged_values = []

hedge_shares = 0.0      # shares of underlying we hold as hedge
hedged_portfolio_value = 0.0

for i, s in enumerate(spots):
    ttm = max(T0 - i * dt, 0.0001)

    # price options
    p1 = black_scholes_price(s, opt1.strike, rate, vol, ttm, "call")
    p2 = black_scholes_price(s, opt2.strike, rate, vol, ttm, "put")

    # unhedged options portfolio value
    prices = {"OPT1": p1, "OPT2": p2}
    opt_value = 0.0
    for pos in opt_portfolio.positions:
        opt_value += pos.value(prices[pos.instrument_id])
    unhedged_values.append(opt_value)

    # compute portfolio delta
    g1 = black_scholes_greeks(s, opt1.strike, rate, vol, ttm, "call")
    g2 = black_scholes_greeks(s, opt2.strike, rate, vol, ttm, "put")
    portfolio_delta = opt_portfolio.total_delta({"OPT1": g1, "OPT2": g2})

    # re-hedge to delta-neutral: hedge_shares such that total delta ≈ 0
    target_hedge_shares = -portfolio_delta  # 1 share has delta = 1
    # we assume we can trade underlying at price s, no transaction costs
    hedge_trade = target_hedge_shares - hedge_shares
    hedge_shares = target_hedge_shares

    # --- transaction costs (e.g., 20 bps per notional traded) ---
    transaction_cost = abs(hedge_trade) * s * 0.002  # 0.2% = 20 bps
    
    # total value of hedged portfolio = options + hedge position
    total_hedged_value = opt_value + hedge_shares * s
    hedged_values.append(total_hedged_value)

# ---------- 4. Compute PnL series ----------
unhedged_pnls = [
    unhedged_values[i] - unhedged_values[i - 1]
    for i in range(1, len(unhedged_values))
]

hedged_pnls = [
    hedged_values[i] - hedged_values[i - 1]
    for i in range(1, len(hedged_values))
]

def summarize(label, pnls):
    avg = sum(pnls) / len(pnls)
    var = sum((x - avg) ** 2 for x in pnls) / (len(pnls) - 1)
    std = math.sqrt(var)
    print(f"\n{label}:")
    print(f"  Mean daily PnL: {avg:.4f}")
    print(f"  PnL stdev     : {std:.4f}")

summarize("Unhedged", unhedged_pnls)
summarize("Delta-hedged", hedged_pnls)
