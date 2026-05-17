# 🚀 SigCrypt (Crypto Futures Signal Engine V3)
**Dokumentasi Resmi Proyek SigCrypt**

SigCrypt adalah *bot* penasihat teknikal (Signal Generator) yang telah berevolusi menjadi sistem **Paper Trading & Backtesting Engine** otomatis penuh untuk pasar Cryptocurrency Perpetual Futures (USDT-M).

Dibangun dengan fokus ekstrem pada perlindungan modal (Capital Preservation), sistem ini menggunakan arsitektur modular yang memadukan analisa multi-timeframe, manajemen risiko ketat berbasis volatilitas (ATR), dan pelacakan portofolio virtual (SQLite) secara *real-time*.

---

## 1. Arsitektur Modul & Hierarki Proyek

Proyek ini telah direstrukturisasi agar rapi, *scalable*, dan mudah dipelihara. Seluruh modul utama berada di dalam folder `src/`.

*   **`app.py` (Core Engine)**: File *entry point* di akar direktori untuk menjalankan seluruh sistem (Mode 1: Live Paper Trading Daemon, Mode 2: Backtest).
*   **`src/config.py`**: Konfigurasi kunci (*Timeframe*, *Symbols*) & integrasi `.env`.
*   **`src/core/` (Logika Utama)**:
    *   `data_fetcher.py`: Penarikan data OHLCV via CCXT.
    *   `indicators.py`: Kalkulator *Technical Analysis* (RSI, MACD, BB, ATR, EMA).
    *   `signal_engine.py`: "Otak" sistem yang mencari setup dan meracik keputusan SL/TP.
    *   `backtest.py`: Mesin simulasi historis.
*   **`src/services/` (Layanan Eksternal & State)**:
    *   `database.py`: Pembungkus SQLite yang mengelola *State* (Saldo, Sinyal, Trades).
    *   `notifier.py`: Modul integrasi pesan Telegram.
*   **`data/` (Penyimpanan Data)**:
    *   Tempat bernaungnya file `trading_log.db` dan `backtest_log.db`.

---

## 2. Logika Sinyal & "Anti-Rugi" Filter (V3)

Berbeda dengan indikator dasar (Golden Cross biasa), SigCrypt mengadopsi 2 lapis filter tambahan sebelum masuk ke *setup* utama.

### 2.1. Filter Berlapis (Pre-Filters)
Sinyal HANYA akan diproses jika melewati gerbang pelindung ini:
*   **Volume Validation:** Volume *candle* terakhir wajib berada di atas *Volume SMA 20*. Pasar yang tidak *liquid* atau statis akan ditolak.
*   **Sideways/No Trade Zone:** Jika jarak EMA 9 dan EMA 21 terlalu sempit (< 0.1%), bot tidak akan mengeksekusi *trade* karena berisiko tinggi kena gocekan (whipsaw).
*   **Multi-Timeframe Trend Check:** Arah tren *1-Hour* (EMA 50) **wajib selaras** dengan arah tren *1-Day* (EMA 50 harian).

### 2.2. Dua Model Setup Utama
Jika filter di atas terpenuhi, SigCrypt memonitor 2 skenario probabilitas tinggi:
1.  **Setup A (Trend Continuation):** Mencari momen *pullback* (koreksi harga sesaat) saat tren besar sedang kuat. Parameter:
    *   **LONG:** Harga di atas EMA 50 + RSI Turun ke (35-45) + MACD Histogram *bearish* yang mulai memendek (momentum pelemahan).
    *   **SHORT:** Kebalikannya.
2.  **Setup B (Extreme Reversal):** Mencari titik balik di pucuk (mean-reversion) saat harga sudah bergerak terlampau jauh.
    *   **LONG:** Harga menjebol *Lower Bollinger Band* + RSI < 25 (Sangat Oversold).
    *   **SHORT:** Harga menjebol *Upper Bollinger Band* + RSI > 75 (Sangat Overbought).

---

## 3. Sistem Manajemen Risiko (Risk Management)

Ini adalah jantung utama dari SigCrypt. Keamanan saldo (*Virtual Balance*) dijaga dengan protokol ketat:

