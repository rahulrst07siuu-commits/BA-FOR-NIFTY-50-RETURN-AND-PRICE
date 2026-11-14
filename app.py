from pathlib import Path
import warnings
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from sklearn.base import clone
from sklearn.ensemble import RandomForestRegressor, ExtraTreesRegressor, HistGradientBoostingRegressor
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LinearRegression, Ridge
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import TimeSeriesSplit, cross_val_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.inspection import permutation_importance

warnings.filterwarnings("ignore")
BASE = Path(__file__).resolve().parent
BOOK = BASE / "market_data.xlsx"
MIN_LABELLED = 250

st.set_page_config(page_title="NIFTY 50 Return & Price Predictor", page_icon="📈", layout="wide")
st.markdown("""
<style>
.main {background:#f5f8fb}
h1,h2,h3 {color:#142b45}
div[data-testid="stMetric"] {background:white;border:1px solid #e1e8ef;padding:13px;border-radius:9px}
section[data-testid="stSidebar"] {background:#102a43}
section[data-testid="stSidebar"] * {color:white}
.stButton>button {background:#087f8c;color:white;border:0;border-radius:7px}
</style>
""", unsafe_allow_html=True)

# Exactly ten explanatory variables are used for next-session return prediction.
FEATURE_LABELS = {
    "return_today": "1. NIFTY return (today)",
    "return_lag1": "2. NIFTY return (previous session)",
    "return_lag2": "3. NIFTY return (two sessions ago)",
    "momentum_5": "4. NIFTY 5-session momentum",
    "volatility_5": "5. NIFTY 5-session volatility",
    "volatility_20": "6. NIFTY 20-session volatility",
    "rsi_14": "7. RSI (14)",
    "macd_pct": "8. MACD (% of NIFTY)",
    "india_vix": "9. India VIX level",
    "sp500_prev_return": "10. Previous completed S&P 500 return"
}
FEATURES = list(FEATURE_LABELS)

@st.cache_data(show_spinner=False)
def load_workbook():
    if not BOOK.exists():
        raise FileNotFoundError("market_data.xlsx must be in the same GitHub root as app.py.")
    daily = pd.read_excel(BOOK, sheet_name="Daily Nifty Model Data", header=3)
    factors = pd.read_excel(BOOK, sheet_name="Full Daily VIX SP500", header=3)
    daily = daily.rename(columns={"Nifty_Open":"Open","Nifty_High":"High","Nifty_Low":"Low",
                                  "Nifty_Close":"Close","Volume_Shares_Approx":"Volume"})
    daily = clean_ohlc(daily)
    factors["Date"] = pd.to_datetime(factors["Date"], errors="coerce")
    for c in ["SP500_Return_Calc_Pct","IndiaVIX_Close"]:
        factors[c] = pd.to_numeric(factors[c], errors="coerce")
    return daily, factors

def clean_ohlc(x):
    x=x.copy()
    x["Date"]=pd.to_datetime(x["Date"],errors="coerce")
    for c in ["Open","High","Low","Close"]:
        x[c]=pd.to_numeric(x[c],errors="coerce")
    if "Volume" not in x: x["Volume"]=np.nan
    x["Volume"]=pd.to_numeric(x["Volume"],errors="coerce")
    x=x.dropna(subset=["Date","Open","High","Low","Close"])
    x=x[(x[["Open","High","Low","Close"]]>0).all(axis=1)]
    x=x[(x.High>=x[["Open","Close","Low"]].max(axis=1)) &
        (x.Low<=x[["Open","Close","High"]].min(axis=1))]
    return x.drop_duplicates("Date",keep="last").sort_values("Date").reset_index(drop=True)

@st.cache_data(ttl=21600,show_spinner=False)
def get_ten_year_nifty():
    import yfinance as yf
    raw=yf.download("^NSEI",period="10y",interval="1d",auto_adjust=False,progress=False,threads=False)
    if raw is None or raw.empty: raise RuntimeError("Yahoo Finance did not return NIFTY 50 data.")
    if isinstance(raw.columns,pd.MultiIndex): raw.columns=raw.columns.get_level_values(0)
    raw=raw.reset_index()
    date_col="Date" if "Date" in raw.columns else raw.columns[0]
    raw=raw.rename(columns={date_col:"Date"})
    return clean_ohlc(raw)

def attach_factors(nifty,factors):
    x=nifty.copy()
    f=factors.copy().dropna(subset=["Date"])
    # India VIX is matched to the NIFTY trading date.
    v=f[["Date","IndiaVIX_Close"]].dropna().drop_duplicates("Date").sort_values("Date")
    x=x.merge(v,on="Date",how="left")
    # S&P 500 is strictly lagged: only a completed US session before NIFTY date is used.
    s=f[["Date","SP500_Return_Calc_Pct"]].dropna().drop_duplicates("Date").sort_values("Date")
    s=s.rename(columns={"Date":"SP500_Date","SP500_Return_Calc_Pct":"sp500_prev_return"})
    x=pd.merge_asof(x.sort_values("Date"),s,left_on="Date",right_on="SP500_Date",
                    direction="backward",allow_exact_matches=False)
    return x.sort_values("Date").reset_index(drop=True)

