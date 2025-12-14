import math


def black_scholes_price(
    spot: float,
    strike: float,
    rate: float,
    vol: float,
    time_to_maturity: float,
    option_type: str = "call"
) -> float:
    """Black–Scholes price for a European option on a non-dividend stock."""
    if time_to_maturity <= 0:
        if option_type == "call":
            return max(0.0, spot - strike)
        else:
            return max(0.0, strike - spot)

    d1 = (math.log(spot / strike) + (rate + 0.5 * vol**2) * time_to_maturity) / (
        vol * math.sqrt(time_to_maturity)
    )
    d2 = d1 - vol * math.sqrt(time_to_maturity)

    from math import erf

    def norm_cdf(x: float) -> float:
        return 0.5 * (1.0 + erf(x / math.sqrt(2.0)))

    if option_type == "call":
        return spot * norm_cdf(d1) - strike * math.exp(-rate * time_to_maturity) * norm_cdf(d2)
    else:
        return strike * math.exp(-rate * time_to_maturity) * norm_cdf(-d2) - spot * norm_cdf(-d1)
