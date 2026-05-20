import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configuration
symbols_env = os.getenv('SYMBOLS', 'BTC/USDT,ETH/USDT,SOL/USDT,BNB/USDT,ZEC/USDT')
SYMBOLS = [s.strip() for s in symbols_env.split(',')]
TIMEFRAME = '1h'
LIMIT = 500

# API Keys
BINANCE_API_KEY = os.getenv('BINANCE_API_KEY', '')
BINANCE_SECRET = os.getenv('BINANCE_SECRET', '')

TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN', '')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID', '')

# Trading
INITIAL_CAPITAL = 10000
