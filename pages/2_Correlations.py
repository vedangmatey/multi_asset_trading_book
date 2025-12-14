from __future__ import annotations

from datetime import date, timedelta
import streamlit as st
import pandas as pd

from src.dashboard.utils import BASKETS, fetch_factor

st.title("Correlations")


def _rolling_corr(series_a: pd.Series, series_b: pd.Series, window: int) -> pd.Series:
    df = pd.concat([series_a, series_b], axis=1).dropna()
    if df.shape[0] < window + 5:
        return pd.Series(index=df.index, dtype=float, name="rolling_corr")
    return df.iloc[:, 0].rolling(window).corr(df.iloc[:, 1]).rename("rolling_corr")


with st.sidebar:
    st.header("Controls")

    basket_keys = st.multiselect(
        "Select baskets",
        options=list(BASKETS.keys()),
        default=list(BASKETS.keys()),
    )

    today = date.today()
    default_start = today - timedelta(days=365)

    start = st.date_input("Start date", value=default_start)
    end = st.date_input("End date", value=today)

    align_mode = st.selectbox(
        "Alignment",
        options=[
            "Strict overlap (drop any missing date)",
            "Loose overlap (ffill then drop start gaps)",
        ],
        index=0,
        help="Strict is safest for clean correlation. Loose is closer to desk dashboards when small gaps exist.",
    )

    show_heatmap = st.checkbox("Show heatmap", value=True)
    show_rolling = st.checkbox("Show rolling correlation (pair)", value=True)

    rolling_window = st.number_input("Rolling window (days)", value=60, min_value=20, max_value=252, step=5)

    run = st.button("Compute correlations", type="primary")

if not run:
    st.info("Select baskets and dates, then click **Compute correlations**.")
    st.stop()

source = st.session_state.get("DATA_SOURCE", "refinitiv")

with st.spinner(f"Fetching factor data from {source}..."):
    frames = []
    used_keys = []
    for key in basket_keys:
        f = fetch_factor(key, start, end, source)
        if f is not None and not f.empty:
            frames.append(f)
            used_keys.append(key)

if not frames:
    st.warning("No factor data returned. Try a wider date range or fewer baskets.")
    st.stop()

# Combine factors
factors = pd.concat(frames, axis=1).sort_index()
factors = factors.dropna(axis=1, how="all")

# Align
if align_mode.startswith("Strict"):
    factors = factors.dropna(axis=0, how="any")
else:
    # forward-fill small gaps, then remove leading all-NaN region
    factors = factors.ffill()
    factors = factors.dropna(axis=0, how="all")

# Safety checks
if factors.shape[0] < 10 or factors.shape[1] < 2:
    st.warning("Not enough overlapping data to compute correlations.")
    st.stop()

st.subheader("Factor preview (tail)")
st.dataframe(factors.tail(10), use_container_width=True)

# Correlation
corr = factors.corr()

st.subheader("Correlation matrix")
st.dataframe(corr.round(3), use_container_width=True)

# Heatmap (Streamlit native: style)
if show_heatmap:
    st.subheader("Heatmap (visual)")
    st.dataframe(
        corr.style.format("{:.2f}").background_gradient(axis=None),
        use_container_width=True,
    )

# Rolling correlation for a selected pair
if show_rolling and factors.shape[1] >= 2:
    st.subheader("Rolling correlation (pair)")

    cols = list(factors.columns)
    c1, c2 = st.columns(2)
    with c1:
        a = st.selectbox("Series A", options=cols, index=0)
    with c2:
        # pick a different default if possible
        default_b = 1 if len(cols) > 1 else 0
        b = st.selectbox("Series B", options=cols, index=default_b)

    if a == b:
        st.info("Choose two different series to compute rolling correlation.")
    else:
        rc = _rolling_corr(factors[a], factors[b], window=int(rolling_window))
        if rc.dropna().empty:
            st.warning("Not enough data for rolling correlation with this window.")
        else:
            st.line_chart(rc)

            st.caption(
                "Rolling correlation highlights **regime changes**. "
                "This is closer to how desks monitor hedges and diversification over time."
            )

# Download to CSV (desk-friendly)
st.subheader("Export")
csv = corr.to_csv(index=True).encode("utf-8")
st.download_button(
    "Download correlation matrix (CSV)",
    data=csv,
    file_name="correlation_matrix.csv",
    mime="text/csv",
)

st.caption(
    "Correlations are computed on **aligned factor series**: "
    "returns for EQ/FX/INDEX and **bps changes** for RATES. "
    "Strict overlap is recommended for clean statistics."
)
