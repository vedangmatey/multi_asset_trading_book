from dataclasses import dataclass
from datetime import date
from typing import Dict, Any
from .base import Instrument


@dataclass
class FixedRateBond(Instrument):
    """
    Simple fixed-rate bond, with coupon paid at a constant frequency.
    All rates will be treated as annualized decimals (e.g. 0.05 = 5%).
    """
    face: float            # notional / par value
    coupon_rate: float     # annual coupon rate, e.g. 0.05 for 5%
    maturity: date
    frequency: int = 2     # coupon payments per year (2 = semi-annual)

    def describe(self) -> Dict[str, Any]:
        return {
            "type": "fixed_rate_bond",
            "id": self.id,
            "currency": self.currency,
            "face": self.face,
            "coupon_rate": self.coupon_rate,
            "maturity": self.maturity.isoformat(),
            "frequency": self.frequency,
        }
