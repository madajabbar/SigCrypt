---
name: dynamic-control-panel
description: Implement the Dynamic Control Panel & Signal Logger (V4). Interaktif dashboard, dynamic parameter tuning via .env (CONFIDENCE_THRESHOLD), dan bot decision transparency (bot_logs table). Transform bot dari black box ke glass box.
---

# Dynamic Control Panel & Signal Logger

## Overview

Skill ini mengimplementasikan arsitektur "Glass Box" - bot mencatat alasan keputusan setiap jam ke database, dan Dashboard menyediakan kontrol dinamis untuk mengatur agresivitas bot.

## Design Reference

Dokumen lengkap: `Design/Implementation DYNAMIC CONTROL PANEL & SIGNAL LOGGER.md`

## Files to Modify

| File | Change |
|------|--------|
| `.env` | Tambah `CONFIDENCE_THRESHOLD=40` dan update `SYMBOLS` list |
| `src/services/database.py` | Tambah `bot_logs` table creation dan `log_bot_decision()` method |
| `app.py` | Baca threshold dari env, log ke bot_logs di setiap branch (SIGNAL_FOUND, NO_SIGNAL, too weak) |
| `dashboard.py` | Tambah halaman "Bot Mind & Logs" (filter symbol/decision, highlight warna) dan "System Control" (threshold slider + save to .env) |

## Key Implementation Steps

### 1. Database: bot_logs Table

Tambahkan di `src/services/database.py` method `log_bot_decision()`:

```python
def log_bot_decision(self, timestamp, symbol, decision, reason, confidence):
    cursor = self.conn.cursor()
    cursor.execute("""
        INSERT INTO bot_logs (timestamp, symbol, decision, reason, confidence)
        VALUES (?, ?, ?, ?, ?)
    """, (timestamp, symbol, decision, reason, confidence))
    self.conn.commit()
```

Tabel `bot_logs` sudah ada di `create_tables()` (kolom: id, timestamp, symbol, decision, reason, confidence).

### 2. Engine: Dynamic Threshold + Logging

Di `app.py`, `CONFIDENCE_THRESHOLD` sudah dibaca dari env:
```python
CONFIDENCE_THRESHOLD = int(os.environ.get('CONFIDENCE_THRESHOLD', 40))
```

Logging ke bot_logs sudah diimplementasi di 3 branch:
- **SIGNAL_FOUND**: `db.log_bot_decision(current_time, symbol, 'SIGNAL_FOUND', ...)`
- **Confidence too weak**: `db.log_bot_decision(current_time, symbol, 'NO_SIGNAL', ...)`
- **No setup**: `db.log_bot_decision(current_time, symbol, 'NO_SIGNAL', 'No valid setup match...', 0)`

### 3. Dashboard: Bot Mind & Logs Page

Di `dashboard.py`, halaman "Bot Mind & Logs" sudah ada dengan:
- Filter multiselect symbol dan selectbox decision
- Query builder dengan WHERE clause dinamis
- Highlight warna hijau (#d4edda) untuk SIGNAL_FOUND, kuning (#fff3cd) untuk NO_SIGNAL

### 4. Dashboard: System Control Page

Halaman "System Control" sudah ada dengan:
- Threshold slider (10-80, step 5, default dari env)
- Button "Save Threshold to .env" menggunakan `set_key('.env', 'CONFIDENCE_THRESHOLD', str(new_threshold))`
- Force Run Scanner button (placeholder)

### 5. .env Configuration

Tambahkan di `.env`:
```env
CONFIDENCE_THRESHOLD=40
SYMBOLS=BTC/USDT,ETH/USDT,SOL/USDT,BNB/USDT,ZEC/USDT,AVAX/USDT,INJ/USDT,LINK/USDT,SUI/USDT,FET/USDT
```

## Architecture Notes

- Threshold dibaca dari env saat loop mulai. Bot tidak re-read env mid-cycle. User harus `docker compose restart sigcrypt-engine` atau bot akan re-read saat cycle berikutnya.
- `bot_logs` terpisah dari `signals` dan `trades` agar tidak mencemari data trading.
- `set_key` dari `python-dotenv` dipakai untuk write ke .env dari Dashboard.
- `db.log_bot_decision()` menggunakan SQLite connection yang sama (`self.conn`) dengan `check_same_thread=False`.

## Verification

Setelah implementasi, verifikasi dengan:
1. Jalankan bot 1 cycle, check `bot_logs` di SQLite: `sqlite3 data/trading_log.db "SELECT * FROM bot_logs LIMIT 10"`
2. Buka Dashboard, navigasi ke "Bot Mind & Logs", pastikan data muncul dengan warna highlight
3. Di "System Control", geser threshold slider, klik Save, verify `.env` berubah
4. Restart engine container, verify threshold baru dipakai
