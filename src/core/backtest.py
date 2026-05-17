import pandas as pd
import sqlite3

class Backtester:
    def __init__(self, initial_capital=10000, fee_pct=0.0004, db_path='data/backtest_log.db'): # 0.04% taker fee Binance Futures
        self.initial_capital = initial_capital
        self.fee_pct = fee_pct
        self.max_risk_pct = 0.01 # 1% risk per trade
        self.leverage = 5
        self.db_path = db_path
        self._init_db()
        
    def _init_db(self):
        """Bersihkan dan buat tabel baru setiap kali backtest berjalan"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # WIPE DATA LAMA
        cursor.execute("DROP TABLE IF EXISTS backtest_trades")
        
        # BUAT TABEL BARU
        cursor.execute("""
            CREATE TABLE backtest_trades (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT,
                side TEXT,
                entry_time DATETIME,
                entry_price REAL,
                exit_time DATETIME,
                exit_price REAL,
                exit_reason TEXT,
                quantity REAL,
                fee REAL,
                pnl REAL,
                pnl_pct REAL,
                running_balance REAL
            )
        """)
        conn.commit()
        conn.close()
    
    def run(self, df, df_daily, signal_func):
        """Jalankan backtest pada data historis futures"""
        capital = self.initial_capital
        position_size = 0 # in base currency
        entry_price = 0
        sl_price = 0
        tp_price = 0
        position_type = None # 'LONG' or 'SHORT'
        entry_time = None
        symbol = None
        fee_open = 0
        
        trades = []
        peak_capital = self.initial_capital
        max_drawdown = 0
        
        gross_profit = 0
        gross_loss = 0
        
        consecutive_losses = 0
        max_consecutive_losses = 0
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        for i in range(200, len(df)):
            current_row = df.iloc[i]
            current_time = current_row.name
            current_high = current_row['high']
            current_low = current_row['low']
            current_close = current_row['close']
            
            # Update peak capital and DD
            if position_size > 0:
                if position_type == 'LONG':
                    unrealized_pnl = position_size * (current_close - entry_price)
                else:
                    unrealized_pnl = position_size * (entry_price - current_close)
                    
                current_value = capital + unrealized_pnl
            else:
                current_value = capital
                
            if current_value > peak_capital:
                peak_capital = current_value
            dd = (peak_capital - current_value) / peak_capital
            if dd > max_drawdown:
                max_drawdown = dd
                
            # Check TP/SL if position is open
            if position_size > 0:
                closed = False
                exit_price = 0
                reason = ''
                
                if position_type == 'LONG':
                    if current_low <= sl_price:
                        exit_price = sl_price
                        reason = 'Stop Loss'
                        closed = True
                    elif current_high >= tp_price:
                        exit_price = tp_price
                        reason = 'Take Profit'
                        closed = True
                elif position_type == 'SHORT':
                    if current_high >= sl_price:
                        exit_price = sl_price
                        reason = 'Stop Loss'
                        closed = True
                    elif current_low <= tp_price:
                        exit_price = tp_price
                        reason = 'Take Profit'
                        closed = True
                        
                if closed:
                    trade_val = position_size * exit_price
                    fee_close = trade_val * self.fee_pct
                    total_fee = fee_open + fee_close
                    
                    if position_type == 'LONG':
                        gross_pnl = (position_size * exit_price) - (position_size * entry_price)
                    else:
                        gross_pnl = (position_size * entry_price) - (position_size * exit_price)
                        
                    profit = gross_pnl - fee_close
                    capital += profit
                    
                    if profit > 0:
                        gross_profit += profit
                        consecutive_losses = 0
                    else:
                        gross_loss += abs(profit)
                        consecutive_losses += 1
                        if consecutive_losses > max_consecutive_losses:
                            max_consecutive_losses = consecutive_losses
                            
                    pnl_pct = (profit / (position_size * entry_price)) * 100
                    
                    # LOG TO DATABASE
                    cursor.execute("""
                        INSERT INTO backtest_trades 
                        (symbol, side, entry_time, entry_price, exit_time, exit_price, exit_reason, quantity, fee, pnl, pnl_pct, running_balance)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (symbol, position_type, str(entry_time), entry_price, str(current_time), exit_price, reason, position_size, total_fee, profit, pnl_pct, capital))
                    conn.commit()
                            
                    trades.append({
                        'type': position_type, 
                        'exit_price': exit_price, 
                        'reason': reason, 
                        'profit': profit, 
                        'index': i
                    })
                    
                    position_size = 0
                    position_type = None
                    fee_open = 0
                    
                continue # Skip checking signals if we just closed or still hold
            
            # Check for new signals
            window = df.iloc[:i+1].copy()
            window_daily = df_daily[df_daily.index <= current_time].copy() if df_daily is not None else None
            
            signal = signal_func(window, window_daily)
            
            if signal is None:
                continue
                
            # Position Sizing Logic
            risk_usd = capital * self.max_risk_pct
            sl_pct = signal['sl_pct'] / 100
            
            # Size in USD = Risk_USD / SL_PCT
            pos_size_usd = risk_usd / sl_pct if sl_pct > 0 else 0
            
            # Check leverage limits
            max_pos_usd = capital * self.leverage
            if pos_size_usd > max_pos_usd:
                pos_size_usd = max_pos_usd
                
            if pos_size_usd > 0:
                entry_price = current_close
                position_size = pos_size_usd / entry_price
                
                # Deduct open fee
                fee_open = pos_size_usd * self.fee_pct
                capital -= fee_open
                
                position_type = signal['type']
                sl_price = signal['sl_price']
                tp_price = signal['tp_price']
                entry_time = current_time
                symbol = signal['symbol']
                
        conn.close()
                
        # Final calculations
        pnl = capital - self.initial_capital
        pnl_pct = (pnl / self.initial_capital) * 100
        
        wins = len([t for t in trades if t.get('profit', 0) > 0])
        total_trades = len(trades)
        win_rate = (wins / total_trades * 100) if total_trades > 0 else 0
        profit_factor = (gross_profit / gross_loss) if gross_loss > 0 else float('inf')
        
        expectancy = pnl / total_trades if total_trades > 0 else 0
        
        print(f"""
╔══════════════════════════════╗
║     FUTURES BACKTEST         ║
╠══════════════════════════════╣
║ Initial:  ${self.initial_capital:>10,.2f}    ║
║ Final:    ${capital:>10,.2f}      ║
║ PnL:      ${pnl:>+10,.2f}      ║
║ PnL %:    {pnl_pct:>+9.2f}%      ║
║ Max DD:   {max_drawdown*100:>9.2f}%      ║
║ Trades:   {total_trades:>10}        ║
║ Win Rate: {win_rate:>9.1f}%      ║
║ PF:       {profit_factor:>10.2f}        ║
║ Expectancy:${expectancy:>9.2f}        ║
║ Max Cons. Loss: {max_consecutive_losses:>4}         ║
╚══════════════════════════════╝
""")
        return trades, pnl_pct, win_rate