*   **Dynamic Stop Loss (ATR):** Jarak batas kerugian tidak menggunakan persentase statis. SL diposisikan sejauh `1.5 x nilai ATR`. Semakin bergejolak pasar, SL semakin lebar (dan posisi semakin mengecil otomatis).
*   **Take Profit Ratio:** Wajib mencapai RR 1:1.5 dari jarak SL. Jika tidak tercapai, *trade* tidak akan memuaskan syarat eksekusi matematis bot.
*   **Position Sizing Presisi 1%:** Ukuran/Jumlah koin yang dibeli dikalkulasi sedemikian rupa agar **jika Stop Loss tersentuh, saldo total (balance) HANYA berkurang tepat 1%**.
*   **Futures Simulation:** Bot mengadopsi gaya *Isolated Leverage 5x*. Terdapat simulasi biaya **Maker/Taker Fee (0.04% x 2)** dan **Slippage (0.05%)** yang langsung memotong keuntungan PnL di dalam tabel database.

---

## 4. Mode Operasi Aplikasi

Aplikasi berjalan dalam 2 pilar utama melalui terminal `app.py`:

### Mode 1: Live Paper Trading Daemon
Bot tidak akan pernah berhenti berjalan (Loop Forever).
1.  Mengambil data OHLCV terbaru.
2.  Memeriksa database (`data/trading_log.db`). Apakah ada posisi yang sedang **OPEN**?
    *   Jika **Ya**: Bot akan melihat nilai `High` dan `Low` dari jam terakhir. Apakah menyentuh TP atau SL? Jika kena, status diubah menjadi `CLOSED`, Balance diupdate, PnL dicatat, dan notif Telegram "TRADE CLOSED" dikirim.
    *   Jika **Tidak**: Mesin mencari *Setup* baru. Jika dapat sinyal, bot akan pura-pura mengeksekusi pembelian dengan biaya *Fee* realistis, mengubah DB ke status `OPEN`, dan mengirim notif Telegram.
3.  Tidur otomatis hingga perpindahan jam berikutnya (contoh: 15:00:05).

### Mode 2: Backtest Database Logger
Bot mengeksekusi simulasi waktu lampau dengan saldo awal mandiri.
1.  Tabel `backtest_trades` di dalam file `data/backtest_log.db` akan dihapus (Wipe Clean) untuk memulai sesi segar.
2.  Mesin menjalankan 1000 iterasi *candle* ke masa lalu untuk setiap pasangan koin.
3.  Setiap trade (Menang maupun Kalah) diunggah baris per baris ke SQLite, lengkap dengan `entry_price`, `exit_time`, `pnl_pct`, hingga nilai `running_balance`.
4.  Terminal akan mencetak papan skor elegan berisi metrik profesional (Max Drawdown, Win Rate, Profit Factor, Expectancy, Max Consecutive Losses).

---

## 5. Prasyarat Sistem & Setup (Requirements)

Pastikan lingkungan kerja (Environment) telah dikonfigurasi dengan baik.

### Kebutuhan Modul (`requirements.txt`)
*   `ccxt`: Komunikasi Data Exchange.
*   `pandas` & `numpy`: Manipulasi tabel OHLCV.
*   `python-dotenv`: Manajemen kunci rahasia.
*   `requests`: Eksekusi HTTP untuk Telegram.
*   `ta` (Opsional/Legacy)
*   `schedule` (Legacy, kini digantikan modul standard `time`)

### Konfigurasi Variabel (`.env`)
Buat file bernama `.env` (tanpa ekstensi) di akar folder:
```env
TELEGRAM_BOT_TOKEN="123456789:ABCDefghIJKlmnOPQRstuVWXYZ"
TELEGRAM_CHAT_ID="987654321"

# API Binance opsional (Saat ini CCXT dapat menarik data OHLCV publik tanpa key).
BINANCE_API_KEY=""
BINANCE_SECRET_KEY=""
```

### Cara Memulai
1.  Aktifkan lingkungan virtual: `.\env\Scripts\activate` (Windows)
2.  Jalankan aplikasi: `python app.py`
3.  Pilih `1` (Live Virtual) atau `2` (Backtest Evaluasi).
4.  Buka aplikasi *DB Browser for SQLite* dan seret file `data/trading_log.db` atau `data/backtest_log.db` untuk membaca riwayat pergerakan uang bot.
