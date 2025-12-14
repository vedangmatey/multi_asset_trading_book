from __future__ import annotations

from datetime import date, timedelta
import pandas as pd
import numpy as np
import streamlit as st

from src.data.market_data import MarketData, Basket
from src.portfolio.book import Position, TradingBook
from src.hedging.engine import HedgeRule, build_hedges


st.title("VaR — Trading Book ($PnL) + Hedging")

# -----------------------------
# Helpers
# -----------------------------
def get_md() -> MarketData:
    src = st.session_state.get("DATA_SOURCE", "refinitiv")
    return MarketData(source=src)


def historical_es(pnl: pd.Series, alpha: float = 0.99) -> float:
    """
    1-day historical Expected Shortfall (a.k.a. CVaR) on PnL.
    Returns a positive dollar ES (average loss beyond VaR threshold).
    """
    x = pnl.dropna().values
    if len(x) < 30:
        return float("nan")
    q = np.quantile(x, 1 - alpha)  # VaR threshold in PnL space (typically negative)
    tail = x[x <= q]
    if len(tail) == 0:
        return float("nan")
    return float(-tail.mean())


def factor_series_for_positions(md: MarketData, positions: list[Position], start: date, end: date) -> pd.DataFrame:
    """
    Build factor dataframe with columns = required RICs.
    - EQ/INDEX: log returns on TR.PriceClose
    - FX: log returns on MID (fallback BID/ASK)
    - RATES: bps changes for yield indices (quote_mode=cboe_x10)
    """
    eq_rics = sorted({p.ric for p in positions if p.enabled and p.asset_class in ("EQ", "INDEX")})
    fx_rics = sorted({p.ric for p in positions if p.enabled and p.asset_class == "FX"})
    r_rics = sorted({p.ric for p in positions if p.enabled and p.asset_class == "RATES"})

    frames: list[pd.DataFrame] = []

    if eq_rics:
        b = Basket(name="EQ_INDEX_FACTORS", rics=eq_rics, asset_class="INDEX", history_field="TR.PriceClose")
        rets = md.returns(b, start=start, end=end, method="log")
        frames.append(rets)

    if fx_rics:
        fxrets = md.fx_returns(fx_rics, start=start, end=end, method="log")
        frames.append(fxrets)

    if r_rics:
        rb = Basket(name="RATES_FACTORS", rics=r_rics, asset_class="RATES", history_field="TR.PriceClose")
        bps = md.rates_changes_bps(rb, start=start, end=end, quote_mode="cboe_x10")
        frames.append(bps)

    if not frames:
        return pd.DataFrame()

    factors = pd.concat(frames, axis=1).sort_index()
    # strict overlap for portfolio aggregation
    factors = factors.dropna(axis=1, how="all").dropna(axis=0, how="any")
    return factors


def default_book_rows() -> pd.DataFrame:
    """
    Editable desk-style example.
    You can change anything in UI: name, asset_class, ric, notional, delta/beta, dv01, enabled.
    """
    return pd.DataFrame(
        [
            # Returns-based examples
            {"enabled": True, "name": "AAPL Delta", "asset_class": "EQ", "ric": "AAPL.O", "notional_usd": 1_000_000, "multiplier": 0.55, "dv01_usd_per_bp": 0.0},
            {"enabled": True, "name": "SPX Beta", "asset_class": "INDEX", "ric": ".SPX", "notional_usd": 2_000_000, "multiplier": 1.00, "dv01_usd_per_bp": 0.0},
            {"enabled": True, "name": "FX EURUSD", "asset_class": "FX", "ric": "EUR=", "notional_usd": 500_000, "multiplier": 1.00, "dv01_usd_per_bp": 0.0},
            # Rates: DV01 exposure per 1bp (factor is bps change)
            {"enabled": True, "name": "Rates 10Y", "asset_class": "RATES", "ric": ".TNX", "notional_usd": 0.0, "multiplier": 1.00, "dv01_usd_per_bp": 120_000},
            {"enabled": True, "name": "Rates 30Y", "asset_class": "RATES", "ric": ".TYX", "notional_usd": 0.0, "multiplier": 1.00, "dv01_usd_per_bp": 80_000},
        ]
    )


