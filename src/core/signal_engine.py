import pandas as pd
from datetime import datetime

class SignalEngine:
    
    def __init__(self):
        self.signals = []

    def generate_combined_signal(self, df, df_daily=None, symbol='BTC/USDT'):
        last = df.iloc[-1]
        prev = df.iloc[-2]
        
        current_price = last['close']
        
        # ==========================================
        # PRE-FILTER: ANTI-RUGI
        # ==========================================
        # 1. Volume Filter
        is_volume_strong = last['volume'] > last.get('volume_sma', 0)
        if not is_volume_strong:
            return None
            
        # 2. No Trade Zone (EMA 9 & EMA 21 terlalu dekat)
        ema_9 = last.get('ema_9', 0)
        ema_21 = last.get('ema_21', 0)
        if ema_9 == 0 or ema_21 == 0:
            return None
            
        ema_diff_pct = abs(ema_9 - ema_21) / current_price
        if ema_diff_pct < 0.001:  # Selisih kurang dari 0.1%, pasar sideways
            return None
            
        # ==========================================
        # EVALUASI SETUP (LONG / SHORT)
        # ==========================================
        is_uptrend = current_price > last.get('ema_50', 0)
        is_downtrend = current_price < last.get('ema_50', 0)
        
        rsi = last.get('rsi', 50)
        macd_hist = last.get('macd_histogram', 0)
        prev_macd_hist = prev.get('macd_histogram', 0)
        bb_lower = last.get('bb_lower', 0)
        bb_upper = last.get('bb_upper', float('inf'))
        
        active_signals = []
        setup_type = ""
        
        # --- Setup A: Trend Continuation ---
        if is_uptrend and (35 <= rsi <= 45) and (prev_macd_hist < 0 and macd_hist < 0 and macd_hist > prev_macd_hist):
            active_signals.append({'type': 'LONG', 'reason': 'Trend Continuation (Pullback)', 'strength': 'STRONG'})
            setup_type = "Trend Continuation"
            
        if is_downtrend and (55 <= rsi <= 65) and (prev_macd_hist > 0 and macd_hist > 0 and macd_hist < prev_macd_hist):
            active_signals.append({'type': 'SHORT', 'reason': 'Trend Continuation (Bounce)', 'strength': 'STRONG'})
            setup_type = "Trend Continuation"
            
        # --- Setup B: Extreme Reversal ---
        if current_price <= bb_lower and rsi < 25:
            active_signals.append({'type': 'LONG', 'reason': 'Extreme Reversal (Oversold)', 'strength': 'STRONG'})
            setup_type = "Extreme Reversal"
            
        if current_price >= bb_upper and rsi > 75:
            active_signals.append({'type': 'SHORT', 'reason': 'Extreme Reversal (Overbought)', 'strength': 'STRONG'})
            setup_type = "Extreme Reversal"

        if not active_signals:
            return None
            
        long_count = sum(1 for s in active_signals if s['type'] == 'LONG')
        short_count = sum(1 for s in active_signals if s['type'] == 'SHORT')
        
        if long_count > 0 and short_count == 0:
            signal_type = 'LONG'
        elif short_count > 0 and long_count == 0:
            signal_type = 'SHORT'
        else:
            return None # Conflicting signals
            
        # ==========================================
        # MANAJEMEN RISIKO (DYNAMIC SL & TP)
        # ==========================================
        atr_value = last.get('atr', pd.NA)
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
            'confidence': 100, # Di Futures V2, if rule met = confidence high
            'price': current_price,
            'setup': setup_type,
            'signals': active_signals,
            'sl_price': round(sl_price, 4),
            'tp_price': round(tp_price, 4),
            'sl_pct': round(sl_pct * 100, 2),
            'tp_pct': round(tp_pct * 100, 2),
            'rr_ratio': 1.5,
            'timestamp': datetime.now().isoformat(),
        }
