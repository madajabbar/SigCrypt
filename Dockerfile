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
