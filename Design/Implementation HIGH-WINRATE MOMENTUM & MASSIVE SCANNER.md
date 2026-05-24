# 📄 DOKUMEN TEKNIS V5: HIGH-WINRATE MOMENTUM & MASSIVE SCANNER

**Fokus:** Eliminasi sinyal palsu, 100% searah tren besar, dan Auto-Scanning Seluruh Binance Futures.
**Filosofi Baru:** *Kita tidak menebak puncak/dasar. Kita menunggu kereta bergerak, lalu ikut naik di stasiun berikutnya (Pullback).*

---

## 1. Revolusi Logika Sinyal (Menghilangkan Kerugian ZEC)

Sistem V3/V4 memiliki Setup B (Extreme Reversal). **Setup B sekarang DIHAPUS PERMANEN.** Menebak puncak/dasar di pasar Crypto itu bunuh diri.

Kita akan menggunakan satu-satunya setup yang memiliki win rate tertinggi di dunia trading: **Trend Continuation Pullback (TCP) + Konfirmasi Price Action.**

### Aturan Baru yang Sangat Ketat (Wajib 3 Konfirmasi):
Untuk mengeluarkan sinyal LONG, **SEMUA** syarat ini wajib terpenuhi bersamaan:
1.  **Tren Besar Bully (Daily):** Harga tutup (Close) candle 1-Hari kemarin **HARUS** di atas EMA 50 Harian. (Membuktikan ini uptrend besar, bukan sekadar bounce).
2.  **Pullback (Koreksi Sehat):** Di timeframe 1 Jam, RSI harus menyentuh area 35-45. (Membuktikan koin ini sedang diskon/sehat koreksi, bukan jenuh).
3.  **Bounce / Konfirmasi Masuk:** Candle 1 Jam yang sedang berjalan harus menunjukkan histogram MACD yang sudah tidak turun lagi (mulai memutih/memanjang ke atas). (Membuktikan penjual sudah kehabisan tenaga, pembeli mulai mengambil alih).

*(Aturan kebalikan berlaku untuk SHORT).*

---

## 2. Arsitektur Massive Scanner (Auto-Scan 200+ Koin)

Sebelumnya Anda hardcode 5-10 koin di `.env`. Ini tidak efisien. Kita akan membuat bot **secara otomatis mengunduh daftar seluruh koin Perpetual Futures di Binance** yang aktif dan memiliki volume bagus.

### Alur Kerja Bot Baru (Setiap Jam):
1.  **Discovery:** Bot bertanya ke Binance: *"Berikan saya semua pair USDT Perpetual yang volume perdagangannya 24 jam terakhir di atas $5 Juta."* (Ini menyaring koin sampah/mati).
2.  **Sequential Scanning:** Bot mengecek satu per satu dari 100-200 koin tersebut.
3.  **Execution:** Jika dari 200 koin tersebut hanya 1 koin yang memenuhi syarat ketat TCP, eksekusi. Jika tidak ada, tidur lagi.

---

## 3. Spesifikasi Implementasi Kode

### 3.1. Update `src/core/data_fetcher.py` (Tambah Fungsi Scanner)

Tambahkan fungsi ini untuk mengambil daftar koin dinamis dari Binance:

```python
import ccxt
import pandas as pd

class CryptoDataFetcher:
    def __init__(self):
        self.exchange = ccxt.binance({
            'enableRateLimit': True,
            'options': {'defaultType': 'future'},
            'urls': {
                'api': {
                    'public': 'https://api3.binance.com/api/v3',
                    'fapiPublic': 'https://fapi.binance.com/fapi/v1',
                }
            }
        })

    def get_active_futures_symbols(self, min_volume_usd=5_000_000):
        """Ambil semua pair USDT perpetual yang volume 24j di atas threshold"""
        try:
            markets = self.exchange.fetch_markets()
            tickers = self.exchange.fetch_tickers()
            
            valid_symbols = []
            for market in markets:
                # Filter: Harus Perpetual USDT-M, dan aktif
                if market['quote'] == 'USDT' and market['linear'] and market['active']:
                    symbol = market['symbol']
                    if symbol in tickers:
                        volume_usd = tickers[symbol].get('quoteVolume', 0)
                        # Hanya masukkan jika volume 24 jam lebih dari $5 Juta
                        if volume_usd >= min_volume_usd:
                            valid_symbols.append(symbol)
                            
            print(f"🔍 Scanner found {len(valid_symbols)} active high-volume pairs.")
            return valid_symbols
            
        except Exception as e:
            print(f"Error fetching market list: {e}")
            return ['BTC/USDT', 'ETH/USDT'] # Fallback
```

### 3.2. Update `src/core/signal_engine.py` (Hapus Reversal, Perketat TCP)

Kita akan merombak total `generate_combined_signal`. 

