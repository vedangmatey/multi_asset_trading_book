# Mathematical Framework

## Returns
Log returns:
r_t = ln(P_t / P_{t-1})

## FX Mid Construction
Mid_t = (Bid_t + Ask_t) / 2

## Rates (Yield Indices)
Daily change in basis points:
Δy_t (bps) = (y_t - y_{t-1}) × 100

## Value-at-Risk (Historical)
VaR_α = -Quantile_α(PnL)

## DV01-Scaled Returns
r_scaled = r_future × DV01

This converts futures returns into rate-risk-equivalent factors.
