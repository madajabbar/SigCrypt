# 📄 DOKUMEN TEKNIS: BACKTEST DATABASE LOGGER

## 1. Konsep Dasar
*   **Engine:** SQLite (sama seperti Paper Trading).
*   **File DB:** Pisahkan file databasenya, misalnya `backtest_log.db`, agar tidak mencemari data paper trading nanti.
*   **Siklus Hidup (Lifecycle):** Setiap kali fungsi `run_backtest()` dipanggil, sistem **wajib menghapus (DROP)** tabel lama dan membuat yang baru. Ini memastikan data backtest selalu bersih dan hanya mewakili satu sesi run.

---

## 2. Skema Database (Tabel `backtest_trades`)

Tabel ini akan mencatat setiap detik keputusan bot selama periode historis.

| Kolom | Tipe Data | Deskripsi |
|-------|-----------|-----------|
| id | INTEGER (PK) | Auto increment |
| symbol | TEXT | Pair (e.g., BTC/USDT) |
| side | TEXT | LONG / SHORT |
| entry_time | DATETIME | Waktu candle saat posisi dibuka |
| entry_price | REAL | Harga masuk (ditambah slippage simulasi) |
| exit_time | DATETIME | Waktu candle saat posisi ditutup |
| exit_price | REAL | Harga keluar (SL/TP/Signal) |
| exit_reason | TEXT | **Take Profit**, **Stop Loss**, atau **Signal Reversal** |
| quantity | REAL | Ukuran posisi |
| fee | REAL | Biaya trading (0.04% x 2) |
| pnl | REAL | Profit/Loss bersih dalam dolar |
| pnl_pct | REAL | Profit/Loss bersih dalam persen |
| running_balance | REAL | Total saldo akun setelah trade ini ditutup |

---

## 3. Modifikasi Logika `backtest.py`

Anda perlu mengimpor library `sqlite3` bawaan Python dan memodifikasi kelas `Backtester`.

### 3.1. Inisialisasi & Clear Database
Di awal method `run()`, lakukan koneksi dan bersihkan tabel.

```python
import sqlite3
import pandas as pd

class Backtester:
    def __init__(self, initial_capital=10000, db_path='backtest_log.db'):
        self.initial_capital = initial_capital
        self.db_path = db_path

    def _init_db(self):
        """Bersihkan dan buat tabel baru setiap kali backtest berjalan"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # WIPE DATA LAMA (Sesuai permintaan Anda)
        cursor.execute("DROP TABLE IF EXISTS backtest_trades")
        
        # BUAT TABEL BARU
        cursor.execute("""
            CREATE TABLE backtest_trades (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT,
                side TEXT,
                entry_time DATETIME,
                entry_price REAL,
                exit_time DATETIME,
                exit_price REAL,
                exit_reason TEXT,
                quantity REAL,
                fee REAL,
                pnl REAL,
                pnl_pct REAL,
                running_balance REAL
            )
        """)
        conn.commit()
        return conn
```

### 3.2. Mencatat Trade ke Database (Saat Posisi Ditutup)
Di dalam loop utama backtest, tepat setelah posisi ditutup (tersentuh TP, SL, atau sinyal balik), lakukan `INSERT INTO`.

```python
    def run(self, df, signal_func, symbol='BTC/USDT', stop_loss_pct=0.05, take_profit_pct=0.10):
        conn = self._init_db() # Panggil inisialisasi DB
        cursor = conn.cursor()
        
        capital = self.initial_capital
        position = 0
        entry_price = 0
        entry_time = None
        side = None
        
        for i in range(200, len(df)):
            current_time = df.iloc[i].name # Asumsi index adalah Datetime
            price = df.iloc[i]['close']
            high = df.iloc[i]['high']
            low = df.iloc[i]['low']
            
            # Cek jika sedang memegang posisi
            if position > 0:
                # ... (Logika pengecekan TP/SL seperti sebelumnya)
                
                # CONTOH: Jika Take Profit terkena
                if high >= entry_price * (1 + take_profit_pct):
                    exit_price = entry_price * (1 + take_profit_pct)
                    fee = (position * entry_price * 0.0004) + (position * exit_price * 0.0004) # Fee Buka + Tutup
                    gross_pnl = position * (exit_price - entry_price)
                    net_pnl = gross_pnl - fee
                    capital = (position * entry_price) + net_pnl
                    pnl_pct = (net_pnl / (position * entry_price)) * 100
                    
                    # CATAT KE DATABASE
                    cursor.execute("""
                        INSERT INTO backtest_trades 
                        (symbol, side, entry_time, entry_price, exit_time, exit_price, exit_reason, quantity, fee, pnl, pnl_pct, running_balance)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (symbol, side, entry_time, entry_price, current_time, exit_price, 'Take Profit', position, fee, net_pnl, pnl_pct, capital))
                    conn.commit()
                    
                    position = 0
                    continue
                
                # ... (Logika yang sama untuk Stop Loss / Signal Exit)
            
            # Logika pencarian sinyal BUY/SHORT jika tidak ada posisi
            # ... (Sama seperti sebelumnya, tapi simpan entry_time & side)
            if position == 0:
                window = df.iloc[:i+1].copy()
                signal = signal_func(window)
                
                if signal and signal['confidence'] >= 60:
                    position = capital / price
                    entry_price = price
                    entry_time = current_time
                    side = signal['type'] # LONG atau SHORT
                    capital = 0
        
        conn.close() # Tutup koneksi DB setelah selesai
        
        # ... Lanjutkan cetak hasil ringkasan ke terminal seperti biasa
```