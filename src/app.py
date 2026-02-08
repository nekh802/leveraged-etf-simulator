import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from fetch_data import fetch_prices
import yfinance as yf

st.title("Leveraged ETF Simulator")

def fetch_prices(ticker: str, period: str = "1y", interval: str = "1d") -> pd.DataFrame:
    df = yf.download(ticker, period=period, interval=interval, auto_adjust=False, progress=False)

    if df is None or df.empty: 
        raise ValueError(f"가격 데이터를 못 가져왔어요: {ticker}")

    df.index = pd.to_datetime(df.index)
    return df


ticker = st.text_input("Ticker", "AMD")
base_date = st.date_input("기준일 0000-00-00 형태로 입력")
shares = st.number_input("매수 수량", min_value=1, value=3)
base_ts = pd.to_datetime(base_date)

if st.button("시뮬레이션 실행"):
    prices = fetch_prices(ticker)
    prices.index = pd.to_datetime(prices.index)

    close_ticker = prices['Close']
    returns = close_ticker.pct_change().fillna(0)
    leveraged_2x = 2* returns

    shareprices = float(close_ticker.loc[base_ts])

    #누적 (첫날)
    cum_1x = (1+returns).cumprod()
    cum_2x = (1+leveraged_2x).cumprod()

    #기준일을 1로 리베이스
    cum_from_base_1x = cum_1x / cum_1x.loc[base_ts] 
    cum_from_base_2x = cum_2x / cum_2x.loc[base_ts]

    final_r_1x = float(cum_from_base_1x.loc[base_ts:].iloc[-1] -1 )
    final_r_2x = float(cum_from_base_2x.loc[base_ts:].iloc[-1] -1 )

    initial_capital = shares * float(shareprices)

    total_1x = (cum_from_base_1x * initial_capital).loc[base_ts:]
    total_2x = (cum_from_base_2x * initial_capital).loc[base_ts:]

    st.subheader("결과")
    st.markdown(f"""
             [기준일 {base_ts}] <br>
             {ticker} {shares}주 매수<br>
             매수가: {shareprices:.2f}, 비용: {initial_capital:.2f}

             기본형
             - 누적 수익률(기준일 이후): {final_r_1x:.2%}
             - 최종 자산: {total_1x.iloc[-1, 0]:,.2f}

             레버리지(2x)
             - 누적 수익률(기준일 이후): {final_r_2x:.2%}
             - 최종 자산 {total_2x.iloc[-1, 0]:,.2f}
    """,
    unsafe_allow_html=True)

    r1 = returns
    r2 = returns * 2

    r1_plot = r1.loc[base_ts:]
    r2_plot = r2.loc[base_ts:]

    fig, ax = plt.subplots(figsize=(10,4))

    ax.plot(r1_plot.index, r1_plot, label="1x daily return")
    ax.plot(r2_plot.index, r2_plot, label="2x daily target return")
    ax.axhline(0, color="black", linewidth=0.8)

    ax.legend()
    ax.set_title(f"{ticker} Daily Returns from {base_ts.date()} (1x vs 2x target)")

    st.pyplot(fig)


