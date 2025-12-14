from datetime import date

from src.instruments.bond import FixedRateBond
from src.portfolio.portfolio import Portfolio
from src.portfolio.positions import Position
from src.pricing.bond_pricing import fixed_rate_bond_price, fixed_rate_bond_dv01

print("\n=== Bond Portfolio Rates Risk Demo ===")

settlement = date(2025, 12, 5)

# Two simple USD bonds
bond1 = FixedRateBond(
    id="BOND1",
    currency="USD",
    face=1000.0,
    coupon_rate=0.04,              # 4% coupon
    maturity=date(2030, 12, 31),
    frequency=2,
)

bond2 = FixedRateBond(
    id="BOND2",
    currency="USD",
    face=1000.0,
    coupon_rate=0.06,              # 6% coupon
    maturity=date(2035, 12, 31),
    frequency=2,
)

# Yields (flat curve for simplicity)
y1 = 0.035   # 3.5%
y2 = 0.045   # 4.5%

p1 = fixed_rate_bond_price(settlement, bond1.maturity, bond1.face, bond1.coupon_rate, y1, bond1.frequency)
p2 = fixed_rate_bond_price(settlement, bond2.maturity, bond2.face, bond2.coupon_rate, y2, bond2.frequency)

dv01_1 = fixed_rate_bond_dv01(settlement, bond1.maturity, bond1.face, bond1.coupon_rate, y1, bond1.frequency)
dv01_2 = fixed_rate_bond_dv01(settlement, bond2.maturity, bond2.face, bond2.coupon_rate, y2, bond2.frequency)

print(f"\nBond 1 price: {p1:.4f}, DV01: {dv01_1:.4f}")
print(f"Bond 2 price: {p2:.4f}, DV01: {dv01_2:.4f}")

# Build a rates portfolio
port = Portfolio()
port.add(Position("BOND1", quantity=50))   # long 50 of bond1
port.add(Position("BOND2", quantity=-30))  # short 30 of bond2

# Instrument-level DV01 map
dv01_map = {
    "BOND1": {"dv01": dv01_1},
    "BOND2": {"dv01": dv01_2},
}

# Reuse total_greeks to aggregate DV01 (treat dv01 as a "Greek")
total_rates_risk = port.total_greeks(dv01_map)

print("\nPortfolio DV01 (approx total price change for +1bp):")
print(f"Total DV01: {total_rates_risk.get('dv01', 0.0):.4f}")

# Simple parallel rate shock of +50bp
shock_bp = 50
p1_up = fixed_rate_bond_price(settlement, bond1.maturity, bond1.face, bond1.coupon_rate, y1 + shock_bp / 10000, bond1.frequency)
p2_up = fixed_rate_bond_price(settlement, bond2.maturity, bond2.face, bond2.coupon_rate, y2 + shock_bp / 10000, bond2.frequency)

port_value_0 = 50 * p1 + (-30) * p2
port_value_up = 50 * p1_up + (-30) * p2_up
shock_pnl = port_value_up - port_value_0

print(f"\nParallel +{shock_bp}bp shock PnL: {shock_pnl:.4f}")
print("DV01 * 50bp (approx):", total_rates_risk.get('dv01', 0.0) * shock_bp)
