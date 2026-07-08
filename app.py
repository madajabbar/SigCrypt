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
        print(f"\n🔍 [SCALP] Processing {symbol} (threshold={threshold})...")
        
        df_5m = fetcher.get_ohlcv(symbol, config.TIMEFRAME, limit=200)
        df_1h = fetcher.get_ohlcv(symbol, config.TREND_TIMEFRAME, limit=100)
        
        if df_5m.empty or df_1h.empty:
            print(f"  → Data empty for {symbol}")
            return
            
        current_candle = df_5m.iloc[-1]
        
        open_trade = db.get_open_trade(symbol)
        
        if open_trade:
            print(f"  → Found OPEN trade: {open_trade['side']} at {open_trade['entry_price']}")
            
            try:
                open_time = datetime.fromisoformat(open_trade['open_time'])
                minutes_open = (datetime.now() - open_time).total_seconds() / 60
            except (ValueError, TypeError):
                minutes_open = 0
            max_minutes = float(os.environ.get('MAX_TRADE_HOURS', 1)) * 60
            
            cursor = db.conn.cursor()
            cursor.execute('SELECT sl_price, tp_price FROM signals WHERE id = ?', (open_trade['signal_id'],))
            sig_data = cursor.fetchone()
            
            closed = False
            exit_price = 0
            reason = ""
            
            # Timeout
            if minutes_open >= max_minutes:
                exit_price = current_candle['close']
                reason = f"Timeout ({minutes_open:.0f}m >= {max_minutes:.0f}m)"
                closed = True
            
            # No SL/TP data (safety close)
            elif not sig_data:
                exit_price = current_candle['close']
                reason = "No SL/TP data (safety close)"
                closed = True
            
            # Normal SL/TP evaluation
            else:
                sl_price, tp_price = sig_data
                high = current_candle['high']
                low = current_candle['low']
                
                if open_trade['side'] == 'LONG':
                    if low <= sl_price:
                        exit_price = sl_price; reason = "Stop Loss"; closed = True
                    elif high >= tp_price:
                        exit_price = tp_price; reason = "Take Profit"; closed = True
                elif open_trade['side'] == 'SHORT':
                    if high >= sl_price:
                        exit_price = sl_price; reason = "Stop Loss"; closed = True
                    elif low <= tp_price:
                        exit_price = tp_price; reason = "Take Profit"; closed = True
            
            if closed:
                trade_val = open_trade['quantity'] * exit_price
                fee_close = trade_val * 0.0004
                
                if open_trade['side'] == 'LONG':
                    pnl = (open_trade['quantity'] * exit_price) - (open_trade['quantity'] * open_trade['entry_price']) - fee_close
                else:
                    pnl = (open_trade['quantity'] * open_trade['entry_price']) - (open_trade['quantity'] * exit_price) - fee_close
                    
                db.close_trade(open_trade['id'], exit_price, pnl, fee_close, datetime.now().isoformat())
                
                current_bal = db.get_balance()
                new_bal = current_bal + pnl
                db.update_balance(new_bal)
                
                open_trade['exit_price'] = exit_price
                open_trade['pnl'] = pnl
                notifier.notify_exit(open_trade, reason, new_bal)
            
            return

        # Search for new signal
        df_5m = indicators.apply_all(df_5m)
        df_1h = indicators.apply_all(df_1h)
        
        signal = engine.generate_combined_signal(df_5m, df_1h, symbol)
        current_time = datetime.now().isoformat()
        
        if signal:
            if signal['confidence'] >= threshold:
                print(f"  → Signal: {signal['type']} {symbol} conf={signal['confidence']}% setup={signal['setup'][:40]}")
                
                db.log_bot_decision(current_time, symbol, 'SIGNAL_FOUND', f"Executed {signal['type']}. {signal['setup']}", signal['confidence'])

                signal_id = db.save_signal(signal)
                
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
                
                pos_size_usd = risk_usd / sl_pct if sl_pct > 0 else 0
                if pos_size_usd > balance * 5:
                    pos_size_usd = balance * 5
                    
                quantity = pos_size_usd / actual_entry
                fee_open = pos_size_usd * 0.0004
                
                db.update_balance(balance - fee_open)
                db.open_trade(signal_id, symbol, side, actual_entry, quantity, fee_open, datetime.now().isoformat())
                notifier.notify_entry(signal)
            else:
                print(f"  → Signal too weak: {signal['confidence']}% < {threshold}%")
                db.log_bot_decision(current_time, symbol, 'NO_SIGNAL', f"Signal found but confidence {signal['confidence']}% < Threshold {threshold}%", signal['confidence'])
        else:
            print(f"  → No signal for {symbol}")
            db.log_bot_decision(current_time, symbol, 'NO_SIGNAL', 'No valid setup match', 0)
            
    except Exception as e:
        print(f"❌ Error processing {symbol}: {e}")

def run_all_live():
    load_dotenv(override=True)
    threshold = int(os.environ.get('CONFIDENCE_THRESHOLD', 40))
    scan_limit = int(os.environ.get('SCAN_LIMIT', '30'))
    
    print(f"\n⏰ SCALP SCAN @ {time.strftime('%Y-%m-%d %H:%M:%S')} | Balance: ${db.get_balance():,.2f} | Threshold: {threshold}%")
    print("=" * 50)
    
    all_symbols = fetcher.get_active_futures_symbols(min_volume_usd=5_000_000)
    symbols_to_scan = all_symbols[:scan_limit]
    print(f"🔍 Scanning {len(symbols_to_scan)} of {len(all_symbols)} pairs")
    
    for symbol in symbols_to_scan:
        run_paper_trading(symbol, threshold)

def sleep_until_next_cycle():
    cycle_min = int(os.environ.get('CYCLE_MINUTES', '5'))
    now = datetime.now()
    next_cycle = now + timedelta(minutes=cycle_min)
    next_cycle = next_cycle.replace(second=2, microsecond=0)
    sleep_sec = (next_cycle - now).total_seconds()
    if sleep_sec < 10:
        sleep_sec = cycle_min * 60
    
    print(f"\n💤 Sleeping {int(sleep_sec)}s until {next_cycle.strftime('%H:%M:%S')} (every {cycle_min}m)...")
    time.sleep(sleep_sec)

def run_backtest():
    print("\n📊 Running Backtest...")
    bt = Backtester(initial_capital=config.INITIAL_CAPITAL)
    for symbol in config.SYMBOLS[:10]:
        print(f"\n--- {symbol} ---")
        df_5m = fetcher.get_ohlcv(symbol, config.TIMEFRAME, limit=1000)
        df_1h = fetcher.get_ohlcv(symbol, config.TREND_TIMEFRAME, limit=200)
        if df_5m.empty or df_1h.empty:
            continue
        df_5m = indicators.apply_all(df_5m)
        df_1h = indicators.apply_all(df_1h)
        bt.run(df_5m, df_1h, engine.generate_combined_signal)

if __name__ == '__main__':
    mode = os.environ.get("MODE", "1")
    
    if mode == '2':
        print("\n📊 Running Backtest...")
        run_backtest()
    else:
        print(f"\n🚀 Scalping system started ({config.TIMEFRAME} entry + {config.TREND_TIMEFRAME} trend)... (Ctrl+C to stop)")
        run_all_live()
        
        while True:
            sleep_until_next_cycle()
            run_all_live()
