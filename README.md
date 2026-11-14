# NIFTY 50 — 10 Variable Return & Price Prediction

This is a single-page Streamlit app. It has no navigation pages and no subfolders.

## What it predicts
- Next NIFTY 50 trading-session percentage return.
- Implied next-session NIFTY closing level, calculated from the predicted return.

## Exactly 10 model variables
1. NIFTY return today
2. NIFTY return previous session
3. NIFTY return two sessions ago
4. NIFTY 5-session momentum
5. NIFTY 5-session volatility
6. NIFTY 20-session volatility
7. RSI (14)
8. MACD as percentage of NIFTY
9. India VIX level
10. Previous completed S&P 500 session return

The app shows permutation importance for these ten variables on the untouched chronological holdout. Importance is predictive contribution, not causal impact.

## Data
The user's Excel workbook is embedded as `market_data.xlsx`. It contains 22 daily NIFTY rows, 130 monthly SIP/FII/DII rows and 2,824 daily VIX/S&P 500 rows. The VIX/S&P history is not ten years of NIFTY OHLC.
At runtime, the app attempts to download up to 10 years of daily NIFTY 50 OHLC using Yahoo Finance `^NSEI` (no API key). If unavailable, the app falls back to embedded NIFTY data and refuses to train with fewer than 250 labelled rows.

## Models and validation
Linear Regression, Ridge, Random Forest, Extra Trees, HistGradientBoosting.
Chronological 80/20 holdout; 5-fold expanding TimeSeriesSplit model selection; sklearn pipelines; no random splitting. The best model is selected by training-period walk-forward CV RMSE.

## Deploy
Upload all files in this folder directly to GitHub repository root. Choose `app.py` as the Streamlit Cloud main file. No subfolders or manual Excel upload.

## Local run
```bash
pip install -r requirements.txt
streamlit run app.py
```
