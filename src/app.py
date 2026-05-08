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
        compare_text = "환율 데이터가 없어 비교할 수 없음"
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
    
        compare_diff = final_1x_krw - final_2x_krw
    
        if compare_diff < 0:
            compare_text = f"기본형보다 {abs(compare_diff):,.0f}원 이익"
        elif compare_diff > 0:
            compare_text = f"기본형보다 {abs(compare_diff):,.0f}원 손해"
        else:
            compare_text = "기본형과 수익이 동일"
    
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

    # 양도소득세 계산
    # 해외주식 기준:
    # 수익금 - 250만원 기본공제 후
    # 22%(지방세 포함) 과세
    
    profit_2x_krw = final_2x_krw - initial_invest_krw
    
    taxable_profit = max(profit_2x_krw - 2_500_000, 0)
    
    capital_gains_tax = taxable_profit * 0.22
    
    after_tax_krw = final_2x_krw - capital_gains_tax
    
    ### 레버리지(2x)
    - 누적 수익률: {final_r_2x:.2%}
    - 최종 자산: {total_2x.iloc[-1]:,.2f} USD
    - 최종 자산 원화 환산: {final_2x_krw_text}
    - 양도소득세 공제 후 원화 : {after_tax_krw:,.0f} 원
    - 기본형과 비교: {compare_text}
    """)

    # ----------------------------
    # 1. 기준일 이후 주가 그래프
    # ----------------------------
    st.subheader("1) 주가 그래프")

    price_plot = close_ticker.loc[base_ts:]

    if len(price_plot) < 2:
        st.warning("기준일 이후 데이터가 1개 이하라서 선그래프가 거의 보이지 않을 수 있어요. 더 이전 날짜를 선택하면 그래프가 잘 보입니다.")

    x = range(len(price_plot))
    
    fig1, ax1 = plt.subplots(figsize=(10, 4))
    
    ax1.plot(
        x,
        price_plot.values,
        marker="o",
        label=f"{ticker} Price"
    )
    
    ax1.set_xticks(x)
    ax1.set_xticklabels(
        [d.strftime("%Y-%m-%d") for d in price_plot.index],
        rotation=45
    )
    
    ax1.set_title(f"{ticker} Price from {base_ts.date()}")
    ax1.set_xlabel("Trading Date")
    ax1.set_ylabel("Price (USD)")
    ax1.legend()
    st.pyplot(fig1)

    # ----------------------------
    # 2. 누적 수익률 그래프 + 매일 괴리율 점/텍스트 표시
    # ----------------------------
    st.subheader("2) 누적 수익률 그래프")
    
    # 누적 수익률(%)
    cum_r1 = (cum_from_base_1x.loc[base_ts:] - 1) * 100
    cum_r2 = (cum_from_base_2x.loc[base_ts:] - 1) * 100
    
    # 실제 2x 복리 결과
    actual_2x = cum_from_base_2x.loc[base_ts:]
    
    # 단순 2배 기대값
    simple_2x = 1 + 2 * (cum_from_base_1x.loc[base_ts:] - 1)
    
    # 매일 괴리율(%)
    gap_rate = ((actual_2x - simple_2x) / simple_2x) * 100
    
    # 점 크기: 괴리율 절댓값이 클수록 크게
    gap_abs = gap_rate.abs()
    max_gap = gap_abs.max()
    
    if max_gap == 0 or pd.isna(max_gap):
        point_size = pd.Series(80, index=gap_rate.index)
    else:
        point_size = 80 + 220 * (gap_abs / max_gap)
    
    # x축: 거래일만 간격 없이 표시
    x = range(len(cum_r1))
    
    fig2, ax2 = plt.subplots(figsize=(12, 5))
    
    # 기본 선
    ax2.plot(x, cum_r1.values, marker="o", label="1x cumulative return (%)")
    ax2.plot(x, cum_r2.values, marker="o", label="2x cumulative return (%)")
    
    # 2x 선 위에 괴리율 점 표시
    ax2.scatter(
        x,
        cum_r2.values,
        c=gap_rate.values,
        s=point_size.values,
        cmap="coolwarm",
        alpha=0.85,
        edgecolors="black",
        linewidths=0.5,
        zorder=3,
        label="Daily gap rate"
    )
    
    # 점 위에 괴리율 텍스트 표시
    for xi, yi, gap in zip(x, cum_r2.values, gap_rate.values):
        ax2.annotate(
            f"{gap:+.2f}%",
            xy=(xi, yi),
            xytext=(0, 10),
            textcoords="offset points",
            ha="center",
            fontsize=10,
            fontweight="bold"
        )
    
    ax2.axhline(0, color="black", linewidth=0.8)
    
    ax2.set_xticks(list(x))
    ax2.set_xticklabels(
        [d.strftime("%Y-%m-%d") for d in cum_r1.index],
        rotation=45
    )
    
    ax2.set_title(f"{ticker} Cumulative Return from {base_ts.date()}")
    ax2.set_xlabel("Trading Date")
    ax2.set_ylabel("Return (%)")
    ax2.legend()
    
    st.pyplot(fig2)
    
    st.info("""
    점의 색깔과 크기는 매일 괴리율의 크기를 나타내고, 점 위 숫자는 해당 거래일의 괴리율(%)입니다.  
    
    괴리율이 0%에 가까우면 :  
    실제 2x 복리 결과가 단순 2배 기대값과 거의 비슷합니다.  
    
    괴리율이 양수면 :  
    → 실제 2x 복리 결과가 단순 2배 기대값보다 높습니다.  
    → 상승장에서는 더 많이 오르고, 하락장에서는 덜 떨어집니다.  
    
    괴리율이 음수면 :  
    → 실제 2x 복리 결과가 단순 2배 기대값보다 낮습니다.  
    → 상승장에서는 덜 오르고, 하락장에서는 더 많이 떨어집니다.  
    """)

    # ----------------------------
    # 3. 총 자산 그래프 + 매일 괴리율 점/텍스트 표시
    # ----------------------------
    st.subheader("3) 총 자산 그래프")
    
    # x축: 거래일만 간격 없이 표시
    x = range(len(total_1x))
    
    fig3, ax3 = plt.subplots(figsize=(12, 5))
    
    # 기본 총 자산 선
    ax3.plot(
        x,
        total_1x.values,
        marker="o",
        label="1x portfolio value"
    )
    
    ax3.plot(
        x,
        total_2x.values,
        marker="o",
        label="2x portfolio value"
    )
    
    # 2x 총 자산 선 위에 괴리율 점 표시
    ax3.scatter(
        x,
        total_2x.values,
        c=gap_rate.values,
        s=point_size.values,
        cmap="coolwarm",
        alpha=0.85,
        edgecolors="black",
        linewidths=0.5,
        zorder=3,
        label="Daily gap rate"
    )
    
    # 점 위에 괴리율 텍스트 표시
    for xi, yi, gap in zip(x, total_2x.values, gap_rate.values):
        ax3.annotate(
            f"{gap:+.2f}%",
            xy=(xi, yi),
            xytext=(0, 10),
            textcoords="offset points",
            ha="center",
            fontsize=10,
            fontweight="bold"
        )
    
    ax3.set_xticks(list(x))
    ax3.set_xticklabels(
        [d.strftime("%Y-%m-%d") for d in total_1x.index],
        rotation=45
    )
    
    ax3.set_title(f"{ticker} Portfolio Value from {base_ts.date()}")
    ax3.set_xlabel("Trading Date")
    ax3.set_ylabel("Portfolio Value (USD)")
    ax3.legend()
    
    st.pyplot(fig3)
