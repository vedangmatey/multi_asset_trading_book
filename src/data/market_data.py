from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, List, Optional, Union

import numpy as np
import pandas as pd

from src.data.refinitiv_loader import RefinitivLoader, RDLConfig, DateLike


# -----------------------------
# Basket definition
# -----------------------------
@dataclass(frozen=True)
class Basket:
    name: str
    rics: List[str]
    asset_class: str           # "EQ", "FX", "RATES", "INDEX"
    history_field: str = "TR.PriceClose"


# -----------------------------
# Mock/local loader (Step 4 toggle)
# -----------------------------
class MockLoader:
    """
    Minimal fallback backend when Refinitiv is OFF.
    For now: returns empty frames (or simple synthetic data).
    Later: replace with CSV cache loader.
    """

    def __enter__(self) -> "MockLoader":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        return None

    def get_snapshot(self, universe: Union[str, Iterable[str]], fields: Union[str, Iterable[str]]) -> pd.DataFrame:
        # Return empty but valid schema
        u = [universe] if isinstance(universe, str) else list(universe)
        f = [fields] if isinstance(fields, str) else list(fields)
        cols = ["Instrument"] + f
        return pd.DataFrame({"Instrument": u}).reindex(columns=cols)

    def get_history(
        self,
        universe: Union[str, Iterable[str]],
        fields: Union[str, Iterable[str]],
        start: DateLike,
        end: DateLike,
        interval: str = "daily",
    ) -> pd.DataFrame:
        # Empty dataframe with Date index and column structure similar to rd.get_history output
        u = [universe] if isinstance(universe, str) else list(universe)
        f = [fields] if isinstance(fields, str) else list(fields)

        idx = pd.date_range(pd.to_datetime(start), pd.to_datetime(end), freq="B")
        if len(idx) == 0:
            return pd.DataFrame()

        cols = pd.MultiIndex.from_product([f, u])
        df = pd.DataFrame(index=idx, columns=cols, dtype=float)
        return df


