import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from fetch_data import fetch_prices

st.title("Leveraged ETF Simulator")

ticker = st.text_input("Ticker", "AMD")
base_date = st.date_input("기준일")
shares = st.number_input("매수 수량", min_value=1, value=3)

base_ts = pd.to_datetime(base_date).normalize()

if st.button("시뮬레이션 실행"):
    prices = fetch_prices(ticker)

    prices.index = pd.to_datetime(prices.index).tz_localize(None).normalize()

    close_ticker = prices["Close"]

    if isinstance(close_ticker, pd.DataFrame):
        if ticker in close_ticker.columns:
            close_ticker = close_ticker[ticker]
        else:
            close_ticker = close_ticker.iloc[:, 0]

    close_ticker = close_ticker.dropna()

    returns = close_ticker.pct_change().fillna(0)
    leveraged_2x = 2 * returns

    if base_ts not in close_ticker.index:
        available = close_ticker.index[close_ticker.index <= base_ts]

        if len(available) == 0:
            st.error("기준일이 데이터 범위보다 이전입니다. 날짜를 다시 선택해주세요.")
            st.stop()

        base_ts = available[-1]
        st.info(f"선택한 날짜가 거래일이 아니어서 {base_ts.date()}로 조정됐어요.")

    shareprices = float(close_ticker.loc[base_ts])

    cum_1x = (1 + returns).cumprod()
    cum_2x = (1 + leveraged_2x).cumprod()

    cum_from_base_1x = cum_1x / cum_1x.loc[base_ts]
    cum_from_base_2x = cum_2x / cum_2x.loc[base_ts]

    final_r_1x = float(cum_from_base_1x.loc[base_ts:].iloc[-1] - 1)
    final_r_2x = float(cum_from_base_2x.loc[base_ts:].iloc[-1] - 1)

    initial_capital = shares * shareprices

    total_1x = (cum_from_base_1x * initial_capital).loc[base_ts:]
    total_2x = (cum_from_base_2x * initial_capital).loc[base_ts:]

    st.subheader("결과")

    st.markdown(f"""
    기준일: {base_ts.date()} <br>
    {ticker} {shares}주 매수 <br>
    매수가: {shareprices:.2f}, 비용: {initial_capital:,.2f}

    기본형  
    - 누적 수익률: {final_r_1x:.2%}  
    - 최종 자산: {total_1x.iloc[-1]:,.2f}

    레버리지 2x  
    - 누적 수익률: {final_r_2x:.2%}  
    - 최종 자산: {total_2x.iloc[-1]:,.2f}
    """, unsafe_allow_html=True)

    fig, ax = plt.subplots(figsize=(10, 4))

    ax.plot(total_1x.index, total_1x, label="1x portfolio value")
    ax.plot(total_2x.index, total_2x, label="2x portfolio value")

    ax.legend()
    ax.set_title(f"{ticker} Portfolio Value from {base_ts.date()}")
    ax.set_xlabel("Date")
    ax.set_ylabel("Portfolio Value")
