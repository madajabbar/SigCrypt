# 📄 DOKUMEN TEKNIS V2: CRYPTO FUTURES SIGNAL ENGINE (CFSE)
**Fokus:** High Probability Setup, Risk Management Ketat, Capital Preservation.
**Pasar:** USDT-M Perpetual Futures (Binance/Bybit)

---

## 1. Gambaran Umum
Sistem ini dirombak total dari versi Spot. Kini sistem mampu menghasilkan sinyal **LONG** dan **SHORT**. Inti filosofi V2 adalah: *Kita tidak mencari profit maksimal, kita mencari risiko minimal. Profit adalah byproduct dari pengelolaan risiko yang baik.*

---

## 2. Arsitektur Modul Tambahan

Selain modul sebelumnya, ditambahkan 1 modul krusial:
*   **Risk Management Engine:** Menghitung ukuran posisi (Position Sizing), Leverage aman, harga Liquidasi, dan dynamic Stop Loss sebelum trade dieksekusi.

---

## 3. Spesifikasi Indikator & Konsep Volatilitas (ATR)

Indikator RSI, MACD, EMA, BB tetap dipakai. Namun, ditambahkan indikator wajib untuk Futures:

| Nama Indikator | Parameter | Fungsi Utama di Futures |
|----------------|-----------|-------------------------|
| **ATR** (Average True Range) | period = 14 | **Wajib.** Mengukur volatilitas. Digunakan untuk menentukan seberapa jauh Stop Loss dipasang agar tidak tersentuh oleh noise pasar. |

---

## 4. Aturan Logika Sinyal (Long / Short)

Kita menggabungkan pelajaran dari backtest sebelumnya (ZEC butuh trend, BTC butuh reversal) menjadi **2 Tipe Setup**:

### Setup A: Trend Continuation (Sinyal dengan Win Rate Tinggi)
Mencari koin yang sudah trending kuat, lalu masuk saat ada *pullback* (koreksi kecil).
*   **LONG:** Harga di atas EMA 50 + Terjadi koreksi (RSI turun ke area 35-45) + MACD histogram mulai memerah pendek (momentum turun melemah).
*   **SHORT:** Harga di bawah EMA 50 + Terjadi bounce (RSI naik ke area 55-65) + MACD histogram mulai hijau pendek (momentum naik melemah).

### Setup B: Extreme Reversal (Mean-Reversion Aman)
Mencari koin yang sudah sangat jenuh beli/jual (overextended), hanya di area Support/Resistance ekstrem.
*   **LONG:** Harga menyentuh Lower Bollinger Band **DAN** RSI di bawah 25 (Oversold ekstrem).
*   **SHORT:** Harga menyentuh Upper Bollinger Band **DAN** RSI di atas 75 (Overbought ekstrem).

### Filter Anti-Rugi (Wajib):
*   **Volume Filter:** Volume candle *wajib* di atas Volume SMA 20. Tidak ada sinyal di pasar sepi.
*   **No Trade Zone:** Jika EMA 9 dan EMA 21 terlalu berdekatan (sapuan/cacing), sistem TIDAK BOLEH mengeluarkan sinyal karena pasar sedang sideways (rawan stop loss hunting).

---

## 5. Manajemen Risiko "Seaman Mungkin" (Inti V2)

Ini adalah aturan mutlak yang tidak boleh dilanggar oleh mesin backtest maupun live trading:

### 5.1. Aturan Leverage & Margin
*   **Leverage Maksimal:** 5x. (Lebih dari itu, harga tinggal sedikit bergerak langsung liquidasi).
*   **Jenis Margin:** Wajib **Isolated Margin**. Jika satu trade salah, hanya modal di posisi itu yang habis, tidak menggerus seluruh saldo akun.

### 5.2. Dynamic Stop Loss (ATR Stop Loss)
Stop Loss tidak lagi pakai persentase kaku (misal -3%). Stop Loss dihitung berdasarkan volatilitas (ATR).
*   **Rumus SL Long:** `Entry Price - (1.5 x ATR)`
*   **Rumus SL Short:** `Entry Price + (1.5 x ATR)`
*   *Logika:* Jika pasar sedang bergolak (ATR tinggi), SL dilebarkan agar tidak kena "spike" sesaat. Jika pasar tenang (ATR rendah), SL diperketat.

### 5.3. Position Sizing (Risk Per Trade)
*   **Maksimal Risiko Per Trade:** 1% dari Total Modal.
*   *Eksekusi Kode:* Jika SL terhitung berjarak 2% dari entry, maka ukuran posisi (quantity) otomatis diperkecil agar jika kena SL, kerugian tetap tepat 1% dari total saldo. Jangan pernah masuk full margin.

### 5.4. Risk:Reward Ratio (RR) Minimum
*   **RR Minimum Wajib:** 1 : 1.5
*   Jika jarak ke Stop Loss adalah $100, maka Take Profit *harus* minimal $150. Jika kondisi pasar tidak memungkinkan TP sejauh itu, **SINYAL DIBATALKAN (No Trade)**.

---

## 6. Spesifikasi Backtesting Engine V2

Backtest harus disesuaikan untuk mensimulasikan realita Futures.

*   **Modal Awal:** $10,000
*   **Biaya (Fee):** 0.04% per trade (Taker fee Binance Futures) dikali 2 (buka dan tutup).
*   **Risk Per Trade:** 1% ($100 per trade).
*   **Leverage Simulasi:** 5x Isolated.

### Alur Eksekusi Backtest:
1.  Cek sinyal LONG/SHORT.
2.  Jika ada, hitung jarak SL berdasarkan ATR.
3.  Cek apakah jarak TP (1.5x SL) memungkinkan. Jika tidak, skip.
4.  Hitung ukuran posisi (Quantity) berdasarkan risiko 1%.
5.  Eksekusi trade, potong biaya fee.
6.  Cek candle selanjutnya: Apakah High/Low menyentuh TP atau SL? (Prioritas TP di atas SL jika terjadi di candle yang sama).

### Output Metrik Tambahan yang Wajib:
*   **Expectancy:** Rata-rata dolar yang Anda harapkan per trade (contoh: +$15 per trade).
*   **Max Consecutive Loss:** Berapa kali kena SL berturut-turut (penting untuk persiapan mental).

---

## 7. Spesifikasi Notifikasi (Telegram)

Format pesan diubah total agar mencerminkan keamanan Futures:

```text
📈 LONG SIGNAL | 📉 SHORT SIGNAL
━━━━━━━━━━━━━━━━━━━━
📌 Pair: {Symbol} (Perpetual)
💰 Entry: ${Price}
⚙️ Leverage: 5x (Isolated)

🛡 Stop Loss: ${SL_Price} (-{SL_pct}%)
🎯 Take Profit: ${TP_Price} (+{TP_pct}%)
📊 Risk:Reward: 1:{RR_Ratio}

📝 Setup: {Trend_Continuation / Extreme_Reversal}
📝 Reasons:
• {Reason_1}
• {Reason_2}

⚠️ Max Risk 1% per trade. Bukan financial advice!
```
