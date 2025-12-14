
# Mathematical Framework

This project is designed to replicate the quantitative decision-making process of a professional multi-asset derivatives trading desk. The mathematical framework integrates asset pricing, return construction, risk measurement, and dynamic hedging into a unified system for monitoring and controlling portfolio risk.

The framework spans **equities, FX, and interest rate instruments**, with a strong emphasis on **risk sensitivities (Greeks, DV01)** and **distributional risk metrics (VaR, Expected Shortfall)**.

---

## 1. Price and Return Construction

### 1.1 Log Returns (Price-Based Assets)

For equities, indices, and futures, returns are computed using **logarithmic returns**:

$$
r_t = \ln\left(\frac{P_t}{P_{t-1}}\right)
$$

**Why log returns?**
- Time-additive across periods  
- Symmetric treatment of gains and losses  
- Standard assumption in continuous-time finance models  
- Compatible with normal and lognormal approximations  

These returns form the **base risk factors** used in correlation analysis, VaR, and backtesting.

---

## 2. FX Mid-Price Construction

FX markets quote **bid and ask prices**, not a single traded price. To avoid directional bias, a mid-price is constructed:

$$
\text{Mid}_t = \frac{\text{Bid}_t + \text{Ask}_t}{2}
$$

FX returns are then computed as:

$$
r_t^{FX} = \ln\left(\frac{\text{Mid}_t}{\text{Mid}_{t-1}}\right)
$$

**Practical motivation**
- Removes microstructure noise  
- Matches how desks compute FX PnL  
- Avoids systematic bias from bid-only or ask-only pricing  

---

## 3. Interest Rate Modeling

Interest rate risk is treated differently from price-based assets.

### 3.1 Yield Index Levels

U.S. Treasury yields are represented using **yield indices** (e.g. `.TNX`, `.TYX`, `.IRX`), which reflect market-implied yields rather than prices.

These indices typically quote yields in **percent or scaled percent**.

---

### 3.2 Yield Changes in Basis Points

Risk in rates is driven by **changes in yields**, not yield levels.

Daily changes are computed as:

$$
\Delta y_t^{bps} = (y_t - y_{t-1}) \times 100
$$

**Why basis points?**
- Linear approximation of bond price sensitivity  
- Industry-standard unit for rate risk  
- Directly compatible with DV01  

These yield changes are used as **rate risk factors**.

---

## 4. DV01 and Rate Sensitivity

### 4.1 DV01 Definition

DV01 (Dollar Value of a Basis Point) measures the change in instrument value for a **1 bp move in yield**:

$$
\text{DV01} = \frac{\partial P}{\partial y} \times 0.0001
$$

DV01 is the **primary risk unit** used by rates traders.

---

### 4.2 DV01-Scaled Returns

For rate futures, raw returns do not directly reflect risk exposure. Returns are scaled by DV01:

$$
r_t^{DV01} = r_t^{future} \times \text{DV01}
$$

This transforms futures returns into a **PnL-relevant risk factor**, allowing:

- Cross-instrument comparability  
- Portfolio aggregation  
- Realistic VaR estimation  

---

## 5. Portfolio PnL Construction

Let:
- $\\mathbf{r}_t$ be the vector of asset returns  
- $\\mathbf{w}$ be the vector of portfolio weights  

Portfolio PnL is computed as:

$$
\text{PnL}_t = \\mathbf{w}^\\top \\mathbf{r}_t
$$

This time series forms the empirical distribution used for risk estimation.

---

## 6. Value-at-Risk (VaR)

### 6.1 Historical VaR

Historical VaR estimates risk using the **empirical return distribution**:

$$
\text{VaR}_\\alpha = -\\text{Quantile}_\\alpha(\\text{PnL})
$$

**Interpretation**  
> With $\\alpha$ confidence, the portfolio will not lose more than VaR over the chosen horizon.

---

### 6.2 Limitations of VaR
- Ignores tail severity beyond the cutoff  
- Not subadditive in all cases  
- Can underestimate extreme risk  

This motivates Expected Shortfall.

---

## 7. Expected Shortfall (ES)

Expected Shortfall measures the **average loss conditional on losses exceeding VaR**:

$$
\text{ES}_\\alpha = -\\mathbb{E}[\\text{PnL} \\mid \\text{PnL} \\le -\\text{VaR}_\\alpha]
$$

**Why ES is superior**
- Captures tail risk severity  
- Coherent risk measure  
- Preferred by regulators (Basel III / FRTB)

---

## 8. Greeks and Sensitivity-Based Hedging

### 8.1 Delta (Equity Options)

Delta measures sensitivity to underlying price changes:

$$
\\Delta = \\frac{\\partial V}{\\partial S}
$$

A delta-neutral portfolio satisfies:

$$
\\sum_i \\Delta_i \\cdot w_i = 0
$$

---

### 8.2 DV01 Neutrality (Rates)

For rates portfolios, hedging targets **DV01 neutrality**:

$$
\\sum_i \\text{DV01}_i \\cdot w_i = 0
$$

This ensures first-order immunity to parallel yield curve shifts.

---

## 9. Dynamic Hedging

Markets evolve continuously; static hedges decay.

At each rebalancing date:
1. Recompute sensitivities (Delta, DV01)  
2. Solve hedge ratios  
3. Adjust hedge instruments  
4. Re-evaluate residual risk  

Dynamic hedging mirrors **real trading desk workflows**.

---

## 10. Risk Monitoring and Dashboard Integration

All metrics feed directly into the dashboard:
- Time-series visualization of prices and factors  
- Correlation tracking  
- VaR and ES monitoring  
- Hedged vs unhedged risk comparison  

The dashboard acts as a **real-time risk control panel**, similar to institutional trading systems.

---

## 11. Summary

This framework integrates:
- Market-aware pricing  
- Sensitivity-based risk modeling  
- Distributional risk measures  
- Dynamic hedging mechanics  

Together, these components form a **production-style quantitative risk management system**, bridging academic finance theory with professional trading desk practice.
