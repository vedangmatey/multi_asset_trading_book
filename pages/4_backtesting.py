from __future__ import annotations

from datetime import date, timedelta
import numpy as np
import pandas as pd
import streamlit as st

from src.data.market_data import MarketData, Basket
from src.portfolio.book import Position, TradingBook


st.title("Backtesting — VaR Breaches + Kupiec / Christoffersen")


# -----------------------------
# Helpers (reuse logic from VaR page)
# -----------------------------
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
    factors = factors.dropna(axis=1, how="all").dropna(axis=0, how="any")
    return factors


def rolling_var_es(pnl: pd.Series, window: int, alpha: float) -> pd.DataFrame:
    """
    Rolling historical VaR & ES computed from trailing window of PnL.
    VaR is positive number; ES is positive number.
    """
    x = pnl.dropna().copy()
    if len(x) < window + 5:
        return pd.DataFrame(index=pnl.index, columns=["VaR", "ES"], dtype=float)

    var = pd.Series(index=x.index, dtype=float)
    es = pd.Series(index=x.index, dtype=float)

    # VaR/ES at time t is computed from pnl[t-window:t)
    vals = x.values
    idx = x.index
    for i in range(window, len(x)):
        sample = vals[i-window:i]
        q = np.quantile(sample, 1 - alpha)
        var.iloc[i] = -q
        tail = sample[sample <= q]
        es.iloc[i] = float(-tail.mean()) if len(tail) > 0 else np.nan

    out = pd.DataFrame({"VaR": var, "ES": es})
    return out.reindex(pnl.index)


def kupiec_test(exceed: np.ndarray, alpha: float) -> dict:
    """
    Kupiec unconditional coverage test.
    exceed = boolean array, True if breach (loss > VaR), or pnl < -VaR.
    """
    n = int(exceed.size)
    x = int(exceed.sum())
    p = 1 - alpha
    if n == 0:
        return {"LR_uc": np.nan, "p_value": np.nan, "breaches": x, "n": n}

    # avoid log(0)
    phat = max(min(x / n, 1 - 1e-12), 1e-12)

    # LR = -2 ln( ( (1-p)^(n-x) p^x ) / ( (1-phat)^(n-x) phat^x ) )
    num = (1 - p) ** (n - x) * (p ** x)
    den = (1 - phat) ** (n - x) * (phat ** x)
    lr = -2.0 * np.log(num / den)

    # Chi-square(1) p-value
    from scipy.stats import chi2
    pv = 1 - chi2.cdf(lr, df=1)
    return {"LR_uc": float(lr), "p_value": float(pv), "breaches": x, "n": n}


def christoffersen_test(exceed: np.ndarray) -> dict:
    """
    Christoffersen conditional coverage (independence) test.
    Uses 2-state Markov chain of exceedances.
    """
    if exceed.size < 2:
        return {"LR_ind": np.nan, "p_value": np.nan}

    x = exceed.astype(int)

    n00 = np.sum((x[:-1] == 0) & (x[1:] == 0))
    n01 = np.sum((x[:-1] == 0) & (x[1:] == 1))
    n10 = np.sum((x[:-1] == 1) & (x[1:] == 0))
    n11 = np.sum((x[:-1] == 1) & (x[1:] == 1))

    # transition probabilities
    p01 = n01 / (n00 + n01) if (n00 + n01) > 0 else 0.0
    p11 = n11 / (n10 + n11) if (n10 + n11) > 0 else 0.0

    # unconditional probability
    pi = (n01 + n11) / (n00 + n01 + n10 + n11)

    def safe_loglik(n00, n01, n10, n11, p01, p11):
        eps = 1e-12
        p01 = min(max(p01, eps), 1 - eps)
        p11 = min(max(p11, eps), 1 - eps)
        return (
            n00 * np.log(1 - p01) + n01 * np.log(p01) +
            n10 * np.log(1 - p11) + n11 * np.log(p11)
        )

    ll_ind = safe_loglik(n00, n01, n10, n11, p01, p11)

    # restricted (independent) model: same prob pi regardless of state
    eps = 1e-12
    pi = min(max(pi, eps), 1 - eps)
    ll_const = (
        (n00 + n10) * np.log(1 - pi) +
        (n01 + n11) * np.log(pi)
    )

    lr = -2.0 * (ll_const - ll_ind)

    from scipy.stats import chi2
    pv = 1 - chi2.cdf(lr, df=1)
    return {"LR_ind": float(lr), "p_value": float(pv)}


