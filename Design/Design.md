# ✅ Tentu Bisa! Sistem Sinyal Crypto

Anda bisa membangun sistem analisis harga crypto dan pembuat sinyal. Berikut gambaran lengkapnya:

---

## 🏗️ Arsitektur Sistem

```
┌─────────────┐     ┌──────────────┐     ┌─────────────┐     ┌────────────┐
│  Data Source │────▶│  Processing  │────▶│  Analysis   │────▶│  Signal    │
│  (API/Scrape)│     │  & Storage   │     │  Engine     │     │  Output    │
└─────────────┘     └──────────────┘     └─────────────┘     └────────────┘
   Binance API        Database             Indikator TA        Telegram
   CoinGecko          (PostgreSQL)         Pattern Recognition  Dashboard
   Bybit WS           Redis Cache          ML Model             Email
```

---

## 📊 Jenis Analisis yang Bisa Dibuat

### 1. **Technical Analysis (TA)**
- RSI, MACD, Bollinger Bands
- Moving Average (SMA/EMA crossover)
- Volume Profile, Order Flow
- Support/Resistance Detection

### 2. **On-Chain Analysis**
- Wallet movement (whale tracking)
- Exchange inflow/outflow
- Mempool activity

### 3. **Sentiment Analysis**
- News scraping & NLP
- Twitter/X sentiment
- Fear & Greed Index
- Reddit sentiment

### 4. **Machine Learning**
- Price prediction model (LSTM, XGBoost)
- Anomaly detection
- Pattern recognition

---

## 💻 Contoh Implementasi (Python)

### Struktur Proyek
```
crypto-signal-system/
├── config.py            # Konfigurasi API keys, parameter
├── data_fetcher.py      # Ambil data dari exchange
├── indicators.py        # Kalkulasi indikator teknikal
├── signal_engine.py     # Logic pembuat sinyal
├── backtest.py          # Backtesting strategi
├── notifier.py          # Kirim notifikasi
├── ml_model.py          # Model machine learning (opsional)
├── app.py               # Main application
└── requirements.txt
```

### 1. Data Fetcher (`data_fetcher.py`)
```python
import ccxt
import pandas as pd
from datetime import datetime

class CryptoDataFetcher:
    def __init__(self, exchange_id='binance'):
        self.exchange = getattr(ccxt, exchange_id)({
            'apiKey': 'YOUR_API_KEY',
            'secret': 'YOUR_SECRET',
            'enableRateLimit': True,
        })
    
    def get_ohlcv(self, symbol='BTC/USDT', timeframe='1h', limit=500):
        """Ambil data OHLCV (Open, High, Low, Close, Volume)"""
        ohlcv = self.exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
        
        df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        df.set_index('timestamp', inplace=True)
        
        return df
    
    def get_orderbook(self, symbol='BTC/USDT', limit=20):
        """Ambil data orderbook untuk analisis depth"""
        return self.exchange.fetch_order_book(symbol, limit)

# Usage
fetcher = CryptoDataFetcher()
df = fetcher.get_ohlcv('BTC/USDT', '1h')
print(df.tail())
```

### 2. Indikator Teknikal (`indicators.py`)
```python
import pandas as pd
import numpy as np

class TechnicalIndicators:
    
    @staticmethod
    def rsi(df, period=14):
        """Relative Strength Index"""
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        df['rsi'] = 100 - (100 / (1 + rs))
        return df
    
    @staticmethod
    def macd(df, fast=12, slow=26, signal=9):
        """MACD"""
        df['ema_fast'] = df['close'].ewm(span=fast).mean()
        df['ema_slow'] = df['close'].ewm(span=slow).mean()
        df['macd'] = df['ema_fast'] - df['ema_slow']
        df['macd_signal'] = df['macd'].ewm(span=signal).mean()
        df['macd_histogram'] = df['macd'] - df['macd_signal']
        return df
    
    @staticmethod
    def bollinger_bands(df, period=20, std_dev=2):
        """Bollinger Bands"""
        df['bb_middle'] = df['close'].rolling(window=period).mean()
        df['bb_std'] = df['close'].rolling(window=period).std()
        df['bb_upper'] = df['bb_middle'] + (df['bb_std'] * std_dev)
        df['bb_lower'] = df['bb_middle'] - (df['bb_std'] * std_dev)
        return df
    
    @staticmethod
    def ema(df, periods=[9, 21, 50, 200]):
        """Multiple EMAs"""
        for period in periods:
            df[f'ema_{period}'] = df['close'].ewm(span=period).mean()
        return df
    
    @staticmethod
    def volume_sma(df, period=20):
        """Volume Simple Moving Average"""
        df['volume_sma'] = df['volume'].rolling(window=period).mean()
        return df

    def apply_all(self, df):
        """Terapkan semua indikator"""
        df = self.rsi(df)
        df = self.macd(df)
        df = self.bollinger_bands(df)
        df = self.ema(df)
        df = self.volume_sma(df)
        return df
```

