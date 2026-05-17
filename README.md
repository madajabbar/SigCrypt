# 🚀 SigCrypt - Crypto Futures Signal Engine V3

SigCrypt adalah bot *Signal Generator* otomatis untuk pasar Cryptocurrency Perpetual Futures (USDT-M) yang mengedepankan **Capital Preservation** (Perlindungan Modal) dan Manajemen Risiko Ekstrem. Dibangun menggunakan Python, SigCrypt saat ini dirancang sebagai mesin *Virtual/Paper Trading* murni dan *Backtesting Logger* berbasis SQLite.

## ✨ Fitur Utama

- **Double-Layer Trend Filter:** Sinyal disaring dengan EMA-50 Multi-Timeframe (1H & 1D) dan validasi volume (*Volume SMA 20*). Menghindari pasar yang sedang *sideways*.
- **Dynamic Risk Management:** Kalkulasi ukuran posisi (*position sizing*) otomatis sebesar maksimal 1% risiko dari sisa saldo virtual. Stop Loss diposisikan secara dinamis menggunakan nilai **1.5x ATR (Average True Range)**.
- **Two-Way Paper Trading:** Mendukung sinyal *LONG* dan *SHORT* dengan simulasi interaktif *Take Profit* (RR Minimum 1:1.5) maupun Stop Loss. Mengalkulasi biaya Taker Fee Binance (0.04% x 2) dan *Slippage* secara instan.
- **SQLite State Management:** Tidak ada memori yang hilang. Saldo virtual, rekam jejak historis sinyal, dan histori PnL (Profit & Loss) disimpan rapi ke dalam *database*.
- **Docker-Ready:** Tersedia konfigurasi *Dockerfile* dan *Docker Compose* untuk *deployment* server 24/7 yang anti-crash.
- **Telegram Alert:** Integrasi Bot Telegram untuk pelaporan aktivitas *Entry* dan *Exit* ke *smartphone* Anda.

---

## 📂 Struktur Proyek

```text
SigCrypt/
│
├── app.py                  # Entry point (Live Daemon / Backtester)
├── docker-compose.yml      # Konfigurasi Docker Server
├── Dockerfile              # Cetak biru Linux Environment
├── requirements.txt        # Dependensi Python
├── .env                    # Variabel Rahasia (Token & Mode)
│
├── data/                   # [Auto-Generated] Tempat penyimpanan SQLite
│   ├── trading_log.db      # Database riwayat Paper Trading
│   └── backtest_log.db     # Database hasil evaluasi Backtest
│
└── src/                    # Source Code Inti
    ├── config.py           # Parameter statis (Pairs, Timeframe)
    ├── core/
    │   ├── backtest.py     # Mesin simulasi historis (Time-travel)
    │   ├── data_fetcher.py # Integrasi API Binance (via CCXT)
    │   ├── indicators.py   # Modul Kalkulator Teknikal (RSI, MACD, dll)
    │   └── signal_engine.py# Otak pencari setup probabilitas tinggi
    │
    └── services/
        ├── database.py     # Pembungkus manajemen koneksi SQLite
        └── notifier.py     # Integrasi pesan HTTP Telegram
```

---

## ⚙️ Persyaratan & Instalasi (Lokal)

Pastikan Anda memiliki **Python 3.11+** terinstall di mesin Anda.

1. **Clone repositori:**
   ```bash
   git clone https://github.com/USERNAME/SigCrypt.git
   cd SigCrypt
   ```

2. **Buat dan aktifkan Virtual Environment:**
   ```bash
   python -m venv env
   # Di Windows:
   .\env\Scripts\activate
   # Di Linux/Mac:
   source env/bin/activate
   ```

3. **Install Dependensi:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Setup Environment Variables:**
   Buat file bernama `.env` di direktori *root* dan isi sesuai template (lihat `.env.example` jika tersedia):
   ```env
   # Mode Operasi (1: Paper Trading Daemon | 2: Backtest History)
   MODE=1
   
   # Setup Bot Telegram
   TELEGRAM_TOKEN="123456789:ABCDefghIJKlmnOPQRstuVWXYZ"
   TELEGRAM_CHAT_ID="987654321"
   ```

---

## 🚀 Menjalankan Aplikasi

Aplikasi berjalan sepenuhnya tanpa interaksi terminal (sehingga ramah Docker). Mode yang dijalankan bergantung pada nilai variabel `MODE` di dalam file `.env`.

**Jika `MODE=1` (Live Paper Trading):**
```bash
python app.py
```
Aplikasi akan terus berjalan (*daemon*) mengecek data OHLCV Binance secara otomatis setiap perpindahan jam dan memberikan *alert* di Telegram.

**Jika `MODE=2` (Backtester):**
Ubah file `.env` menjadi `MODE=2`, lalu jalankan kembali. Sistem akan memuat ulang simulasi waktu lampau dari 1000 *candle* ke belakang dan mencetak papan skor performa (Win Rate, Profit Factor, dll) ke layar terminal Anda, sembari mencatat rekaman *trade* ke dalam tabel `backtest_trades`.

---

## 🐳 Deployment (Docker / VPS Server)

Aplikasi ini disiapkan *plug-and-play* untuk server Linux (contoh: Debian Trixie) menggunakan Docker.

1.  Pastikan Docker dan Docker-Compose sudah terinstall di server Anda.
2.  Atur `.env` (pastikan `MODE=1` untuk pemantauan *real-time*).
3.  Jalankan perintah ini di dalam folder proyek:
    ```bash
    docker-compose up -d --build
    ```
4.  Data saldo dan riwayat Anda akan sepenuhnya abadi di dalam folder `./data/` walaupun sistem di *re-deploy* puluhan kali.
5.  Untuk mengecek *log terminal*:
    ```bash
    docker-compose logs -f
    ```

---

### ⚠️ Disclaimer
**Proyek SigCrypt 100% bertujuan untuk Edukasi dan Riset (Paper Trading Virtual).** Kode ini **TIDAK** didesain untuk secara langsung mengakses dompet (*wallet*) dan API rahasia *exchange* nyata tanpa *refactoring* tingkat lanjut pada modul keamanan dan konektivitas (WebSocket). *Do Your Own Research* (DYOR). Segala bentuk kerugian finansial di luar simulasi menjadi tanggung jawab pribadi pengguna.
