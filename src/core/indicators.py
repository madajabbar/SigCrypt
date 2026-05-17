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

    @staticmethod
    def atr(df, period=14):
        """Average True Range"""
        high_low = df['high'] - df['low']
        high_close = np.abs(df['high'] - df['close'].shift())
        low_close = np.abs(df['low'] - df['close'].shift())
        ranges = pd.concat([high_low, high_close, low_close], axis=1)
        true_range = np.max(ranges, axis=1)
        df['atr'] = true_range.rolling(period).mean()
        return df

    def apply_all(self, df):
        """Terapkan semua indikator"""
        df = self.rsi(df)
        df = self.macd(df)
        df = self.bollinger_bands(df)
        df = self.ema(df)
        df = self.volume_sma(df)
        df = self.atr(df)
        return df
