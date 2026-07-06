---
name: interactive-market-terminal
description: Implement the Interactive Market Terminal Dashboard (V6). Market Screener dengan Ag-Grid interaktif, click-to-chart dengan Plotly candlestick, dan auto-refresh data.
---

# Interactive Market Terminal Dashboard

## Overview

Skill ini mengimplementasikan dashboard profesional dengan Market Screener interaktif menggunakan Ag-Grid tabel premium, Plotly candlestick chart pop-out, dan auto-refresh caching.

## Design Reference

Dokumen lengkap: `Design/Implementation INTERACTIVE MARKET TERMINAL DASHBOARD.md`

## Dashboard Pages (4)

1. **Market Screener** - Tabel dinamis 100+ koin, warna RSI/Change otomatis, click-to-chart
2. **Portfolio & Equity** - Ringkasan saldo, equity curve, active positions
3. **Bot Mind & Logs** - Decision diaries bot (dari V4)
4. **System Control** - Threshold slider + force scanner (dari V4)

## Required Libraries

```text
streamlit-aggrid
plotly
```

Tambah di `requirements.txt` dan `Dockerfile.dashboard`, lalu rebuild: `docker compose build sigcrypt-dashboard`

## Files to Modify

| File | Change |
|------|--------|
| `requirements.txt` | Tambah `streamlit-aggrid` dan `plotly` |
| `Dockerfile.dashboard` | Tambah install untuk libs baru |
| `src/core/data_fetcher.py` | Tambah `get_market_snapshot()` untuk screener data |
| `dashboard.py` | Rombak total: Ag-Grid screener, Plotly charts, 4 pages |

## Key Implementation Steps

### 1. Data Fetcher: Market Snapshot

`src/core/data_fetcher.py` sudah punya `get_market_snapshot()`:

- Fetch active futures symbols
- Ambil 24 candle 1H per symbol (limit 100 symbols untuk rate limit safety)
- Kalkulasi RSI cepat dari 24 candle
- Return DataFrame: Symbol, Price, 24h Change (%), RSI (1H), Volume

### 2. Dashboard: Market Screener Page

`dashboard.py` sudah mengimplementasi Ag-Grid screener:

```python
gb = GridOptionsBuilder.from_dataframe(df_screener)
gb.configure_pagination(paginationAutoPageSize=True)
gb.configure_side_bar()
gb.configure_selection(selection_mode='single', use_checkbox=True)
```

Kolom RSI diwarnai: red bg jika >70, green bg jika <30.
Kolom 24h Change: green text jika >0, red text jika <0.

### 3. Click-to-Chart: Plotly Candlestick

Saat user klik baris di Ag-Grid, symbol terpilih ditangkap:
```python
selected = grid_response.get('selected_rows')
```

Format `selected_rows` bisa DataFrame atau list of dicts - sudah dihandle:
```python
if isinstance(selected, pd.DataFrame) and not selected.empty:
    selected_symbol = selected.iloc[0]['Symbol']
elif isinstance(selected, list) and len(selected) > 0:
    selected_symbol = selected[0]['Symbol']
```

Chart menggunakan Plotly go.Candlestick dengan tema dark (`plotly_dark`).

### 4. Caching Strategy

- Screener data: `@st.cache_data(ttl=300)` (5 menit refresh)
- Chart data: `@st.cache_data(ttl=10)` (10 detik refresh)
- DB queries: `@st.cache_data(ttl=10)` (10 detik refresh)

### 5. Portfolio Page

Portfolio page sudah ada dengan:
- Metrics: Virtual Balance, Total PnL, Win Rate
- Equity Curve dari closed trades (running balance dari cumsum PnL)
- Active positions table
- Initial balance 10000 jika no closed trades

### 6. History & Logs Page

Tab-based layout:
- Tab 1: Closed Trades (from trades table)
- Tab 2: Signal Logs (from signals table)

### 7. Bot Mind & Logs Page

Dari V4, dengan filter symbol multiselect dan decision selectbox.
Highlight hijau/kuning berdasarkan decision value.

### 8. System Control Page

Dari V4, threshold slider + save ke .env + force run scanner button.

## Architecture Notes

- `sys.path.append(os.path.dirname(os.path.abspath(__file__)))` dipakai agar Streamlit bisa import modul `src`.
- `Database(DB_PATH)` di-initialize saat dashboard load untuk create tables jika belum ada.
- Ag-Grid `update_mode='SELECTION_CHANGED'` agar chart langsung muncul saat baris diklik.
- Rate limit: screener capped 100 symbols. Jika butuh lebih, bisa naikkan tapi hati-hati Binance throttle.
- Endpoint cadangan `api3.binance.com` untuk bypass ISP blokir.

## Verification

Setelah implementasi, verifikasi dengan:
1. `pip install streamlit-aggrid plotly` atau rebuild docker
2. `streamlit run dashboard.py` - pastikan 4 pages muncul di sidebar
3. Market Screener: pastikan tabel muncul dengan warna RSI/Change, klik baris dan candlestick chart muncul
4. Portfolio: pastikan metrics dan equity curve render
5. Bot Logs: pastikan filter dan highlight berfungsi
6. System Control: geser threshold, save, verify .env berubah
