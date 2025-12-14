import streamlit as st

st.title("Options / Greeks — What a real desk does beyond linear VaR")

st.markdown(
"""
## Why our current mapping works
Your current PnL mapping is **linear** in factors:

- EQ / INDEX / FX:  \\( PnL_t = Exposure_{USD} \\times Return_t \\)
- RATES:            \\( PnL_t = DV01 \\times \\Delta bps_t \\)

This is appropriate for:
- spot equities
- equity index exposure (beta/weights)
- FX spot exposure
- DV01-style rates exposure (first-order)

## What is missing for options (nonlinear risk)
Options (and many structured products) are **nonlinear**:
- Delta changes as the underlying moves
- Gamma matters (curvature)
- Vega matters (vol sensitivity)
- Correlations can change in stress regimes

### Delta-Gamma approximation (common in intraday risk)
A desk often uses a Taylor approximation:

\\[
\\Delta P \\approx \\Delta \\cdot \\Delta S + \\frac{1}{2} \\Gamma \\cdot (\\Delta S)^2
\\]

And for volatility:
\\[
\\Delta P \\approx Vega \\cdot \\Delta \\sigma
\\]

This makes VaR more realistic without full repricing.

### Full revaluation (best practice for official VaR)
A more robust approach is:
1) Shock risk factors (S, rates, vol, FX)
2) **Reprice** each instrument under the shocked scenario (pricing model)
3) Portfolio PnL = shocked value − base value
4) VaR/ES computed from revalued scenario PnL distribution

This is required for:
- exotic options
- path-dependent products
- products with strong convexity

## How to extend this project (realistic next steps)
### 1) Add option positions
Store:
- underlying RIC
- option type, strike, expiry
- implied vol (or vol surface)
- Greeks (delta, gamma, vega)

### 2) Add scenario revaluation
For each day:
- simulate factor shocks from historical returns
- reprice (e.g., Black-Scholes for equity options)
- build PnL distribution

### 3) Add risk decomposition
- marginal VaR / component VaR via covariance or regression
- factor contribution (which factor drives tail losses)

## How to explain scope professionally
This project intentionally focuses on **desk-style linear factor mapping** to:
- build a unified multi-asset PnL engine quickly
- demonstrate VaR/ES + hedging control
- provide a framework that can be extended to nonlinear instruments
"""
)

st.info(
    "Use this page in your report/presentation to justify scope and describe how a real desk extends VaR for options."
)
