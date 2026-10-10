import datetime

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import yfinance as yf
from fetch_data import fetch_prices

st.set_page_config(
    page_title="Leveraged ETF Simulator",
    page_icon="📈",
    layout="wide",
)

COLOR_1X = "#4C72B0"
COLOR_2X = "#DD8452"
COLOR_EXPECTED = "#999999"

st.title("Leveraged ETF Simulator")


@st.cache_data(ttl=3600)
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


with st.sidebar:
    st.header("입력값")
    ticker_1x = st.text_input("기본형 주식 티커", "AMD")
    ticker_2x = st.text_input("레버리지 ETF 티커", "AMDL")
    base_date = st.date_input("기준일", value=datetime.date(2025, 10, 10))
    base_ts_preview = pd.to_datetime(base_date).normalize()

    investment_usd = st.number_input("투자금액 (USD, 두 종목 동일)", min_value=1, value=10000)

    with st.spinner("환율 조회 중..."):
        usdkrw_preview, fx_ts_preview = get_usdkrw_rate(base_ts_preview)

    if usdkrw_preview:
        st.caption(
            f"≈ ₩{investment_usd * usdkrw_preview:,.0f}  "
            f"(환율 {usdkrw_preview:,.2f}원, {fx_ts_preview.date()} 종가 기준)"
        )
    else:
        st.caption("기준일 환율 정보를 가져오지 못했어요.")

    run = st.button("결과보기", use_container_width=True, type="secondary")

base_ts = base_ts_preview

if not run:
    st.info("왼쪽 사이드바에서 티커와 투자 조건을 입력한 뒤 **결과보기**를 눌러주세요.")
    st.stop()

with st.spinner("데이터를 불러오는 중..."):
    prices_1x = fetch_prices(ticker_1x)
    prices_2x = fetch_prices(ticker_2x)

    close_1x = get_close_series(prices_1x)
    close_2x = get_close_series(prices_2x)

    common_dates = close_1x.index.intersection(close_2x.index)

    close_1x = close_1x.loc[common_dates]
    close_2x = close_2x.loc[common_dates]

    if len(common_dates) == 0:
        st.error("두 티커의 공통 거래일 데이터가 없습니다.")
        st.stop()

    if base_ts not in common_dates:
        available = common_dates[common_dates <= base_ts]

        if len(available) == 0:
            st.error("기준일이 데이터 범위보다 이전입니다. 날짜를 다시 선택해주세요.")
            st.stop()

        base_ts = available[-1]
        st.caption(f"선택한 날짜가 거래일이 아니어서 {base_ts.date()}로 조정됐어요.")

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

    initial_capital_1x = float(investment_usd)
    initial_capital_2x = float(investment_usd)
    shares_1x = initial_capital_1x / shareprice_1x
    shares_2x = initial_capital_2x / shareprice_2x

    total_1x = (cum_from_base_1x * initial_capital_1x).loc[base_ts:]
    total_2x = (cum_from_base_2x * initial_capital_2x).loc[base_ts:]

    usdkrw, fx_ts = get_usdkrw_rate(base_ts)

    if usdkrw is None:
        st.warning("기준일 환율 데이터를 가져오지 못했어요.")
        st.stop()

    sale_ts = common_dates[-1]
    usdkrw_sale, fx_ts_sale = get_usdkrw_rate(sale_ts)

    if usdkrw_sale is None:
        st.warning("조회일 환율 데이터를 가져오지 못했어요.")
        st.stop()

    initial_capital_1x_krw = initial_capital_1x * usdkrw
    initial_capital_2x_krw = initial_capital_2x * usdkrw

    final_1x_krw = total_1x.iloc[-1] * usdkrw_sale
    final_2x_krw = total_2x.iloc[-1] * usdkrw_sale

    profit_1x_krw = final_1x_krw - initial_capital_1x_krw
    profit_2x_krw = final_2x_krw - initial_capital_2x_krw

    taxable_profit_1x = max(profit_1x_krw - 2_500_000, 0)
    taxable_profit_2x = max(profit_2x_krw - 2_500_000, 0)

    capital_gains_tax_1x = taxable_profit_1x * 0.22
    capital_gains_tax_2x = taxable_profit_2x * 0.22

    after_tax_krw_1x = final_1x_krw - capital_gains_tax_1x
    after_tax_krw_2x = final_2x_krw - capital_gains_tax_2x

    compare_diff = after_tax_krw_2x - after_tax_krw_1x

    purchase_date_text = base_ts.strftime("%Y년 %m월 %d일")

