import pandas as pd
from datetime import datetime

class SignalEngine:

    def __init__(self):
        self.signals = []

    def trend_continuation_pullback_signal(self, df_5m, df_1h):
        """
        TCP (Trend Continuation Pullback) for 5m scalping.
        Entry on 5m pullback within 1H trend direction.
        """
        last_5m = df_5m.iloc[-1]
        prev_5m = df_5m.iloc[-2]
        last_1h = df_1h.iloc[-1]

        is_trend_up = last_1h['close'] > last_1h.get('ema_50', 0)
        is_trend_down = last_1h['close'] < last_1h.get('ema_50', 0)

        rsi = last_5m.get('rsi', 50)
        macd_now = last_5m.get('macd_histogram', 0)
        macd_prev = prev_5m.get('macd_histogram', 0)

        # LONG: Deep Pullback in uptrend (RSI 30-40)
        if is_trend_up and 30 <= rsi <= 40 and macd_now > macd_prev:
            return {'type': 'LONG', 'reason': 'TCP Deep Pullback (1H UP + 5m RSI 30-40 + MACD up)', 'strength': 'STRONG', 'confidence': 80}

        # LONG: Shallow Pullback in uptrend (RSI 40-50)
        if is_trend_up and 40 < rsi <= 50 and macd_now > macd_prev:
            return {'type': 'LONG', 'reason': 'TCP Shallow Pullback (1H UP + 5m RSI 40-50 + MACD up)', 'strength': 'MEDIUM', 'confidence': 65}

        # SHORT: Deep Pullback in downtrend (RSI 60-70)
        if is_trend_down and 60 <= rsi <= 70 and macd_now < macd_prev:
            return {'type': 'SHORT', 'reason': 'TCP Deep Pullback (1H DOWN + 5m RSI 60-70 + MACD down)', 'strength': 'STRONG', 'confidence': 80}

        # SHORT: Shallow Pullback in downtrend (RSI 50-60)
        if is_trend_down and 50 <= rsi < 60 and macd_now < macd_prev:
            return {'type': 'SHORT', 'reason': 'TCP Shallow Pullback (1H DOWN + 5m RSI 50-60 + MACD down)', 'strength': 'MEDIUM', 'confidence': 65}

        return None

    def ema_momentum_signal(self, df_5m, df_1h):
        """
        EMA Momentum on 5m - EMA9/21 crossover aligned with 1H trend.
        """
        last_5m = df_5m.iloc[-1]
        prev_5m = df_5m.iloc[-2]
        last_1h = df_1h.iloc[-1]

        is_trend_up = last_1h['close'] > last_1h.get('ema_50', 0)
        is_trend_down = last_1h['close'] < last_1h.get('ema_50', 0)

        ema9_now = last_5m.get('ema_9', 0)
        ema21_now = last_5m.get('ema_21', 0)
        ema9_prev = prev_5m.get('ema_9', 0)
        ema21_prev = prev_5m.get('ema_21', 0)

        # LONG: EMA9 crosses above EMA21 in uptrend
        if is_trend_up and ema9_prev <= ema21_prev and ema9_now > ema21_now:
            return {'type': 'LONG', 'reason': 'EMA Momentum (1H UP + 5m EMA9/21 bullish cross)', 'strength': 'MEDIUM', 'confidence': 60}

        # SHORT: EMA9 crosses below EMA21 in downtrend
        if is_trend_down and ema9_prev >= ema21_prev and ema9_now < ema21_now:
            return {'type': 'SHORT', 'reason': 'EMA Momentum (1H DOWN + 5m EMA9/21 bearish cross)', 'strength': 'MEDIUM', 'confidence': 60}

        return None

    def generate_combined_signal(self, df_5m, df_1h=None, symbol='BTC/USDT'):
        if df_1h is None or df_1h.empty:
            return None

        last_5m = df_5m.iloc[-1]
        current_price = last_5m['close']

        # Volume gate (70% of average)
        volume_sma = last_5m.get('volume_sma', 0)
        if volume_sma > 0 and last_5m['volume'] < volume_sma * 0.7:
            return None

        # ATR required for SL/TP
        atr_value = last_5m.get('atr', pd.NA)
        if pd.isna(atr_value):
            return None

        # No Trade Zone (sideways filter - only for TCP)
        ema_9 = last_5m.get('ema_9', 0)
        ema_21 = last_5m.get('ema_21', 0)
        sideways = False
        if ema_9 != 0 and ema_21 != 0:
            if abs(ema_9 - ema_21) / current_price < 0.001:
                sideways = True

        # Try setups in priority order
        signal = None

        if not sideways:
            signal = self.trend_continuation_pullback_signal(df_5m, df_1h)

        if not signal:
            signal = self.ema_momentum_signal(df_5m, df_1h)

        if not signal:
            return None

        signal_type = signal['type']
        confidence = signal.get('confidence', 70)
        strength = signal.get('strength', 'MEDIUM')

        # Scalping SL/TP: 5m ATR is small, so wider SL relative to ATR for safety
        # TP is close for frequent small wins
        if strength == 'STRONG':
            sl_dist = 3.0 * atr_value
            tp_dist = 2.0 * atr_value  # RR 0.67 — deep pullback, close TP for quick win
        else:
            sl_dist = 3.0 * atr_value
            tp_dist = 1.5 * atr_value  # RR 0.5 — shallow entry, very close TP for high WR

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
            'confidence': confidence,
            'price': current_price,
            'setup': signal['reason'],
            'signals': [signal],
            'sl_price': round(sl_price, 6),
            'tp_price': round(tp_price, 6),
            'sl_pct': round(sl_pct * 100, 2),
            'tp_pct': round(tp_pct * 100, 2),
            'rr_ratio': round(tp_dist / sl_dist, 1),
            'timestamp': datetime.now().isoformat(),
        }
