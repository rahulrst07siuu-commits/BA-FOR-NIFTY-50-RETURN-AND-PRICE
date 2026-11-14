from pathlib import Path
import warnings
warnings.filterwarnings("ignore")

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go

st.set_page_config(page_title="Nifty 50 Market Intelligence", page_icon="📈", layout="wide")
BASE = Path(__file__).resolve().parent
DATA_FILE = BASE / "market_data.xlsx"

NAVY = "#14283F"
TEAL = "#008C95"
GREY = "#718096"

@st.cache_data
def load_data():
    if not DATA_FILE.exists():
        raise FileNotFoundError("market_data.xlsx is missing. Keep it beside app.py in the GitHub repository.")
    daily = pd.read_excel(DATA_FILE, sheet_name="Daily Nifty Model Data", header=3)
    monthly = pd.read_excel(DATA_FILE, sheet_name="Monthly SIP FII DII", header=3)
    derived = pd.read_excel(DATA_FILE, sheet_name="Monthly Derived Vars", header=3)
    external = pd.read_excel(DATA_FILE, sheet_name="Full Daily VIX SP500", header=3)
    audit = pd.read_excel(DATA_FILE, sheet_name="Source Audit", header=3)
    variables = pd.read_excel(DATA_FILE, sheet_name="Variable Register", header=3)
    daily["Date"] = pd.to_datetime(daily["Date"], errors="coerce")
    monthly["Month"] = pd.to_datetime(monthly["Month"], errors="coerce")
    derived["Month"] = pd.to_datetime(derived["Month"], errors="coerce")
    external["Date"] = pd.to_datetime(external["Date"], errors="coerce")
    daily = daily.dropna(subset=["Date"]).sort_values("Date").reset_index(drop=True)
    monthly = monthly.dropna(subset=["Month"]).sort_values("Month").reset_index(drop=True)
    return daily, monthly, derived, external, audit, variables

try:
    daily, monthly, derived, external, source_audit, variable_register = load_data()
    DATA_OK = True
except Exception as exc:
    DATA_OK = False
    LOAD_ERROR = str(exc)

st.markdown(f"""
<style>
.stApp {{background:#F4F7FA; color:{NAVY};}}
[data-testid="stSidebar"] {{background:#10243A;}}
[data-testid="stSidebar"] * {{color:#F4F7FA !important;}}
h1,h2,h3 {{color:{NAVY};}}
div[data-testid="stMetric"] {{background:white;border:1px solid #E3EAF0;padding:14px;border-radius:10px;}}
div.stButton>button {{background:{TEAL};color:white;border-radius:7px;}}
</style>
""", unsafe_allow_html=True)

st.title("📈 NIFTY 50 | MARKET INTELLIGENCE TERMINAL")
st.caption("Embedded historical workbook · Daily forecasting and monthly SIP Shield research remain separate analytical workstreams.")

if not DATA_OK:
    st.error(f"Dataset could not be loaded: {LOAD_ERROR}")
    st.stop()

pages = [
    "Executive Overview", "Data Audit", "Exploratory Analysis", "Technical Indicators",
    "Regression", "Classification", "Model Comparison", "Walk-Forward Validation",
    "Unsupervised Learning", "Market Regimes", "Explainability", "Next-Session Forecast",
    "Risk Analysis", "SIP Shield Research", "Managerial Decision Support",
    "Methodology and Disclaimer"
]
page = st.sidebar.radio("NAVIGATION", pages)
st.sidebar.markdown("---")
st.sidebar.caption("Data is bundled in market_data.xlsx. No upload or API key is required.")
st.sidebar.caption(f"Daily observations: {len(daily)} · Monthly observations: {len(monthly)}")

def metric_row():
    last = daily.iloc[-1]
    a,b,c,d = st.columns(4)
    a.metric("Latest Nifty close", f"{last['Nifty_Close']:,.2f}")
    a2 = last.get("Nifty_Return_Calc_Pct", np.nan)
    b.metric("Latest daily return", f"{a2:.3f}%" if pd.notna(a2) else "N/A")
    c.metric("India VIX", f"{last['IndiaVIX_Close']:.2f}" if pd.notna(last["IndiaVIX_Close"]) else "N/A")
    d.metric("Daily observations", f"{len(daily)}")

def note_small_sample():
    st.warning(f"Only {len(daily)} daily observations are available. This is insufficient for reliable machine-learning training, five-fold time-series validation, or a defensible out-of-sample forecast. The app will not manufacture model scores.")