### 3. Signal Engine (`signal_engine.py`)
```python
import pandas as pd
from datetime import datetime

class SignalEngine:
    
    def __init__(self):
        self.signals = []
    
    def rsi_signal(self, df):
        """Sinyal berdasarkan RSI"""
        last = df.iloc[-1]
        prev = df.iloc[-2]
        
        # Oversold → BUY, Overbought → SELL
        if prev['rsi'] < 30 and last['rsi'] > 30:
            return {'type': 'BUY', 'reason': 'RSI Oversold Recovery', 'strength': 'STRONG'}
        elif prev['rsi'] > 70 and last['rsi'] < 70:
            return {'type': 'SELL', 'reason': 'RSI Overbought Rejection', 'strength': 'STRONG'}
        elif last['rsi'] < 35:
            return {'type': 'BUY', 'reason': 'RSI Approaching Oversold', 'strength': 'MODERATE'}
        elif last['rsi'] > 65:
            return {'type': 'SELL', 'reason': 'RSI Approaching Overbought', 'strength': 'MODERATE'}
        return None
    
    def macd_signal(self, df):
        """Sinyal berdasarkan MACD Crossover"""
        last = df.iloc[-1]
        prev = df.iloc[-2]
        
        if prev['macd'] < prev['macd_signal'] and last['macd'] > last['macd_signal']:
            return {'type': 'BUY', 'reason': 'MACD Bullish Crossover', 'strength': 'STRONG'}
        elif prev['macd'] > prev['macd_signal'] and last['macd'] < last['macd_signal']:
            return {'type': 'SELL', 'reason': 'MACD Bearish Crossover', 'strength': 'STRONG'}
        return None
    
    def ema_crossover_signal(self, df):
        """Sinyal berdasarkan EMA Crossover"""
        last = df.iloc[-1]
        prev = df.iloc[-2]
        
        # EMA 9 cross above EMA 21 → Golden Cross (BUY)
        if prev['ema_9'] < prev['ema_21'] and last['ema_9'] > last['ema_21']:
            return {'type': 'BUY', 'reason': 'EMA 9/21 Golden Cross', 'strength': 'MODERATE'}
        # EMA 9 cross below EMA 21 → Death Cross (SELL)
        elif prev['ema_9'] > prev['ema_21'] and last['ema_9'] < last['ema_21']:
            return {'type': 'SELL', 'reason': 'EMA 9/21 Death Cross', 'strength': 'MODERATE'}
        return None
    
    def bollinger_signal(self, df):
        """Sinyal berdasarkan Bollinger Bands"""
        last = df.iloc[-1]
        
        if last['close'] <= last['bb_lower']:
            return {'type': 'BUY', 'reason': 'Price at Lower Bollinger Band', 'strength': 'MODERATE'}
        elif last['close'] >= last['bb_upper']:
            return {'type': 'SELL', 'reason': 'Price at Upper Bollinger Band', 'strength': 'MODERATE'}
        return None
    
    def volume_breakout_signal(self, df):
        """Sinyal berdasarkan Volume Anomaly"""
        last = df.iloc[-1]
        
        if last['volume'] > last['volume_sma'] * 2:
            price_change = (last['close'] - df.iloc[-2]['close']) / df.iloc[-2]['close']
            if price_change > 0.02:  # 2% naik dengan volume tinggi
                return {'type': 'BUY', 'reason': f'Volume Breakout (+{price_change*100:.1f}%)', 'strength': 'STRONG'}
            elif price_change < -0.02:
                return {'type': 'SELL', 'reason': f'Volume Breakdown ({price_change*100:.1f}%)', 'strength': 'STRONG'}
        return None
    
    def generate_combined_signal(self, df, symbol='BTC/USDT'):
        """Gabungkan semua sinyal → skor konfirmasi"""
        signal_checks = [
            self.rsi_signal(df),
            self.macd_signal(df),
            self.ema_crossover_signal(df),
            self.bollinger_signal(df),
            self.volume_breakout_signal(df),
        ]
        
        active_signals = [s for s in signal_checks if s is not None]
        
        if not active_signals:
            return None
        
        # Hitung skor
        buy_score = sum(2 if s['strength'] == 'STRONG' else 1 
                       for s in active_signals if s['type'] == 'BUY')
        sell_score = sum(2 if s['strength'] == 'STRONG' else 1 
                        for s in active_signals if s['type'] == 'SELL')
        
        total = buy_score + sell_score
        if total == 0:
            return None
        
        if buy_score > sell_score:
            signal_type = 'BUY'
            confidence = (buy_score / (total + 1)) * 100
        elif sell_score > buy_score:
            signal_type = 'SELL'
            confidence = (sell_score / (total + 1)) * 100
        else:
            return {'symbol': symbol, 'type': 'NEUTRAL', 'confidence': 50, 
                    'signals': active_signals, 'price': df.iloc[-1]['close']}
        
        return {
            'symbol': symbol,
            'type': signal_type,
            'confidence': round(confidence, 1),
            'price': df.iloc[-1]['close'],
            'signals': active_signals,
            'timestamp': datetime.now().isoformat(),
        }
```