def build_features(x):
    z=x.copy().sort_values("Date").reset_index(drop=True)
    close=z["Close"]
    daily_return=close.pct_change()*100
    z["return_today"]=daily_return
    z["return_lag1"]=daily_return.shift(1)
    z["return_lag2"]=daily_return.shift(2)
    z["momentum_5"]=(close/close.shift(5)-1)*100
    z["volatility_5"]=daily_return.rolling(5).std()
    z["volatility_20"]=daily_return.rolling(20).std()
    delta=close.diff()
    gain=delta.clip(lower=0).rolling(14).mean()
    loss=(-delta.clip(upper=0)).rolling(14).mean()
    rs=gain/loss.replace(0,np.nan)
    z["rsi_14"]=100-(100/(1+rs))
    ema12=close.ewm(span=12,adjust=False).mean()
    ema26=close.ewm(span=26,adjust=False).mean()
    z["macd_pct"]=(ema12-ema26)/close*100
    z["india_vix"]=pd.to_numeric(z["IndiaVIX_Close"],errors="coerce")
    z["sp500_prev_return"]=pd.to_numeric(z["sp500_prev_return"],errors="coerce")
    # Predict next session return. No current/future target leaks into predictors.
    z["target_return_next"] = daily_return.shift(-1)
    z["target_close_next"] = close.shift(-1)
    return z

def model_candidates():
    return {
        "Linear Regression":Pipeline([("imputer",SimpleImputer(strategy="median")),
                                       ("scale",StandardScaler()),("model",LinearRegression())]),
        "Ridge Regression":Pipeline([("imputer",SimpleImputer(strategy="median")),
                                     ("scale",StandardScaler()),("model",Ridge(alpha=5.0))]),
        "Random Forest":Pipeline([("imputer",SimpleImputer(strategy="median")),
                                  ("model",RandomForestRegressor(n_estimators=300,min_samples_leaf=3,
                                                                  max_features=0.8,random_state=42,n_jobs=-1))]),
        "Extra Trees":Pipeline([("imputer",SimpleImputer(strategy="median")),
                                ("model",ExtraTreesRegressor(n_estimators=300,min_samples_leaf=3,
                                                              max_features=0.8,random_state=42,n_jobs=-1))]),
        "Hist Gradient Boosting":Pipeline([("imputer",SimpleImputer(strategy="median")),
                                           ("model",HistGradientBoostingRegressor(max_iter=180,
                                                                                   l2_regularization=2,
                                                                                   random_state=42))])
    }

def fit_models(z):
    d=z.replace([np.inf,-np.inf],np.nan).dropna(subset=["target_return_next"]).copy()
    # Require actual factor coverage; pipeline can impute a small number of missing factor cells.
    d=d.dropna(subset=["return_today","return_lag1","return_lag2","momentum_5",
                       "volatility_5","volatility_20","rsi_14","macd_pct"])
    if len(d)<MIN_LABELLED:
        return None, f"Only {len(d)} labelled observations with technical features are available. At least {MIN_LABELLED} are required; model training is blocked to avoid misleading accuracy."
    X=d[FEATURES]
    y=d["target_return_next"]
    cut=int(len(d)*0.80)
    X_train,X_test=X.iloc[:cut],X.iloc[cut:]
    y_train,y_test=y.iloc[:cut],y.iloc[cut:]
    folds=TimeSeriesSplit(n_splits=5)
    rows=[]; fitted={}
    for name,pipe in model_candidates().items():
        try:
            cv=-cross_val_score(clone(pipe),X_train,y_train,cv=folds,
                                scoring="neg_root_mean_squared_error")
            m=clone(pipe).fit(X_train,y_train)
            p=m.predict(X_test)
            rows.append({"Model":name,"Walk-forward CV RMSE":float(cv.mean()),
                         "Holdout RMSE":float(np.sqrt(mean_squared_error(y_test,p))),
                         "Holdout MAE":float(mean_absolute_error(y_test,p)),
                         "Holdout R²":float(r2_score(y_test,p))})
            fitted[name]=(m,p)
        except Exception:
            continue
    scores=pd.DataFrame(rows)
    if scores.empty: return None,"All model fits failed. Check historical data coverage."
    scores=scores.sort_values("Walk-forward CV RMSE")
    best=scores.iloc[0]["Model"]
    final=clone(model_candidates()[best]).fit(X,y)
    return {"scores":scores,"best":best,"model":final,"fitted":fitted,
            "X_test":X_test,"y_test":y_test,"X":X,"y":y},None

# -------------------------- ONE-PAGE APPLICATION --------------------------
st.title("📈 NIFTY 50 RETURN & PRICE PREDICTION")
st.caption("Predict next-session NIFTY return and closing level using exactly 10 market variables.")

try:
    embedded, factors=load_workbook()
