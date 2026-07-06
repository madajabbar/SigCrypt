---
name: high-winrate-momentum
description: Implement the High-Winrate Momentum & Massive Scanner (V5). Hapus Setup B (Extreme Reversal), perketat TCP (Trend Continuation Pullback) dengan 3 konfirmasi wajib, dan auto-scan 200+ Binance Futures pairs.
---

# High-Winrate Momentum & Massive Scanner

## Overview

Skill ini mengimplementasikan revolusi logika sinyal: menghapus semua setup reversal yang berisiko, hanya menggunakan TCP (Trend Continuation Pullback) dengan 3 konfirmasi ketat, dan scanning masif seluruh Binance Futures secara dinamis.

## Design Reference

Dokumen lengkap: `Design/Implementation HIGH-WINRATE MOMENTUM & MASSIVE SCANNER.md`

## Core Philosophy

> *Kita tidak menebak puncak/dasar. Kita menunggu kereta bergerak, lalu ikut naik di stasiun berikutnya (Pullback).*

Setup B (Extreme Reversal) **DIHAPUS PERMANEN**. Satu-satunya setup yang valid adalah TCP.

## Files to Modify

| File | Change |
|------|--------|
| `src/core/signal_engine.py` | Hapus reversal logic, implementasi strict TCP dengan 3 konfirmasi |
| `src/core/data_fetcher.py` | Tambah `get_active_futures_symbols()` untuk dynamic coin discovery |
| `app.py` | Loop utama scan dynamic symbols, fetch 2 timeframe (1H + 1D) |

## TCP Signal Rules (3 Mandatory Confirmations)

### LONG Setup (Bullish Pullback)
1. **Daily Uptrend**: Close candle 1Hari kemarin HARUS di atas EMA 50 Harian
2. **1H Pullback**: RSI 1H di area 35-45 (koreksi sehat, bukan jenuh)
3. **1H Bounce**: MACD histogram mulai memutih/memanjang ke atas (penjual kehabisan tenaga)

### SHORT Setup (Bearish Pullback)
1. **Daily Downtrend**: Close candle 1Hari kemarin HARUS di bawah EMA 50 Harian
2. **1H Pullback**: RSI 1H di area 55-65 (bounce sehat)
3. **1H Bounce**: MACD histogram mulai memendek ke bawah (penjual kembali menguasai)

## Key Implementation Steps

### 1. Signal Engine (Already Implemented)

`src/core/signal_engine.py` sudah mengimplementasi TCP:

- `trend_continuation_pullback_signal(df_1h, df_1d)` - method utama TCP
- LONG: cek `is_daily_uptrend` (close > ema_50), RSI 35-45, MACD histogram bounce
- SHORT: cek `is_daily_downtrend` (close < ema_50), RSI 55-65, MACD histogram decline
- `generate_combined_signal()` - volume filter + No Trade Zone (EMA 9 & 21 diff < 0.1%) + ATR-based SL/TP
- Confidence fixed 85 (sudah super ketat)
- RR ratio 1.5 minimum

**Pastikan tidak ada remnants dari Setup B atau reversal logic.**

### 2. Data Fetcher: Dynamic Symbol Discovery

`src/core/data_fetcher.py` sudah punya `get_active_futures_symbols(min_volume_usd=5_000_000)`:

- Fetch markets + tickers dari Binance
- Filter: USDT quote, linear (USDT-M), active, type=swap
- Filter volume 24h >= threshold
- Fallback: ['BTC/USDT', 'ETH/USDT'] jika error

**Pastikan filter `market['type'] == 'swap'` ada** untuk memastikan hanya perpetual futures.

### 3. Engine Loop: 2-Timeframe Scanning

`app.py` `run_all_live()` sudah menggunakan dynamic scanner:

```python
symbols_to_scan = fetcher.get_active_futures_symbols(min_volume_usd=5_000_000)
for symbol in symbols_to_scan:
    run_paper_trading(symbol)
```

`run_paper_trading()` sudah fetch 2 timeframe:
- `df = fetcher.get_ohlcv(symbol, config.TIMEFRAME, limit=100)` (1H)
- `df_daily = fetcher.get_ohlcv(symbol, '1d', limit=100)` (1D)

Dan apply indicators + generate signal dengan kedua dataframe.

### 4. Volume Gate

Di `generate_combined_signal()`, volume gate sudah ada:
```python
if last_1h['volume'] < last_1h.get('volume_sma', 0):
    return None
```

### 5. No Trade Zone

Di `generate_combined_signal()`, sideways filter sudah ada:
```python
ema_diff_pct = abs(ema_9 - ema_21) / current_price
if ema_diff_pct < 0.001:  # Selisih < 0.1%, pasar sideways
    return None
```

## Architecture Notes

- TCP filter 3-lapis sangat ketat. Bot mungkin hanya 1-3 sinyal per minggu, tapi probabilitas win jauh lebih tinggi.
- Scanning 200+ koin sequential. Rate limit ccxt `enableRateLimit: True` mencegah throttle Binance.
- Endpoint cadangan `api3.binance.com` dan `fapi.binance.com` sudah di `data_fetcher.py` untuk bypass ISP blokir.
- Confidence tetap 85 karena setup TCP sudah super ketat. Threshold default 40 dari `.env`.

## Verification

Setelah implementasi, verifikasi dengan:
1. Print jumlah symbols scanned: `print(f"Scanner found {len(symbols)} pairs")`
2. Run 1 cycle, pastikan tidak ada sinyal reversal di log
3. Check `bot_logs`: semua SIGNAL_FOUND harus berisi "TCP" reason
4. Backtest mode (MODE=2): run backtest dan check hanya TCP signals di output
