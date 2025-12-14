from __future__ import annotations

from datetime import date, timedelta
import pandas as pd
import streamlit as st

from src.portfolio.book import Position, TradingBook


st.title("Stress Testing — Factor Shock Scenarios")


# Load positions from session (same as Backtesting)
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

st.subheader("Scenario controls (1-day shocks)")
with st.sidebar:
    st.header("Shocks")
    eq_shock = st.number_input("EQ/INDEX shock (%)", value=-10.0, step=1.0)
    fx_shock = st.number_input("FX shock (%)", value=5.0, step=1.0)
    rates_shock_bps = st.number_input("Rates shock (bps)", value=100.0, step=10.0)
    run = st.button("Run stress test", type="primary")

st.caption(
    "This page applies **deterministic 1-day shocks** to risk factors and computes stressed PnL using your desk-style mapping."
)

if not run:
    st.stop()

# Build a synthetic one-day factor move vector
# Returns-based factors: shock in decimal return
# Rates factors: shock in bps
shock_map = {}
for p in book.enabled_positions():
    if p.asset_class in ("EQ", "INDEX"):
        shock_map[p.ric] = float(eq_shock) / 100.0
    elif p.asset_class == "FX":
        shock_map[p.ric] = float(fx_shock) / 100.0
    elif p.asset_class == "RATES":
        shock_map[p.ric] = float(rates_shock_bps)

# Aggregate net exposure by factor
exposures = book.exposure_by_factor()

rows = []
total = 0.0
for ric, exp in exposures.items():
    move = shock_map.get(ric, 0.0)
    pnl = exp * move
    total += pnl
    rows.append({"Factor (RIC)": ric, "Exposure": exp, "Shock": move, "StressedPnL": pnl})

out = pd.DataFrame(rows).sort_values("StressedPnL")

st.subheader("Stress results")
st.metric("Total stressed PnL (1-day)", f"${total:,.0f}")

st.dataframe(out, use_container_width=True)

st.caption(
    "Interpretation: positive = gain, negative = loss. "
    "This is a **factor shock** stress test, not VaR."
)
