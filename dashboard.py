import streamlit as st
import pandas as pd
import sqlite3
import plotly.express as px
import ccxt
from datetime import datetime
import os
from dotenv import load_dotenv, set_key

# Load environment
load_dotenv()

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
st.sidebar.title("🤖 SigCrypt V4")
menu = st.sidebar.radio("Navigation", ["📊 Portfolio", "📜 History & Logs", "🧠 Bot Mind & Logs", "⚙️ System Control"])

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

# ==========================================
# HALAMAN BARU: BOT MIND & LOGS
# ==========================================
elif menu == "🧠 Bot Mind & Logs":
    st.header("🧠 What is the Bot Thinking?")
    st.write("Every hour, the bot evaluates the market. Here are its exact reasons for acting or staying out.")
    
    # Filter
    col1, col2 = st.columns(2)
    with col1:
        filter_symbol = st.multiselect("Filter by Symbol", ['BTC/USDT', 'ETH/USDT', 'SOL/USDT', 'BNB/USDT', 'ZEC/USDT', 'AVAX/USDT', 'INJ/USDT', 'LINK/USDT', 'SUI/USDT', 'FET/USDT'])
    with col2:
        filter_decision = st.selectbox("Filter by Decision", ["ALL", "SIGNAL_FOUND", "NO_SIGNAL"])

    # Query Builder
    query = "SELECT * FROM bot_logs WHERE 1=1"
    if filter_symbol:
        symbols_str = "','".join(filter_symbol)
        query += f" AND symbol IN ('{symbols_str}')"
    if filter_decision != "ALL":
        query += f" AND decision = '{filter_decision}'"
    query += " ORDER BY timestamp DESC LIMIT 200"

    # Load & Display
    @st.cache_data(ttl=10)
    def load_logs(q):
        try:
            conn = sqlite3.connect(DB_PATH)
            df = pd.read_sql_query(q, conn)
            conn.close()
            return df
        except sqlite3.OperationalError:
            return pd.DataFrame()

    df_logs = load_logs(query)
    
    if df_logs.empty:
        st.warning("No logs yet. Bot might be sleeping or DB is empty.")
    else:
        # Warna berdasarkan keputusan
        def highlight_decision(val):
            if val == 'SIGNAL_FOUND': color = '#d4edda' # Hijau
            elif val == 'NO_SIGNAL': color = '#fff3cd' # Kuning
            else: color = ''
            return f'background-color: {color}'

        st.dataframe(df_logs.style.applymap(highlight_decision, subset=['decision']), use_container_width=True)

# ==========================================
# HALAMAN UPDATE: SYSTEM CONTROL
# ==========================================
elif menu == "⚙️ System Control":
    st.header("⚙️ System Control & Configuration")
    
    # --- DYNAMIC THRESHOLD CONTROLLER ---
    st.subheader("🎯 Aggressiveness Tuning")
    st.write("Adjust the minimum confidence required for the bot to execute a trade.")
    
    current_threshold = int(os.environ.get("CONFIDENCE_THRESHOLD", 40))
    new_threshold = st.slider("Confidence Threshold (%)", min_value=10, max_value=80, value=current_threshold, step=5)
    
    if st.button("💾 Save Threshold to .env"):
        # Update file .env di server
        set_key('.env', 'CONFIDENCE_THRESHOLD', str(new_threshold))
        st.success(f"Threshold updated to {new_threshold}%. Bot will use this on the next hourly cycle.")
        st.warning("Note: The running engine container needs a moment to re-read the .env, or you can force restart it via terminal: `docker compose restart sigcrypt-engine`")

    st.markdown("---")

    # --- MANUAL FETCH CHART (Seperti sebelumnya) ---
    st.subheader("🔄 Fetch Latest Data")
    st.warning("⚠️ Manual fetch only updates this dashboard's chart. It does NOT interfere with the core Engine bot.")
    
    symbol = st.selectbox("Select Symbol", ['BTC/USDT', 'ETH/USDT', 'SOL/USDT', 'BNB/USDT', 'ZEC/USDT'])
    
    if st.button("🔄 Fetch Latest 100 Candles"):
        with st.spinner('Fetching data from Binance...'):
            try:
                exchange = ccxt.binance({
                    'enableRateLimit': True,
                    'options': {
                        'defaultType': 'future',
                        'aiohttp_trust_env': True
                    },
                    'urls': {
                        'api': {
                            'public': 'https://api3.binance.com/api/v3',
                            'fapiPublic': 'https://fapi.binance.com/fapi/v1',
                        }
                    }
                })
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