# ----------------------------------------------------------
# 1. 결과 한 줄 요약 (가장 중요한 숫자를 맨 위에)
# ----------------------------------------------------------
if compare_diff > 0:
    st.success(f"**{ticker_2x}**가 **{ticker_1x}**보다 세후 **₩{abs(compare_diff):,.0f}** 더 유리합니다.")
elif compare_diff < 0:
    st.error(f"**{ticker_2x}**가 **{ticker_1x}**보다 세후 **₩{abs(compare_diff):,.0f}** 불리합니다.")
else:
    st.info("두 종목의 세후 수익이 동일합니다.")

st.caption(
    f"매수일 {purchase_date_text} (환율 {usdkrw:,.2f}원) · "
    f"조회일 {fx_ts_sale.strftime('%Y년 %m월 %d일')} (환율 {usdkrw_sale:,.2f}원) 기준"
)

# ----------------------------------------------------------
# 2. 비교 표 (중복 카드 대신 표 하나로 정리)
# ----------------------------------------------------------
row_1x = f"{ticker_1x} (기본형)"
row_2x = f"{ticker_2x} (레버리지)"
winner_row = row_2x if after_tax_krw_2x >= after_tax_krw_1x else row_1x
winner_ticker = ticker_2x if winner_row == row_2x else ticker_1x

after_tax_usd_1x = after_tax_krw_1x / usdkrw
after_tax_usd_2x = after_tax_krw_2x / usdkrw


def sign_color(val):
    return "#2e7d32" if val > 0 else ("#c62828" if val < 0 else "inherit")


# (지표, 1x 값, 2x 값, 단위, 퍼센트여부)
metric_rows = [
    ("누적 수익률", final_r_1x, final_r_2x, "", True),
    ("세후 자산 (USD)", after_tax_usd_1x, after_tax_usd_2x, "$", False),
    ("세후 자산 (₩)", after_tax_krw_1x, after_tax_krw_2x, "₩", False),
    ("세전 자산 (USD)", total_1x.iloc[-1], total_2x.iloc[-1], "$", False),
    ("세전 자산 (₩)", final_1x_krw, final_2x_krw, "₩", False),
    ("양도소득세", capital_gains_tax_1x, capital_gains_tax_2x, "₩", False),
]

cell_style = "padding:9px 12px; border:1px solid #ddd; word-break:break-word; line-height:1.4;"
col_style_1x = cell_style + ("background-color:#e8f5e9;" if winner_row == row_1x else "")
col_style_2x = cell_style + ("background-color:#e8f5e9;" if winner_row == row_2x else "")
col_style_diff = cell_style + "background-color:#f5f5f5;"

metric_rows_html = ""
for label, v1, v2, unit, pct in metric_rows:
    diff = v2 - v1
    if pct:
        c1 = f"<span style='color:{sign_color(v1)}; font-weight:600;'>{v1:+.2%}</span>"
        c2 = f"<span style='color:{sign_color(v2)}; font-weight:600;'>{v2:+.2%}</span>"
        cdiff = f"<span style='color:{sign_color(diff)}; font-weight:700;'>{diff:+.2%}</span>"
    else:
        c1 = f"{unit}{v1:,.0f}"
        c2 = f"{unit}{v2:,.0f}"
        cdiff = f"<span style='color:{sign_color(diff)}; font-weight:700;'>{unit}{diff:+,.0f}</span>"
    metric_rows_html += f"""<tr>
<td style='{cell_style}'>{label}</td>
<td style='{col_style_1x}'>{c1}</td>
<td style='{col_style_2x}'>{c2}</td>
<td style='{col_style_diff}'>{cdiff}</td>
</tr>"""

st.markdown(
    f"""
<table style="width:100%; max-width:100%; table-layout:fixed; border-collapse:collapse; font-size:0.95em;">
<colgroup>
<col style="width:18%;"><col style="width:24%;"><col style="width:24%;"><col style="width:34%;">
</colgroup>
<tr>
<th style='{cell_style} text-align:left;'></th>
<th style='{col_style_1x} text-align:left;'>{ticker_1x} (기본형)</th>
<th style='{col_style_2x} text-align:left;'>{ticker_2x} (레버리지)</th>
<th style='{col_style_diff} text-align:left;'>차이 (레버리지-기본형)</th>
</tr>
{metric_rows_html}
</table>
""",
    unsafe_allow_html=True,
)

bar_labels = [ticker_1x, ticker_2x]
bar_values = [after_tax_krw_1x, after_tax_krw_2x]
bar_colors = [COLOR_1X, COLOR_2X]
bar_opacities = [1.0 if label == winner_ticker else 0.45 for label in bar_labels]

