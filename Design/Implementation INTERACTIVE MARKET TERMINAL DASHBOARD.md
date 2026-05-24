# 📄 DOKUMEN TEKNIS V6: INTERACTIVE MARKET TERMINAL DASHBOARD

**Fokus:** Visualisasi Mass-Market Scanning, Interaktivitas Tabel, dan Detail Chart Pop-out.
**Library Baru:** `streamlit-aggrid` (Tabel premium), `plotly` (Grafik interaktif).

---

## 1. Arsitektur UI/UX Baru

Dashboard akan dibagi menjadi 4 halaman utama di Sidebar:

1.  **🚀 Market Screener:** Tabel dinamis menampilkan ratusan koin, peringkat berdasarkan indikator (RSI, Volatilitas), dan diberi warna merah/hijau. **Bisa diklik** untuk melihat grafik.
2.  **📊 Portfolio & Equity:** Ringkasan saldo dan kurva pertumbuhan (seperti sebelumnya).
3.  **🧠 Bot Mind & Logs:** Diaries bot (seperti V4).
4.  **⚙️ System Control:** Pengaturan Threshold dan manual fetch.

---

## 2. Implementasi Kode

### Langkah 1: Install Library Baru

Tambahkan ini di file `requirements.txt` Anda (dan di `Dockerfile.dashboard`):
```text
streamlit-aggrid
plotly
```

Jangan lupa rebuild docker nanti: `docker compose build sigcrypt-dashboard`

### Langkah 2: Tambah Fungsi Screener di `src/core/data_fetcher.py`

Kita butuh fungsi yang mengambil data ringkas (Ticker) untuk 200+ koin sekaligus, agar tabel screener cepat dimuat tanpa harus download 500 candle per koin.

```python
    def get_market_snapshot(self):
        """Mengambil data RSI dan perubahan harga 24h untuk seluruh market futures"""
        symbols = self.get_active_futures_symbols()
        tickers = self.exchange.fetch_tickers(symbols)
        
        snapshot = []
        # Ambil data 24jam terakhir untuk kalkulasi RSI cepat (tidak perlu 500 candle)
        for symbol in symbols[0:100]: # Batas 100 dulu agar tidak kena rate limit Binance
            try:
                # Cukup ambil 24 candle 1H untuk kalkulasi RSI cepat
                df = self.get_ohlcv(symbol, '1h', limit=24)
                if df.empty: continue
                
                delta = df['close'].diff()
                gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
                loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
                rs = gain / loss
                df['rsi'] = 100 - (100 / (1 + rs))
                
                last_rsi = df['rsi'].iloc[-1]
                price_change_24h = ((df['close'].iloc[-1] - df['close'].iloc[0]) / df['close'].iloc[0]) * 100
                
                snapshot.append({
                    'Symbol': symbol,
                    'Price': df['close'].iloc[-1],
                    '24h Change (%)': round(price_change_24h, 2),
                    'RSI (1H)': round(last_rsi, 2),
                    'Volume': tickers[symbol].get('quoteVolume', 0)
                })
            except:
                continue
                
        return pd.DataFrame(snapshot)
```

### Langkah 3: Rombak Total `dashboard.py`

Ini adalah kode lengkap untuk halaman **Market Screener** yang sangat interaktif.

