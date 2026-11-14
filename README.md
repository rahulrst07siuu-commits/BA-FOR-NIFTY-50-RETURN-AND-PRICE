# Nifty 50 Market Intelligence Terminal

## One-step deployment
This repository is deliberately flat: all files are in the repository root. The historical workbook is bundled as `market_data.xlsx`; no upload is required at runtime.

1. Upload **all files** in this folder to the root of a GitHub repository.
2. In Streamlit Community Cloud, create an app from that repository.
3. Set the main file path to `app.py`.
4. Deploy. Streamlit installs packages from `requirements.txt`.

Do not upload only `app.py`. Keep `market_data.xlsx` in the same directory as `app.py`.

## Run locally
```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

## Included source data
`market_data.xlsx` is the exact supplied workbook and contains eight worksheets. The app loads:
- Daily Nifty Model Data (daily)
- Monthly SIP FII DII (monthly)
- Monthly Derived Vars (monthly)
- Full Daily VIX SP500 (daily external history)
- Source Audit and Variable Register

The daily and monthly datasets are kept separate. Missing values are not filled with zero.

## Known data limitations
- Daily Nifty modelling sheet contains 22 observations. This is insufficient for reliable ML fitting, walk-forward model comparison, clustering, or a calibrated next-session forecast. Those outputs are intentionally withheld.
- Monthly SIP/FII/DII contains 130 months, with missing SIP values. The workbook does not include a current-month Nifty return outcome for the SIP Shield regression. `Previous Month Nifty Return (%)` is a lagged field and is not substituted as the dependent variable.
- No paid APIs or API keys are used.

## Deployment configuration
- Repository root: this folder's contents
- Main file: `app.py`
- Dependencies: `requirements.txt`
- Bundled data: `market_data.xlsx`
