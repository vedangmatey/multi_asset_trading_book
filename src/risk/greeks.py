import math


def black_scholes_greeks(
    spot: float,
    strike: float,
    rate: float,
    vol: float,
    time_to_maturity: float,
    option_type: str = "call"
):
    from math import erf

    def norm_cdf(x: float) -> float:
        return 0.5 * (1.0 + erf(x / math.sqrt(2.0)))

    def norm_pdf(x: float) -> float:
        return (1.0 / math.sqrt(2.0 * math.pi)) * math.exp(-0.5 * x**2)

    if time_to_maturity <= 0:
        # At expiry we’ll just return zeros for now
        return {"delta": 0.0, "gamma": 0.0, "vega": 0.0, "theta": 0.0, "rho": 0.0}

    d1 = (math.log(spot / strike) + (rate + 0.5 * vol**2) * time_to_maturity) / (
        vol * math.sqrt(time_to_maturity)
    )
    d2 = d1 - vol * math.sqrt(time_to_maturity)

    pdf_d1 = norm_pdf(d1)

    if option_type == "call":
        delta = norm_cdf(d1)
        rho = strike * time_to_maturity * math.exp(-rate * time_to_maturity) * norm_cdf(d2)
    else:
        delta = norm_cdf(d1) - 1.0
        rho = -strike * time_to_maturity * math.exp(-rate * time_to_maturity) * norm_cdf(-d2)

    gamma = pdf_d1 / (spot * vol * math.sqrt(time_to_maturity))
    vega = spot * pdf_d1 * math.sqrt(time_to_maturity)
    theta = (
        - (spot * pdf_d1 * vol) / (2 * math.sqrt(time_to_maturity))
        - (
            rate
            * strike
            * math.exp(-rate * time_to_maturity)
            * (norm_cdf(d2) if option_type == "call" else norm_cdf(-d2))
        )
    )

    return {
        "delta": delta,
        "gamma": gamma,
        "vega": vega,
        "theta": theta,
        "rho": rho,
    }
