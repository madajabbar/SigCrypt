Tentu, ini adalah dokumen teknis (Technical Design Document) lengkap untuk pengembangan lebih lanjut sistem Anda. Dokumen ini berfungsi sebagai *blueprint* agar logika, arsitektur, dan aturan bisnis terstruktur dengan rapi sebelum Anda menulis kode.

---

# 📄 DOKUMEN TEKNIS: CRYPTO SIGNAL GENERATOR SYSTEM (CSGS)

**Versi:** 1.1
**Tanggal:** 24 Mei 2024
**Status:** Development / Optimization Phase

---

## 1. Gambaran Umum (Overview)
Sistem ini dirancang untuk mengambil data pasar crypto secara real-time/historis, mengolahnya menggunakan indikator teknikal, memberikan sinyal beli/jual berdasarkan aturan logika tertentu, memberikan notifikasi kepada pengguna, serta mensimulasikan performa sinyal tersebut melalui mesin *backtesting*.

---

## 2. Arsitektur Sistem

Sistem dibagi menjadi 4 modul utama yang berjalan secara asinkron/berurutan:

1.  **Data Ingestion Module:** Bertanggung jawab mengambil data OHLCV & Orderbook dari Exchange via API (CCXT). Menangani *rate limit* dan *error handling* koneksi.
2.  **Analysis & Indicator Engine:** Menerima data mentah, menghitung indikator teknikal (TA), dan mendeteksi anomali (volume/volatilitas).
3.  **Signal & Risk Engine:** Mengevaluasi output dari Engine TA, menghitung skor *confidence*, menentukan arah sinyal (BUY/SELL/HOLD), serta menghitung parameter Risk Management (SL/TP).
4.  **Execution & Output Module:** Menyimpan log sinyal ke database, mengirim notifikasi (Telegram/API), dan memproses simulasi *backtesting*.

---

## 3. Spesifikasi Data

### 3.1. Sumber Data
*   **Primary Exchange:** Binance (via CCXT)
*   **Data Format:** Pandas DataFrame
*   **Timeframes:** Mendukung multi-timeframe (MTF). Utama: `1h`. Konfirmasi: `1d`.

### 3.2. Struktur DataFrame Standar (OHLCV)
| Kolom | Tipe Data | Deskripsi |
|-------|-----------|-----------|
| timestamp | datetime (UTC) | Waktu candle dibuka |
| open | float | Harga pembukaan |
| high | float | Harga tertinggi |
| low | float | Harga terendah |
| close | float | Harga penutupan |
| volume | float | Volume transaksi base asset |

---

## 4. Spesifikasi Indikator Teknikal

Modul analisis wajib menghitung dan menambahkan kolom berikut ke DataFrame:

| Nama Indikator | Parameter Standar | Kolom Output Dihasilkan |
|----------------|-------------------|-------------------------|
| RSI | period = 14 | `rsi` |
| MACD | fast=12, slow=26, signal=9 | `macd`, `macd_signal`, `macd_histogram` |
| Bollinger Bands | period=20, std=2 | `bb_upper`, `bb_middle`, `bb_lower` |
| EMA | periods = [9, 21, 50, 200] | `ema_9`, `ema_21`, `ema_50`, `ema_200` |
| Volume SMA | period = 20 | `volume_sma` |

---

## 5. Aturan Logika Sinyal (Signal Engine)

Sistem menggunakan metode **Scoring System**. Setiap kondisi yang terpenuhi memberikan skor. Skor total menentukan sinyal akhir dan persentase *confidence*.

### 5.1. Kondisi Pemberian Skor

| Kondisi (Trigger) | Aksi | Skor | Kategori |
|-------------------|------|------|----------|
| RSI memotong ke atas 30 | BUY | 2 | STRONG |
| RSI memotong ke bawah 70 | SELL | 2 | STRONG |
| MACD Bullish Crossover | BUY | 2 | STRONG |
| MACD Bearish Crossover | SELL | 2 | STRONG |
| EMA 9 memotong ke atas EMA 21 | BUY | 1 | MODERATE |
| EMA 9 memotong ke bawah EMA 21 | SELL | 1 | MODERATE |
| Harga menyentuh Lower BB | BUY | 1 | MODERATE |
| Harga menyentuh Upper BB | SELL | 1 | MODERATE |
| Vol > 2x Vol SMA & Harga naik >2% | BUY | 2 | STRONG |
| Vol > 2x Vol SMA & Harga turun >2% | SELL | 2 | STRONG |