bar_fig = go.Figure(go.Bar(
    x=bar_values,
    y=bar_labels,
    orientation="h",
    marker=dict(color=bar_colors, opacity=bar_opacities),
    text=[f"₩{v:,.0f}" for v in bar_values],
    textposition="inside",
    insidetextanchor="end",
    textfont=dict(color="white", size=12),
    hovertemplate="%{y}: ₩%{x:,.0f}<extra></extra>",
))
bar_max = max(bar_values) if max(bar_values) > 0 else 1
bar_fig.update_layout(
    title=dict(text="After-tax Value Comparison (KRW)", font=dict(size=13), x=0, xanchor="left"),
    height=180,
    margin=dict(l=60, r=20, t=40, b=20),
    xaxis=dict(visible=False, range=[0, bar_max * 1.1]),
    yaxis=dict(title=None),
    plot_bgcolor="rgba(0,0,0,0)",
    showlegend=False,
)
st.plotly_chart(bar_fig, use_container_width=True, config={"displayModeBar": False})

base_date_short = f"{base_ts.month}/{base_ts.day}"

with st.expander("투자금 · 세금 계산 방식 자세히 보기"):
    st.markdown(
        f"두 종목 모두 **{initial_capital_1x:,.0f} USD (₩{initial_capital_1x_krw:,.0f})**를 "
        "기준일에 동일하게 투자했다고 가정합니다. (소수점 주식 매수 가능 전제)\n\n"
        f"원화 환산은 매수금액은 **매수일 환율({usdkrw:,.2f}원)**, 매도(평가)금액은 "
        f"**조회일 환율({usdkrw_sale:,.2f}원)**을 각각 적용합니다 — 실제 해외주식 양도소득세 계산 방식과 동일하며, "
        "그 기간 환율 변동 효과(환차손/익)도 그대로 반영됩니다."
    )

    detail_rows = [
        (f"매수가 ({base_date_short} 기준)", f"{shareprice_1x:,.2f} USD", f"{shareprice_2x:,.2f} USD"),
        ("매수 수량(추정)", f"{shares_1x:,.2f}주", f"{shares_2x:,.2f}주"),
        ("투자원금(₩)", f"₩{initial_capital_1x_krw:,.0f}", f"₩{initial_capital_2x_krw:,.0f}"),
        ("수익금(세전 원화, 조회일 기준)", f"₩{profit_1x_krw:,.0f}", f"₩{profit_2x_krw:,.0f}"),
    ]
    detail_label_style = "padding:10px 14px; border:1px solid #ddd; white-space:nowrap;"
    detail_val_style = "padding:10px 14px; border:1px solid #ddd;"
    rows_html = "".join(
        f"<tr><td style='{detail_label_style}'>{label}</td>"
        f"<td style='{detail_val_style}'>{v1}</td>"
        f"<td style='{detail_val_style}'>{v2}</td></tr>"
        for label, v1, v2 in detail_rows
    )
    st.markdown(
        f"""
<table style="width:100%; max-width:100%; table-layout:fixed; border-collapse:collapse; font-size:0.9em;">
<colgroup>
<col style="width:46%;"><col style="width:27%;"><col style="width:27%;">
</colgroup>
<tr>
<th style='{detail_label_style}'></th>
<th style='{detail_val_style} text-align:left;'>{ticker_1x}</th>
<th style='{detail_val_style} text-align:left;'>{ticker_2x}</th>
</tr>
{rows_html}
</table>
""",
        unsafe_allow_html=True,
    )

    st.markdown("양도소득세는 수익금에서 250만 원을 뺀 금액의 22%입니다. (수익금 250만 원 이하면 세금 0원)")

st.divider()

# ----------------------------------------------------------
# 3. 차트 (기본은 깔끔하게, 괴리율은 선택적으로만 표시)
# ----------------------------------------------------------
tab2, tab3 = st.tabs(["누적 수익률", "총자산"])

cum_r1 = (cum_from_base_1x.loc[base_ts:] - 1) * 100
cum_r2 = (cum_from_base_2x.loc[base_ts:] - 1) * 100

simple_2x = 1 + 2 * (cum_from_base_1x.loc[base_ts:] - 1)
simple_2x_return = (simple_2x - 1) * 100

actual_2x = cum_from_base_2x.loc[base_ts:]
gap_rate = ((actual_2x - simple_2x) / simple_2x) * 100
final_gap = float(gap_rate.iloc[-1])


def base_layout(title, yaxis_title):
    return dict(
        title=dict(text=title, font=dict(size=14), x=0, xanchor="left"),
        hovermode="x unified",
        height=420,
        margin=dict(l=50, r=20, t=50, b=60),
        xaxis=dict(title=None, hoverformat="%Y-%m-%d"),
        yaxis=dict(title=yaxis_title),
        legend=dict(orientation="h", yanchor="top", y=-0.18, xanchor="left", x=0),
        plot_bgcolor="rgba(0,0,0,0)",
    )


