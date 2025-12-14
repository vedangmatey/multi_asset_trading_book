from typing import Sequence


def historical_var(pnl_series: Sequence[float], confidence: float = 0.99) -> float:
    """
    Plain historical VaR (positive number = loss).
    pnl_series: list of daily PnL values.
    """
    if not pnl_series:
        raise ValueError("pnl_series is empty")

    # Convert PnL to losses
    losses = sorted([-x for x in pnl_series])  # largest loss = right tail
    n = len(losses)

    # Simple quantile index
    idx = int((n - 1) * confidence)
    return losses[idx]