if page == "Executive Overview":
    metric_row()
    st.subheader("Market snapshot")
    c1,c2 = st.columns([2,1])
    with c1:
        fig=px.line(daily,x="Date",y="Nifty_Close",title="Nifty 50 closing level", markers=True)
        fig.update_traces(line_color=TEAL)
        st.plotly_chart(fig,use_container_width=True)
    with c2:
        st.metric("Monthly SIP records",len(monthly))
        st.metric("SIP values available",int(monthly["SIP Inflow (cr)"].notna().sum()))
        st.metric("Daily date range",f"{daily.Date.min():%d %b %Y} – {daily.Date.max():%d %b %Y}")
    note_small_sample()
    st.info("The bundled workbook is loaded automatically. No manual file upload is needed.")

elif page == "Data Audit":
    st.subheader("Workbook inventory")
    st.write("The application reads the original eight-sheet workbook bundled with the project.")
    inventory=[]
    for name in pd.ExcelFile(DATA_FILE).sheet_names:
        raw=pd.read_excel(DATA_FILE,sheet_name=name,header=None)
        inventory.append({"Worksheet":name,"Rows":len(raw),"Columns":len(raw.columns)})
    st.dataframe(pd.DataFrame(inventory),use_container_width=True,hide_index=True)
    st.subheader("Daily Nifty data quality")
    audit=daily.isna().sum().rename("Missing values").to_frame()
    audit["Missing %"]=(audit["Missing values"]/len(daily)*100).round(1)
    st.dataframe(audit,use_container_width=True)
    st.write("Date range:",daily.Date.min(), "to", daily.Date.max())
    st.write("Duplicate dates:",int(daily.Date.duplicated().sum()))
    st.subheader("Monthly SIP/FII/DII data quality")
    ma=monthly.isna().sum().rename("Missing values").to_frame()
    ma["Missing %"]=(ma["Missing values"]/len(monthly)*100).round(1)
    st.dataframe(ma,use_container_width=True)
    st.info("Missing SIP observations remain missing. No missing financial observations are silently replaced with zero.")
    with st.expander("Source audit worksheet"): st.dataframe(source_audit,use_container_width=True)
    with st.expander("Variable register worksheet"): st.dataframe(variable_register,use_container_width=True)

elif page == "Exploratory Analysis":
    st.subheader("Daily Nifty history")
    col=st.selectbox("Metric",["Nifty_Close","Nifty_Open","Nifty_High","Nifty_Low","IndiaVIX_Close","SP500_Close"])
    st.plotly_chart(px.line(daily,x="Date",y=col,markers=True),use_container_width=True)
    st.subheader("Monthly investor flows")
    mcol=st.selectbox("Monthly variable",["SIP Inflow (cr)","FII Net Flow (cr)","DII Net Flow (cr)"])
    st.plotly_chart(px.line(monthly,x="Month",y=mcol,markers=True),use_container_width=True)
    st.caption("Daily and monthly series are plotted independently and are never expanded to a shared daily panel.")

elif page == "Technical Indicators":
    st.subheader("Technical indicators")
    x=daily.copy()
    x["SMA5"]=x.Nifty_Close.rolling(5).mean()
    x["SMA10"]=x.Nifty_Close.rolling(10).mean()
    x["EMA9"]=x.Nifty_Close.ewm(span=9,adjust=False).mean()
    x["EMA20"]=x.Nifty_Close.ewm(span=20,adjust=False).mean()
    delta=x.Nifty_Close.diff()
    gain=delta.clip(lower=0).rolling(14).mean()
    loss=-delta.clip(upper=0).rolling(14).mean()
    x["RSI14"]=100-(100/(1+gain/loss.replace(0,np.nan)))
    fig=go.Figure()
    for col in ["Nifty_Close","SMA5","SMA10","EMA9","EMA20"]:
        fig.add_trace(go.Scatter(x=x.Date,y=x[col],name=col))
    st.plotly_chart(fig,use_container_width=True)
    st.plotly_chart(px.line(x,x="Date",y="RSI14",title="RSI (14) — unavailable until sufficient history"),use_container_width=True)
    st.dataframe(x[["Date","Nifty_Close","SMA5","SMA10","EMA9","EMA20","RSI14"]],use_container_width=True)

elif page in ["Regression","Classification","Model Comparison","Walk-Forward Validation"]:
    st.subheader(page)
    note_small_sample()
    st.write("The modelling workflow is intentionally gated until the daily history supports defensible chronological training and validation.")
    st.write("No random train/test split is used. No performance metrics are fabricated.")
    st.write("Available future workflow: chronological holdout, expanding-window walk-forward validation, baseline comparison, and fold-contained preprocessing.")
    st.dataframe(daily[["Date","Nifty_Close","Nifty_Return_Calc_Pct","Target_Next_Session_Return_Pct"]].tail(10),use_container_width=True)

