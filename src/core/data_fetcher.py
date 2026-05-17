import ccxt
import pandas as pd
from datetime import datetime
import src.config as config

class CryptoDataFetcher:
    def __init__(self, exchange_id='binance'):
        exchange_args = {
            'enableRateLimit': True,
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

if __name__ == '__main__':
    # Usage
    fetcher = CryptoDataFetcher()
    df = fetcher.get_ohlcv('BTC/USDT', '1h', 50)
    print(df.tail())