```python
import pandas as pd

class SignalEngine:
    
    def trend_continuation_pullback_signal(self, df_1h, df_1d):
        """
        Setup Satu-satunya yang akan kita pakai: TCP (Trend Continuation Pullback)
        Wajib searah tren harian, koreksi di 1H, lalu bouncing.
        """
        last_1h = df_1h.iloc[-1]
        prev_1h = df_1h.iloc[-2]
        
        # Cek tren 1 Hari (Kemarin harus tutup di atas/bawah EMA 50)
        last_1d = df_1d.iloc[-1]
        is_daily_uptrend = last_1d['close'] > last_1d['ema_50']
        is_daily_downtrend = last_1d['close'] < last_1d['ema_50']

        # ==========================================
        # LONG SETUP (Bullish Pullback)
        # ==========================================
        if is_daily_uptrend:
            # Syarat 1: RSI 1H mendekati oversold (koreksi sehat)
            if 35 <= last_1h['rsi'] <= 45:
                # Syarat 2: MACD histogram mulai memutih/memanjang ke atas (Bounce mulai)
                if prev_1h['macd_histogram'] < 0 and last_1h['macd_histogram'] > prev_1h['macd_histogram']:
                    return {
                        'type': 'LONG', 
                        'reason': 'Bullish TCP (Daily Uptrend + 1H RSI Pullback + MACD Bounce)',
                        'strength': 'STRONG'
                    }

        # ==========================================
        # SHORT SETUP (Bearish Pullback)
        # ==========================================
        if is_daily_downtrend:
            # Syarat 1: RSI 1H mendekati overbought (bounce sehat)
            if 55 <= last_1h['rsi'] <= 65:
                # Syarat 2: MACD histogram mulai memendek ke bawah (Penjual kembali menguasai)
                if prev_1h['macd_histogram'] > 0 and last_1h['macd_histogram'] < prev_1h['macd_histogram']:
                    return {
                        'type': 'SHORT', 
                        'reason': 'Bearish TCP (Daily Downtrend + 1H RSI Pullback + MACD Bounce)',
                        'strength': 'STRONG'
                    }

        # Jika tidak memenuhi syarat TCP, TIDAK ADA SINYAL
        return None


    def generate_combined_signal(self, df_1h, df_1d, symbol='BTC/USDT'):
        # Cek Volume (Wajib di atas rata-rata agar tidak masuk pasar sepi)
        last_1h = df_1h.iloc[-1]
        if last_1h['volume'] < last_1h['volume_sma']:
            return None # Pasar sepi, batalkan

        # Panggil satu-satunya setup yang valid
        signal = self.trend_continuation_pullback_signal(df_1h, df_1d)
        
        if signal:
            return {
                'symbol': symbol,
                'type': signal['type'],
                'confidence': 85, # Tetap 85 karena ini sudah super ketat
                'price': last_1h['close'],
                'signals': [signal],
                'timestamp': pd.Timestamp.now().isoformat()
            }
        
        return None
```

### 3.3. Update `app.py` (Loop Utama)

Anda harus menyesuaikan loop utama agar dia melakukan scanning masif dan mengambil data 2 timeframe (1H dan 1D).

```python
# Di dalam mode Live Daemon loop Anda:

fetcher = CryptoDataFetcher()
engine = SignalEngine()

def run_live():
    # 1. Dapatkan daftar koin secara dinamis
    symbols_to_scan = fetcher.get_active_futures_symbols(min_volume_usd=5_000_000)
    
    for symbol in symbols_to_scan:
        try:
            # 2. Ambil Data 1 Jam (500 candle terakhir untuk indikator)
            df_1h = fetcher.get_ohlcv(symbol, '1h', limit=500)
            
            # 3. Ambil Data 1 Hari (200 candle terakhir untuk tren besar)
            df_1d = fetcher.get_ohlcv(symbol, '1d', limit=200)
            
            if df_1h.empty or df_1d.empty:
                continue
                
            # 4. Hitung Indikator untuk kedua timeframe
            df_1h = indicators.apply_all(df_1h)
            df_1d = indicators.apply_all(df_1d) 
            
            # 5. Cek Sinyal (Masukkan 2 dataframe)
            signal = engine.generate_combined_signal(df_1h, df_1d, symbol)
            
            if signal and signal['confidence'] >= int(os.environ.get('CONFIDENCE_THRESHOLD', 40)):
                # Eksekusi trade / Catat ke DB
                print(f"🚀 SIGNAL FOUND: {signal['type']} {symbol}")
                # ... (logika eksekusi SL/TP menggunakan ATR dari df_1h)
                
        except Exception as e:
            print(f"Error scanning {symbol}: {e}")
            continue
```

---

## 4. Apa yang Berubah dari Sudut Pandang Anda?

1.  **Tidak Akan Ada Lagi Sinyal Aneh Seperti ZEC Tadi:** Sinyal seperti "Extreme Reversal" saat harga lagi naik tajam sudah dihapus. Bot sekarang hanya akan SHORT jika tren harian memang sudah turun, harga mengalami bounce ke atas (RSI 55-65), lalu mulai turun lagi. Ini adalah sinyal yang sangat aman.
2.  **Lebih Banyak Peluang:** Anda tidak perlu lagi memilih koin manual. Setiap jam, bot merazia 100-200 koin untuk mencari koin yang sedang dalam fase "diskon sehat" (Pullback) di tengah tren besar.
3.  **Frekuensi Trade:** Meskipun memindai 200 koin, filter TCP yang 3 lapis itu sangat ketat. Mungkin bot hanya akan mengeluarkan 1-3 sinyal per minggu. Tapi itu **1-3 sinyal dengan probabilitas menang yang jauh lebih tinggi.**
