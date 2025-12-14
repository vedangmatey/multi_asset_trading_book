from datetime import date

from src.instruments.equity import EquityOption
from src.instruments.bond import FixedRateBond

from src.pricing.equity_pricing import black_scholes_price
from src.risk.greeks import black_scholes_greeks

from src.pricing.bond_pricing import fixed_rate_bond_price, fixed_rate_bond_dv01

from src.portfolio.portfolio import Portfolio
from src.portfolio.positions import Position


print("\n=== MULTI-ASSET TRADING BOOK DEMO (Equity + Rates) ===")

# -----------------------------
# 1) Define instruments
# -----------------------------
# Equity options
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

# Bonds
settlement = date(2025, 12, 5)
bond1 = FixedRateBond(
    id="BOND1",
    currency="USD",
    face=1000.0,
    coupon_rate=0.04,
    maturity=date(2030, 12, 31),
    frequency=2,
)
bond2 = FixedRateBond(
    id="BOND2",
    currency="USD",
    face=1000.0,
    coupon_rate=0.06,
    maturity=date(2035, 12, 31),
    frequency=2,
)

# -----------------------------
# 2) Build ONE multi-asset portfolio
# -----------------------------
book = Portfolio()

# Equity positions
book.add(Position("OPT1", quantity=5))    # long 5 calls
book.add(Position("OPT2", quantity=-3))   # short 3 puts

# Rates positions
book.add(Position("BOND1", quantity=50))   # long 50 bonds
book.add(Position("BOND2", quantity=-30))  # short 30 bonds

# -----------------------------
# 3) Market inputs (base)
# -----------------------------
spot0 = 185.0
rf = 0.03
vol = 0.25
ttm = 0.5  # years

y1 = 0.035  # bond1 yield
y2 = 0.045  # bond2 yield

# Shocks
eq_shock_pct = -0.05      # -5% equity shock
rate_shock_bp = 50        # +50bp rate shock
rate_shock = rate_shock_bp / 10000.0

# -----------------------------
# 4) Helper: price + risk for given market state
# -----------------------------
def price_and_risk(spot, y1_in, y2_in):
    # Option prices
    opt1_price = black_scholes_price(spot, opt1.strike, rf, vol, ttm, "call")
    opt2_price = black_scholes_price(spot, opt2.strike, rf, vol, ttm, "put")

    # Option greeks
    g1 = black_scholes_greeks(spot, opt1.strike, rf, vol, ttm, "call")
    g2 = black_scholes_greeks(spot, opt2.strike, rf, vol, ttm, "put")

    # Bond prices
    b1_price = fixed_rate_bond_price(settlement, bond1.maturity, bond1.face, bond1.coupon_rate, y1_in, bond1.frequency)
    b2_price = fixed_rate_bond_price(settlement, bond2.maturity, bond2.face, bond2.coupon_rate, y2_in, bond2.frequency)

    # Bond DV01 (instrument-level)
    dv01_1 = fixed_rate_bond_dv01(settlement, bond1.maturity, bond1.face, bond1.coupon_rate, y1_in, bond1.frequency)
    dv01_2 = fixed_rate_bond_dv01(settlement, bond2.maturity, bond2.face, bond2.coupon_rate, y2_in, bond2.frequency)

    # Price map for valuation
    prices = {
        "OPT1": opt1_price,
        "OPT2": opt2_price,
        "BOND1": b1_price,
        "BOND2": b2_price,
    }

    # Risk map (combine Greeks + DV01 into one dict)
    risk_map = {
        "OPT1": g1,
        "OPT2": g2,
        "BOND1": {"dv01": dv01_1},
        "BOND2": {"dv01": dv01_2},
    }

    # Portfolio value
    pv = 0.0
    for pos in book.positions:
        pv += pos.value(prices[pos.instrument_id])

    # Portfolio risks (aggregated)
    total_risk = book.total_greeks(risk_map)

    return pv, total_risk, prices


# -----------------------------
# 5) Base valuation + risk report
# -----------------------------
pv0, risk0, prices0 = price_and_risk(spot0, y1, y2)

print("\n--- BASE STATE ---")
print(f"Spot: {spot0:.4f} | y1: {y1:.4%} | y2: {y2:.4%}")
print(f"Portfolio Value: {pv0:.4f}")

print("\nPortfolio Risk (Greeks + DV01):")
for k in ["delta", "gamma", "vega", "theta", "rho", "dv01"]:
    if k in risk0:
        print(f"{k}: {risk0[k]:.6f}")

# -----------------------------
# 6) Scenario analysis
# -----------------------------
# Equity-only shock
spot_eq = spot0 * (1.0 + eq_shock_pct)
pv_eq, risk_eq, _ = price_and_risk(spot_eq, y1, y2)
pnl_eq = pv_eq - pv0

# Rates-only shock
pv_rt, risk_rt, _ = price_and_risk(spot0, y1 + rate_shock, y2 + rate_shock)
pnl_rt = pv_rt - pv0

# Combined shock
pv_cb, risk_cb, _ = price_and_risk(spot_eq, y1 + rate_shock, y2 + rate_shock)
pnl_cb = pv_cb - pv0

print("\n--- SCENARIO RESULTS ---")
print(f"Equity shock: {eq_shock_pct*100:.2f}% (spot {spot0:.2f} -> {spot_eq:.2f})")
print(f"Rates shock : +{rate_shock_bp}bp")

print("\nPnL by scenario:")
print(f"Equity-only shock PnL   : {pnl_eq:.4f}")
print(f"Rates-only shock PnL    : {pnl_rt:.4f}")
print(f"Combined shock PnL      : {pnl_cb:.4f}")

print("\nNon-additivity check (combined vs sum of parts):")
print(f"Combined - (Eq + Rates) : {pnl_cb - (pnl_eq + pnl_rt):.6f}")

print("\nDone.")