elif page == "Unsupervised Learning":
    st.subheader("Unsupervised learning")
    st.warning("K-Means and PCA are not run on 22 observations with sparse lag/indicator features. Clusters would be unstable and misleading.")
    st.write("A larger daily history is required before clustering or PCA is enabled.")

elif page == "Market Regimes":
    st.subheader("Market regime context")
    st.write("A descriptive volatility view is available; statistical regime clustering is withheld due to the short daily sample.")
    st.plotly_chart(px.line(daily,x="Date",y="IndiaVIX_Close",title="India VIX"),use_container_width=True)
    st.dataframe(daily[["Date","Nifty_Close","IndiaVIX_Close","Nifty_Rolling_Volatility_5d_Pct"]],use_container_width=True)

elif page == "Explainability":
    st.subheader("Model explainability")
    note_small_sample()
    st.info("Feature importance, permutation importance, SHAP, and coefficients require a validated fitted model. None are displayed without one.")
    st.write("Available observed inputs:")
    st.dataframe(daily.select_dtypes(include="number").describe().T,use_container_width=True)

elif page == "Next-Session Forecast":
    st.subheader("Next-session forecast")
    note_small_sample()
    st.metric("Last observed Nifty close",f"{daily.iloc[-1].Nifty_Close:,.2f}")
    st.metric("Last observed India VIX",f"{daily.iloc[-1].IndiaVIX_Close:.2f}")
    st.error("A statistically defensible next-session model forecast is unavailable with the current 22-session history. The app deliberately does not present a naïve extrapolation as an ML forecast.")
    st.write("The workbook contains historical next-session target labels for 21 rows, but that is not enough for reliable training and untouched holdout evaluation.")

elif page == "Risk Analysis":
    st.subheader("Observed market risk")
    vix=daily["IndiaVIX_Close"].dropna()
    st.metric("Latest India VIX",f"{vix.iloc[-1]:.2f}" if len(vix) else "N/A")
    st.metric("Mean India VIX in supplied daily sample",f"{vix.mean():.2f}" if len(vix) else "N/A")
    st.plotly_chart(px.line(daily,x="Date",y="IndiaVIX_Close",title="India VIX history"),use_container_width=True)
    st.warning("A calibrated prediction interval or forecast-risk score cannot be estimated credibly from this short sample.")

elif page == "SIP Shield Research":
    st.subheader("The Domestic SIP Shield Effect")
    st.write("Research question: Do mutual fund SIP inflows support Nifty returns during periods of FII selling?")
    a,b,c=st.columns(3)
    a.metric("Monthly observations",len(monthly))
    b.metric("SIP observations available",int(monthly["SIP Inflow (cr)"].notna().sum()))
    c.metric("FII selling months",int((monthly["FII Selling (0/1)"]==1).sum()))
    st.dataframe(monthly[["Month","SIP Inflow (cr)","FII Net Flow (cr)","FII Selling (0/1)","DII Net Flow (cr)"]],use_container_width=True)
    st.subheader("Data sufficiency")
    st.error("The supplied monthly workbook does not contain the current-month Nifty return dependent variable required for the stated SIP Shield regression.")
    st.info("The 'Previous Month Nifty Return (%)' field is a lagged control, not the current-month dependent variable. It is not silently substituted.")
    st.write("Once a correctly aligned monthly Nifty return series is added to the source workbook, the OLS interaction model can be estimated.")
    st.write("H0: SIP inflows have no significant effect on Nifty returns during FII selling.")
    st.write("H1: Higher SIP inflows have a significant positive effect on Nifty returns during FII selling.")

elif page == "Managerial Decision Support":
    st.subheader("Managerial decision support")
    st.markdown("""
    **Current decision: WAIT FOR MORE DATA.**

    - Daily ML forecast: not approved; only 22 daily observations.
    - SIP Shield inference: not approved; current-month Nifty return outcome is absent.
    - Descriptive monitoring: available for Nifty, India VIX, SIP, FII and DII series.
    - Do not interpret descriptive charts as causal evidence or trading recommendations.
    """)
    st.warning("This is a data-readiness decision, not a market direction call.")

elif page == "Methodology and Disclaimer":
    st.subheader("Methodology")
    st.markdown("""
    - Daily forecasting and monthly SIP/FII/DII research are independent datasets.
    - Historical observations are preserved; missing values are not converted to zero.
    - Any future supervised models must use chronological splits and expanding-window validation.
    - Preprocessing must be fitted inside each training fold.
    - Metrics must be reported honestly, including negative out-of-sample R².
    - SIP × FII-selling interaction must be interpreted as conditional association, not causal proof.
    """)
    st.subheader("Disclaimer")
    st.write("Educational and research tool only. Not investment advice, not a guaranteed forecasting system, and not a recommendation to buy or sell securities.")
