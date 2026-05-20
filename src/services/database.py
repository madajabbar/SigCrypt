import sqlite3
import json
from datetime import datetime

class Database:
    def __init__(self, db_name='data/trading_log.db'):
        self.conn = sqlite3.connect(db_name, check_same_thread=False)
        self.create_tables()
        
    def create_tables(self):
        cursor = self.conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS signals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME,
                symbol TEXT,
                side TEXT,
                confidence REAL,
                entry_price REAL,
                sl_price REAL,
                tp_price REAL,
                reasons TEXT
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS trades (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                signal_id INTEGER,
                symbol TEXT,
                status TEXT,
                side TEXT,
                entry_price REAL,
                exit_price REAL,
                quantity REAL,
                pnl REAL,
                fee REAL,
                open_time DATETIME,
                close_time DATETIME
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS balance (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                virtual_balance REAL
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS bot_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME,
                symbol TEXT,
                decision TEXT,
                reason TEXT,
                confidence REAL
            )
        ''')
        self.conn.commit()
        
        # Initialize balance if empty
        cursor.execute('SELECT virtual_balance FROM balance ORDER BY id DESC LIMIT 1')
        res = cursor.fetchone()
        if not res:
            cursor.execute('INSERT INTO balance (virtual_balance) VALUES (?)', (10000.0,))
            self.conn.commit()

    def get_balance(self):
        cursor = self.conn.cursor()
        cursor.execute('SELECT virtual_balance FROM balance ORDER BY id DESC LIMIT 1')
        return cursor.fetchone()[0]
        
    def update_balance(self, new_balance):
        cursor = self.conn.cursor()
        cursor.execute('INSERT INTO balance (virtual_balance) VALUES (?)', (new_balance,))
        self.conn.commit()

    def save_signal(self, signal):
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT INTO signals (timestamp, symbol, side, confidence, entry_price, sl_price, tp_price, reasons)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            signal['timestamp'], signal['symbol'], signal['type'], signal['confidence'],
            signal['price'], signal['sl_price'], signal['tp_price'], json.dumps(signal['signals'])
        ))
        self.conn.commit()
        return cursor.lastrowid
        
    def get_open_trade(self, symbol):
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM trades WHERE symbol = ? AND status = "OPEN"', (symbol,))
        row = cursor.fetchone()
        if row:
            columns = [column[0] for column in cursor.description]
            return dict(zip(columns, row))
        return None

    def open_trade(self, signal_id, symbol, side, entry_price, quantity, fee, open_time):
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT INTO trades (signal_id, symbol, status, side, entry_price, quantity, pnl, fee, open_time)
            VALUES (?, ?, "OPEN", ?, ?, ?, 0.0, ?, ?)
        ''', (signal_id, symbol, side, entry_price, quantity, fee, open_time))
        self.conn.commit()
        
    def close_trade(self, trade_id, exit_price, pnl, fee_close, close_time):
        cursor = self.conn.cursor()
        cursor.execute('''
            UPDATE trades 
            SET status = "CLOSED", exit_price = ?, pnl = ?, fee = fee + ?, close_time = ?
            WHERE id = ?
        ''', (exit_price, pnl, fee_close, close_time, trade_id))
        self.conn.commit()

    def log_bot_decision(self, timestamp, symbol, decision, reason, confidence):
        """Catat alasan keputusan bot setiap jam"""
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO bot_logs (timestamp, symbol, decision, reason, confidence)
            VALUES (?, ?, ?, ?, ?)
        """, (timestamp, symbol, decision, reason, confidence))
        self.conn.commit()
