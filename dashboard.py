import streamlit as st
import pandas as pd
import sqlite3
import plotly.express as px
import ccxt
from datetime import datetime
import os

# --- KONFIGURASI ---
DB_PATH = 'data/trading_log.db'
st.set_page_config(page_title="SigCrypt Dashboard", layout="wide")

# Ensure DB folder exists
if not os.path.exists('data'):
    os.makedirs('data')

# --- CACHE DATA UNTUK PERFORMANCE ---
@st.cache_data(ttl=10) # Cache selama 10 detik, agar tidak membom DB
def load_data(query):
    try:
        conn = sqlite3.connect(DB_PATH)
        df = pd.read_sql_query(query, conn)
        conn.close()
        return df
    except sqlite3.OperationalError:
        return pd.DataFrame()

# --- SIDEBAR ---
st.sidebar.title("🤖 SigCrypt V3")
menu = st.sidebar.radio("Navigation", ["📊 Portfolio", "📜 History & Logs", "⚙️ System Control"])

# --- HALAMAN 1: PORTFOLIO ---
if menu == "📊 Portfolio":
    st.header("📊 Live Paper Trading Portfolio")
    
    # Ambil data trades
    df_trades = load_data("SELECT * FROM trades ORDER BY close_time DESC")
    
    if not df_trades.empty:
        df_open = df_trades[df_trades['status'] == 'OPEN']
        df_closed = df_trades[df_trades['status'] == 'CLOSED']
    else:
        df_open = pd.DataFrame()
        df_closed = pd.DataFrame()
    
    # Metrik Utama
    if not df_closed.empty:
        latest_balance = df_closed.iloc[-1]['running_balance']
        total_pnl = df_closed['pnl'].sum()
        wins = len(df_closed[df_closed['pnl'] > 0])
        win_rate = (wins / len(df_closed)) * 100 if len(df_closed) > 0 else 0
    else:
        latest_balance = 10000.0
        total_pnl = 0.0
        win_rate = 0.0

    col1, col2, col3 = st.columns(3)
    col1.metric("Virtual Balance", f"${latest_balance:,.2f}")
    col2.metric("Total PnL", f"${total_pnl:,.2f}", delta=f"{(total_pnl/10000)*100:.2f}%")
    col3.metric("Win Rate", f"{win_rate:.1f}%")

    st.markdown("---")
    
    # Equity Curve
    if not df_closed.empty:
        fig = px.line(df_closed, x="close_time", y="running_balance", title="Equity Curve")
        st.plotly_chart(fig, use_container_width=True)

    # Active Positions
    st.subheader("🟢 Active Positions")
    if df_open.empty:
        st.info("No active positions. Bot is scanning...")
    else:
        st.dataframe(df_open[['symbol', 'side', 'entry_price', 'sl_price', 'tp_price']], use_container_width=True)

# --- HALAMAN 2: HISTORY ---
elif menu == "📜 History & Logs":
    st.header("📜 Trade History & Logs")
    
    tab1, tab2 = st.tabs(["Closed Trades", "Signal Logs"])
    
    with tab1:
        df_closed = load_data("SELECT * FROM trades WHERE status='CLOSED' ORDER BY close_time DESC")
        if df_closed.empty:
            st.warning("No closed trades yet.")
        else:
            st.dataframe(df_closed, use_container_width=True)
            
    with tab2:
        df_signals = load_data("SELECT * FROM signals ORDER BY timestamp DESC")
        if df_signals.empty:
            st.warning("No signals generated yet.")
        else:
            st.dataframe(df_signals, use_container_width=True)

# --- HALAMAN 3: SYSTEM CONTROL ---
elif menu == "⚙️ System Control":
    st.header("⚙️ System Control & Manual Fetch")
    st.warning("⚠️ Manual fetch only updates this dashboard's chart. It does NOT interfere with the core Engine bot.")
    
    symbol = st.selectbox("Select Symbol", ['BTC/USDT', 'ETH/USDT', 'SOL/USDT', 'BNB/USDT', 'ZEC/USDT'])
    
    if st.button("🔄 Fetch Latest 100 Candles"):
        with st.spinner('Fetching data from Binance...'):
            try:
                exchange = ccxt.binance({'enableRateLimit': True, 'options': {'defaultType': 'future'}})
                ohlcv = exchange.fetch_ohlcv(symbol, '1h', limit=100)
                df_manual = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
                df_manual['timestamp'] = pd.to_datetime(df_manual['timestamp'], unit='ms')
                
                st.subheader(f"📈 {symbol} - Latest 1H Chart Data")
                st.dataframe(df_manual.tail(20), use_container_width=True)
                
                # Simple plot
                fig = px.line(df_manual, x='timestamp', y='close', title=f"{symbol} Close Price")
                st.plotly_chart(fig, use_container_width=True)
                
                st.success("Data fetched successfully!")
            except Exception as e:
                st.error(f"Error fetching data: {e}")
