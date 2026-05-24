import ccxt
import pandas as pd
from datetime import datetime
import src.config as config

class CryptoDataFetcher:
    def __init__(self, exchange_id='binance'):
        exchange_args = {
            'enableRateLimit': True,
            'options': {
                'defaultType': 'future',
                'aiohttp_trust_env': True # Penting untuk routing di Docker/Linux
            },
            # Hardcode endpoint cadangan untuk menghindari 301 Redirect / Blokir ISP
            'urls': {
                'api': {
                    'public': 'https://api3.binance.com/api/v3',
                    'fapiPublic': 'https://fapi.binance.com/fapi/v1', # Endpoint Futures
                }
            }
        }
        if config.BINANCE_API_KEY and config.BINANCE_SECRET:
            exchange_args['apiKey'] = config.BINANCE_API_KEY
            exchange_args['secret'] = config.BINANCE_SECRET
            
        self.exchange = getattr(ccxt, exchange_id)(exchange_args)
    
    def get_ohlcv(self, symbol='BTC/USDT', timeframe='1h', limit=500):
        """Ambil data OHLCV (Open, High, Low, Close, Volume)"""
        try:
            ohlcv = self.exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
            
            df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            df.set_index('timestamp', inplace=True)
            
            return df
        except Exception as e:
            print(f"Error fetching data for {symbol}: {e}")
            return pd.DataFrame()
    
    def get_orderbook(self, symbol='BTC/USDT', limit=20):
        """Ambil data orderbook untuk analisis depth"""
        return self.exchange.fetch_order_book(symbol, limit)

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
                        # Hanya masukkan jika volume 24 jam lebih dari threshold
                        if volume_usd >= min_volume_usd:
                            valid_symbols.append(symbol)
                            
            print(f"🔍 Scanner found {len(valid_symbols)} active high-volume pairs.")
            return valid_symbols
            
        except Exception as e:
            print(f"Error fetching market list: {e}")
            return ['BTC/USDT', 'ETH/USDT'] # Fallback

    def get_market_snapshot(self):
        """Mengambil data RSI dan perubahan harga 24h untuk seluruh market futures"""
        symbols = self.get_active_futures_symbols()
        tickers = self.exchange.fetch_tickers(symbols)
        
        snapshot = []
        # Ambil data 24jam terakhir untuk kalkulasi RSI cepat (tidak perlu 500 candle)
        for symbol in symbols[0:100]: # Batas 100 dulu agar tidak kena rate limit Binance
            try:
                # Cukup ambil 24 candle 1H untuk kalkulasi RSI cepat
                df = self.get_ohlcv(symbol, '1h', limit=24)
                if df.empty: continue
                
                delta = df['close'].diff()
                gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
                loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
                rs = gain / loss
                df['rsi'] = 100 - (100 / (1 + rs))
                
                last_rsi = df['rsi'].iloc[-1]
                price_change_24h = ((df['close'].iloc[-1] - df['close'].iloc[0]) / df['close'].iloc[0]) * 100
                
                snapshot.append({
                    'Symbol': symbol,
                    'Price': df['close'].iloc[-1],
                    '24h Change (%)': round(price_change_24h, 2),
                    'RSI (1H)': round(last_rsi, 2),
                    'Volume': tickers[symbol].get('quoteVolume', 0)
                })
            except:
                continue
                
        return pd.DataFrame(snapshot)

if __name__ == '__main__':
    # Usage
    fetcher = CryptoDataFetcher()
    df = fetcher.get_ohlcv('BTC/USDT', '1h', 50)
    print(df.tail())
