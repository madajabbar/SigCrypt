# 📄 DOKUMEN IMPLEMENTASI: SigCrypt Network Bypass & Resilience Update

**Versi:** V3.1
**Tanggal:** 24 Mei 2024
**Fokus:** Mitigasi pemblokiran API Binance oleh ISP (Internet Positif), Routing Docker via WARP, dan Hardcoding Alternate Endpoints.

## 1. Latar Belakang & Solusi Arsitektur

ISP (Internet Positif) melakukan pemblokiran terhadap domain utama Binance (`api.binance.com`) menggunakan teknik *Deep Packet Inspection (DPI)* yang memutuskan koneksi SSL dan menyuntikkan sertifikat palsu. 

Solusi yang diimplementasikan berlapis 2 (Defense in Depth):
1.  **Cloudflare WARP (Global Mode):** Terinstal di level OS Debian (Host). WARP mengenkripsi seluruh trafik keluar server, membuat DPI ISP buta sehingga tidak bisa mengidentifikasi dan memblokir domain Binance.
2.  **Docker Host Networking:** Agar container Docker (Bot & Dashboard) dapat menumpang koneksi WARP yang ada di Host OS, container harus berbagi *network namespace* dengan Host.
3.  **Binance Alternate Endpoints:** Sebagai lapisan ketahanan (resilience), CCXT diarahkan secara hardcode ke server cadangan Binance (`api3.binance.com`) yang jarang menjadi target utama pemblokiran.

---

## 2. Daftar File yang Diupdate

Anda perlu mengubah **3 file** di dalam proyek Anda:

1.  `docker-compose.yml`
2.  `src/core/data_fetcher.py`
3.  `dashboard.py`

---

## 3. Spesifikasi Perubahan Kode

### 3.1. Update `docker-compose.yml`

**Perubahan:** Menambahkan `network_mode: "host"` pada kedua service dan menghapus mapping port yang redundan.

**Kode Lengkap Baru:**
```yaml
services:
  sigcrypt-engine:
    build: 
      context: .
      dockerfile: Dockerfile
    container_name: sigcrypt_engine
    restart: unless-stopped
    env_file:
      - .env
    volumes:
      - ./data:/app/data
    network_mode: "host" # RUTEKAN TRAFIK MELALUI HOST OS (WARP)

  sigcrypt-dashboard:
    build:
      context: .
      dockerfile: Dockerfile.dashboard
    container_name: sigcrypt_dashboard
    restart: unless-stopped
    volumes:
      - ./data:/app/data
    network_mode: "host" # RUTEKAN TRAFIK MELALUI HOST OS (WARP)
    # Catatan: Baris "ports: - 8501:8501" DIHAPUS karena host networking 
    # langsung mengekspos port 8501 dari Streamlit ke internet.
```

---

### 3.2. Update `src/core/data_fetcher.py`

**Perubahan:** 
1. Menghapus konfigurasi proxy manual (karena sekarang ditangani OS/WARP).
2. Menambahkan `aiohttp_trust_env: True` untuk kompatibilitas jaringan Linux.
3. Mengarahkan CCXT ke endpoint cadangan Binance (`api3`).

**Ganti blok inisialisasi Exchange Anda dengan kode ini:**
```python
import os

class CryptoDataFetcher:
    def __init__(self, exchange_id='binance'):
        self.exchange = getattr(ccxt, exchange_id)({
            'enableRateLimit': True,
            'options': {
                'defaultType': 'future',
                'aiohttp_trust_env': True # Penting untuk routing di Docker/Linux
            },
            # Hardcode endpoint cadangan untuk menghindari 301 Redirect / Blokir ISP
            'urls': {
                'api': {
                    'public': 'https://api3.binance.com/api/v3',
                    'fapiPublic': 'https://fapi.binance.com/fapi/v1', # Endpoint Futures
                }
            }
        })
```
*(Catatan: Jika ada parameter `apiKey` dan `secret` di kode Anda, biarkan kosong/hapus untuk Paper Trading, karena data OHLCV publik tidak memerlukannya).*

---

### 3.3. Update `dashboard.py`

**Perubahan:** Sama seperti di atas, update inisialisasi CCXT pada bagian tombol "Manual Fetch" di halaman System Control.

**Cari bagian inisialisasi exchange di dalam blok `if st.button("🔄 Fetch Latest 100 Candles"):` dan ganti dengan:**
```python
exchange = ccxt.binance({
    'enableRateLimit': True,
    'options': {
        'defaultType': 'future',
        'aiohttp_trust_env': True
    },
    'urls': {
        'api': {
            'public': 'https://api3.binance.com/api/v3',
            'fapiPublic': 'https://fapi.binance.com/fapi/v1',
        }
    }
})
```

---

## 4. Langkah Deployment di Server

Setelah Anda melakukan perubahan kode di atas (lokal atau via SSH editor), ikuti prosedur deploy ini di terminal server Debian Anda:

### Step 1: Pastikan WARP Aktif di Server
```bash
warp-cli status
# Harus menunjukkan: Status: Connected | Mode: Warp
```
*(Jika belum, jalankan: `sudo warp-cli connect`)*

### Step 2: Pull Kode Terbaru (Jika Anda push via GitHub)
```bash
cd ~/Documents/SigCrypt
git pull origin main
```

### Step 3: Rebuild Docker dengan Konfigurasi Baru
Kita *musti* rebuild karena ada perubahan di `docker-compose.yml` (network mode).
```bash
docker compose down
docker compose up -d --build
```

### Step 4: Verifikasi Koneksi di Docker
Pastikan container Engine bisa menembus blokir:
```bash
docker exec sigcrypt_engine curl -I https://api.binance.com/api/v3/ping
```
*Jika outputnya `HTTP/2 200`, berarti Docker sudah berhasil merutekan trafik melalui WARP host!*

### Step 5: Verifikasi Dashboard
Buka browser di komputer lokal Anda dan akses:
`http://IP_SERVER_ANDA:8501`

Pergi ke halaman **⚙️ System Control**, lalu klik **"🔄 Fetch Latest 100 Candles"**. Data Binance seharusnya sudah berhasil masuk ke tabel tanpa error SSL.

--- 

*Dokumen ini menutup issue kritis terkait pemblokiran jaringan dan menetapkan standar keamanan routing untuk SigCrypt ke depannya.*