# Multi-Asset Trading Book — Refinitiv Dashboard

This project implements a professional-style multi-asset derivatives trading book
with an emphasis on risk management, factor modeling, and hedging, inspired by
real trading-desk workflows.

The system integrates Refinitiv data, quantitative risk metrics, and an interactive
**Streamlit dashboard** to monitor prices, returns, correlations, and Value-at-Risk (VaR)
across asset classes.

---

##  Dashboard Preview
![Dashboard Demo](assets/dashboard_demo.gif)

*(Add `dashboard_demo.gif` under an `assets/` folder in the repo)*

---

## Documentation

- 📐 [Data & Architecture](docs/data_and_architecture.md)
- 🚀 [How to Run](docs/how_to_run.md)
- 🧭 [How to Use](docs/how_to_use.md)
- 🧮 [Mathematical Framework](docs/mathematical_framework.md)
- ☁️ [Deployment Notes](docs/deployment_notes.md)

---

##  Asset Classes Covered
- **Equities & Indices**: price levels and log returns
- **FX**: mid-rate construction and FX returns
- **Rates**: yield indices (bps changes) and futures DV01-scaled returns

---

##  Project Objective
The goal is to replicate the functioning of a **real trading desk**, combining:
- market data ingestion
- factor construction
- portfolio risk measurement
- dynamic hedging logic

This project bridges **theoretical derivatives pricing** with **practical risk management**.

---

## ⚠️ Disclaimer
This project is for **educational purposes only** and does not constitute financial advice.
