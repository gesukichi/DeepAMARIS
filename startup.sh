#!/bin/bash

# Azure App Service用起動スクリプト
echo "Starting Azure App Service application..."

# 環境変数の設定（デフォルトポート8000）
if [ -z "$PORT" ]; then
    export PORT=8000
fi

echo "Using PORT: $PORT"

# フロントエンドビルドをスキップ（事前ビルド済みを使用）
echo "Skipping frontend build - using pre-built assets"

# バックエンド起動
echo "Starting backend server..."
cd /home/site/wwwroot
python -m uvicorn app:app --host 0.0.0.0 --port $PORT --workers 4 --worker-class uvicorn.workers.UvicornWorker
