import requests
import json

class Notifier:
    def __init__(self, telegram_token=None, chat_id=None):
        self.telegram_token = telegram_token
        self.chat_id = chat_id
    
    def send_telegram(self, message):
        """Kirim sinyal ke Telegram"""
        if not self.telegram_token:
            print("[TELEGRAM] Token not set")
            return
        
        url = f"https://api.telegram.org/bot{self.telegram_token}/sendMessage"
        payload = {'chat_id': self.chat_id, 'text': message, 'parse_mode': 'HTML'}
        try:
            requests.post(url, json=payload)
        except Exception as e:
            print(f"[TELEGRAM] Error sending message: {e}")
            
    def notify_entry(self, signal):
        emoji = "📈" if signal['type'] == 'LONG' else "📉"
        
        reasons_list = signal.get('signals', [])
        if isinstance(reasons_list, str):
            try:
                reasons_list = json.loads(reasons_list)
            except:
                reasons_list = []
                
        reasons = "\n".join([f"• {s['reason']} ({s['strength']})" for s in reasons_list])
        
        msg = f"""
{emoji} <b>{signal['type']} SIGNAL</b>
━━━━━━━━━━━━━━━━━━━━
📌 <b>Pair:</b> {signal['symbol']}
💰 <b>Entry:</b> ${signal['price']:,.4f}
⚙️ <b>Leverage:</b> 5x (Isolated)
🛡 <b>SL:</b> ${signal.get('sl_price', 0):,.4f} | 🎯 <b>TP:</b> ${signal.get('tp_price', 0):,.4f}

📝 <b>Reasons:</b>
{reasons}
🟡 <b>STATUS: VIRTUAL TRADE OPENED</b>
"""
        self.send_telegram(msg)
        print(f"[ENTRY SIGNAL] {signal['type']} {signal['symbol']} @ ${signal['price']:,.4f}")

    def notify_exit(self, trade, reason_exit, balance):
        emoji = "✅" if reason_exit == "Take Profit" else "🛑"
        pnl_symbol = "+" if trade['pnl'] > 0 else ""
        
        msg = f"""
🏁 <b>TRADE CLOSED!</b>
━━━━━━━━━━━━━━━━━━━━
📌 <b>Pair:</b> {trade['symbol']}
<b>Side:</b> {trade['side']}
💸 <b>Exit Reason:</b> {emoji} {reason_exit}
📉 <b>Entry:</b> ${trade['entry_price']:,.4f} ➡️ <b>Exit:</b> ${trade['exit_price']:,.4f}
💰 <b>PnL:</b> {pnl_symbol}${trade['pnl']:,.2f}
📊 <b>Virtual Balance:</b> ${balance:,.2f}
"""
        self.send_telegram(msg)
        print(f"[EXIT] {trade['symbol']} closed. PnL: {pnl_symbol}${trade['pnl']:,.2f}")
