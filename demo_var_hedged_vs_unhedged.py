from src.risk.var import historical_var

var95_un = historical_var(unhedged_pnls, 0.95)
var99_un = historical_var(unhedged_pnls, 0.99)

var95_hd = historical_var(hedged_pnls, 0.95)
var99_hd = historical_var(hedged_pnls, 0.99)

print("\n--- VaR Comparison ---")
print(f"Unhedged 95% VaR: {var95_un:.4f}")
print(f"Delta-hedged 95% VaR: {var95_hd:.4f}")

print(f"Unhedged 99% VaR: {var99_un:.4f}")
print(f"Delta-hedged 99% VaR: {var99_hd:.4f}")
