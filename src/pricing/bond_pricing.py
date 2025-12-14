import math
from datetime import date


def year_fraction(start: date, end: date) -> float:
    """Simple ACT/365 year fraction."""
    return (end - start).days / 365.0


def fixed_rate_bond_price(
    settlement: date,
    maturity: date,
    face: float,
    coupon_rate: float,
    yield_rate: float,
    frequency: int = 2,
) -> float:
    """
    Price a standard fixed-rate bond with constant yield (YTM).
    coupon_rate and yield_rate are annual decimals, frequency coupons per year.
    """
    # time between coupons
    dt = 1.0 / frequency

    # number of remaining coupons (round up)
    years_to_maturity = max(year_fraction(settlement, maturity), 0.0)
    n_coupons = max(int(round(years_to_maturity * frequency)), 0)

    coupon = face * coupon_rate / frequency
    price = 0.0

    for k in range(1, n_coupons + 1):
        t = k * dt
        disc = math.exp(-yield_rate * t)
        price += coupon * disc

    # add discounted principal at maturity
    price += face * math.exp(-yield_rate * years_to_maturity)

    return price


def fixed_rate_bond_dv01(
    settlement: date,
    maturity: date,
    face: float,
    coupon_rate: float,
    yield_rate: float,
    frequency: int = 2,
    bump: float = 0.0001,   # 1bp
) -> float:
    """
    DV01 ≈ -(dPrice/dYield) * 0.0001.
    We approximate derivative using bump-and-reprice.
    """
    p0 = fixed_rate_bond_price(settlement, maturity, face, coupon_rate, yield_rate, frequency)
    p_up = fixed_rate_bond_price(settlement, maturity, face, coupon_rate, yield_rate + bump, frequency)
    # price change for +1bp
    dP = p_up - p0
    # DV01 is price change for +1bp, usually reported as positive number for long bond
    return -dP
