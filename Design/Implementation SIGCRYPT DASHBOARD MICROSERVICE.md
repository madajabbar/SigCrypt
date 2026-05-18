# 📄 DOKUMEN TEKNIS V4: SIGCRYPT DASHBOARD MICROSERVICE

## 1. Arsitektur Baru (Docker Compose)

Kita akan mengubah `docker-compose.yml` Anda agar menjalankan 2 container:
1.  `sigcrypt-engine`: Berjalan di background, menghitung sinyal, menulis ke DB.
2.  `sigcrypt-dashboard`: Berjalan sebagai web-server (Streamlit), membaca DB, dan menerima input manual.

**Aturan Kritis:** SQLite tidak handle concurrent write dengan baik. Oleh karena itu, **Engine** tetap menjadi *writer* utama, dan **Dashboard** hanya bertindak sebagai *reader*.

---

## 2. Spesifikasi Dashboard (UI/UX)

Dashboard dibagi menjadi 3 halaman utama menggunakan menu sidebar Streamlit.

### Halaman 1: 📊 Live Portfolio & Performance
*   **Metrik Utama:** Virtual Balance, Total PnL, Win Rate, Active Positions.
*   **Equity Curve:** Grafik garis (Plotly) yang diambil dari kolom `running_balance` di tabel trades, menunjukkan pertumbuhan saldo dari waktu ke waktu.
*   **Active Trades Table:** Menampilkan posisi yang sedang `OPEN` (Symbol, Side, Entry, SL, TP).

### Halaman 2: 📜 History & Logs (The "Autopsy" Room)
*   **Trade History Table:** Tabel interaktif (Ag-Grid atau Dataframe) menampilkan semua trade yang sudah `CLOSED`. Bisa di-sort berdasarkan PnL terbesar/terkecil.
*   **Signal Logs Table:** Menampilkan semua sinyal mentah yang pernah dimuntahkan mesin (termasuk yang tidak dieksekusi karena sudah ada posisi).
*   **Detail View:** Saat baris trade diklik, tampilkan detail alasan masuk (`reasons` JSON).

### Halaman 3: ⚙️ System Control (Fetch Data Manual)
*   **System Info:** Uptime bot, Mode (Live/Backtest), Waktu server.
*   **Tombol "🔄 Force Fetch Latest Data":** Tombol ini **TIDAK** memaksa Engine berjalan (karena bisa bikin konflik DB). Fungsinya adalah memaksa Dashboard mengambil data OHLCV terbaru langsung dari Binance API (via CCXT) dan menampilkan chart pergerakan harga terkini di dashboard, terpisah dari proses Engine.

---

## 3. Struktur File Baru

Buat file baru di akar direktori Anda:

```text
SigCrypt/
├── dashboard.py             # Kode Streamlit baru
├── Dockerfile.dashboard     # Dockerfile khusus untuk Streamlit
├── docker-compose.yml       # Diupdate untuk 2 services
├── app.py                   # Engine utama (tidak diubah)
└── src/...
```

---

## 4. Implementasi Kode

### 4.1. `dashboard.py` (Buat File Baru)

```python
import streamlit as st
import pandas as pd
import sqlite3
import plotly.express as px
import ccxt
from datetime import datetime

# --- KONFIGURASI ---
DB_PATH = 'data/trading_log.db'
st.set_page_config(page_title="SigCrypt Dashboard", layout="wide")

# --- CACHE DATA UNTUK PERFORMANCE ---
@st.cache_data(ttl=10) # Cache selama 10 detik, agar tidak membom DB
def load_data(query):
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql_query(query, conn)
    conn.close()
    return df

# --- SIDEBAR ---
st.sidebar.title("🤖 SigCrypt V3")
menu = st.sidebar.radio("Navigation", ["📊 Portfolio", "📜 History & Logs", "⚙️ System Control"])

# --- HALAMAN 1: PORTFOLIO ---
if menu == "📊 Portfolio":
    st.header("📊 Live Paper Trading Portfolio")
    
    # Ambil data trades
    df_trades = load_data("SELECT * FROM trades ORDER BY close_time DESC")
    df_open = df_trades[df_trades['status'] == 'OPEN']
    df_closed = df_trades[df_trades['status'] == 'CLOSED']
    
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
```

### 4.2. `Dockerfile.dashboard` (Buat File Baru)

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install streamlit & plotly khusus untuk dashboard
RUN pip install --no-cache-dir streamlit plotly

COPY . .

EXPOSE 8501

# Jalankan streamlit
ENTRYPOINT ["streamlit", "run", "dashboard.py", "--server.port=8501", "--server.address=0.0.0.0"]
```

### 4.3. Update `docker-compose.yml` (Ganti Seluruh File)

```yaml
version: '3.8'

services:
  # 1. Core Engine Bot
  sigcrypt-engine:
    build: 
      context: .
      dockerfile: Dockerfile
    container_name: sigcrypt_engine
    restart: unless-stopped
    env_file:
      - .env
    volumes:
      - ./data:/app/data

  # 2. Dashboard Microservice
  sigcrypt-dashboard:
    build:
      context: .
      dockerfile: Dockerfile.dashboard
    container_name: sigcrypt_dashboard
    restart: unless-stopped
    ports:
      - "8501:8501" # EXPOSE PORT INI AGAR BISA DIAKSES BROWSER
    volumes:
      - ./data:/app/data # BAGI FOLDER YANG SAMA DENGAN ENGINE
    environment:
      - MODE=1 # Dashboard tidak butuh mode, tapi wajib punya env dasar
```

---

## 5. Cara Deploy Update Ini di Server

1.  Buat file `dashboard.py` dan `Dockerfile.dashboard` di lokal, lalu push ke GitHub.
2.  Di server Debian Anda, jalankan:
    ```bash
    cd SigCrypt
    git pull origin main
    docker-compose down
    docker-compose up -d --build
    ```

3.  Cek status:
    ```bash
    docker-compose ps
    ```
    Anda harusnya melihat 2 container berstatus `Up`: `sigcrypt_engine` dan `sigcrypt_dashboard`.

4.  **Akses Dashboard:** Buka browser di komputer pribadi Anda, lalu ketik:
    `http://IP_ADDRESS_SERVER_ANDA:8501`

*(Catatan: Pastikan firewall server Anda (seperti UFW) mengizinkan port 8501: `sudo ufw allow 8501`)*