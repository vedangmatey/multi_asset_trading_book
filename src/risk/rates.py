from datetime import date
from src.pricing.bond_pricing import fixed_rate_bond_price, fixed_rate_bond_dv01


def bond_price_and_dv01(
    settlement: date,
    maturity: date,
    face: float,
    coupon_rate: float,
    yield_rate: float,
    frequency: int = 2,
):
    """
    Convenience wrapper that returns both price and DV01.
    """
    price = fixed_rate_bond_price(settlement, maturity, face, coupon_rate, yield_rate, frequency)
    dv01 = fixed_rate_bond_dv01(settlement, maturity, face, coupon_rate, yield_rate, frequency)
    return price, dv01
