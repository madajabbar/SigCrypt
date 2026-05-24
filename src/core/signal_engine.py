import pandas as pd
from datetime import datetime

class SignalEngine:
    
    def __init__(self):
        self.signals = []

    def trend_continuation_pullback_signal(self, df_1h, df_1d):
        """
        Setup Satu-satunya yang akan kita pakai: TCP (Trend Continuation Pullback)
        Wajib searah tren harian, koreksi di 1H, lalu bouncing.
        """
        last_1h = df_1h.iloc[-1]
        prev_1h = df_1h.iloc[-2]
        
        # Cek tren 1 Hari (Kemarin harus tutup di atas/bawah EMA 50)
        last_1d = df_1d.iloc[-1]
        is_daily_uptrend = last_1d['close'] > last_1d.get('ema_50', 0)
        is_daily_downtrend = last_1d['close'] < last_1d.get('ema_50', 0)

        # ==========================================
        # LONG SETUP (Bullish Pullback)
        # ==========================================
        if is_daily_uptrend:
            # Syarat 1: RSI 1H mendekati oversold (koreksi sehat)
            if 35 <= last_1h.get('rsi', 50) <= 45:
                # Syarat 2: MACD histogram mulai memutih/memanjang ke atas (Bounce mulai)
                if prev_1h.get('macd_histogram', 0) < 0 and last_1h.get('macd_histogram', 0) > prev_1h.get('macd_histogram', 0):
                    return {
                        'type': 'LONG', 
                        'reason': 'Bullish TCP (Daily Uptrend + 1H RSI Pullback + MACD Bounce)',
                        'strength': 'STRONG'
                    }

        # ==========================================
        # SHORT SETUP (Bearish Pullback)
        # ==========================================
        if is_daily_downtrend:
            # Syarat 1: RSI 1H mendekati overbought (bounce sehat)
            if 55 <= last_1h.get('rsi', 50) <= 65:
                # Syarat 2: MACD histogram mulai memendek ke bawah (Penjual kembali menguasai)
                if prev_1h.get('macd_histogram', 0) > 0 and last_1h.get('macd_histogram', 0) < prev_1h.get('macd_histogram', 0):
                    return {
                        'type': 'SHORT', 
                        'reason': 'Bearish TCP (Daily Downtrend + 1H RSI Pullback + MACD Bounce)',
                        'strength': 'STRONG'
                    }

        # Jika tidak memenuhi syarat TCP, TIDAK ADA SINYAL
        return None

    def generate_combined_signal(self, df_1h, df_1d=None, symbol='BTC/USDT'):
        if df_1d is None or df_1d.empty:
            return None

        last_1h = df_1h.iloc[-1]
        current_price = last_1h['close']

        # Cek Volume (Wajib di atas rata-rata agar tidak masuk pasar sepi)
        if last_1h['volume'] < last_1h.get('volume_sma', 0):
            return None # Pasar sepi, batalkan
            
        # No Trade Zone (EMA 9 & EMA 21 terlalu dekat)
        ema_9 = last_1h.get('ema_9', 0)
        ema_21 = last_1h.get('ema_21', 0)
        if ema_9 != 0 and ema_21 != 0:
            ema_diff_pct = abs(ema_9 - ema_21) / current_price
            if ema_diff_pct < 0.001:  # Selisih kurang dari 0.1%, pasar sideways
                return None

        # Panggil satu-satunya setup yang valid
        signal = self.trend_continuation_pullback_signal(df_1h, df_1d)
        
        if not signal:
            return None
            
        signal_type = signal['type']
            
        # ==========================================
        # MANAJEMEN RISIKO (DYNAMIC SL & TP)
        # ==========================================
        atr_value = last_1h.get('atr', pd.NA)
        if pd.isna(atr_value):
            return None # Membutuhkan ATR untuk manajemen risiko
            
        sl_dist = 1.5 * atr_value
        
        # RR Ratio 1:1.5 minimum
        tp_dist = sl_dist * 1.5
        
        if signal_type == 'LONG':
            sl_price = current_price - sl_dist
            tp_price = current_price + tp_dist
        else:
            sl_price = current_price + sl_dist
            tp_price = current_price - tp_dist
            
        sl_pct = sl_dist / current_price
        tp_pct = tp_dist / current_price
        
        return {
            'symbol': symbol,
            'type': signal_type,
            'confidence': 85, # TCP super ketat
            'price': current_price,
            'setup': 'Trend Continuation Pullback',
            'signals': [signal],
            'sl_price': round(sl_price, 4),
            'tp_price': round(tp_price, 4),
            'sl_pct': round(sl_pct * 100, 2),
            'tp_pct': round(tp_pct * 100, 2),
            'rr_ratio': 1.5,
            'timestamp': datetime.now().isoformat(),
        }
