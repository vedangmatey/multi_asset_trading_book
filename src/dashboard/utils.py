from __future__ import annotations

from datetime import date
import streamlit as st
import pandas as pd

from src.data.market_data import MarketData
from src.data.baskets import EQ_MEGA, FX_G10, INDEX_CORE
from src.data.baskets_rates import RATES_US_YIELD_IDX


BASKETS = {
    "Equities: EQ_MEGA (AAPL/MSFT/AMZN/GOOGL)": EQ_MEGA,
    "FX: FX_G10 (EUR/JPY/GBP/CHF/CAD/AUD/NZD)": FX_G10,
    "Indices: INDEX_CORE (.SPX/.NDX)": INDEX_CORE,
    "Rates: RATES_US_YIELD_IDX (.IRX/.TNX/.TYX)": RATES_US_YIELD_IDX,
}


@st.cache_data(show_spinner=False, ttl=60 * 30)
def fetch_prices(basket_key: str, start: date, end: date, data_source: str) -> pd.DataFrame:
    md = MarketData(source=data_source)
    b = BASKETS[basket_key]
    df = md.history_prices(b, start=start, end=end)

    # Save FX field info for UI banner
    if str(getattr(b, "asset_class", "")).upper() == "FX":
        st.session_state["FX_PRICE_FIELD_REQUESTED"] = getattr(md, "_fx_price_field_requested", None)
        st.session_state["FX_PRICE_FIELD_USED"] = getattr(md, "_fx_price_field_used", None)

    if df is None:
        return pd.DataFrame()
    if isinstance(df.columns, pd.MultiIndex):
        df = df.droplevel(0, axis=1)
    return df


@st.cache_data(show_spinner=False, ttl=60 * 30)
def fetch_factor(basket_key: str, start: date, end: date, data_source: str) -> pd.DataFrame:
    md = MarketData(source=data_source)
    b = BASKETS[basket_key]

    if b.asset_class == "RATES":
        df = md.rates_changes_bps(b, start=start, end=end, quote_mode="cboe_x10")
    elif b.asset_class == "FX":
        df = md.fx_returns(b.rics, start=start, end=end, method="log")
    else:
        df = md.returns(b, start=start, end=end, method="log")

    if df is None:
        return pd.DataFrame()
    if isinstance(df.columns, pd.MultiIndex):
        df = df.droplevel(0, axis=1)
    return df


def get_data_source() -> str:
    return st.session_state.get("DATA_SOURCE", "refinitiv")
