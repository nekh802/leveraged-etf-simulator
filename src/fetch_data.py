import os
import shutil

import certifi

# 프로젝트 경로에 한글이 포함되어 있으면 curl_cffi(libcurl)가 인증서 파일을
# 못 읽는 경우가 있어서, ASCII 경로로 복사한 뒤 환경변수로 지정해준다.
_ascii_cacert = os.path.join(os.path.expanduser("~"), ".cache", "certifi", "cacert.pem")
os.makedirs(os.path.dirname(_ascii_cacert), exist_ok=True)
if not os.path.exists(_ascii_cacert):
    shutil.copyfile(certifi.where(), _ascii_cacert)
os.environ.setdefault("CURL_CA_BUNDLE", _ascii_cacert)
os.environ.setdefault("SSL_CERT_FILE", _ascii_cacert)

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

    # 최신 yfinance는 단일 티커여도 컬럼을 (Price, Ticker) MultiIndex로 반환함
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)

    df.index = pd.to_datetime(df.index)
    return df