except Exception as e:
    st.error(f"Could not read the embedded workbook: {e}")
    st.stop()

with st.spinner("Loading up to 10 years of NIFTY 50 daily history..."):
    try:
        nifty=get_ten_year_nifty()
        source="Yahoo Finance ^NSEI — up to 10 years of daily data"
    except Exception as e:
        nifty=embedded
        source="Embedded workbook fallback (22 NIFTY sessions)"
        st.warning(f"10-year NIFTY download unavailable: {e}")

market=attach_factors(nifty,factors)
data=build_features(market)
result,error=fit_models(data)

last=data.iloc[-1]
current_close=float(last["Close"])
st.info(f"**Data:** {source}  |  **Observations:** {len(nifty):,}  |  **Period:** {nifty.Date.min():%d %b %Y} – {nifty.Date.max():%d %b %Y}")

if result is None:
    st.warning(error)
    st.markdown("The workbook contains only 22 daily NIFTY observations. Its 2,824-row history is India VIX/S&P 500, not NIFTY OHLC. The app tries to download 10 years of NIFTY history automatically. It will not invent prices or show fake accuracy.")
else:
    latest_X=last[FEATURES].to_frame().T
    predicted_return=float(result["model"].predict(latest_X)[0])
    predicted_close=current_close*(1+predicted_return/100)
    name=result["best"]
    test_model,test_pred=result["fitted"][name]
    residuals=result["y_test"].to_numpy()-test_pred
    q=float(np.quantile(np.abs(residuals),0.90))
    lower=current_close*(1+(predicted_return-q)/100)
    upper=current_close*(1+(predicted_return+q)/100)

    st.subheader("Next Trading Session Prediction")
    a,b,c=st.columns(3)
    a.metric("Predicted NIFTY Return",f"{predicted_return:+.3f}%")
    b.metric("Predicted NIFTY Closing Level",f"{predicted_close:,.2f}")
    c.metric("Latest NIFTY Close",f"{current_close:,.2f}")
    st.write(f"**Selected model:** {name}")
    st.caption(f"Approximate 90% residual-based closing range: {lower:,.2f} – {upper:,.2f}. This is not a guarantee.")

    st.subheader("Effect of the 10 Variables on NIFTY Return")
    st.caption("Permutation importance on the untouched chronological holdout. Larger values indicate a larger contribution to holdout prediction error when that variable is shuffled; this is predictive importance, not causal impact.")
    try:
        imp=permutation_importance(test_model,result["X_test"],result["y_test"],
                                   n_repeats=10,random_state=42,
                                   scoring="neg_root_mean_squared_error")
        importance=pd.DataFrame({"Variable":[FEATURE_LABELS[x] for x in FEATURES],
                                 "Importance":imp.importances_mean,
                                 "Std. deviation":imp.importances_std}).sort_values("Importance",ascending=True)
        fig=px.bar(importance,x="Importance",y="Variable",orientation="h",
                   error_x="Std. deviation",title="Which of the 10 variables matters most for prediction?")
        fig.update_layout(template="plotly_white",height=520)
        st.plotly_chart(fig,use_container_width=True)
        st.dataframe(importance.sort_values("Importance",ascending=False).style.format(
            {"Importance":"{:.5f}","Std. deviation":"{:.5f}"}),use_container_width=True)
    except Exception as e:
        st.warning(f"Variable importance could not be calculated: {e}")

    st.subheader("Model Performance")
    st.caption("Chronological 80/20 final holdout; five-fold expanding-window TimeSeriesSplit for model selection. No random splitting.")
    st.dataframe(result["scores"].style.format({
        "Walk-forward CV RMSE":"{:.4f}","Holdout RMSE":"{:.4f}",
        "Holdout MAE":"{:.4f}","Holdout R²":"{:.4f}"}),use_container_width=True)
    pred_frame=pd.DataFrame({"Actual return (%)":result["y_test"].to_numpy(),
                             "Predicted return (%)":test_pred})
    fig=go.Figure()
    fig.add_trace(go.Scatter(y=pred_frame["Actual return (%)"],mode="lines",name="Actual"))
    fig.add_trace(go.Scatter(y=pred_frame["Predicted return (%)"],mode="lines",name="Predicted"))
    fig.update_layout(title="Actual vs Predicted NIFTY Next-Session Return",
                      xaxis_title="Chronological holdout observation",
                      yaxis_title="Return (%)",template="plotly_white",height=360)
    st.plotly_chart(fig,use_container_width=True)
    st.caption("A negative holdout R² is reported honestly. Model selection is based on training-period walk-forward CV RMSE.")

with st.expander("The 10 variables used by the model"):
    for key,label in FEATURE_LABELS.items():
        st.write(f"**{label}**")
    st.caption("All ten variables are calculated from information available by the forecast date. S&P 500 uses only a prior completed US session. Target is the next NIFTY trading-session return.")

st.warning("Educational forecasting only. Financial market relationships are unstable; no forecast or model accuracy is guaranteed. Predictive importance does not establish causation or investment advice.")
