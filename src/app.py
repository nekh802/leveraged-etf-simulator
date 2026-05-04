import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import yfinance as yf
from fetch_data import fetch_prices

st.title("Leveraged ETF Simulator")

ticker = st.text_input("Ticker", "AMD")
base_date = st.date_input("기준일")
shares = st.number_input("매수 수량", min_value=1, value=3)

base_ts = pd.to_datetime(base_date).normalize()

def get_usdkrw_rate(base_ts):
    start = base_ts - pd.Timedelta(days=10)
    end = base_ts + pd.Timedelta(days=1)

    fx = yf.download(
        "KRW=X",
        start=start,
        end=end,
        progress=False,
        auto_adjust=False
    )

    if fx.empty:
        return None, None

    fx.index = pd.to_datetime(fx.index).tz_localize(None).normalize()

    fx_close = fx["Close"]

    if isinstance(fx_close, pd.DataFrame):
        fx_close = fx_close.iloc[:, 0]

    fx_close = fx_close.dropna()

    available = fx_close.index[fx_close.index <= base_ts]

    if len(available) == 0:
        return None, None

    fx_ts = available[-1]
    usdkrw = float(fx_close.loc[fx_ts])

    return usdkrw, fx_ts

if st.button("시뮬레이션 실행"):
    prices = fetch_prices(ticker)

    # 인덱스 날짜 정리
    prices.index = pd.to_datetime(prices.index).tz_localize(None).normalize()

    close_ticker = prices["Close"]

    # Close가 DataFrame일 경우 대비
    if isinstance(close_ticker, pd.DataFrame):
        if ticker in close_ticker.columns:
            close_ticker = close_ticker[ticker]
        else:
            close_ticker = close_ticker.iloc[:, 0]

    close_ticker = close_ticker.dropna()

    # 기준일이 거래일이 아니면 가장 가까운 이전 거래일 선택
    if base_ts not in close_ticker.index:
        available = close_ticker.index[close_ticker.index <= base_ts]
        if len(available) == 0:
            st.error("기준일이 데이터 범위보다 이전입니다. 날짜를 다시 선택해주세요.")
            st.stop()
        base_ts = available[-1]
        st.info(f"선택한 날짜가 거래일이 아니어서 {base_ts.date()}로 조정됐어요.")

    shareprices = float(close_ticker.loc[base_ts])

    returns = close_ticker.pct_change().fillna(0)
    leveraged_2x = 2 * returns

    # 누적 성과
    cum_1x = (1 + returns).cumprod()
    cum_2x = (1 + leveraged_2x).cumprod()

    # 기준일을 1로 리베이스
    cum_from_base_1x = cum_1x / cum_1x.loc[base_ts]
    cum_from_base_2x = cum_2x / cum_2x.loc[base_ts]

    final_r_1x = float(cum_from_base_1x.loc[base_ts:].iloc[-1] - 1)
    final_r_2x = float(cum_from_base_2x.loc[base_ts:].iloc[-1] - 1)

    initial_capital = shares * shareprices
    
    # 총 자산 먼저 계산
    total_1x = (cum_from_base_1x * initial_capital).loc[base_ts:]
    total_2x = (cum_from_base_2x * initial_capital).loc[base_ts:]
    
    # 기준일 USD/KRW 환율 가져오기
    usdkrw, fx_ts = get_usdkrw_rate(base_ts)
    
    if usdkrw is None:
        st.warning("기준일 환율 데이터를 가져오지 못했어요.")
        exchange_text = ""
        final_1x_krw_text = "환율 데이터 없음"
        final_2x_krw_text = "환율 데이터 없음"
    else:
        shareprices_krw = shareprices * usdkrw
        initial_capital_krw = initial_capital * usdkrw
        final_1x_krw = total_1x.iloc[-1] * usdkrw
        final_2x_krw = total_2x.iloc[-1] * usdkrw
    
        exchange_text = f"""
    **기준 환율일:** {fx_ts.date()}  
    **USD/KRW 환율:** {usdkrw:,.2f}원  
    
    **매수가 원화 환산:** {shareprices_krw:,.0f}원  
    **투자금 원화 환산:** {initial_capital_krw:,.0f}원  
    """
    
        final_1x_krw_text = f"{final_1x_krw:,.0f}원"
        final_2x_krw_text = f"{final_2x_krw:,.0f}원"
    
    st.subheader("결과")
    st.markdown(f"""
    **기준일:** {base_ts.date()}  
    **{ticker} {shares}주 매수**  
    **매수가:** {shareprices:.2f} USD  
    **투자금:** {initial_capital:,.2f} USD  
    
    {exchange_text}
    
    ### 기본형(1x)
    - 누적 수익률: {final_r_1x:.2%}
    - 최종 자산: {total_1x.iloc[-1]:,.2f} USD
    - 최종 자산 원화 환산: {final_1x_krw_text}
    
    ### 레버리지(2x)
    - 누적 수익률: {final_r_2x:.2%}
    - 최종 자산: {total_2x.iloc[-1]:,.2f} USD
    - 최종 자산 원화 환산: {final_2x_krw_text}
    """)

    # ----------------------------
    # 1. 기준일 이후 주가 그래프
    # ----------------------------
    st.subheader("1) 주가 그래프")

    price_plot = close_ticker.loc[base_ts:]

    if len(price_plot) < 2:
        st.warning("기준일 이후 데이터가 1개 이하라서 선그래프가 거의 보이지 않을 수 있어요. 더 이전 날짜를 선택하면 그래프가 잘 보입니다.")

    fig1, ax1 = plt.subplots(figsize=(10, 4))
    ax1.plot(price_plot.index, price_plot.values, label=f"{ticker} Price")
    ax1.set_title(f"{ticker} Price from {base_ts.date()}")
    ax1.set_xlabel("Date")
    ax1.set_ylabel("Price (USD)")
    ax1.legend()
    st.pyplot(fig1)

    # ----------------------------
    # 2. 누적 수익률 그래프
    # ----------------------------
    st.subheader("2) 누적 수익률 그래프")

    cum_r1 = (cum_from_base_1x.loc[base_ts:] - 1) * 100
    cum_r2 = (cum_from_base_2x.loc[base_ts:] - 1) * 100

    fig2, ax2 = plt.subplots(figsize=(10, 4))
    ax2.plot(cum_r1.index, cum_r1.values, label="1x cumulative return (%)")
    ax2.plot(cum_r2.index, cum_r2.values, label="2x cumulative return (%)")
    ax2.axhline(0, color="black", linewidth=0.8)
    ax2.set_title(f"{ticker} Cumulative Return from {base_ts.date()}")
    ax2.set_xlabel("Date")
    ax2.set_ylabel("Return (%)")
    ax2.legend()
    st.pyplot(fig2)

    # ----------------------------
    # 3. 총 자산 그래프(USD)
    # ----------------------------
    st.subheader("3) 총 자산 그래프")

    fig3, ax3 = plt.subplots(figsize=(10, 4))
    ax3.plot(total_1x.index, total_1x.values, label="1x portfolio value")
    ax3.plot(total_2x.index, total_2x.values, label="2x portfolio value")
    ax3.set_title(f"{ticker} Portfolio Value from {base_ts.date()}")
    ax3.set_xlabel("Date")
    ax3.set_ylabel("Portfolio Value (USD)")
    ax3.legend()
    st.pyplot(fig3)
