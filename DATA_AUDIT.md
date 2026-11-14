# Data audit summary

Audited source: `Nifty50_Daily_and_Monthly_Dataset_V2(2).xlsx` (copied unchanged to `market_data.xlsx`).

Workbook worksheets: 8
- Read Me
- Daily Nifty Model Data
- Monthly SIP FII DII
- Monthly Derived Vars
- Full Daily VIX SP500
- Source Audit
- Variable Register
- Model Plan

## Key observations
- Daily Nifty Model Data: 22 rows, 26 columns; dates 2026-10-14 through 2026-11-13 (as supplied).
- Monthly SIP FII DII: 130 rows, 14 columns; 125 non-missing SIP inflows (5 missing).
- Monthly Derived Vars: 130 rows, 4 columns; Previous Month Nifty Return has 128 non-missing values; Previous 3-Month Return Volatility has 126 non-missing values.
- Full Daily VIX SP500: 2,824 rows, 13 columns.
- The daily target columns have 21 non-missing next-session returns/closes, not enough for defensible ML validation.
- The SIP/FII/DII sheet does not include a current-month Nifty return dependent variable. The lagged previous-month return is not a substitute.

## Safeguards
- Daily and monthly datasets remain at their original frequencies.
- Original workbook is bundled unchanged.
- No missing market observations are replaced with zero.
- No synthetic market observations are used in the app.
