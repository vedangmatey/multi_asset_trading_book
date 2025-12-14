from __future__ import annotations

from datetime import date, timedelta
import numpy as np
import pandas as pd
import streamlit as st

from src.data.market_data import MarketData, Basket
from src.portfolio.book import Position, TradingBook


st.title("Risk Limits — VaR / ES / Stress Headroom")


def get_md() -> MarketData:
    src = st.session_state.get("DATA_SOURCE", "refinitiv")
    return MarketData(source=src)

def factor_series_for_positions(md: MarketData, positions: list[Position], start: date, end: date) -> pd.DataFrame:
    eq_rics = sorted({p.ric for p in positions if p.enabled and p.asset_class in ("EQ", "INDEX")})
    fx_rics = sorted({p.ric for p in positions if p.enabled and p.asset_class == "FX"})
    r_rics  = sorted({p.ric for p in positions if p.enabled and p.asset_class == "RATES"})

    frames = []
    if eq_rics:
        b = Basket(name="EQ_INDEX_FACTORS", rics=eq_rics, asset_class="INDEX", history_field="TR.PriceClose")
        frames.append(md.returns(b, start=start, end=end, method="log"))
    if fx_rics:
        frames.append(md.fx_returns(fx_rics, start=start, end=end, method="log"))
    if r_rics:
        rb = Basket(name="RATES_FACTORS", rics=r_rics, asset_class="RATES", history_field="TR.PriceClose")
        frames.append(md.rates_changes_bps(rb, start=start, end=end, quote_mode="cboe_x10"))

    if not frames:
        return pd.DataFrame()

    factors = pd.concat(frames, axis=1).sort_index()
    return factors.dropna(axis=1, how="all").dropna(axis=0, how="any")


def historical_es(pnl: pd.Series, alpha: float) -> float:
    x = pnl.dropna().values
    if len(x) < 30:
        return float("nan")
    q = np.quantile(x, 1 - alpha)
    tail = x[x <= q]
    return float(-tail.mean()) if len(tail) > 0 else float("nan")


# Load book
if "BOOK_ROWS" not in st.session_state:
    st.warning("No trading book found in session. Go to the VaR page first, edit the book, then return here.")
    st.stop()

book_df = st.session_state["BOOK_ROWS"]
positions: list[Position] = []
for _, r in book_df.iterrows():
    try:
        positions.append(
            Position(
                name=str(r.get("name", "")),
                asset_class=str(r.get("asset_class", "")).upper().strip(),
                ric=str(r.get("ric", "")).strip(),
                notional_usd=float(r.get("notional_usd", 0.0) or 0.0),
                multiplier=float(r.get("multiplier", 1.0) or 1.0),
                dv01_usd_per_bp=float(r.get("dv01_usd_per_bp", 0.0) or 0.0),
                enabled=bool(r.get("enabled", True)),
            )
        )
    except Exception:
        pass

positions = [p for p in positions if p.enabled and p.name and p.ric and p.asset_class in {"EQ","INDEX","FX","RATES"}]
book = TradingBook(positions)

with st.sidebar:
    st.header("Computation window")
    today = date.today()
    start = st.date_input("Start date", value=today - timedelta(days=750))
    end = st.date_input("End date", value=today)
    alpha = st.selectbox("Confidence level", [0.95, 0.99], index=1)

    st.markdown("---")
    st.header("Limits")
    var_limit = st.number_input("VaR limit ($)", value=2_000_000.0, step=100_000.0)
    es_limit = st.number_input("ES limit ($)", value=2_500_000.0, step=100_000.0)
    stress_limit = st.number_input("Stress loss limit ($)", value=5_000_000.0, step=250_000.0)

    eq_shock = st.number_input("Stress: EQ/INDEX shock (%)", value=-10.0, step=1.0)
    fx_shock = st.number_input("Stress: FX shock (%)", value=5.0, step=1.0)
    rates_shock = st.number_input("Stress: Rates shock (bps)", value=100.0, step=10.0)

    run = st.button("Compute limits", type="primary")

if not run:
    st.stop()

md = get_md()
factors = factor_series_for_positions(md, positions, start, end)
if factors.empty:
    st.error("No factor data returned.")
    st.stop()

pnl = book.portfolio_pnl(factors)
var = TradingBook.historical_var(pnl, alpha=float(alpha))
es = historical_es(pnl, alpha=float(alpha))

# Stress loss (deterministic)
shock_map = {}
for p in book.enabled_positions():
    if p.asset_class in ("EQ", "INDEX"):
        shock_map[p.ric] = float(eq_shock) / 100.0
    elif p.asset_class == "FX":
        shock_map[p.ric] = float(fx_shock) / 100.0
    elif p.asset_class == "RATES":
        shock_map[p.ric] = float(rates_shock)

stress_pnl = 0.0
for ric, exp in book.exposure_by_factor().items():
    stress_pnl += exp * shock_map.get(ric, 0.0)

stress_loss = max(0.0, -stress_pnl)  # limit compares losses

def status(metric, limit):
    if not np.isfinite(metric):
        return "n/a"
    if metric <= 0.8 * limit:
        return "OK"
    if metric <= limit:
        return "Near"
    return "BREACH"

st.subheader("Risk vs Limits")
tbl = pd.DataFrame(
    [
        {"Metric": f"VaR (1-day) @{int(alpha*100)}%", "Value": var, "Limit": var_limit, "Status": status(var, var_limit), "Headroom": var_limit - var},
        {"Metric": f"ES (1-day) @{int(alpha*100)}%",  "Value": es,  "Limit": es_limit,  "Status": status(es, es_limit),  "Headroom": es_limit - es},
        {"Metric": "Stress Loss (1-day)",            "Value": stress_loss, "Limit": stress_limit, "Status": status(stress_loss, stress_limit), "Headroom": stress_limit - stress_loss},
    ]
)

st.dataframe(tbl, use_container_width=True)

c1, c2, c3 = st.columns(3)
c1.metric("VaR", f"${var:,.0f}", status(var, var_limit))
c2.metric("ES", f"${es:,.0f}", status(es, es_limit))
c3.metric("Stress loss", f"${stress_loss:,.0f}", status(stress_loss, stress_limit))

st.caption("OK: <= 80% of limit. Near: 80–100%. BREACH: > 100%.")
