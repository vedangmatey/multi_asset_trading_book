from datetime import date, timedelta
from src.data.refinitiv_loader import RefinitivLoader

end = date.today()
start = end - timedelta(days=30)

with RefinitivLoader() as rdl:
    snap = rdl.get_snapshot(
        universe=["AAPL.O", "MSFT.O"],
        fields=["TR.PriceClose", "TR.Volume", "TR.CompanyMarketCap"],
    )
    print("SNAPSHOT:\n", snap)

    hist = rdl.get_history(
        universe=["AAPL.O", "MSFT.O"],
        fields=["TR.PriceClose"],
        start=start,
        end=end,
        interval="daily",
    )
    print("\nHISTORY (tail):\n", hist.tail())