### 4. Notifier (`notifier.py`)
```python
import requests

class Notifier:
    
    def __init__(self, telegram_token=None, chat_id=None):
        self.telegram_token = telegram_token
        self.chat_id = chat_id
    
    def send_telegram(self, message):
        """Kirim sinyal ke Telegram"""
        if not self.telegram_token:
            print("[TELEGRAM] Token not set")
            return
        
        url = f"https://api.telegram.org/bot{self.telegram_token}/sendMessage"
        payload = {
            'chat_id': self.chat_id,
            'text': message,
            'parse_mode': 'HTML'
        }
        requests.post(url, json=payload)
    
    def format_signal(self, signal):
        """Format sinyal untuk notifikasi"""
        emoji = "🟢" if signal['type'] == 'BUY' else "🔴" if signal['type'] == 'SELL' else "🟡"
        
        reasons = "\n".join([f"  • {s['reason']} ({s['strength']})" for s in signal['signals']])
        
        msg = f"""
{emoji} <b>{signal['type']} SIGNAL</b> {emoji}
━━━━━━━━━━━━━━━━━━
📌 <b>Pair:</b> {signal['symbol']}
💰 <b>Price:</b> ${signal['price']:,.2f}
📊 <b>Confidence:</b> {signal['confidence']}%
⏰ <b>Time:</b> {signal['timestamp']}

📝 <b>Reasons:</b>
{reasons}

⚠️ <i>Bukan financial advice. DYOR!</i>
"""
        return msg
    
    def notify(self, signal):
        """Kirim notifikasi jika sinyal cukup kuat"""
        if signal and signal['confidence'] >= 60:
            msg = self.format_signal(signal)
            self.send_telegram(msg)
            print(f"[SIGNAL] {signal['type']} {signal['symbol']} @ ${signal['price']:,.2f} (Confidence: {signal['confidence']}%)")
        else:
            print(f"[SKIP] Signal too weak or neutral ({signal['confidence'] if signal else 0}%)")
```

