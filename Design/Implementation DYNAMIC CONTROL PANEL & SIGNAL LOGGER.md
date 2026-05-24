# 📄 DOKUMEN TEKNIS V4: DYNAMIC CONTROL PANEL & SIGNAL LOGGER

**Fokus:** Interaktivitas Dashboard, Dynamic Parameter Tuning, dan Decision Transparency (Log Alasan Bot).
**Prasyarat:** Streamlit, SQLite, konfigurasi Docker Host Network.

---

## 1. Konsep Arsitektur Baru: "The Glass Box"

Sebelumnya, bot adalah *Black Box* (dia diam kerja, cuma teriak kalau ada sinyal). Sekarang, kita ubah jadi *Glass Box*. Setiap jam, bot akan menulis "diary" kenapa dia tidak masuk pasar, dan Dashboard bisa mengatur seberapa agresif bot tersebut berburu.

### Tambahahan Tabel Database: `bot_logs`
Kita butuh tabel khusus untuk mencatat alasan bot menolak/menerima setup, tanpa mencemari tabel `signals` atau `trades`.

| Kolom | Tipe Data | Deskripsi |
|-------|-----------|-----------|
| id | INTEGER (PK) | Auto increment |
| timestamp | DATETIME | Waktu pengecekan |
| symbol | TEXT | Pair yang dicek |
| decision | TEXT | **SIGNAL_FOUND** / **NO_SIGNAL** |
| reason | TEXT | Penjelasan detail (misal: "RSI 42, but below EMA 50") |
| confidence | REAL | Skor saat itu (0 jika NO_SIGNAL) |

---

## 2. Spesifikasi Perubahan Modul

### 2.1. Dynamic Config via `.env` (Opsi 1)
Kita akan memindahkan `CONFIDENCE_THRESHOLD` dari hardcode di Python ke dalam file `.env`, agar bisa dibaca oleh Streamlit dan Engine secara dinamis.

**Tambahkan di file `.env`:**
```env
# Minimum confidence to execute trade (Adjustable via Dashboard)
CONFIDENCE_THRESHOLD=40
```

### 2.2. Perluasan Cakupan Buruan (Opsi 2)
Perbesar list simbol di konfigurasi agar bot lebih sibuk menganalisis.

**Tambahkan di file `.env`:**
```env
SYMBOLS=BTC/USDT,ETH/USDT,SOL/USDT,BNB/USDT,ZEC/USDT,AVAX/USDT,INJ/USDT,LINK/USDT,SUI/USDT,FET/USDT
```

---

## 3. Implementasi Kode

### 3.1. Update `src/services/database.py`
Tambahkan fungsi untuk membuat tabel dan memasukkan log ke `bot_logs`.

```python
import sqlite3

class DatabaseManager:
    # ... (Fungsi sebelumnya tetap) ...

    def log_bot_decision(self, timestamp, symbol, decision, reason, confidence):
        """Catat alasan keputusan bot setiap jam"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Buat tabel jika belum ada
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS bot_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME,
                symbol TEXT,
                decision TEXT,
                reason TEXT,
                confidence REAL
            )
        """)
        
        cursor.execute("""
            INSERT INTO bot_logs (timestamp, symbol, decision, reason, confidence)
            VALUES (?, ?, ?, ?, ?)
        """, (timestamp, symbol, decision, reason, confidence))
        
        conn.commit()
        conn.close()
```

### 3.2. Update `app.py` (Core Engine)
Modifikasi loop utama agar membaca threshold dari env, dan mencetak alasan ke DB.

```python
import os
from src.services.database import DatabaseManager

# Baca threshold dari env, default 40 jika kosong
CONFIDENCE_THRESHOLD = int(os.environ.get('CONFIDENCE_THRESHOLD', 40))
db = DatabaseManager()

def run_analysis(symbol):
    # ... (Ambil data OHLCV & hitung indikator) ...
    
    signal = engine.generate_combined_signal(df, symbol)
    current_time = datetime.now().isoformat()
    
    if signal:
        if signal['confidence'] >= CONFIDENCE_THRESHOLD:
            # CATAT KE LOG: SINYAL DITERIMA
            db.log_bot_decision(
                current_time, symbol, 'SIGNAL_FOUND', 
                f"Executed {signal['type']}. Reasons: {signal['signals']}", 
                signal['confidence']
            )
            # Eksekusi trade...
        else:
            # CATAT KE LOG: SINYAL TERLALU LEMAH
            db.log_bot_decision(
                current_time, symbol, 'NO_SIGNAL', 
                f"Signal found but confidence {signal['confidence']}% < Threshold {CONFIDENCE_THRESHOLD}%", 
                signal['confidence']
            )
    else:
        # CATAT KE LOG: TIDAK ADA SETUP SAMA SEKALI
        # (Opsional: Anda bisa print spesifik kenapa, misal "RSI not oversold" dll di sini)
        db.log_bot_decision(
            current_time, symbol, 'NO_SIGNAL', 
            'No valid setup match (Filtered by Trend/Volume/Zone)', 
            0
        )
```

### 3.3. Update `dashboard.py` (Control Panel & Logger)
Ini adalah penambahan besar pada Streamlit. Kita akan menambahkan halaman baru dan fitur kontrol.

```python
import streamlit as st
import pandas as pd
import sqlite3
import os
from dotenv import load_dotenv, set_key

# Load environment
load_dotenv()

DB_PATH = 'data/trading_log.db'
st.set_page_config(page_title="SigCrypt Dashboard", layout="wide")

# --- SIDEBAR ---
st.sidebar.title("🤖 SigCrypt V4")
menu = st.sidebar.radio("Navigation", ["📊 Portfolio", "📜 Trade History", "🧠 Bot Mind & Logs", "⚙️ System Control"])

# ... (Halaman Portfolio dan History tetap sama) ...

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
        conn = sqlite3.connect(DB_PATH)
        df = pd.read_sql_query(q, conn)
        conn.close()
        return df

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
    # ... (kode fetch data chart sebelumnya) ...
```

---

## 4. Cara Kerja Sistem Ini

1.  **Jam 15:00:** Engine Bot bangun, membaca `CONFIDENCE_THRESHOLD` dari file `.env` (misal: 40).
2.  Engine mengecek `INJ/USDT`. Dia menemukan EMA cross, RSI di 42. Skornya cuma 35%.
3.  Karena 35% < 40%, dia **TIDAK** trade.
4.  Engine menulis ke database `bot_logs`: *"INJ/USDT - NO_SIGNAL - Signal found but confidence 35% < Threshold 40%"*.
5.  **Anda buka Dashboard di browser.** Anda melihat log kuning tersebut. Anda berpikir, *"Hmm, sayang banget INJ tadi, kalau threshold 30% pasti masuk."*
6.  Anda geser slider di halaman **⚙️ System Control** ke angka 30%, lalu klik **Save**.
7.  File `.env` di server otomatis berubah.
8.  **Jam 16:00:** Bot bangun lagi, sekarang membaca threshold 30%. Jika setup INJ tadi masih bertahan, dia akan masuk!