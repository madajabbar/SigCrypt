import pandas as pd
from datetime import datetime

class SignalEngine:

    def __init__(self):
        self.signals = []

    def trend_continuation_pullback_signal(self, df_1h, df_1d):
        """
        TCP (Trend Continuation Pullback) - Deep and Shallow variants.
        All entries are trend-continuation, NOT reversal.
        Wider RSI zones capture more pullback opportunities.
        """
        last_1h = df_1h.iloc[-1]
        prev_1h = df_1h.iloc[-2]
        last_1d = df_1d.iloc[-1]

        is_daily_uptrend = last_1d['close'] > last_1d.get('ema_50', 0)
        is_daily_downtrend = last_1d['close'] < last_1d.get('ema_50', 0)

        rsi = last_1h.get('rsi', 50)
        macd_hist_now = last_1h.get('macd_histogram', 0)
        macd_hist_prev = prev_1h.get('macd_histogram', 0)

        # LONG: Deep Pullback (RSI 30-40) - best entry, deep discount in uptrend
        if is_daily_uptrend and 30 <= rsi <= 40 and macd_hist_now > macd_hist_prev:
            return {
                'type': 'LONG',
                'reason': 'TCP Deep Pullback (Daily UP + RSI 30-40 + MACD turning up)',
                'strength': 'STRONG',
                'confidence': 80
            }

        # LONG: Shallow Pullback (RSI 40-50) - valid in strong trend, moderate discount
        if is_daily_uptrend and 40 < rsi <= 50 and macd_hist_now > macd_hist_prev:
            return {
                'type': 'LONG',
                'reason': 'TCP Shallow Pullback (Daily UP + RSI 40-50 + MACD turning up)',
                'strength': 'MEDIUM',
                'confidence': 65
            }

        # SHORT: Deep Pullback (RSI 60-70) - best entry, high premium in downtrend
        if is_daily_downtrend and 60 <= rsi <= 70 and macd_hist_now < macd_hist_prev:
            return {
                'type': 'SHORT',
                'reason': 'TCP Deep Pullback (Daily DOWN + RSI 60-70 + MACD turning down)',
                'strength': 'STRONG',
                'confidence': 80
            }

        # SHORT: Shallow Pullback (RSI 50-60) - valid in strong downtrend
        if is_daily_downtrend and 50 <= rsi < 60 and macd_hist_now < macd_hist_prev:
            return {
                'type': 'SHORT',
                'reason': 'TCP Shallow Pullback (Daily DOWN + RSI 50-60 + MACD turning down)',
                'strength': 'MEDIUM',
                'confidence': 65
            }

        return None

    def ema_momentum_signal(self, df_1h, df_1d):
        """
        EMA Momentum Acceleration - trend-continuation via EMA9/21 crossover.
        NOT a reversal signal. Requires daily trend alignment.
        Captures momentum acceleration after consolidation.
        """
        last_1h = df_1h.iloc[-1]
        prev_1h = df_1h.iloc[-2]
        last_1d = df_1d.iloc[-1]

        is_daily_uptrend = last_1d['close'] > last_1d.get('ema_50', 0)
        is_daily_downtrend = last_1d['close'] < last_1d.get('ema_50', 0)

        ema_9_now = last_1h.get('ema_9', 0)
        ema_21_now = last_1h.get('ema_21', 0)
        ema_9_prev = prev_1h.get('ema_9', 0)
        ema_21_prev = prev_1h.get('ema_21', 0)

        # LONG: EMA 9 crosses above EMA 21 in daily uptrend
        if is_daily_uptrend and ema_9_prev <= ema_21_prev and ema_9_now > ema_21_now:
            return {
                'type': 'LONG',
                'reason': 'EMA Momentum Acceleration (Daily UP + EMA9/21 bullish cross)',
                'strength': 'MEDIUM',
                'confidence': 60
            }

        # SHORT: EMA 9 crosses below EMA 21 in daily downtrend
        if is_daily_downtrend and ema_9_prev >= ema_21_prev and ema_9_now < ema_21_now:
            return {
                'type': 'SHORT',
                'reason': 'EMA Momentum Acceleration (Daily DOWN + EMA9/21 bearish cross)',
                'strength': 'MEDIUM',
                'confidence': 60
            }

        return None

    def generate_combined_signal(self, df_1h, df_1d=None, symbol='BTC/USDT'):
        if df_1d is None or df_1d.empty:
            return None

        last_1h = df_1h.iloc[-1]
        current_price = last_1h['close']

        # Volume gate (softened: allow 70% of average)
        volume_sma = last_1h.get('volume_sma', 0)
        if volume_sma > 0 and last_1h['volume'] < volume_sma * 0.7:
            return None

        # ATR required for SL/TP
        atr_value = last_1h.get('atr', pd.NA)
        if pd.isna(atr_value):
            return None

        # No Trade Zone (sideways filter - only for TCP, not EMA momentum)
        ema_9 = last_1h.get('ema_9', 0)
        ema_21 = last_1h.get('ema_21', 0)
        sideways = False
        if ema_9 != 0 and ema_21 != 0:
            ema_diff_pct = abs(ema_9 - ema_21) / current_price
            if ema_diff_pct < 0.001:
                sideways = True

        # Try setups in priority order
        signal = None

        # Setup 1: TCP (skip if sideways - pullback in sideways is unreliable)
        if not sideways:
            signal = self.trend_continuation_pullback_signal(df_1h, df_1d)

        # Setup 2: EMA Momentum (crossover itself breaks sideways - valid signal)
        if not signal:
            signal = self.ema_momentum_signal(df_1h, df_1d)

        if not signal:
            return None

        signal_type = signal['type']
        confidence = signal.get('confidence', 70)
        strength = signal.get('strength', 'MEDIUM')

        # SL/TP: Wide SL (3ATR) avoids getting stopped out by normal crypto swings
        # Close TP (2-2.5ATR) hits frequently → high win rate, small consistent profit
        if strength == 'STRONG':
            sl_dist = 3.0 * atr_value
            tp_dist = 2.5 * atr_value  # RR 0.83 — deep pullback bounces stronger
        else:
            sl_dist = 3.0 * atr_value
            tp_dist = 2.0 * atr_value  # RR 0.67 — shallow entry, closer TP for higher WR

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
            'sl_price': round(sl_price, 4),
            'tp_price': round(tp_price, 4),
            'sl_pct': round(sl_pct * 100, 2),
            'tp_pct': round(tp_pct * 100, 2),
            'rr_ratio': round(tp_dist / sl_dist, 1),
            'timestamp': datetime.now().isoformat(),
        }
