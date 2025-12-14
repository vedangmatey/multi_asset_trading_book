from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List
import numpy as np
import pandas as pd


@dataclass
class Position:
    """
    A desk-style position mapped to ONE risk factor series (by RIC).
    For returns-based factors: exposure_usd = notional_usd * multiplier (delta/beta)
      pnl_t = exposure_usd * factor_t
    For rates bps factors: exposure_usd = dv01_usd_per_bp
      pnl_t = exposure_usd * factor_t   (factor_t is bps change)
    """
    name: str
    asset_class: str   # "EQ" | "FX" | "INDEX" | "RATES"
    ric: str           # factor identifier
    notional_usd: float = 0.0
    multiplier: float = 1.0           # delta/beta/weight for returns-based
    dv01_usd_per_bp: float = 0.0      # for RATES
    enabled: bool = True

    def exposure_usd(self) -> float:
        if self.asset_class == "RATES":
            return float(self.dv01_usd_per_bp)
        return float(self.notional_usd) * float(self.multiplier)


class TradingBook:
    def __init__(self, positions: List[Position]):
        self.positions = positions

    def enabled_positions(self) -> List[Position]:
        return [p for p in self.positions if p.enabled]

    def exposure_by_factor(self) -> Dict[str, float]:
        """
        Sum exposures by factor RIC.
        Returns-based: $ exposure per 1.0 return
        Rates: $ exposure per 1bp
        """
        out: Dict[str, float] = {}
        for p in self.enabled_positions():
            out[p.ric] = out.get(p.ric, 0.0) + p.exposure_usd()
        return out

    def pnl_matrix(self, factor_df: pd.DataFrame) -> pd.DataFrame:
        """
        Build instrument PnL series: one column per position (name).
        Requires factor_df columns contain the RICs used by positions.
        """
        pnl_cols = {}
        for p in self.enabled_positions():
            if p.ric not in factor_df.columns:
                continue
            pnl_cols[p.name] = factor_df[p.ric] * p.exposure_usd()

        if not pnl_cols:
            return pd.DataFrame(index=factor_df.index)

        pnl = pd.DataFrame(pnl_cols, index=factor_df.index)
        return pnl

    def portfolio_pnl(self, factor_df: pd.DataFrame) -> pd.Series:
        pnl = self.pnl_matrix(factor_df)
        if pnl.empty:
            return pd.Series(index=factor_df.index, dtype=float, name="PortfolioPnL")
        return pnl.sum(axis=1).rename("PortfolioPnL")

    @staticmethod
    def historical_var(pnl: pd.Series, alpha: float = 0.99) -> float:
        """
        1-day historical VaR on PnL (loss is negative).
        Returns a positive dollar VaR.
        """
        x = pnl.dropna().values
        if len(x) < 30:
            return float("nan")
        q = np.quantile(x, 1 - alpha)
        return float(-q)
