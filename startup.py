import sys
import os
import logging

# Pythonパスの設定（リファクタリング後の構造に対応）
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

# ログレベルを設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

try:
    # アプリケーションのインポート
    from app import app
    
    logger.info("Application imported successfully")
    logger.info(f"Python version: {sys.version}")
    logger.info(f"Working directory: {os.getcwd()}")
    logger.info(f"Environment variables: PORT={os.getenv('PORT', 'Not set')}")
    
    # アプリケーション起動
    if __name__ == "__main__":
        port = int(os.getenv("PORT", 8000))
        logger.info(f"Starting application on port {port}")
        app.run(host="0.0.0.0", port=port)
        
except ImportError as e:
    logger.error(f"Import error: {e}")
    sys.exit(1)
except Exception as e:
    logger.error(f"Application startup error: {e}")
    sys.exit(1)
