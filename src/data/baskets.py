from src.data.market_data import Basket

# Equities
EQ_MEGA = Basket(
    name="EQ_MEGA",
    asset_class="EQ",
    rics=["AAPL.O", "MSFT.O", "AMZN.O", "GOOGL.O"],
    history_field="TR.PriceClose",
)

# FX spot (examples — adjust to what you want)
FX_G10 = Basket(
    name="FX_G10",
    asset_class="FX",
    rics=["EUR=", "JPY=", "GBP=", "CHF=", "CAD=", "AUD=", "NZD="],
    history_field="MID",  # if MID not entitled, switch to BID/ASK and compute mid
)

# Indices (example; use the index RICs you want)
INDEX_CORE = Basket(
    name="INDEX_CORE",
    asset_class="INDEX",
    rics=[".SPX", ".NDX"],
    history_field="TR.PriceClose",
)

# -----------------------
# US Treasury yields (Reuters/RIC style)
# -----------------------
RATES_UST = Basket(
    name="RATES_UST",
    asset_class="RATES",
    rics=["US2YT=RR", "US5YT=RR", "US10YT=RR", "US30YT=RR"],
    # We’ll *try* this first, but MarketData will auto-fallback if not supported
    history_field="TR.FiCloseYield",
)
