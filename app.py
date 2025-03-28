import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import yfinance as yf
import streamlit.components.v1 as components

st.set_page_config(page_title="Stock Analysis", layout="centered")
st.title("Stock Analysis App")

# Load S&P 500 symbols
@st.cache_data
def load_symbols():
    url = "https://raw.githubusercontent.com/datasets/s-and-p-500-companies/master/data/constituents.csv"
    df = pd.read_csv(url)
    return df["Symbol"].tolist()

stock_list = load_symbols()

# User selects from dropdown or types custom symbol
selected_option = st.selectbox("Pick a stock (or type your own below):", [""] + stock_list)
custom_symbol = st.text_input("Or enter a custom symbol:")

# Final stock symbol selection
if custom_symbol.strip():
    final_symbol = custom_symbol.strip().upper()
elif selected_option:
    final_symbol = selected_option
else:
    final_symbol = None

@st.cache_data
def load_data(symbol, period="1y"):
    df = yf.download(symbol, period=period)
    if df.empty:
        raise ValueError(f"No data found for {symbol}.")
    df.reset_index(inplace=True)
    df["Date"] = pd.to_datetime(df["Date"])
    df.set_index("Date", inplace=True)
    return df

def key_levels(data):
    high = data["High"].rolling(window=30).max()
    low = data["Low"].rolling(window=30).min()
    return high, low

def make_decision(data):
    if len(data) < 200:
        return "HOLD", None, None, None, None

    latest = data.iloc[-1]

    # Check for missing values in required indicators
    if pd.isnull(latest[["SMA_50", "SMA_200", "Volatility", "Close", "Support"]]).any():
        return "HOLD", None, None, None, None

    try:
        sma_50 = float(latest["SMA_50"])
        sma_200 = float(latest["SMA_200"])
        volatility = float(latest["Volatility"])
        close = float(latest["Close"])
        support = float(latest["Support"])
    except Exception as e:
        return "HOLD", None, None, None, None

    # Now all values are scalars, safe to compare
    if (sma_50 > sma_200) and (volatility < 0.02) and (close > support):
        return "BUY", close, close * 1.02, close * 0.98, 2

    return "HOLD", None, None, None, None

if final_symbol:
    try:
        df = load_data(final_symbol)
        df["SMA_50"] = df["Close"].rolling(window=50).mean()
        df["SMA_200"] = df["Close"].rolling(window=200).mean()
        df["Daily Return"] = df["Close"].pct_change()
        df["Volatility"] = df["Daily Return"].rolling(window=30).std()
        df["Resistance"], df["Support"] = key_levels(df)

        # Plotting
        st.subheader("Stock Price Chart")
        fig, ax = plt.subplots(figsize=(10, 5))
        ax.plot(df.index, df["Close"], label="Closing Price", color="blue")
        ax.plot(df.index, df["SMA_50"], label="50-day SMA", linestyle="dashed", color="green")
        ax.plot(df.index, df["SMA_200"], label="200-day SMA", linestyle="dashed", color="red")
        ax.fill_between(df.index, df["Support"], df["Resistance"], color="gray", alpha=0.3, label="Key Levels")
        ax.set_title(f"{final_symbol} Stock Price Evolution")
        ax.legend()
        st.pyplot(fig)

        # Interactive TradingView chart
        st.subheader("TradingView Chart")

        exchange = st.selectbox("Select Exchange:", ["NYSE", "NASDAQ"], index=0)
        symbol_tv = f"{exchange}:{final_symbol}"

        full_widget = f"""
        <!-- TradingView Widget BEGIN -->
        <div class="tradingview-widget-container">
        <div id="tradingview_{final_symbol}"></div>
        <script type="text/javascript" src="https://s3.tradingview.com/tv.js"></script>
        <script type="text/javascript">
        new TradingView.widget({{
            "width": "100%",
            "height": 500,
            "symbol": "{symbol_tv}",
            "interval": "D",
            "timezone": "Etc/UTC",
            "theme": "dark",
            "style": "1",
            "locale": "en",
            "toolbar_bg": "#f1f3f6",
            "enable_publishing": false,
            "hide_top_toolbar": true,
            "save_image": false,
            "container_id": "tradingview_{final_symbol}"
        }});
        </script>
        </div>
        <!-- TradingView Widget END -->
        """

        components.html(full_widget, height=520)

        # Trading Decision
        st.subheader("Trading Decision")

        decision, entry, tp, sl, rr = make_decision(df)
        if decision == "BUY":
            st.markdown(
    f"<div style='background-color:#1b4332;padding:10px;border-radius:8px;color:white'>"
    f"<strong>BUY</strong> at ${entry:.2f} | <strong>TP:</strong> ${tp:.2f} | "
    f"<strong>SL:</strong> ${sl:.2f} | <strong>RR:</strong> {rr}:1"
    f"</div>",
    unsafe_allow_html=True
)
        else:
            st.info("Not worth it. HOLD.")
    except Exception as e:
        st.error(f"Error loading data: {e}")
else:
    st.info("Please select or enter a stock symbol to continue.")