# -----------------------------
# Sidebar controls
# -----------------------------
with st.sidebar:
    st.header("Backtest controls")
    today = date.today()
    start = st.date_input("Start date", value=today - timedelta(days=900))
    end = st.date_input("End date", value=today)
    alpha = st.selectbox("Confidence level", options=[0.95, 0.99], index=1)
    window = st.number_input("Rolling window (days)", value=250, min_value=60, max_value=1500, step=10)
    run = st.button("Run backtest", type="primary")

st.info("This backtest uses **historical rolling VaR/ES** on the **portfolio PnL series** from your Trading Book mapping.")

# Load positions from session if available (reuse your VaR page session table)
if "BOOK_ROWS" not in st.session_state:
    st.warning("No trading book found in session. Go to the VaR page first, edit the book, then return here.")
    st.stop()

book_df = st.session_state["BOOK_ROWS"]
positions = []
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

positions = [p for p in positions if p.name and p.ric and p.asset_class in {"EQ", "INDEX", "FX", "RATES"} and p.enabled]
book = TradingBook(positions)

if not run:
    st.stop()

md = get_md()
with st.spinner("Fetching factors and building PnL series..."):
    factors = factor_series_for_positions(md, positions, start, end)

if factors.empty:
    st.error("No factor data returned. Check RICs/entitlement/date range.")
    st.stop()

pnl = book.portfolio_pnl(factors)

roll = rolling_var_es(pnl, window=int(window), alpha=float(alpha))
df = pd.concat([pnl.rename("PnL"), roll], axis=1).dropna()

if df.empty:
    st.error("Not enough data after alignment to compute rolling VaR/ES.")
    st.stop()

# breaches: PnL < -VaR
df["Breach"] = df["PnL"] < (-df["VaR"])
breach_rate = df["Breach"].mean()

st.subheader("Backtest summary")
c1, c2, c3, c4 = st.columns(4)
c1.metric("Obs", f"{len(df):d}")
c2.metric("Breaches", f"{int(df['Breach'].sum()):d}")
c3.metric("Breach rate", f"{breach_rate*100:.2f}%")
c4.metric("Expected rate", f"{(1-float(alpha))*100:.2f}%")

# tests
try:
    k = kupiec_test(df["Breach"].values, alpha=float(alpha))
    ch = christoffersen_test(df["Breach"].values)
except Exception as e:
    st.warning(f"Stat tests require scipy. If missing, install: pip install scipy. Error: {e}")
    k = {"LR_uc": np.nan, "p_value": np.nan, "breaches": int(df["Breach"].sum()), "n": len(df)}
    ch = {"LR_ind": np.nan, "p_value": np.nan}

st.subheader("Statistical tests")
t1, t2, t3, t4 = st.columns(4)
t1.metric("Kupiec LR_uc", f"{k['LR_uc']:.3f}" if np.isfinite(k["LR_uc"]) else "n/a")
t2.metric("Kupiec p-value", f"{k['p_value']:.3f}" if np.isfinite(k["p_value"]) else "n/a")
t3.metric("Christoffersen LR_ind", f"{ch['LR_ind']:.3f}" if np.isfinite(ch["LR_ind"]) else "n/a")
t4.metric("Christoffersen p-value", f"{ch['p_value']:.3f}" if np.isfinite(ch["p_value"]) else "n/a")

st.subheader("PnL vs VaR (breaches marked)")
plot_df = df[["PnL", "VaR"]].copy()
plot_df["-VaR"] = -plot_df["VaR"]
st.line_chart(plot_df[["PnL", "-VaR"]])

st.subheader("Breach table (tail)")
breaches = df[df["Breach"]].copy()
st.dataframe(breaches.tail(20), use_container_width=True)
