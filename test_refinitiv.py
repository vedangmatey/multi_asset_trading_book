import warnings
from datetime import date, timedelta
import refinitiv.data as rd

def main():
    warnings.filterwarnings("ignore", category=RuntimeWarning)

    rd.open_session()
    print("✅ Session opened")

    try:
        snap = rd.get_data(
            universe=["AAPL.O", "MSFT.O"],
            fields=["TR.PriceClose", "TR.Volume", "TR.CompanyMarketCap"]
        )
        print("\n✅ Snapshot:\n", snap)

        end = date.today()
        start = end - timedelta(days=30)

        hist = rd.get_history(
            universe=["AAPL.O", "MSFT.O"],
            fields=["TR.PriceClose"],
            interval="daily",
            start=start.strftime("%Y-%m-%d"),
            end=end.strftime("%Y-%m-%d"),
        )
        print("\n✅ History (tail):\n", hist.tail())

    finally:
        rd.close_session()
        print("\n✅ Session closed")

if __name__ == "__main__":
    main()
