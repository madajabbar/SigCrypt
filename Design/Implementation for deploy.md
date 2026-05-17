Pindah dari lokal ke server (Debian Trixie) dengan Docker dan GitHub adalah langkah profesional. Namun, ada **1 tantangan utama** saat memasukkan aplikasi interaktif (yang meminta input `Mode 1/2`) ke dalam Docker: Docker dirancang untuk proses yang berjalan otomatis di background (*detached*). Container Docker tidak suka ditunggu untuk mengetik inputan.

Oleh karena itu, kita akan merubah sedikit pola pikir eksekusinya: **Mode akan ditentukan via Environment Variable (`.env`), bukan via `input()` di terminal.**

Berikut adalah panduan lengkap step-by-step untuk deploy SigCrypt:

---

### Langkah 1: Penyesuaian Kode untuk Docker (Wajib)

Ubah bagian penerima mode di file **`app.py`** Anda. Ganti dari `input()` menjadi membaca variabel environment.

```python
import os
# ... import modul lainnya ...

if __name__ == '__main__':
    # Baca mode dari environment variable, default ke '1' jika tidak diset
    mode = os.environ.get("MODE", "1") 
    
    if mode == '2':
        print("📊 Running Backtest (Docker Mode)...")
        run_backtest()
    else:
        print("🚀 Starting Live Paper Trading Daemon (Docker Mode)...")
        run_live()
```

---

### Langkah 2: Siapkan File-file Docker

Buat 3 file baru di **akar direktori (root)** proyek Anda (sejajar dengan `app.py`).

#### 1. `Dockerfile`
Ini adalah cetak biru (blueprint) untuk membangun lingkungan Linux mini Anda.
```dockerfile
# Gunakan Python 3.11 slim (Ringan dan sangat stabil untuk Data Science)
FROM python:3.11-slim

# Set timezone agar cocok dengan waktu server exchange (UTC sangat disarankan)
ENV TZ=UTC

# Set working directory di dalam container
WORKDIR /app

# Salin requirements.txt terlebih dahulu (Untuk caching Docker yang efisien)
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Salin seluruh kode proyek ke dalam container
COPY . .

# Buat folder data jika belum ada (untuk SQLite)
RUN mkdir -p data

# Perintah default saat container berjalan
CMD ["python", "app.py"]
```

#### 2. `docker-compose.yml`
File ini memudahkan Anda mengatur environment variable dan penyimpanan data (Volume) tanpa perintah Docker yang panjang.
```yaml
version: '3.8'

services:
  sigcrypt-bot:
    build: .
    container_name: sigcrypt_engine
    restart: unless-stopped # Otomatis hidup lagi kalau server reboot atau bot crash
    env_file:
      - .env               # Load API keys dan Mode dari file .env
    volumes:
      - ./data:/app/data   # PENTING: Simpan DB di luar container agar tidak hilang saat update
```

#### 3. `.gitignore`
Wajib ditambahkan sebelum push ke GitHub agar data rahasia dan database tidak bocor ke internet.
```text
# Environment variables (RAHASIA!)
.env

# Database files (Jangan masukkan DB ke GitHub)
data/*.db

# Python cache
__pycache__/
*.pyc
*.pyo
env/
venv/

# Docker local data
.docker/
```

---

### Langkah 3: Push ke GitHub

Jalankan perintah ini di terminal lokal Anda (pastikan Anda sudah buat repo kosong di GitHub):

```bash
git init
git add .
git commit -m "Initial commit: SigCrypt V3 ready for Docker"
git branch -M main
git remote add origin https://github.com/USERNAME_ANDA/SigCrypt.git
git push -u origin main
```

---

### Langkah 4: Setup di Server Debian Trixie

Sekarang kita pindah ke terminal server Anda (via SSH).

**1. Install Docker & Docker Compose (Jika belum ada):**
```bash
sudo apt update
sudo apt install docker.io docker-compose -y
# Pastikan user Anda bisa menjalankan docker tanpa sudo (opsional tapi recommended)
sudo usermod -aG docker $USER
# Log out dan log in lagi SSH agar group user terupdate
```

**2. Clone Repo dari GitHub:**
```bash
git clone https://github.com/USERNAME_ANDA/SigCrypt.git
cd SigCrypt
```

**3. Buat Folder Data dan File `.env`:**
```bash
# Buat folder data agar Docker bisa mapping volume
mkdir -p data

# Buat file .env
nano .env
```

Isi file `.env` di server dengan ini (Perhatikan penambahan variabel `MODE`):
```env
# Pilih "1" untuk Live Paper Trading, atau "2" untuk Backtest
MODE=1

TELEGRAM_BOT_TOKEN="123456789:ABCDefghIJKlmnOPQRstuVWXYZ"
TELEGRAM_CHAT_ID="987654321"

BINANCE_API_KEY=""
BINANCE_SECRET_KEY=""
```
*(Tekan `Ctrl+X`, lalu `Y`, lalu `Enter` untuk save di Nano).*

---

### Langkah 5: Menjalankan Bot di Server

Sekarang saatnya keajaiban Docker!

**Untuk menjalankan Live Paper Trading (Mode 1):**
Pastikan di `.env` tertulis `MODE=1`. Lalu jalankan:
```bash
docker-compose up -d --build
```
*(Flag `-d` artinya detached, berjalan di background. Flag `--build` memastikan Docker membangun image terbaru dari kode Anda).*

**Untuk menjalankan Backtest (Mode 2):**
Anda tidak perlu mengubah kode, cukup ubah `.env` menjadi `MODE=2`, lalu restart container:
```bash
# Ubah .env
nano .env 

# Restart dengan konfigurasi baru
docker-compose up -d --build
```

**Perintah Manajemen Sehari-hari:**
*   **Melihat Log (Penting!):** `docker-compose logs -f` (Tekan `Ctrl+C` untuk keluar dari layar log).
*   **Menghentikan Bot:** `docker-compose down`
*   **Restart Bot:** `docker-compose restart`

---

### 💡 Kenapa Arsitektur Ini Aman?

1.  **Data Persistence (Volume Mapping):** Baris `volumes: - ./data:/app/data` di `docker-compose.yml` adalah penyelamat Anda. Setiap kali Anda update kode (`git pull`) dan rebuild container, file `trading_log.db` tidak akan terhapus karena ia disimpan di folder fisik server Anda, bukan di dalam container yang bersifat sementara.
2.  **Auto-Restart:** Jika server Debian Anda tiba-tiba mati listrik atau reboot karena update sistem, Docker akan otomatis menjalankan bot SigCrypt kembali saat server hidup berkat `restart: unless-stopped`.
3.  **Keamanan API Key:** File `.env` tidak ikut terpush ke GitHub berkat `.gitignore`.