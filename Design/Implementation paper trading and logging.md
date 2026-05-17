# 📄 DOKUMEN TEKNIS V3: PAPER TRADING & LOGGING ENGINE
**Fokus:** Real-time simulation, State Management, Data Persistence.
**Database:** SQLite (Ringan, tanpa perlu install server terpisah, cocok untuk tahap ini).

---

## 1. Gambaran Umum Arsitektur Baru

Sistem kini harus mengingat "keadaan" (State). Bot harus tahu apakah dia sedang memegang posisi atau tidak.

**Alur Kerja Utama (Main Loop - Berjalan setiap jam):**
1.  **Cek Posisi Terbuka:** Cek database, apakah ada status `OPEN`?
2.  **Evaluasi Posisi (Jika ada):** Ambil data candle terbaru. Apakah harga High/Low menyentuh Take Profit atau Stop Loss?
    *   Jika YA → Update database ke status `CLOSED`, catat PnL, kirim notif Telegram.
    *   Jika TIDAK → Biarkan.
3.  **Cari Sinyal Baru (Jika TIDAK ada posisi):** Jalankan Data Fetcher & Signal Engine.
    *   Jika ada sinyal → Hitung SL/TP, simpan ke database sebagai `OPEN`, kirim notif Telegram.
    *   Jika tidak → Abaikan.

---

## 2. Spesifikasi Database (SQLite)

Anda membutuhkan 1 file database (misal: `trading_log.db`) dengan 2 tabel utama.

### Tabel 1: `signals` (Mencatat semua sinyal yang pernah dimuntahkan mesin)
Mencatat sinyal berguna untuk menganalisis apakah mesin sering memberi sinyal palsu di live market.

| Kolom | Tipe Data | Deskripsi |
|-------|-----------|-----------|
| id | INTEGER (PK) | Auto increment |
| timestamp | DATETIME | Waktu sinyal muncul (UTC) |
| symbol | TEXT | Contoh: BTC/USDT |
| side | TEXT | LONG / SHORT |
| confidence | REAL | Skor confidence saat itu |
| entry_price | REAL | Harga saat sinyal muncul |
| sl_price | REAL | Kalkulasi harga Stop Loss |
| tp_price | REAL | Kalkulasi harga Take Profit |
| reasons | TEXT | JSON string alasan sinyal |

### Tabel 2: `trades` (Mencatat hasil Paper Trading)
Ini adalah "ledger" atau buku kasir virtual Anda.

| Kolom | Tipe Data | Deskripsi |
|-------|-----------|-----------|
| id | INTEGER (PK) | Auto increment |
| signal_id | INTEGER | Relasi ke tabel signals |
| status | TEXT | **OPEN** atau **CLOSED** |
| entry_price | REAL | Harga masuk aktual (ditambah slippage) |
| exit_price | REAL | Harga keluar (jika tersentuh SL/TP) |
| quantity | REAL | Ukuran posisi (dihitung dari risk 1%) |
| pnl | REAL | Profit/Loss dalam dolar ($ sudah dipotong fee) |
| fee | REAL | Total biaya trading (Buka + Tutup) |
| open_time | DATETIME | Waktu posisi dibuka |
| close_time | DATETIME | Waktu posisi ditutup (Null jika OPEN) |

---

## 3. Spesifikasi Paper Trading Engine

Simulasi ini harus sedekat mungkin dengan realita pasar Futures.

### 3.1. Manajemen Saldo Virtual
*   **Saldo Awal:** Di-hardcode atau ambil dari konfigurasi (misal $10,000).
*   **PnL Tracking:** Setiap trade ditutup, saldo virtual diupdate. Ukuran posisi trade *berikutnya* harus dihitung berdasarkan saldo terbaru, bukan saldo statis.

### 3.2. Simulasi Slippage & Fee (Wajib)
*   **Fee (Biaya Trading):** Potong 0.04% (Taker Fee Binance) pada saat buka posisi, dan 0.04% saat tutup posisi.
*   **Slippage (Terpeleset):** Harga entry tidak selalu sempurna. Tambahkan aturan:
    *   Jika LONG: `Actual Entry = Signal Entry + (Signal Entry * 0.0005)` (Harga beli sedikit lebih mahal).
    *   Jika SHORT: `Actual Entry = Signal Entry - (Signal Entry * 0.0005)` (Harga jual sedikit lebih murah).

### 3.3. Logika Eksekusi SL/TP menggunakan OHLCV
Saat mengecek apakah SL/TP tersentuh di candle jamannya, gunakan data **High** dan **Low**, bukan Close.
*   **Prioritas Penutupan (Penting):** Jika dalam 1 candle yang sama, harga Low menyentuh SL dan harga High menyentuh TP, mana yang lebih dulu kena? Untuk paper trading yang aman (konservatif), **asumsikan SL lebih dulu kena** (karena volatilitas spiked down lebih dulu).

---

## 4. Spesifikasi Notifikasi Telegram (Update)

Notifikasi kini memiliki 2 jenis: Entry dan Exit.

**Format Entry (Sama seperti sebelumnya):**
```text
📈 LONG SIGNAL | 📉 SHORT SIGNAL
━━━━━━━━━━━━━━━━━━━━
📌 Pair: {Symbol}
💰 Entry: ${Price}
⚙️ Leverage: 5x (Isolated)
🛡 SL: ${SL_Price} | 🎯 TP: ${TP_Price}
📝 Reasons: ...
🟡 STATUS: VIRTUAL TRADE OPENED
```

**Format Exit (BARU):**
```text
🏁 TRADE CLOSED!
━━━━━━━━━━━━━━━━━━━━
📌 Pair: {Symbol}
Side: LONG / SHORT
💸 Exit Reason: ✅ Take Profit / 🛑 Stop Loss
📉 Entry: ${Entry} ➡️ Exit: ${Exit_Price}
💰 PnL: +$XX.XX (+X.XX%)
📊 Virtual Balance: $10,XXX.XX
```

---

## 5. Modul Aplikasi Utama (`app.py`)

Aplikasi tidak lagi hanya berjalan sekali (seperti backtest). Ini adalah *daemon* yang berjalan tanpa henti.

**Alur Utama:**
1.  Inisialisasi koneksi Database.
2.  Hitung waktu tunggu hingga candle 1 jam berikutnya tutup (misal: jam 14:59:50 tidur, bangun di 15:00:05 agar candle confirmed).
3.  Jalankan fungsi evaluasi posisi terbuka (Cek SL/TP dari candle yang baru saja tutup).
4.  Jalankan fungsi pencarian sinyal (Jika tidak ada posisi terbuka untuk symbol tersebut).
5.  Kembali ke step 2 (Loop forever).

---