### 5. Backtesting (`backtest.py`)
```python
import pandas as pd

class Backtester:
    def __init__(self, initial_capital=10000):
        self.initial_capital = initial_capital
    
    def run(self, df, signal_func):
        """Jalankan backtest pada data historis"""
        capital = self.initial_capital
        position = 0
        trades = []
        
        for i in range(200, len(df)):  # Skip warmup period
            window = df.iloc[:i+1].copy()
            signal = signal_func(window)
            
            if signal is None:
                continue
            
            price = df.iloc[i]['close']
            
            if signal['type'] == 'BUY' and position == 0 and signal['confidence'] >= 60:
                position = capital / price
                capital = 0
                trades.append({'type': 'BUY', 'price': price, 'index': i})
            
            elif signal['type'] == 'SELL' and position > 0 and signal['confidence'] >= 60:
                capital = position * price
                position = 0
                trades.append({'type': 'SELL', 'price': price, 'index': i})
        
        # Final value
        final_price = df.iloc[-1]['close']
        final_value = capital + (position * final_price)
        pnl = final_value - self.initial_capital
        pnl_pct = (pnl / self.initial_capital) * 100
        
        # Win rate
        sell_trades = [t for t in trades if t['type'] == 'SELL']
        wins = 0
        for i, sell in enumerate(sell_trades):
            buy_trades = [t for t in trades if t['type'] == 'BUY' and t['index'] < sell['index']]
            if buy_trades:
                last_buy = max(buy_trades, key=lambda x: x['index'])
                if sell['price'] > last_buy['price']:
                    wins += 1
        
        win_rate = (wins / len(sell_trades) * 100) if sell_trades else 0
        
        print(f"""
╔══════════════════════════════╗
║     BACKTEST RESULTS         ║
╠══════════════════════════════╣
║ Initial:  ${self.initial_capital:>10,.2f}    ║
║ Final:    ${final_value:>10,.2f}      ║
║ PnL:      ${pnl:>+10,.2f}      ║
║ PnL %:    {pnl_pct:>+9.2f}%      ║
║ Trades:   {len(trades):>10}        ║
║ Win Rate: {win_rate:>9.1f}%      ║
╚══════════════════════════════╝
""")
        
        return trades, pnl_pct, win_rate
```

### 6. Main Application (`app.py`)
```python
import time
import schedule
from data_fetcher import CryptoDataFetcher
from indicators import TechnicalIndicators
from signal_engine import SignalEngine
from notifier import Notifier
from backtest import Backtester

# ============ CONFIG ============
SYMBOLS = ['BTC/USDT', 'ETH/USDT', 'SOL/USDT', 'BNB/USDT']
TIMEFRAME = '1h'
TELEGRAM_TOKEN = 'YOUR_TELEGRAM_BOT_TOKEN'
TELEGRAM_CHAT_ID = 'YOUR_CHAT_ID'
# =================================

fetcher = CryptoDataFetcher('binance')
indicators = TechnicalIndicators()
engine = SignalEngine()
notifier = Notifier(TELEGRAM_TOKEN, TELEGRAM_CHAT_ID)

def analyze_and_signal(symbol):
    """Proses utama: fetch → analisis → sinyal → notifikasi"""
    try:
        print(f"\n🔍 Analyzing {symbol}...")
        
        # 1. Fetch data
        df = fetcher.get_ohlcv(symbol, TIMEFRAME, limit=500)
        
        # 2. Apply indicators
        df = indicators.apply_all(df)
        
        # 3. Generate signal
        signal = engine.generate_combined_signal(df, symbol)
        
        # 4. Notify
        if signal:
            notifier.notify(signal)
        else:
            print(f"  → No signal for {symbol}")
            
    except Exception as e:
        print(f"❌ Error analyzing {symbol}: {e}")

def run_all():
    """Analyze semua symbol"""
    print(f"\n⏰ Running analysis @ {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 50)
    for symbol in SYMBOLS:
        analyze_and_signal(symbol)

def run_backtest():
    """Jalankan backtest"""
    print("\n📊 Running Backtest...")
    bt = Backtester(initial_capital=10000)
    
    for symbol in SYMBOLS:
        print(f"\n--- {symbol} ---")
        df = fetcher.get_ohlcv(symbol, '1h', limit=1000)
        df = indicators.apply_all(df)
        bt.run(df, engine.generate_combined_signal)

# ============ SCHEDULER ============
if __name__ == '__main__':
    # Pilih mode
    mode = input("Mode (1=Live, 2=Backtest): ")
    
    if mode == '2':
        run_backtest()
    else:
        # Jalankan langsung pertama kali
        run_all()
        
        # Jadwalkan setiap jam
        schedule.every().hour.do(run_all)
        
        print("\n🚀 Signal system running... (Ctrl+C to stop)")
        while True:
            schedule.run_pending()
            time.sleep(60)
```

