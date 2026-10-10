# Leveraged ETF Simulator

## Overview
A Python backtest project analyzing why daily leveraged ETFs (2x, 3x)
do not achieve simple multiple returns over long horizons.

## Live Demo
https://leveraged-etf-simulator.streamlit.app/

Streamlit app (`src/app.py`) deployed on Streamlit Community Cloud.

## Key Concepts
- Daily return reset
- Volatility drag
- Compounding effect

## Notebook
- `notebooks/01_backtest_amd.ipynb`  
  Backtest using AMD price data with daily leveraged return simulation.

## Stack
- Python
- pandas, numpy
- yfinance
- matplotlib
