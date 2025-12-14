# Data & Architecture

## Overview
The project follows a **layered architecture** to cleanly separate concerns between
data access, analytics, and visualization.

## Architecture Layers
1. **Data Layer**
   - `RefinitivLoader`: handles API sessions and batching
   - `MarketData`: unified interface for prices, returns, and rate factors

2. **Analytics Layer**
   - Return computation
   - Yield changes in basis points
   - DV01-scaled rate factors

3. **Risk Layer**
   - Historical VaR
   - Correlation analysis
   - Hedging extensions

4. **Dashboard Layer**
   - Streamlit app
   - Interactive controls and plots

## Design Philosophy
- Modular
- Desk-realistic
- Easily extensible to new instruments
