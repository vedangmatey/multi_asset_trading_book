from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

import numpy as np
import pandas as pd

from src.portfolio.book import Position, TradingBook


@dataclass
class HedgeRule:
    """
    Hedge exposure to a target factor (RIC) using a hedge instrument (RIC).

    Returns-based (EQ/FX/INDEX):
      exposure_usd = notional_usd * multiplier
      hedge notional = -exposure_usd / hedge_multiplier

    Rates (RATES):
      exposure_usd = dv01_usd_per_bp
      hedge dv01 = -exposure_usd

    proxy_beta=True (SPX proxy hedging):
      If target_factor_ric is ".SPX", compute SPX-equivalent exposure:
        SPX_equiv = sum_i exposure_i * beta_i
      where beta_i is computed from factors_df (asset return vs SPX return).
    """
    target_factor_ric: str
    hedge_factor_ric: str
    hedge_name: str = "HEDGE"
    hedge_asset_class: str = "INDEX"  # "EQ" | "FX" | "INDEX" | "RATES"
    hedge_multiplier: float = 1.0
    max_abs_notional: Optional[float] = None
    enabled: bool = True

    # NEW: compute SPX-equivalent exposure using betas from factors_df
    proxy_beta: bool = False


def _clamp(x: float, max_abs: Optional[float]) -> float:
    if max_abs is None:
        return x
    m = float(max_abs)
    if m <= 0:
        return x
    return float(np.clip(x, -m, m))


def _beta(y: pd.Series, x: pd.Series) -> float:
    """
    beta = Cov(y, x) / Var(x)
    where y and x are return series (aligned).
    """
    df = pd.concat([y, x], axis=1).dropna()
    if len(df) < 30:
        return 0.0
    yy = df.iloc[:, 0].to_numpy(dtype=float)
    xx = df.iloc[:, 1].to_numpy(dtype=float)
    vx = float(np.var(xx))
    if vx <= 0:
        return 0.0
    cov = float(np.cov(yy, xx, ddof=0)[0, 1])
    return cov / vx


def build_hedges(
    book: TradingBook,
    rules: List[HedgeRule],
    factors_df: Optional[pd.DataFrame] = None,
) -> List[Position]:
    exposures = book.exposure_by_factor()
    hedges: List[Position] = []

    for r in rules:
        if not r.enabled:
            continue

        target = (r.target_factor_ric or "").strip()
        hedge_ric = (r.hedge_factor_ric or "").strip()
        asset_class = (r.hedge_asset_class or "").upper().strip()

        if not target or not hedge_ric or asset_class not in {"EQ", "FX", "INDEX", "RATES"}:
            continue

        # --- current exposure we want to neutralize ---
        if r.proxy_beta and target == ".SPX" and factors_df is not None and ".SPX" in factors_df.columns:
            spx = factors_df[".SPX"]
            spx_equiv = 0.0

            for p in book.enabled_positions():
                if p.asset_class not in {"EQ", "INDEX"}:
                    continue
                if p.ric not in factors_df.columns:
                    continue

                if p.ric == ".SPX":
                    b = 1.0
                else:
                    b = _beta(factors_df[p.ric], spx)

                spx_equiv += float(p.exposure_usd()) * float(b)

            current_exp = float(spx_equiv)
        else:
            current_exp = float(exposures.get(target, 0.0))

        if abs(current_exp) < 1e-12:
            continue

        # --- build hedge position ---
        if asset_class == "RATES":
            # Interpret exposure as DV01 ($/bp)
            dv01 = -current_exp
            hedges.append(
                Position(
                    name=r.hedge_name,
                    asset_class="RATES",
                    ric=hedge_ric,
                    dv01_usd_per_bp=dv01,
                    notional_usd=0.0,
                    multiplier=1.0,
                    enabled=True,
                )
            )
        else:
            mult = float(r.hedge_multiplier) if float(r.hedge_multiplier) != 0.0 else 1.0
            notional = -current_exp / mult
            notional = _clamp(notional, r.max_abs_notional)

            hedges.append(
                Position(
                    name=r.hedge_name,
                    asset_class=asset_class,
                    ric=hedge_ric,
                    notional_usd=notional,
                    multiplier=mult,
                    dv01_usd_per_bp=0.0,
                    enabled=True,
                )
            )

    return hedges
