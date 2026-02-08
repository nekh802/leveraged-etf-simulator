import yfinance as yf
import pandas as pd

def fetch_prices(ticker: str, period: str = "1y", interval: str = "1d") -> pd.DataFrame:
    """
    ticker: 예) "AMD"
    period: 예) "1y", "6mo", "3y", "max"
    interval: 예) "1d", "1h"
    반환: DateTimeIndex를 가진 DataFrame (Open/High/Low/Close/Volume ...)
    """
    df = yf.download(ticker, period=period, interval=interval, auto_adjust=False, progress=False)

    if df is None or df.empty:
        raise ValueError(f"가격 데이터를 못 가져왔어요: {ticker}")

    df.index = pd.to_datetime(df.index)
    return df