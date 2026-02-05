import yfinance as yf

def fetch_prices(ticker: str):
    df = yf.download(ticker)
    return df