from dataclasses import dataclass
from datetime import date
from typing import Dict, Any
from .base import Instrument


@dataclass
class Equity(Instrument):
    ticker: str

    def describe(self) -> Dict[str, Any]:
        return {
            "type": "equity",
            "id": self.id,
            "ticker": self.ticker,
            "currency": self.currency,
        }


@dataclass
class EquityOption(Instrument):
    underlying: str           # ticker
    strike: float
    expiry: date
    option_type: str          # "call" or "put"
    is_european: bool = True

    def describe(self) -> Dict[str, Any]:
        return {
            "type": "equity_option",
            "id": self.id,
            "underlying": self.underlying,
            "strike": self.strike,
            "expiry": self.expiry.isoformat(),
            "option_type": self.option_type,
            "currency": self.currency,
        }