---

## 🧠 Opsional: Tambahkan Machine Learning

```python
# ml_model.py
from sklearn.ensemble import RandomForestClassifier
import numpy as np

class MLSignalEnhancer:
    def __init__(self):
        self.model = RandomForestClassifier(n_estimators=100, random_state=42)
    
    def prepare_features(self, df):
        """Buat fitur dari indikator"""
        df = df.copy()
        df['return_1h'] = df['close'].pct_change(1)
        df['return_4h'] = df['close'].pct_change(4)
        df['return_24h'] = df['close'].pct_change(24)
        df['volatility'] = df['close'].rolling(24).std()
        df['volume_ratio'] = df['volume'] / df['volume_sma']
        
        # Target: harga naik >1% dalam 4 jam ke depan?
        df['target'] = (df['close'].shift(-4) > df['close'] * 1.01).astype(int)
        
        features = ['rsi', 'macd_histogram', 'return_1h', 'return_4h', 
                    'volatility', 'volume_ratio', 'ema_9', 'ema_21']
        
        return df[features].dropna(), df['target'].dropna()
    
    def train(self, df):
        X, y = self.prepare_features(df)
        # Align indices
        common_idx = X.index.intersection(y.index)
        X, y = X.loc[common_idx], y.loc[common_idx]
        
        self.model.fit(X, y)
        print(f"✅ Model trained. Accuracy: {self.model.score(X, y):.2%}")
    
    def predict(self, df):
        X, _ = self.prepare_features(df)
        if len(X) > 0:
            prob = self.model.predict_proba(X.iloc[[-1]])[0]
            return {'up_probability': prob[1], 'down_probability': prob[0]}
        return None
```

---

## 📦 Dependencies

```txt
# requirements.txt
ccxt==4.1.0
pandas==2.1.0
numpy==1.24.0
ta==0.10.2              # Alternative: technical analysis library
scikit-learn==1.3.0     # Untuk ML
schedule==1.2.0         # Scheduler
requests==2.31.0        # Telegram API
python-dotenv==1.0.0    # Environment variables
streamlit==1.28.0       # Dashboard (opsional)
plotly==5.17.0          # Visualisasi
```

---

## 🚀 Enhancement Ideas

| Fitur | Tool | Tingkat |
|-------|------|---------|
| **Dashboard Web** | Streamlit / Dash | ⭐ Menengah |
| **Real-time WebSocket** | ccxt pro / websockets | ⭐ Menengah |
| **Deep Learning** | PyTorch / TensorFlow | ⭐ Lanjut |
| **On-chain Analysis** | Glassnode / Dune API | ⭐ Lanjut |
| **Multi-exchange Arbitrage** | ccxt multi-exchange | ⭐ Menengah |
| **Social Sentiment** | Twitter API + VADER/BERT | ⭐ Lanjut |
| **Database Storage** | PostgreSQL + TimescaleDB | ⭐ Menengah |
| **Cloud Deploy** | AWS / GCP / Railway | ⭐ Menengah |

---

## ⚠️ Penting!

1. **BUKAN Financial Advice** — Sinyal hanya sebagai referensi, bukan jaminan profit
2. **Selalu Backtest** — Jangan pakai strategi tanpa diuji pada data historis
3. **Paper Trading** — Uji dulu dengan uang palsu sebelum real trading
4. **Risk Management** — Selalu pakai stop-loss, jangan all-in
5. **Overfitting** — Hati-hati model ML yang terlalu fit ke data historis tapi gagal di live
6. **API Rate Limit** — Perhatikan batas request dari exchange API
7. **Security** — Jangan hardcode API keys, pakai `.env` file

---