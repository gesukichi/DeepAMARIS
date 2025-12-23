FROM python:3.10-slim

WORKDIR /app

# 依存関係のコピーとインストール
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# アプリケーションファイルのコピー
COPY app.py .
COPY config/ ./config/
COPY common/ ./common/
COPY backend/ ./backend/
COPY domain/ ./domain/
COPY static/ ./static/

# ポート8000を公開
EXPOSE 8000

# アプリケーション起動
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--workers", "1", "--timeout", "600", "app:app"]
