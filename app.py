import time
import os
from datetime import datetime, timedelta
from dotenv import load_dotenv
from src.core.data_fetcher import CryptoDataFetcher
from src.core.indicators import TechnicalIndicators
from src.core.signal_engine import SignalEngine
from src.services.notifier import Notifier
from src.core.backtest import Backtester
from src.services.database import Database
import src.config as config
import json

fetcher = CryptoDataFetcher('binance')
indicators = TechnicalIndicators()
engine = SignalEngine()
notifier = Notifier(config.TELEGRAM_TOKEN, config.TELEGRAM_CHAT_ID)
db = Database()

def run_paper_trading(symbol, threshold=None):
    if threshold is None:
        threshold = int(os.environ.get('CONFIDENCE_THRESHOLD', 40))

    try:
        print(f"\n🔍 [PAPER TRADING] Processing {symbol} (threshold={threshold})...")
        
        # Fetch latest data
        df = fetcher.get_ohlcv(symbol, config.TIMEFRAME, limit=100)
        df_daily = fetcher.get_ohlcv(symbol, '1d', limit=100)
        
        if df.empty or df_daily.empty:
            print(f"  → Data empty for {symbol}")
            return
            
        current_candle = df.iloc[-1]
        
        # 1. Cek Posisi Terbuka
        open_trade = db.get_open_trade(symbol)
        
        if open_trade:
            # 2. Evaluasi Posisi
            print(f"  → Found OPEN trade: {open_trade['side']} at {open_trade['entry_price']}")
            
            # Ambil detail SL dan TP dari database signals
            cursor = db.conn.cursor()
            cursor.execute('SELECT sl_price, tp_price FROM signals WHERE id = ?', (open_trade['signal_id'],))
            sig_data = cursor.fetchone()
            
            if sig_data:
                sl_price, tp_price = sig_data
                high = current_candle['high']
                low = current_candle['low']
                
                closed = False
                exit_price = 0
                reason = ""
                
                # Asumsi konservatif: SL kena duluan di candle yang sama
                if open_trade['side'] == 'LONG':
                    if low <= sl_price:
                        exit_price = sl_price
                        reason = "Stop Loss"
                        closed = True
                    elif high >= tp_price:
                        exit_price = tp_price
                        reason = "Take Profit"
                        closed = True
                elif open_trade['side'] == 'SHORT':
                    if high >= sl_price:
                        exit_price = sl_price
                        reason = "Stop Loss"
                        closed = True
                    elif low <= tp_price:
                        exit_price = tp_price
                        reason = "Take Profit"
                        closed = True
                        
                if closed:
                    # Tutup trade
                    trade_val = open_trade['quantity'] * exit_price
                    fee_close = trade_val * 0.0004
                    
                    if open_trade['side'] == 'LONG':
                        pnl = (open_trade['quantity'] * exit_price) - (open_trade['quantity'] * open_trade['entry_price']) - fee_close
                    else:
                        pnl = (open_trade['quantity'] * open_trade['entry_price']) - (open_trade['quantity'] * exit_price) - fee_close
                        
                    db.close_trade(open_trade['id'], exit_price, pnl, fee_close, datetime.now().isoformat())
                    
                    # Update Balance
                    current_bal = db.get_balance()
                    new_bal = current_bal + pnl
                    db.update_balance(new_bal)
                    
                    # Notifikasi
                    open_trade['exit_price'] = exit_price
                    open_trade['pnl'] = pnl
                    notifier.notify_exit(open_trade, reason, new_bal)
            return

        # 3. Cari Sinyal Baru
        df = indicators.apply_all(df)
        df_daily = indicators.apply_all(df_daily)
        
        signal = engine.generate_combined_signal(df, df_daily, symbol)
        current_time = datetime.now().isoformat()
        
        if signal:
            if signal['confidence'] >= threshold:
                print(f"  → Found Signal: {signal['type']} {symbol} (Confidence: {signal['confidence']}%)")
                
                # CATAT KE LOG: SINYAL DITERIMA
                db.log_bot_decision(
                    current_time, symbol, 'SIGNAL_FOUND', 
                    f"Executed {signal['type']}. Reasons: {json.dumps(signal['signals'])}", 
                    signal['confidence']
                )

                # Simpan signal
                signal_id = db.save_signal(signal)
                
                # Kalkulasi Slippage, Fee, Position Sizing
                entry_signal = signal['price']
                side = signal['type']
                
                if side == 'LONG':
                    actual_entry = entry_signal + (entry_signal * 0.0005)
                else:
                    actual_entry = entry_signal - (entry_signal * 0.0005)
                    
                balance = db.get_balance()
                risk_usd = balance * 0.01
                sl_dist = abs(actual_entry - signal['sl_price'])
                sl_pct = sl_dist / actual_entry
                
                # Sizing
                pos_size_usd = risk_usd / sl_pct if sl_pct > 0 else 0
                if pos_size_usd > balance * 5:
                    pos_size_usd = balance * 5
                    
                quantity = pos_size_usd / actual_entry
                fee_open = pos_size_usd * 0.0004
                
                # Update balance after open fee
                db.update_balance(balance - fee_open)
                
                # Buka Trade
                db.open_trade(signal_id, symbol, side, actual_entry, quantity, fee_open, datetime.now().isoformat())
                
                # Notif
                notifier.notify_entry(signal)
            else:
                print(f"  → Signal too weak for {symbol}: {signal['confidence']}% < {threshold}%")
                db.log_bot_decision(
                    current_time, symbol, 'NO_SIGNAL', 
                    f"Signal found but confidence {signal['confidence']}% < Threshold {threshold}%", 
                    signal['confidence']
                )
            
        else:
            print(f"  → No signal for {symbol}")
            # CATAT KE LOG: TIDAK ADA SETUP SAMA SEKALI
            db.log_bot_decision(
                current_time, symbol, 'NO_SIGNAL', 
                'No valid setup match (Filtered by Trend/Volume/Zone)', 
                0
            )
            
    except Exception as e:
        print(f"❌ Error processing {symbol}: {e}")