with tab2:
    fig2 = go.Figure()
    fig2.add_trace(go.Scatter(
        x=cum_r1.index, y=cum_r1.values, mode="lines", name=f"{ticker_1x} Return",
        line=dict(color=COLOR_1X, width=2), hovertemplate=f"{ticker_1x}: %{{y:+.2f}}%<extra></extra>",
    ))
    fig2.add_trace(go.Scatter(
        x=simple_2x_return.index, y=simple_2x_return.values, mode="lines", name="Simple 2x Expected",
        line=dict(color=COLOR_EXPECTED, width=1.5, dash="dash"),
        hovertemplate=f"Simple 2x Expected: %{{y:+.2f}}%<extra></extra>",
    ))
    fig2.add_trace(go.Scatter(
        x=cum_r2.index, y=cum_r2.values, mode="lines", name=f"{ticker_2x} Actual Return",
        line=dict(color=COLOR_2X, width=2), hovertemplate=f"{ticker_2x}: %{{y:+.2f}}%<extra></extra>",
    ))
    fig2.add_hline(y=0, line_width=0.6, line_color="black")
    fig2.update_layout(**base_layout(f"{ticker_1x} vs {ticker_2x} Cumulative Return", "%"))
    st.plotly_chart(fig2, use_container_width=True)

    st.caption(f"최근 괴리율: {final_gap:+.2f}% · 실제 2x 결과가 단순 2배 기대값과 벌어진 정도")

    st.markdown("**일별 괴리율 상세**")

    fig2b = go.Figure()
    fig2b.add_trace(go.Scatter(
        x=gap_rate.index, y=gap_rate.values, mode="markers",
        marker=dict(
            color=gap_rate.values, colorscale="RdBu", size=10,
            line=dict(color="black", width=0.5), showscale=False,
        ),
        name="Gap Rate", hovertemplate="Gap: %{y:+.2f}%<extra></extra>",
    ))
    fig2b.add_hline(y=0, line_width=0.6, line_color="black")
    layout2b = base_layout("Daily Gap Rate (%)", "%")
    layout2b["height"] = 280
    layout2b["showlegend"] = False
    fig2b.update_layout(**layout2b)
    st.plotly_chart(fig2b, use_container_width=True)

    with st.expander("괴리율이란?"):
        st.markdown("""
- **0%에 가까우면**: 실제 2x 복리 결과가 단순 2배 기대값과 거의 비슷합니다.
- **양수면**: 실제 결과가 단순 2배보다 높습니다 (상승장에서 더 유리, 하락장에서 덜 불리).
- **음수면**: 실제 결과가 단순 2배보다 낮습니다 (상승장에서 덜 유리, 하락장에서 더 불리).
""")

with tab3:
    expected_2x_value = simple_2x * initial_capital_1x

    fig3 = go.Figure()
    fig3.add_trace(go.Scatter(
        x=total_1x.index, y=total_1x.values, mode="lines", name=f"{ticker_1x} Value",
        line=dict(color=COLOR_1X, width=2), hovertemplate=f"{ticker_1x}: $%{{y:,.0f}}<extra></extra>",
    ))
    fig3.add_trace(go.Scatter(
        x=expected_2x_value.index, y=expected_2x_value.values, mode="lines", name="Simple 2x Expected",
        line=dict(color=COLOR_EXPECTED, width=1.5, dash="dash"),
        hovertemplate="Simple 2x Expected: $%{y:,.0f}<extra></extra>",
    ))
    fig3.add_trace(go.Scatter(
        x=total_2x.index, y=total_2x.values, mode="lines", name=f"{ticker_2x} Actual Value",
        line=dict(color=COLOR_2X, width=2), hovertemplate=f"{ticker_2x}: $%{{y:,.0f}}<extra></extra>",
    ))
    fig3.update_layout(**base_layout(f"{ticker_1x} vs {ticker_2x} Portfolio Value", "USD"))
    st.plotly_chart(fig3, use_container_width=True)

    with st.expander("복리 효과란?"):
        st.markdown("""
누적 수익률은 매일의 수익률이 복리로 누적된 결과입니다.

예를 들어 첫날 +10% 상승 후 다음날 -5% 하락하면 단순 계산으로는 +5%처럼 보이지만,
실제 자산은 100 → 110 → 104.5가 되어 최종 누적 수익률은 +4.5%입니다.

레버리지 ETF(2x)도 같은 방식으로 계산되며, 변동성이 클수록 단순 2배와 차이가 커질 수 있습니다.
""")
