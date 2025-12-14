from datetime import date, timedelta
import refinitiv.data as rd
import pandas as pd

end = date.today()
start = end - timedelta(days=60)

# Start with your current UST RICs (we will adjust if needed)
rics_sets = {
    "UST_RR": ["US2YT=RR", "US5YT=RR", "US10YT=RR", "US30YT=RR"],
    # common alternates that often work depending on entitlement
    "UST_ALT1": ["US2Y", "US5Y", "US10Y", "US30Y"],
    "UST_ALT2": ["US2YT=TR", "US5YT=TR", "US10YT=TR", "US30YT=TR"],
    "UST_ALT3": ["US2YT=EBS", "US5YT=EBS", "US10YT=EBS", "US30YT=EBS"],
}

fields_to_try = [
    "TR.PriceClose",
    "TR.FiCloseYield",
    "TR.FiMidYield",
    "TR.FiYield",
    "TRD.Yield",
    "YIELD",
]

rd.open_session(config_name="refinitiv-data.config.json")
print("Session opened")

for set_name, rics in rics_sets.items():
    print(f"\n=== Testing RIC set: {set_name} ===")
    for field in fields_to_try:
        try:
            df = rd.get_history(
                universe=rics,
                fields=[field],
                start=start,
                end=end,
                interval="daily",
            )

            # normalize output
            if isinstance(df.columns, pd.MultiIndex):
                df = df.droplevel(0, axis=1)
            df = df.apply(pd.to_numeric, errors="coerce")

            ok = (not df.empty) and (not df.isna().all().all())
            print(f"  Field {field:15s} -> {'OK' if ok else 'EMPTY/NA'}")

            if ok:
                print(df.tail())
                break

        except Exception as e:
            print(f"  Field {field:15s} -> FAIL ({type(e).__name__})")

rd.close_session()
print("\nSession closed")