def run_all_live():
    load_dotenv(override=True)  # Pick up .env changes from Dashboard threshold slider
    threshold = int(os.environ.get('CONFIDENCE_THRESHOLD', 40))
    
    print(f"\n⏰ Running LIVE PAPER TRADING @ {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"💰 Current Virtual Balance: ${db.get_balance():,.2f}")
    print(f"🎯 Confidence Threshold: {threshold}%")
    print("=" * 50)
    
    # Massive Scanner: Fetch top high-volume coins dynamically
    symbols_to_scan = fetcher.get_active_futures_symbols(min_volume_usd=5_000_000)
    
    for symbol in symbols_to_scan:
        run_paper_trading(symbol, threshold)

def run_backtest():
    print("\n📊 Running Backtest...")
    bt = Backtester(initial_capital=config.INITIAL_CAPITAL)
    for symbol in config.SYMBOLS:
        print(f"\n--- {symbol} ---")
        df = fetcher.get_ohlcv(symbol, config.TIMEFRAME, limit=1000)
        df_daily = fetcher.get_ohlcv(symbol, '1d', limit=200)
        if df.empty or df_daily.empty:
            continue
        df = indicators.apply_all(df)
        df_daily = indicators.apply_all(df_daily)
        bt.run(df, df_daily, engine.generate_combined_signal)

def sleep_until_next_hour():
    now = datetime.now()
    # Find next hour + 5 seconds for safety
    next_hour = (now + timedelta(hours=1)).replace(minute=0, second=5, microsecond=0)
    sleep_sec = (next_hour - now).total_seconds()
    if sleep_sec < 0:
        sleep_sec = 60 # fallback
    
    print(f"\n💤 Sleeping for {int(sleep_sec)} seconds until {next_hour.strftime('%H:%M:%S')}...")
    time.sleep(sleep_sec)

if __name__ == '__main__':
    # Baca mode dari environment variable, default ke '1' jika tidak diset
    mode = os.environ.get("MODE", "1")
    
    if mode == '2':
        print("\n📊 Running Backtest (Docker Mode)...")
        run_backtest()
    else:
        print("\n🚀 Paper Trading system started (Docker Mode)... (Ctrl+C to stop)")
        # First execution
        run_all_live()
        
        # Loop forever
        while True:
            sleep_until_next_hour()
            run_all_live()