# -----------------------------
# Unified Market Data Layer
# -----------------------------
class MarketData:
    """
    Unified interface used by:
    - pricing
    - VaR / risk
    - backtesting
    - dashboard

    Supports data source switching:
      source="refinitiv" -> RefinitivLoader
      source="mock"      -> MockLoader (placeholder for local/CSV later)
    """

    def __init__(self, loader_cfg: Optional[RDLConfig] = None, source: str = "refinitiv"):
        self.loader_cfg = loader_cfg or RDLConfig()
        self.source = source.lower().strip()

        if self.source not in {"refinitiv", "mock"}:
            raise ValueError("source must be 'refinitiv' or 'mock'")

        # For UI warning banners (FX MID fallback)
        self._fx_price_field_requested: Optional[str] = None
        self._fx_price_field_used: Optional[str] = None

    # -------- Loader factory --------
    def _loader(self):
        if self.source == "refinitiv":
            return RefinitivLoader(self.loader_cfg)
        return MockLoader()

    # -----------------------------
    # Rates helpers (yield indices)
    # -----------------------------
    def rates_levels(
        self,
        rates_basket: Basket,
        start: DateLike,
        end: DateLike,
        interval: str = "daily",
    ) -> pd.DataFrame:
        """Rates levels for proxies like .TNX/.TYX/.IRX (yield indices)."""
        return self.history_prices(rates_basket, start=start, end=end, interval=interval)

    def rates_changes_bps(
        self,
        rates_basket: Basket,
        start: DateLike,
        end: DateLike,
        interval: str = "daily",
        fill_method: str = "ffill",
        dropna: bool = True,
        quote_mode: str = "cboe_x10",  # "cboe_x10" or "percent" or "decimal"
    ) -> pd.DataFrame:
        """
        Daily yield changes in bps from yield-index levels.

        quote_mode:
          - "cboe_x10": indices quoted as yield*10 (e.g., 41.94 means 4.194%)
                        bps change = Δ(level) * 10
          - "percent":  levels in percent (e.g., 4.194) -> bps = Δ * 100
          - "decimal":  levels in decimal (e.g., 0.04194) -> bps = Δ * 10000
        """
        y = self.rates_levels(rates_basket, start=start, end=end, interval=interval)

        if fill_method == "ffill":
            y = y.ffill()

        if quote_mode == "cboe_x10":
            dy_bps = (y - y.shift(1)) * 10.0
        elif quote_mode == "percent":
            dy_bps = (y - y.shift(1)) * 100.0
        elif quote_mode == "decimal":
            dy_bps = (y - y.shift(1)) * 10000.0
        else:
            raise ValueError("quote_mode must be 'cboe_x10', 'percent', or 'decimal'")

        if dropna:
            dy_bps = dy_bps.dropna(how="all")

        return dy_bps

    # -------- Helpers --------
    def _normalize_fx_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Normalize FX history columns so we end up with only RIC columns (EUR=, JPY=, ...).
        Handles:
          - MultiIndex columns like (BID, EUR=)
          - a top label/name like "BID" appearing in printed output
        """
        if df is None or df.empty:
            return df

        if isinstance(df.columns, pd.MultiIndex):
            df = df.droplevel(0, axis=1)

        if getattr(df.columns, "name", None) in {"BID", "ASK", "MID", "Price Close"}:
            df = df.copy()
            df.columns.name = None

        return df

    # -------- SNAPSHOT --------
    def snapshot(self, basket: Basket) -> pd.DataFrame:
        with self._loader() as rdl:
            if basket.asset_class in ("EQ", "INDEX"):
                return rdl.get_snapshot(
                    basket.rics,
                    ["TR.PriceClose", "TR.Volume", "TR.CompanyMarketCap"],
                )
            elif basket.asset_class == "FX":
                return rdl.get_snapshot(basket.rics, ["BID", "ASK"])
            else:
                return rdl.get_snapshot(basket.rics, [basket.history_field])

    # -------- PRICES (HISTORY) --------
    def history_prices(
        self,
        basket: Basket,
        start: DateLike,
        end: DateLike,
        interval: str = "daily",
    ) -> pd.DataFrame:
        """
        Returns a wide dataframe:
          index = Date
          columns = RICs

        FIX:
          FX baskets may NOT support MID in Refinitiv universe.
          For FX only, we do robust fallback:
             try MID -> if 90006 -> compute (BID+ASK)/2
        """
        asset_class = str(getattr(basket, "asset_class", "")).upper().strip()

        # Reset meta each call (useful for UI warnings)
        self._fx_price_field_requested = None
        self._fx_price_field_used = None

        # -------------------------
        # FX: MID -> BID/ASK fallback
        # -------------------------
        if asset_class == "FX":
            self._fx_price_field_requested = basket.history_field or "MID"

            # 1) Try MID explicitly (DO NOT use basket.history_field blindly)
            try:
                with self._loader() as rdl:
                    hist_mid = rdl.get_history(
                        universe=basket.rics,
                        fields=["MID"],
                        start=start,
                        end=end,
                        interval=interval,
                    )

                hist_mid = self._normalize_fx_columns(hist_mid)
                if hist_mid is not None and not hist_mid.empty:
                    hist_mid.index = pd.to_datetime(hist_mid.index)
                    hist_mid = hist_mid.sort_index()
                    hist_mid = hist_mid.apply(pd.to_numeric, errors="coerce")
                    if not hist_mid.isna().all().all():
                        self._fx_price_field_used = "MID"
                        return hist_mid

            except Exception as e:
                msg = str(e)
                # Only fallback on MID-field universe errors
                if ("90006" not in msg) and ("does not support the following fields" not in msg):
                    raise

            # 2) Fallback: BID / ASK midpoint
            with self._loader() as rdl:
                bid = rdl.get_history(
                    universe=basket.rics,
                    fields=["BID"],
                    start=start,
                    end=end,
                    interval=interval,
                )
                ask = rdl.get_history(
                    universe=basket.rics,
                    fields=["ASK"],
                    start=start,
                    end=end,
                    interval=interval,
                )

            bid = self._normalize_fx_columns(bid)
            ask = self._normalize_fx_columns(ask)

            if bid is None or bid.empty or ask is None or ask.empty:
                return pd.DataFrame()

            bid.index = pd.to_datetime(bid.index)
            ask.index = pd.to_datetime(ask.index)

            bid = bid.sort_index().apply(pd.to_numeric, errors="coerce")
            ask = ask.sort_index().apply(pd.to_numeric, errors="coerce")

            mid = (bid + ask) / 2.0
            mid = mid.dropna(axis=0, how="all")

            self._fx_price_field_used = "BID/ASK midpoint"
            return mid

        # -------------------------
        # Non-FX: use basket.history_field as before
        # -------------------------
        with self._loader() as rdl:
            hist = rdl.get_history(
                universe=basket.rics,
                fields=[basket.history_field],
                start=start,
                end=end,
                interval=interval,
            )

        if hist is None or hist.empty:
            return pd.DataFrame()

        if isinstance(hist.columns, pd.MultiIndex):
            hist = hist.droplevel(0, axis=1)

        hist.index = pd.to_datetime(hist.index)
        hist = hist.sort_index()
        hist = hist.apply(pd.to_numeric, errors="coerce")
        return hist

    # -------- RETURNS (PRICE-BASED) --------
    def returns(
        self,
        basket: Basket,
        start: DateLike,
        end: DateLike,
        method: str = "log",
        fill_method: str = "ffill",
        dropna: bool = True,
    ) -> pd.DataFrame:
        """
        For price-based assets (EQ/INDEX/etc): returns from price series.
        For FX and RATES, prefer fx_returns() / rates_changes_bps().
        """
        px = self.history_prices(basket, start=start, end=end)

        if px.empty:
            return pd.DataFrame()

        if fill_method == "ffill":
            px = px.ffill()

        if method == "log":
            rets = np.log(px / px.shift(1))
        elif method == "simple":
            rets = px.pct_change()
        else:
            raise ValueError("method must be 'log' or 'simple'")

        if dropna:
            rets = rets.dropna(how="all")

        return rets

    # =========================
    # FX: mid fallback + returns
    # =========================
    def fx_mid_series(
        self,
        fx_rics: List[str],
        start: DateLike,
        end: DateLike,
        interval: str = "daily",
    ) -> pd.DataFrame:
        """
        Returns Date x FX_RIC mid series.
        Tries MID first; if MID not supported, computes (BID + ASK) / 2.
        """
        # Use the same logic as history_prices FX path by calling a temp FX basket
        b = Basket("FX_TMP", fx_rics, "FX", "MID")
        mid = self.history_prices(b, start=start, end=end, interval=interval)
        return self._normalize_fx_columns(mid).sort_index()

    def fx_returns(
        self,
        fx_rics: List[str],
        start: DateLike,
        end: DateLike,
        method: str = "log",
        fill_method: str = "ffill",
        dropna: bool = True,
    ) -> pd.DataFrame:
        mid = self.fx_mid_series(fx_rics, start=start, end=end).copy()

        if mid.empty:
            return pd.DataFrame()

        if fill_method == "ffill":
            mid = mid.ffill()

        if method == "log":
            rets = np.log(mid / mid.shift(1))
        elif method == "simple":
            rets = mid.pct_change()
        else:
            raise ValueError("method must be 'log' or 'simple'")

        if dropna:
            rets = rets.dropna(how="all")

        return rets

    # =========================
    # Rates: yield levels + bps changes (generic fields)
    # =========================
    def rates_level_series(
        self,
        rate_basket: Basket,
        start: DateLike,
        end: DateLike,
        interval: str = "daily",
    ) -> pd.DataFrame:
        """
        Returns Date x Rate_RIC yield/level series (numeric).
        Tries multiple common yield fields until one works with your entitlement.
        """
        candidate_fields = [
            rate_basket.history_field,
            "TR.FiCloseYield",
            "TR.FiMidYield",
            "TR.FiYield",
            "TRD.Yield",
            "YIELD",
        ]

        last_err: Exception | None = None

        for field in candidate_fields:
            try:
                b = Basket(
                    name=rate_basket.name,
                    asset_class=rate_basket.asset_class,
                    rics=rate_basket.rics,
                    history_field=field,
                )
                df = self.history_prices(b, start=start, end=end, interval=interval)
                if not df.empty and not df.isna().all().all():
                    return df
            except Exception as e:
                last_err = e
                continue

        raise RuntimeError(
            "Could not fetch a usable rates series. Tried fields: "
            + ", ".join(candidate_fields)
        ) from last_err

    def rate_changes_bps(
        self,
        rate_basket: Basket,
        start: DateLike,
        end: DateLike,
        interval: str = "daily",
        fill_method: str = "ffill",
        dropna: bool = True,
        input_units: str = "percent",  # "percent" or "decimal"
    ) -> pd.DataFrame:
        """
        If yields are in percent (e.g., 4.25), bps change = Δ * 100.
        If yields are in decimal (e.g., 0.0425), bps change = Δ * 10000.
        """
        y = self.rates_level_series(rate_basket, start=start, end=end, interval=interval)

        if y.empty:
            return pd.DataFrame()

        if fill_method == "ffill":
            y = y.ffill()

        scale = 100.0 if input_units == "percent" else 10000.0
        dy_bps = (y - y.shift(1)) * scale

        if dropna:
            dy_bps = dy_bps.dropna(how="all")

        return dy_bps

    # =========================
    # Rates: futures proxies (prices/returns/DV01 scaling)
    # =========================
    def rates_prices(
        self,
        rates_basket: Basket,
        start: DateLike,
        end: DateLike,
        interval: str = "daily",
    ) -> pd.DataFrame:
        px = self.history_prices(rates_basket, start=start, end=end, interval=interval)
        return px

    def rates_returns(
        self,
        rates_basket: Basket,
        start: DateLike,
        end: DateLike,
        method: str = "log",
        fill_method: str = "ffill",
        dropna: bool = True,
    ) -> pd.DataFrame:
        return self.returns(
            rates_basket,
            start=start,
            end=end,
            method=method,
            fill_method=fill_method,
            dropna=dropna,
        )

    def rates_dv01_scaled_returns(
        self,
        rates_basket: Basket,
        start: DateLike,
        end: DateLike,
        dv01_map: dict[str, float] | None = None,
        method: str = "log",
    ) -> pd.DataFrame:
        rets = self.rates_returns(rates_basket, start=start, end=end, method=method)
        if rets.empty:
            return pd.DataFrame()

        default_dv01 = {
            "TUc1": 40.0,
            "FVc1": 55.0,
            "TYc1": 80.0,
            "USc1": 160.0,
        }
        dv01 = dv01_map or default_dv01

        scaled = rets.copy()
        for c in scaled.columns:
            scaled[c] = scaled[c] * float(dv01.get(c, 1.0))

        return scaled
