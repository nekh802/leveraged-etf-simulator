import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import yfinance as yf
from fetch_data import fetch_prices

st.title("Leveraged ETF Simulator")

ticker_1x = st.text_input("Ticker 1 - 기본형 주식", "AMD")
ticker_2x = st.text_input("Ticker 2 - 레버리지 ETF", "AMDL")
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


def get_close_series(prices):
    prices.index = pd.to_datetime(prices.index).tz_localize(None).normalize()
    close = prices["Close"]

    if isinstance(close, pd.DataFrame):
        close = close.iloc[:, 0]

    return close.dropna()


if st.button("결과보기"):
    prices_1x = fetch_prices(ticker_1x)
    prices_2x = fetch_prices(ticker_2x)

    close_1x = get_close_series(prices_1x)
    close_2x = get_close_series(prices_2x)

    common_dates = close_1x.index.intersection(close_2x.index)

    close_1x = close_1x.loc[common_dates]
    close_2x = close_2x.loc[common_dates]

    if base_ts not in common_dates:
        available = common_dates[common_dates <= base_ts]

        if len(available) == 0:
            st.error("기준일이 데이터 범위보다 이전입니다. 날짜를 다시 선택해주세요.")
            st.stop()

        base_ts = available[-1]
        st.info(f"선택한 날짜가 거래일이 아니어서 {base_ts.date()}로 조정됐어요.")

    shareprice_1x = float(close_1x.loc[base_ts])
    shareprice_2x = float(close_2x.loc[base_ts])

    returns_1x = close_1x.pct_change().fillna(0)
    returns_2x = close_2x.pct_change().fillna(0)

    cum_1x = (1 + returns_1x).cumprod()
    cum_2x = (1 + returns_2x).cumprod()

    cum_from_base_1x = cum_1x / cum_1x.loc[base_ts]
    cum_from_base_2x = cum_2x / cum_2x.loc[base_ts]

    final_r_1x = float(cum_from_base_1x.loc[base_ts:].iloc[-1] - 1)
    final_r_2x = float(cum_from_base_2x.loc[base_ts:].iloc[-1] - 1)

    initial_capital = shares * shareprice_1x

    total_1x = (cum_from_base_1x * initial_capital).loc[base_ts:]
    total_2x = (cum_from_base_2x * initial_capital).loc[base_ts:]

    usdkrw, fx_ts = get_usdkrw_rate(base_ts)

    if usdkrw is None:
        st.warning("기준일 환율 데이터를 가져오지 못했어요.")
        st.stop()

    initial_capital_krw = initial_capital * usdkrw

    final_1x_krw = total_1x.iloc[-1] * usdkrw
    final_2x_krw = total_2x.iloc[-1] * usdkrw

    profit_1x_krw = final_1x_krw - initial_capital_krw
    taxable_profit_1x = max(profit_1x_krw - 2_500_000, 0)
    capital_gains_tax_1x = taxable_profit_1x * 0.22
    after_tax_krw_1x = final_1x_krw - capital_gains_tax_1x

    profit_2x_krw = final_2x_krw - initial_capital_krw
    taxable_profit_2x = max(profit_2x_krw - 2_500_000, 0)
    capital_gains_tax_2x = taxable_profit_2x * 0.22
    after_tax_krw_2x = final_2x_krw - capital_gains_tax_2x

    compare_diff = after_tax_krw_2x - after_tax_krw_1x

    if compare_diff > 0:
        compare_text = f"기본형보다 {abs(compare_diff):,.0f}원 이익"
    elif compare_diff < 0:
        compare_text = f"기본형보다 {abs(compare_diff):,.0f}원 손해"
    else:
        compare_text = "기본형과 수익이 동일"

    purchase_date_text = base_ts.strftime("%Y년 %m월 %d일")
    purchase_fx_text = f"{usdkrw:,.2f}원"

    st.subheader("결과")

    st.markdown(f"""
    ### 기본형(1x) - {ticker_1x}
    - 매수가: {shareprice_1x:,.2f} USD
    - 누적 수익률: {final_r_1x:.2%}
    - 최종 자산: {total_1x.iloc[-1]:,.2f} USD
    - {purchase_date_text} 기준 환율: {purchase_fx_text}
    - 최종 자산 원화 환산: {final_1x_krw:,.0f}원
    - 양도소득세: {capital_gains_tax_1x:,.0f}원
    - 양도소득세 공제 후 원화: {after_tax_krw_1x:,.0f}원

    ### 레버리지 ETF - {ticker_2x}
    - 기준일 가격: {shareprice_2x:,.2f} USD
    - 누적 수익률: {final_r_2x:.2%}
    - 최종 자산: {total_2x.iloc[-1]:,.2f} USD
    - {purchase_date_text} 기준 환율: {purchase_fx_text}
    - 최종 자산 원화 환산: {final_2x_krw:,.0f}원
    - 양도소득세: {capital_gains_tax_2x:,.0f}원
    - 양도소득세 공제 후 원화: {after_tax_krw_2x:,.0f}원
    - 기본형과 세금 공제 후 비교: {compare_text}
    """)

    st.info("""
    양도소득세는 수익금에서 250만 원 기본공제를 뺀 뒤, 남은 과세 대상 수익에 22%를 적용해 계산합니다.
    """)

    # ----------------------------
    # 1. 주가 그래프
    # ----------------------------
    st.subheader("1) 주가 그래프")

    price_1x_plot = close_1x.loc[base_ts:]
    price_2x_plot = close_2x.loc[base_ts:]

    x = range(len(price_1x_plot))

    fig1, ax1 = plt.subplots(figsize=(12, 5))

    ax1.plot(x, price_1x_plot.values, marker="o", label=f"{ticker_1x} Price")
    ax1.plot(x, price_2x_plot.values, marker="o", label=f"{ticker_2x} Price")

    ax1.set_xticks(list(x))
    ax1.set_xticklabels(
        [d.strftime("%Y-%m-%d") for d in price_1x_plot.index],
        rotation=45
    )

    ax1.set_title(f"{ticker_1x} vs {ticker_2x} Price from {base_ts.date()}")
    ax1.set_xlabel("Trading Date")
    ax1.set_ylabel("Price (USD)")
    ax1.legend()

    st.pyplot(fig1)

    # ----------------------------
    # 2. 누적 수익률 그래프
    # ----------------------------
    st.subheader("2) 누적 수익률 그래프")

    cum_r1 = (cum_from_base_1x.loc[base_ts:] - 1) * 100
    cum_r2 = (cum_from_base_2x.loc[base_ts:] - 1) * 100

    simple_2x = 1 + 2 * (cum_from_base_1x.loc[base_ts:] - 1)
    simple_2x_return = (simple_2x - 1) * 100

    actual_2x = cum_from_base_2x.loc[base_ts:]
    gap_rate = ((actual_2x - simple_2x) / simple_2x) * 100

    gap_abs = gap_rate.abs()
    max_gap = gap_abs.max()

    if max_gap == 0 or pd.isna(max_gap):
        point_size = pd.Series(80, index=gap_rate.index)
    else:
        point_size = 80 + 220 * (gap_abs / max_gap)

    x = range(len(cum_r1))

    fig2, ax2 = plt.subplots(figsize=(12, 5))

    ax2.plot(x, cum_r1.values, marker="o", label=f"{ticker_1x} cumulative return (%)")
    ax2.plot(x, simple_2x_return.values, linestyle="--", label="Simple 2x expectation (%)")
    ax2.plot(x, cum_r2.values, marker="o", label=f"{ticker_2x} actual return (%)")

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
        label="Gap rate"
    )

    for xi, yi, gap in zip(x, cum_r2.values, gap_rate.values):
        ax2.annotate(
            f"{gap:+.2f}%",
            xy=(xi, yi),
            xytext=(0, 10),
            textcoords="offset points",
            ha="center",
            fontsize=9,
            fontweight="bold"
        )

    ax2.axhline(0, color="black", linewidth=0.8)

    ax2.set_xticks(list(x))
    ax2.set_xticklabels(
        [d.strftime("%Y-%m-%d") for d in cum_r1.index],
        rotation=45
    )

    ax2.set_title(f"{ticker_1x} vs {ticker_2x} Cumulative Return from {base_ts.date()}")
    ax2.set_xlabel("Trading Date")
    ax2.set_ylabel("Return (%)")
    ax2.legend()

    st.pyplot(fig2)

    # ----------------------------
    # 3. 총 자산 그래프
    # ----------------------------
    st.subheader("3) 총 자산 그래프")

    expected_2x_value = simple_2x * initial_capital

    x = range(len(total_1x))

    fig3, ax3 = plt.subplots(figsize=(12, 5))

    ax3.plot(x, total_1x.values, marker="o", label=f"{ticker_1x} portfolio value")
    ax3.plot(x, expected_2x_value.values, linestyle="--", label="Simple 2x expected value")
    ax3.plot(x, total_2x.values, marker="o", label=f"{ticker_2x} actual portfolio value")

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
        label="Gap rate"
    )

    for xi, yi, gap in zip(x, total_2x.values, gap_rate.values):
        ax3.annotate(
            f"{gap:+.2f}%",
            xy=(xi, yi),
            xytext=(0, 10),
            textcoords="offset points",
            ha="center",
            fontsize=9,
            fontweight="bold"
        )

    ax3.set_xticks(list(x))
    ax3.set_xticklabels(
        [d.strftime("%Y-%m-%d") for d in total_1x.index],
        rotation=45
    )

    ax3.set_title(f"{ticker_1x} vs {ticker_2x} Portfolio Value from {base_ts.date()}")
    ax3.set_xlabel("Trading Date")
    ax3.set_ylabel("Portfolio Value (USD)")
    ax3.legend()

    st.pyplot(fig3)

    st.info("""
    이 그래프는 세 가지를 비교합니다.

    1. 기본형 1x 실제 자산
    2. 1x 수익률을 단순히 2배 했을 때의 기대 자산
    3. 실제 레버리지 ETF의 자산

    괴리율은 실제 레버리지 ETF가 단순 2배 기대값보다 얼마나 높거나 낮은지를 보여줍니다.
    """)