```python
import streamlit as st
import pandas as pd
import sqlite3
import plotly.graph_objects as go
from st_aggrid import AgGrid, GridOptionsBuilder
import os
import sys

# Tambahkan path agar bisa import modul src
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from src.core.data_fetcher import CryptoDataFetcher

DB_PATH = 'data/trading_log.db'
st.set_page_config(page_title="SigCrypt Terminal", layout="wide")

# Caching data selama 5 menit agar tidak spam Binance API
@st.cache_data(ttl=300)
def load_screener_data():
    fetcher = CryptoDataFetcher()
    return fetcher.get_market_snapshot()

@st.cache_data(ttl=10)
def load_chart_data(symbol):
    fetcher = CryptoDataFetcher()
    df = fetcher.get_ohlcv(symbol, '1h', limit=100)
    return df

# --- SIDEBAR ---
st.sidebar.title("🤖 SigCrypt Terminal V6")
menu = st.sidebar.radio("Navigation", ["🚀 Market Screener", "📊 Portfolio", "🧠 Bot Logs", "⚙️ Control"])

# ==========================================
# HALAMAN 1: MARKET SCREENER (BARU!)
# ==========================================
if menu == "🚀 Market Screener":
    st.header("🚀 Binance Futures Live Market Screener")
    st.write("Scanning top volume pairs. Click on a row to view the interactive chart.")
    
    with st.spinner("Fetching data from Binance... (This takes a few seconds)"):
        df_screener = load_screener_data()
    
    if not df_screener.empty:
        # Konfigurasi Tabel Ag-Grid (Super Interaktif)
        gb = GridOptionsBuilder.from_dataframe(df_screener)
        gb.configure_pagination(paginationAutoPageSize=True) # Pagination otomatis
        gb.configure_side_bar() # Sidebar filter bawaan AgGrid
        gb.configure_selection(selection_mode='single', use_checkbox=True) # Bisa diklik/dipilih
        
        # Warnai RSI secara otomatis
        gb.configure_column("RSI (1H)", type=["numericColumn","customNumericFormat"], 
                            cellStyle={"condition": 
                                       {"condition": "value > 70", "style": {"backgroundColor": "red", "color": "white"}},
                                       {"condition": "value < 30", "style": {"backgroundColor": "green", "color": "white"}}
                                      })
        # Warnai 24h Change
        gb.configure_column("24h Change (%)", type=["numericColumn"],
                            cellStyle={"condition":
                                       {"condition": "value > 0", "style": {"color": "green"}},
                                       {"condition": "value < 0", "style": {"color": "red"}}
                                      })

        gridOptions = gb.build()
        
        # Render Tabel
        grid_response = AgGrid(
            df_screener,
            gridOptions=gridOptions,
            height=500, 
            width='100%',
            data_return_mode='AS_INPUT',
            update_mode='SELECTION_CHANGED'
        )
        
        # Tangkap baris yang diklik oleh user
        selected = grid_response.get('selected_rows')
        
        if selected is not None and len(selected) > 0:
            selected_symbol = selected['Symbol'].iloc[0]
            st.divider()
            st.subheader(f"📈 Interactive Chart: {selected_symbol}")
            
            # Load data chart
            df_chart = load_chart_data(selected_symbol)
            
            if not df_chart.empty:
                # Buat Candlestick Chart menggunakan Plotly
                fig = go.Figure(data=[go.Candlestick(
                    x=df_chart['timestamp'],
                    open=df_chart['open'],
                    high=df_chart['high'],
                    low=df_chart['low'],
                    close=df_chart['close']
                )])
                
                fig.update_layout(
                    xaxis_rangeslider_visible=False,
                    template='plotly_dark', # Tema gelap ala trading
                    height=500
                )
                
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.warning("Could not load chart data.")
    else:
        st.error("Failed to fetch screener data. Check API connection.")

# ==========================================
# HALAMAN LAINNYA (Sama seperti V4/V5)
# ==========================================
elif menu == "📊 Portfolio":
    st.header("📊 Portfolio (Coming Soon with V5 Logic)")
    # ... (Kode portfolio Anda)

elif menu == "🧠 Bot Logs":
    st.header("🧠 Bot Decision Logs")
    # ... (Kode log Anda)

elif menu == "⚙️ Control":
    st.header("⚙️ System Control")
    # ... (Kode threshold slider Anda, ditambah:
    # Manual trigger untuk menjalankan fungsi Scanner sekali)
    if st.button("🚀 Force Run Scanner Now (Bot Engine)"):
        st.warning("This will send a signal to the Engine container. Ensure it's running.")
        # Di sini nanti bisa ditambahkan mekanisme via DB flag atau API sederhana
        # Untuk sekarang, kita biarkan bot berjalan otomatis tiap jam.
```

---

## 3. Apa yang Baru di Dashboard Ini?

1.  **Tabel Ag-Grid:** Ini bukan tabel pandas biasa. Ini tabel profesional. Anda bisa mencari (search), memfilter kolom (misal: cari RSI < 30), meng-sort volume terbesar, dan mengerjakan semuanya langsung di UI.
2.  **Warna Otomatis:** Koin yang RSI-nya sudah overbought (>70) otomatis cel merah di tabel. Yang oversold (<30) sel hijau. Perubahan harga hijau/merah.
3.  **Click-to-Chart:** Anda melihat ZEC sedang RSI 25 di tabel? Klik saja barisnya. Otomatis di bawahnya akan muncul Candlestick chart interaktif (bisa di-zoom, di-hover) menggunakan Plotly dengan tema gelap (dark mode) khas trading.
4.  **Auto-Refresh:** Data screener di-cache 5 menit (300 detik). Setiap 5 menit, UI otomatis update tanpa perlu tekan refresh browser.