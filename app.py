from __future__ import annotations

from datetime import date, timedelta
import numpy as np
import pandas as pd
import streamlit as st

from src.data.market_data import MarketData, Basket
from src.portfolio.book import Position, TradingBook


# ------------------------------------------------------------
# Page config
# ------------------------------------------------------------
st.set_page_config(page_title="Multi-Asset Trading Book", layout="wide")

st.title("Multi-Asset Trading Book — Refinitiv Dashboard")
st.caption("Equities, FX, Indices, Rates (yield indices in bps)")


# ------------------------------------------------------------
# Sidebar: global navigation + data source
# ------------------------------------------------------------
with st.sidebar:
    st.header("Navigation")
    st.write("If you see this, sidebar is working ✅")

    st.header("Data source")
    use_rdp = st.toggle("Use Refinitiv (RDP)", value=True)
    st.session_state["DATA_SOURCE"] = "refinitiv" if use_rdp else "mock"

    st.markdown("---")
    st.header("Preview window")
    preview_days = st.number_input(
        "PnL preview lookback (days)",
        value=90,
        min_value=30,
        max_value=750,
        step=30,
        help="Used on this Home page to compute PnL attribution and tail-loss contributors.",
    )
    preview_run = st.button("Run PnL preview", type="secondary")


# ------------------------------------------------------------
# Helpers
# ------------------------------------------------------------
def default_book_rows() -> pd.DataFrame:
    """
    Default persistent blotter.
    Long/short:
      - EQ/INDEX/FX: sign on notional_usd
      - RATES: sign on dv01_usd_per_bp
    """
    return pd.DataFrame(
        [
            {"enabled": True, "name": "AAPL Delta (LONG)", "asset_class": "EQ", "ric": "AAPL.O",
             "notional_usd": 1_000_000, "multiplier": 0.55, "dv01_usd_per_bp": 0.0},

            {"enabled": True, "name": "SPX Beta (SHORT)", "asset_class": "INDEX", "ric": ".SPX",
             "notional_usd": -2_000_000, "multiplier": 1.00, "dv01_usd_per_bp": 0.0},

            {"enabled": True, "name": "EURUSD (LONG)", "asset_class": "FX", "ric": "EUR=",
             "notional_usd": 500_000, "multiplier": 1.00, "dv01_usd_per_bp": 0.0},

            {"enabled": True, "name": "10Y DV01 (LONG duration)", "asset_class": "RATES", "ric": ".TNX",
             "notional_usd": 0.0, "multiplier": 1.00, "dv01_usd_per_bp": 120_000},

            {"enabled": True, "name": "30Y DV01 (SHORT duration)", "asset_class": "RATES", "ric": ".TYX",
             "notional_usd": 0.0, "multiplier": 1.00, "dv01_usd_per_bp": -80_000},
        ]
    )


