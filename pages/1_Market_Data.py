from datetime import date, timedelta
import streamlit as st

from src.dashboard.utils import BASKETS, fetch_prices, fetch_factor, get_data_source


st.title("Market Data")

with st.sidebar:
    st.header("Controls")

    basket_key = st.selectbox("Select basket", list(BASKETS.keys()), index=0)

    today = date.today()
    start = st.date_input("Start date", value=today - timedelta(days=180))
    end = st.date_input("End date", value=today)

    run = st.button("Load data", type="primary")

if not run:
    st.info("Pick a basket and date range, then click **Load data**.")
    st.stop()

source = get_data_source()
basket = BASKETS[basket_key]

with st.spinner(f"Fetching data from {source}..."):
    try:
        prices = fetch_prices(basket_key, start, end, source)
        factors = fetch_factor(basket_key, start, end, source)
    except Exception as e:
        st.error("Market data request failed.")
        st.exception(e)
        st.stop()

# FX warning banner if fallback occurred
if str(getattr(basket, "asset_class", "")).upper() == "FX":
    requested = st.session_state.get("FX_PRICE_FIELD_REQUESTED")
    used = st.session_state.get("FX_PRICE_FIELD_USED")
    if requested and used and requested != used:
        st.warning(
            f"FX levels: requested '{requested}', but Refinitiv did not support it for this basket. "
            f"Used fallback '{used}' instead."
        )

c1, c2 = st.columns(2)

with c1:
    st.subheader("Prices / Levels")
    if prices is None or prices.empty:
        st.info("No prices to plot (empty response).")
    else:
        st.line_chart(prices)
        st.caption("Tail:")
        st.dataframe(prices.tail(10), use_container_width=True)

with c2:
    st.subheader("Model Factors")
    if factors is None or factors.empty:
        st.info("No factors to plot (empty response).")
    else:
        st.line_chart(factors)
        st.caption("Tail:")
        st.dataframe(factors.tail(10), use_container_width=True)