def rows_to_positions(df: pd.DataFrame) -> list[Position]:
    out: list[Position] = []
    for _, r in df.iterrows():
        out.append(
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
    # filter obvious bad rows
    out = [p for p in out if p.name and p.asset_class in {"EQ", "FX", "INDEX", "RATES"} and p.ric]
    return out


# -----------------------------
# Sidebar controls
# -----------------------------
with st.sidebar:
    st.header("VaR Controls")

    today = date.today()
    start = st.date_input("Start date", value=today - timedelta(days=750))
    end = st.date_input("End date", value=today)

    alpha = st.selectbox("Confidence level", options=[0.95, 0.99], index=1)

    st.markdown("---")
    st.subheader("Hedging")

    enable_hedge = st.checkbox("Apply hedges", value=True)
    hedge_spx = st.checkbox("Hedge equity/index exposure using .SPX (beta proxy)", value=True)
    hedge_rates = st.checkbox("Hedge rates DV01 exposure using .TNX", value=True)

    max_hedge_notional = st.number_input("Max abs hedge notional ($)", value=10_000_000.0, step=500_000.0)

    run = st.button("Compute VaR", type="primary")


# -----------------------------
# Trading book editor (main)
# -----------------------------
st.subheader("Trading Book (editable)")
if "BOOK_ROWS" not in st.session_state:
    st.session_state["BOOK_ROWS"] = default_book_rows()

book_df = st.data_editor(
    st.session_state["BOOK_ROWS"],
    use_container_width=True,
    num_rows="dynamic",
    column_config={
        "enabled": st.column_config.CheckboxColumn("enabled"),
        "asset_class": st.column_config.SelectboxColumn("asset_class", options=["EQ", "FX", "INDEX", "RATES"]),
        "notional_usd": st.column_config.NumberColumn("notional_usd", format="%.0f"),
        "multiplier": st.column_config.NumberColumn("multiplier", format="%.4f"),
        "dv01_usd_per_bp": st.column_config.NumberColumn("dv01_usd_per_bp", format="%.0f"),
    },
)
# persist edits
st.session_state["BOOK_ROWS"] = book_df

positions = rows_to_positions(book_df)
book = TradingBook(positions)

st.caption("Returns-based rows use: **PnL = (notional_usd × multiplier) × return**. Rates rows use: **PnL = DV01 × bps_change**.")

exposures = book.exposure_by_factor()
if exposures:
    st.subheader("Net factor exposures")
    exp_df = pd.DataFrame([{"Factor (RIC)": k, "Exposure": v} for k, v in exposures.items()]).sort_values("Exposure", ascending=False)
    st.dataframe(exp_df, use_container_width=True)
else:
    st.warning("No valid enabled positions yet. Add rows or enable positions above.")

# -----------------------------
# Compute VaR
# -----------------------------
if not run:
    st.info("Edit your book above, then click **Compute VaR**.")
    st.stop()

md = get_md()
source = st.session_state.get("DATA_SOURCE", "refinitiv")

with st.spinner(f"Building factor matrix from {source}..."):
    factors = factor_series_for_positions(md, positions, start, end)

if factors.empty:
    st.error("No factor data returned for the instruments in your book. Check RICs/entitlement or date range.")
    st.stop()

# PnL without hedges
pnl_by_pos = book.pnl_matrix(factors)
port_pnl = book.portfolio_pnl(factors)

var_unhedged = TradingBook.historical_var(port_pnl, alpha=alpha)
es_unhedged = historical_es(port_pnl, alpha=alpha)

c1, c2, c3, c4 = st.columns(4)
c1.metric(f"Unhedged VaR (1-day) @ {int(alpha*100)}%", f"${var_unhedged:,.0f}")
c2.metric(f"Unhedged ES (1-day) @ {int(alpha*100)}%", f"${es_unhedged:,.0f}")
c3.metric("Obs (aligned days)", f"{len(port_pnl.dropna()):d}")
c4.metric("Active positions", f"{len(book.enabled_positions()):d}")

st.subheader("Portfolio PnL series (unhedged)")
st.line_chart(port_pnl)

st.subheader("Position PnL (tail)")
st.dataframe(pnl_by_pos.tail(10), use_container_width=True)

# -----------------------------
# Hedging
# -----------------------------
hedged_var = None
hedged_es = None
hedged_pnl = None
hedge_positions: list[Position] = []

hedge_only_pnl = None
hedge_only_var = None
hedge_only_es = None
corr_hedge_vs_unhedged = float("nan")
corr_hedged_vs_unhedged = float("nan")
abs_notional_sum = 0.0
abs_dv01_sum = 0.0

if enable_hedge:
    rules: list[HedgeRule] = []

    # SPX proxy hedge using betas from the same factor window
    if hedge_spx:
        rules.append(
            HedgeRule(
                target_factor_ric=".SPX",
                hedge_factor_ric=".SPX",
                hedge_name="HEDGE_SPX",
                hedge_asset_class="INDEX",
                hedge_multiplier=1.0,
                max_abs_notional=float(max_hedge_notional),
                proxy_beta=True,
            )
        )

    # Rates DV01 hedge (DV01-neutralize .TNX exposure)
    if hedge_rates:
        rules.append(
            HedgeRule(
                target_factor_ric=".TNX",
                hedge_factor_ric=".TNX",
                hedge_name="HEDGE_TNX_DV01",
                hedge_asset_class="RATES",
            )
        )

    hedge_positions = build_hedges(book, rules, factors_df=factors)

    if hedge_positions:
        hedged_book = TradingBook(book.enabled_positions() + hedge_positions)

        # factor matrix already contains needed factors if hedges use same RICs;
        # if hedges introduce missing RICs, refetch:
        needed_rics = {p.ric for p in hedged_book.enabled_positions()}
        missing = [r for r in needed_rics if r not in factors.columns]
        if missing:
            with st.spinner("Fetching additional hedge factor series..."):
                extra_positions = [Position(name=f"tmp_{m}", asset_class="INDEX", ric=m, enabled=True) for m in missing]
                extra_f = factor_series_for_positions(md, extra_positions, start, end)
                factors2 = pd.concat([factors, extra_f], axis=1).dropna(axis=0, how="any")
        else:
            factors2 = factors

        hedged_pnl = hedged_book.portfolio_pnl(factors2)
        hedged_var = TradingBook.historical_var(hedged_pnl, alpha=alpha)
        hedged_es = historical_es(hedged_pnl, alpha=alpha)

        hedge_only_book = TradingBook(hedge_positions)
        hedge_only_pnl = hedge_only_book.portfolio_pnl(factors2)
        hedge_only_var = TradingBook.historical_var(hedge_only_pnl, alpha=alpha)
        hedge_only_es = historical_es(hedge_only_pnl, alpha=alpha)

        aligned = pd.concat([port_pnl, hedge_only_pnl, hedged_pnl], axis=1).dropna()
        if len(aligned) >= 30:
            corr_hedge_vs_unhedged = float(aligned.iloc[:, 0].corr(aligned.iloc[:, 1]))
            corr_hedged_vs_unhedged = float(aligned.iloc[:, 0].corr(aligned.iloc[:, 2]))

        abs_notional_sum = float(sum(abs(p.notional_usd) for p in hedge_positions if p.asset_class != "RATES"))
        abs_dv01_sum = float(sum(abs(p.dv01_usd_per_bp) for p in hedge_positions if p.asset_class == "RATES"))

        st.subheader("Hedges generated")
        hedges_df = pd.DataFrame(
            [
                {
                    "name": p.name,
                    "asset_class": p.asset_class,
                    "ric": p.ric,
                    "notional_usd": p.notional_usd,
                    "multiplier": p.multiplier,
                    "dv01_usd_per_bp": p.dv01_usd_per_bp,
                    "exposure": p.exposure_usd(),
                }
                for p in hedge_positions
            ]
        )
        st.dataframe(hedges_df, use_container_width=True)

        st.subheader("Portfolio PnL series (hedged)")
        st.line_chart(hedged_pnl)

        st.subheader("Hedge-only PnL series")
        st.line_chart(hedge_only_pnl)

        st.subheader("VaR / ES comparison + hedge effectiveness")

        # Reductions
        if np.isfinite(var_unhedged) and np.isfinite(hedged_var) and var_unhedged != 0:
            rr_var = (var_unhedged - hedged_var) / var_unhedged * 100.0
        else:
            rr_var = float("nan")

        if np.isfinite(es_unhedged) and np.isfinite(hedged_es) and es_unhedged != 0:
            rr_es = (es_unhedged - hedged_es) / es_unhedged * 100.0
        else:
            rr_es = float("nan")

        cc1, cc2, cc3, cc4 = st.columns(4)
        cc1.metric(f"Hedged VaR (1-day) @ {int(alpha*100)}%", f"${hedged_var:,.0f}")
        cc2.metric(f"Hedged ES (1-day) @ {int(alpha*100)}%", f"${hedged_es:,.0f}")
        cc3.metric("VaR reduction", "n/a" if not np.isfinite(rr_var) else f"{rr_var:.1f}%")
        cc4.metric("ES reduction", "n/a" if not np.isfinite(rr_es) else f"{rr_es:.1f}%")

        d1, d2, d3, d4 = st.columns(4)
        d1.metric("Corr(hedge PnL, unhedged PnL)", "n/a" if not np.isfinite(corr_hedge_vs_unhedged) else f"{corr_hedge_vs_unhedged:.2f}")
        d2.metric("Corr(hedged PnL, unhedged PnL)", "n/a" if not np.isfinite(corr_hedged_vs_unhedged) else f"{corr_hedged_vs_unhedged:.2f}")
        d3.metric("Abs hedge notional (non-rates)", f"${abs_notional_sum:,.0f}")
        d4.metric("Abs hedge DV01", f"${abs_dv01_sum:,.0f}/bp")

        st.caption(
            "Hedge effectiveness: ES validates tail-risk reduction beyond VaR. "
            "Corr(hedge, unhedged) should typically be negative for a good hedge."
        )
    else:
        st.info("No hedges were generated (net exposures may already be ~0 for the hedged factors).")

# -----------------------------
# Component VaR (simple historical stand-alone VaR by position PnL)
# -----------------------------
st.subheader("Component VaR (stand-alone, by position PnL)")
rows = []
for col in pnl_by_pos.columns:
    v = TradingBook.historical_var(pnl_by_pos[col], alpha=alpha)
    rows.append({"Position": col, "VaR_1d": v})
comp = pd.DataFrame(rows).sort_values("VaR_1d", ascending=False)
st.dataframe(comp, use_container_width=True)

st.caption(
    "Note: This is stand-alone VaR per position PnL (not marginal/contribution VaR). "
    "Next step is marginal/component via covariance or regression if you want it."
)

if "BOOK_ROWS" not in st.session_state:
    st.session_state["BOOK_ROWS"] = default_book_rows()