def rows_to_positions(df: pd.DataFrame) -> list[Position]:
    out: list[Position] = []
    for _, r in df.iterrows():
        try:
            out.append(
                Position(
                    name=str(r.get("name", "")).strip(),
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

    # Filter bad rows
    out = [
        p for p in out
        if p.enabled and p.name and p.ric and p.asset_class in {"EQ", "FX", "INDEX", "RATES"}
    ]
    return out


def get_md() -> MarketData:
    src = st.session_state.get("DATA_SOURCE", "refinitiv")
    return MarketData(source=src)


def factor_series_for_positions(md: MarketData, positions: list[Position], start: date, end: date) -> pd.DataFrame:
    """
    Build factor dataframe with columns = required RICs.
    - EQ/INDEX: log returns on TR.PriceClose
    - FX: log returns (MID if available, else BID/ASK midpoint fallback via md.fx_returns)
    - RATES: bps changes for yield indices (quote_mode=cboe_x10)
    """
    eq_rics = sorted({p.ric for p in positions if p.asset_class in ("EQ", "INDEX")})
    fx_rics = sorted({p.ric for p in positions if p.asset_class == "FX"})
    r_rics  = sorted({p.ric for p in positions if p.asset_class == "RATES"})

    frames: list[pd.DataFrame] = []

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
    factors = factors.dropna(axis=1, how="all").dropna(axis=0, how="any")
    return factors


# ------------------------------------------------------------
# Trading Book (persistent blotter)
# ------------------------------------------------------------
st.subheader("Trading Book (persistent blotter)")

st.markdown(
    """
**How to represent long/short:**
- **EQ / INDEX / FX:** put `notional_usd` **positive for long**, **negative for short**
- **RATES:** put `dv01_usd_per_bp` **positive for long duration**, **negative for short duration**
"""
)

if "BOOK_ROWS" not in st.session_state:
    st.session_state["BOOK_ROWS"] = default_book_rows()

book_df = st.data_editor(
    st.session_state["BOOK_ROWS"],
    use_container_width=True,
    num_rows="dynamic",
    column_config={
        "enabled": st.column_config.CheckboxColumn("enabled"),
        "asset_class": st.column_config.SelectboxColumn("asset_class", options=["EQ", "FX", "INDEX", "RATES"]),
        "notional_usd": st.column_config.NumberColumn(
            "notional_usd (signed)",
            format="%.0f",
            help="EQ/INDEX/FX only. Use + for long and - for short.",
        ),
        "multiplier": st.column_config.NumberColumn("multiplier", format="%.4f"),
        "dv01_usd_per_bp": st.column_config.NumberColumn(
            "dv01_usd_per_bp (signed)",
            format="%.0f",
            help="RATES only. Use + for long duration and - for short duration.",
        ),
    },
)

# persist edits
st.session_state["BOOK_ROWS"] = book_df

st.success("Saved. All pages (VaR / Backtesting / Stress / Limits) will use this Trading Book.")


# ------------------------------------------------------------
# Net Exposure Summary
# ------------------------------------------------------------
st.markdown("---")
st.subheader("Net exposure summary")

positions = rows_to_positions(st.session_state["BOOK_ROWS"])
book = TradingBook(positions)

if not positions:
    st.info("No enabled positions yet. Add rows and enable them.")
else:
    exp_by_factor = book.exposure_by_factor()
    exp_factor_df = (
        pd.DataFrame([{"RIC": k, "Exposure": v} for k, v in exp_by_factor.items()])
        .sort_values("Exposure", ascending=False)
        .reset_index(drop=True)
    )

    # map RIC -> asset_class (first occurrence is fine for labeling)
    ric_to_ac = {}
    for p in positions:
        ric_to_ac.setdefault(p.ric, p.asset_class)
    exp_factor_df["AssetClass"] = exp_factor_df["RIC"].map(ric_to_ac)

    c1, c2 = st.columns([2, 1])

    with c1:
        st.caption("By factor (signed exposure)")
        st.dataframe(exp_factor_df, use_container_width=True)

    with c2:
        st.caption("By asset class (signed exposure)")
        exp_ac = (
            exp_factor_df.groupby("AssetClass")["Exposure"]
            .sum()
            .sort_values(ascending=False)
            .reset_index()
        )
        st.dataframe(exp_ac, use_container_width=True)

    st.caption(
        "Interpretation: EQ/INDEX/FX exposure is **$ per 1.0 return**; "
        "RATES exposure is **$ per 1 bp** (DV01). "
        "Signed values reflect long/short."
    )


# ------------------------------------------------------------
# PnL Attribution Preview + Tail contributors
# ------------------------------------------------------------
st.markdown("---")
st.subheader("PnL attribution preview (quick)")

st.caption(
    "Run this to sanity-check signs, multipliers, DV01 scaling, and which positions drive PnL "
    "before going to VaR/Stress/Limits."
)

if preview_run:
    if not positions:
        st.warning("Add at least one enabled position first.")
    else:
        md = get_md()
        end_d = date.today()
        start_d = end_d - timedelta(days=int(preview_days))

        with st.spinner("Fetching factors and computing PnL attribution..."):
            factors = factor_series_for_positions(md, positions, start_d, end_d)

        if factors.empty:
            st.error("No factor data returned for preview (check RICs/entitlement/date range).")
        else:
            pnl_by_pos = book.pnl_matrix(factors)
            if pnl_by_pos.empty:
                st.error("PnL matrix is empty (RICs may not overlap with returned factor columns).")
            else:
                port_pnl = pnl_by_pos.sum(axis=1).rename("PortfolioPnL")

                # Portfolio series
                c1, c2 = st.columns(2)
                with c1:
                    st.caption("Portfolio PnL (preview window)")
                    st.line_chart(port_pnl)

                # Cumulative PnL
                cum = pnl_by_pos.cumsum().iloc[-1].sort_values()
                cum_df = cum.reset_index()
                cum_df.columns = ["Position", "CumulativePnL"]
                with c2:
                    st.caption("Position cumulative PnL (end of window)")
                    st.dataframe(cum_df, use_container_width=True)

                # Last day contributions
                last = pnl_by_pos.iloc[-1].sort_values()
                last_df = last.reset_index()
                last_df.columns = ["Position", "LastDayPnL"]

                st.caption("Position PnL (last day)")
                st.dataframe(last_df, use_container_width=True)

                # -----------------------------
                # Tail-loss contributors (desk-style)
                # -----------------------------
                st.markdown("---")
                st.subheader("Top tail-loss contributors (worst days)")

                cA, cB, cC = st.columns(3)
                with cA:
                    tail_pct = st.number_input(
                        "Tail percentile (e.g., 1 = worst 1%)",
                        value=1.0,
                        min_value=0.1,
                        max_value=10.0,
                        step=0.1,
                    )
                with cB:
                    worst_n = st.number_input("Also show worst N days", value=10, min_value=5, max_value=60, step=5)
                with cC:
                    min_obs = st.number_input("Min obs required", value=60, min_value=30, max_value=500, step=10)

                pp = port_pnl.dropna()
                if len(pp) < int(min_obs):
                    st.warning(f"Need at least {int(min_obs)} observations. Currently: {len(pp)}")
                else:
                    q = pp.quantile(float(tail_pct) / 100.0)
                    tail_idx = pp[pp <= q].index

                    if len(tail_idx) < 5:
                        tail_idx = pp.nsmallest(int(worst_n)).index

                    tail_port = port_pnl.loc[tail_idx]
                    tail_pos = pnl_by_pos.loc[tail_idx].copy()

                    avg_contrib = tail_pos.mean(axis=0).sort_values()
                    total_tail_loss = float((-tail_port).sum())  # positive number

                    if total_tail_loss > 0:
                        tail_loss_share = (-tail_pos.sum(axis=0) / total_tail_loss)
                    else:
                        tail_loss_share = pd.Series(0.0, index=tail_pos.columns)

                    tail_df = pd.DataFrame(
                        {
                            "AvgPnL_on_TailDays": avg_contrib,
                            "SumPnL_on_TailDays": tail_pos.sum(axis=0),
                            "TailLossShare": tail_loss_share,
                        }
                    ).sort_values("AvgPnL_on_TailDays")

                    tail_df_show = tail_df.head(15).copy()
                    tail_df_show["TailLossShare"] = tail_df_show["TailLossShare"] * 100.0

                    cX, cY = st.columns([1.2, 1])
                    with cX:
                        st.caption("Worst-day portfolio PnL (tail set)")
                        st.line_chart(tail_port.sort_index())
                    with cY:
                        st.caption("Tail summary")
                        st.write(f"Tail threshold PnL ≤ **{q:,.0f}** (approx {tail_pct:.1f}%)")
                        st.write(f"Tail days used: **{len(tail_idx)}**")
                        st.write(f"Total tail loss (sum of -PnL): **${total_tail_loss:,.0f}**")

                    st.caption("Top tail-loss contributors (most negative average PnL on tail days)")
                    st.dataframe(
                        tail_df_show.reset_index().rename(
                            columns={
                                "index": "Position",
                                "AvgPnL_on_TailDays": "Avg PnL (tail days)",
                                "SumPnL_on_TailDays": "Sum PnL (tail days)",
                                "TailLossShare": "Tail loss share (%)",
                            }
                        ),
                        use_container_width=True,
                    )

                    st.caption(
                        "Interpretation: **Tail loss share (%)** is the fraction of total portfolio loss across tail days "
                        "attributed to each position."
                    )

                    worst_tbl = pd.DataFrame({"PortfolioPnL": pp.nsmallest(int(worst_n))})
                    st.caption(f"Worst {int(worst_n)} days (portfolio)")
                    st.dataframe(worst_tbl, use_container_width=True)

                st.info(
                    "If tail contributors look wrong, it usually means: "
                    "wrong sign (long/short), wrong multiplier, wrong DV01 scale, or wrong RIC mapping."
                )
else:
    st.info("Click **Run PnL preview** in the sidebar to compute PnL attribution and tail contributors.")
