import os
from dotenv import load_dotenv

load_dotenv()

symbols_env = os.getenv('SYMBOLS', 'BTC/USDT,ETH/USDT,SOL/USDT,BNB/USDT,ZEC/USDT')
SYMBOLS = [s.strip() for s in symbols_env.split(',')]
TIMEFRAME = os.getenv('TIMEFRAME', '5m')
TREND_TIMEFRAME = os.getenv('TREND_TIMEFRAME', '1h')
LIMIT = 500
SCAN_LIMIT = int(os.getenv('SCAN_LIMIT', '30'))
CYCLE_MINUTES = int(os.getenv('CYCLE_MINUTES', '5'))

BINANCE_API_KEY = os.getenv('BINANCE_API_KEY', '')
BINANCE_SECRET = os.getenv('BINANCE_SECRET', '')

TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN', '')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID', '')

INITIAL_CAPITAL = 10000