### 5.2. Perhitungan Confidence
*   `Total_Buy_Score` = Jumlah skor dari kondisi BUY yang aktif.
*   `Total_Sell_Score` = Jumlah skor dari kondisi SELL yang aktif.
*   Jika `Total_Buy_Score > Total_Sell_Score` → Sinyal **BUY**, *Confidence* = `(Buy_Score / (Buy_Score + Sell_Score + 1)) * 100`
*   Minimum *confidence* agar sinyal diproses/notifikasi: **60%**

### 5.3. Filter Trend (Multi-Timeframe) - *Wajib Implementasi*
Untuk menghindari sinyal melawan tren besar:
*   **Aturan BUY:** Hanya valid jika harga `close` pada timeframe `1d` berada di atas `ema_50` (Uptrend harian).
*   **Aturan SELL:** Hanya valid jika harga `close` pada timeframe `1d` berada di bawah `ema_50` (Downtrend harian).

---

## 6. Spesifikasi Risk Management

Setiap sinyal yang dihasilkan **wajib** disertai dengan level Stop Loss (SL) dan Take Profit (TP).

*   **Stop Loss (SL):** Dihitung berdasarkan Indikator ATR (Average True Range, period=14) untuk menyesuaikan dengan volatilitas pasar, ATAU persentase tetap (misal: -3% untuk BTC, -5% untuk altcoin).
*   **Take Profit (TP):** Menggunakan rasio Risk:Reward minimum 1:2.
    *   Contoh: Jika SL berjarak 2% dari entry, maka TP harus berjarak minimal 4% dari entry.
*   **Trailing Stop (Opsional Lanjutan):** Jika harga sudah naik sejauh X%, SL dipindahkan ke harga entry (Break-even) atau mengikuti EMA 9.

---

## 7. Spesifikasi Backtesting Engine

Modul ini mensimulasikan eksekusi sinyal pada data historis.

### 7.1. Parameter Default
*   Modal Awal: $10,000
*   Fee Trading (Taker): 0.1% per transaksi (Beli & Jual)
*   Ukuran Posisi: 100% dari modal yang tersedia (bisa diubah menjadi persentase).

### 7.2. Alur Logika Backtest
1.  Iterasi dari candle ke-200 (warmup period untuk EMA 200) hingga akhir dataset.
2.  Cek apakah ada posisi terbuka:
    *   **Jika YA:** Cek apakah candle saat ini menyentuh level **TP** (berdasarkan harga *High*) atau **SL** (berdasarkan harga *Low*). Jika tersentuh, tutup posisi, catat PnL.
    *   **Jika TIDAK:** Panggil Signal Engine. Jika ada sinyal BUY dan *confidence* >= 60%, buka posisi (beli pada harga *Close*).
3.  Di akhir iterasi, hitung metrik performa.

### 7.3. Metrik Performa yang Wajib Dioutput
*   Net Profit / Loss ($ dan %)
*   Total Trades
*   Win Rate (%)
*   Max Drawdown (Penurunan modal maksimal dari puncak)
*   Profit Factor (Gross Profit / Gross Loss)
*   Average Win / Average Loss Ratio

---

## 8. Spesifikasi Output & Notifikasi

Sinyal dikirim ke pengguna melalui Telegram Bot API dengan format pesan standar:

**Template Pesan:**
```text
🟢 BUY SIGNAL | 🔴 SELL SIGNAL
━━━━━━━━━━━━━━━━━━━━
📌 Pair: {Symbol}
💰 Entry: ${Price}
🛡 SL: ${Stop_Loss_Price} (-{SL_pct}%)
🎯 TP: ${Take_Profit_Price} (+{TP_pct}%)
📊 Confidence: {Confidence_score}%
⏰ Time: {Timestamp (UTC)}

📝 Reasons:
• {Reason_1}
• {Reason_2}

⚠️ Bukan financial advice. DYOR!
```