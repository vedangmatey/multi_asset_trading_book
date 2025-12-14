import refinitiv.data as rd

# Candidates that often work depending on entitlement/feed
CANDIDATES = [
    # Common yield indices (often used on Reuters)
    ".TNX",   # CBOE 10Y yield index
    ".TYX",   # CBOE 30Y yield index
    ".IRX",   # CBOE 13-week yield index

    # US Treasury benchmarks / generic rates (varies by account)
    "US10YT=RR",
    "US2YT=RR",
    "US5YT=RR",
    "US30YT=RR",

    # Swap indices (sometimes entitled even when cash UST isn’t)
    "USD2YIRS=",
    "USD5YIRS=",
    "USD10YIRS=",
    "USD30YIRS=",

    # Fed Funds / SOFR style proxies (varies)
    "SOFR=",
    "EFFR=",
]

rd.open_session(config_name="refinitiv-data.config.json")
print("Session opened\n")

resolved_ok = []
for ric in CANDIDATES:
    try:
        # Snapshot is best for "does it resolve?"
        df = rd.get_data([ric], fields=["TR.PriceClose"])
        ok = df is not None and len(df) > 0
        print(f"{ric:12s} -> {'OK' if ok else 'EMPTY'}")
        if ok:
            resolved_ok.append(ric)
    except Exception as e:
        print(f"{ric:12s} -> FAIL")

rd.close_session()
print("\nSession closed")

print("\nResolved OK:")
for r in resolved_ok:
    print("  ", r)
