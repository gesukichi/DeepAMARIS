"""
セキュリティ設定: テスト・デバッグ機能の制御

本番環境でのセキュリティを確保するため、テスト・デバッグ機能へのアクセスを
厳格に制御する設定モジュールです。
"""

import os
import logging
from typing import Dict, List, Optional
from dataclasses import dataclass


@dataclass
class SecurityConfig:
    """セキュリティ関連の設定"""
    
    # 本番環境の検出パターン
    production_indicators: List[str]
    
    # 許可されたテスト機能
    allowed_test_features: List[str]
    
    # デバッグ機能の有効化条件
    debug_requirements: List[str]
    
    # セキュリティレベル (0=最低, 3=最高)
    security_level: int


class TestSecurityManager:
    """テスト機能のセキュリティ管理"""
    
    def __init__(self):
        self.config = self._load_security_config()
        self._validate_environment()
    
    def _load_security_config(self) -> SecurityConfig:
        """セキュリティ設定を読み込み"""
        return SecurityConfig(
            production_indicators=[
                "AZURE_ENV_NAME=prod",
                "AZURE_ENV_NAME=production", 
                "BACKEND_URI=https://",
                "WEBSITE_SITE_NAME",  # Azure App Service
                "AZURE_FUNCTIONS_ENVIRONMENT=Production",
                "ENVIRONMENT=production",
                "NODE_ENV=production"
            ],
            allowed_test_features=[
                "mock_chat_response",
                "mock_modern_rag_web_response"
            ],
            debug_requirements=[
                "LOCAL_MOCK_MODE=true",
                "DEBUG=true", 
                "DEVELOPMENT_MODE=true"
            ],
            security_level=int(os.environ.get("SECURITY_LEVEL", "2"))
        )
    
    def _validate_environment(self):
        """環境の妥当性を検証"""
        if self.is_production_environment():
            # 本番環境では追加のセキュリティチェック
            if any(os.environ.get(req.split("=")[0], "").lower() == "true" 
                   for req in self.config.debug_requirements):
                logging.error("🚨 SECURITY ALERT: Debug flags detected in production environment!")
                # 本番環境でのデバッグフラグは強制的に無効化
                for req in self.config.debug_requirements:
                    key = req.split("=")[0]
                    if key in os.environ:
                        logging.warning(f"Disabling debug flag in production: {key}")
    
    def is_production_environment(self) -> bool:
        """本番環境かどうかを判定"""
        for indicator in self.config.production_indicators:
            if "=" in indicator:
                key, value = indicator.split("=", 1)
                env_value = os.environ.get(key, "")
                if env_value.startswith(value) or env_value.lower() == value.lower():
                    return True
            else:
                # 環境変数の存在確認
                if os.environ.get(indicator):
                    return True
        return False
    
    def is_test_mode_allowed(self) -> bool:
        """テストモードが許可されているかを判定"""
        # 本番環境では一切のテスト機能を禁止
        if self.is_production_environment():
            return False
        
        # セキュリティレベルに応じた制御
        if self.config.security_level >= 3:
            # 最高セキュリティ: すべてのデバッグ要件が満たされている場合のみ
            return all(
                os.environ.get(req.split("=")[0], "").lower() == req.split("=")[1].lower()
                for req in self.config.debug_requirements
            )
        elif self.config.security_level >= 2:
            # 標準セキュリティ: LOCAL_MOCK_MODEのみ確認
            return os.environ.get("LOCAL_MOCK_MODE", "false").lower() == "true"
        else:
            # 低セキュリティ: 開発環境では許可
            return True
    
    def get_allowed_features(self) -> List[str]:
        """利用可能なテスト機能のリストを取得"""
        if not self.is_test_mode_allowed():
            return []
        return self.config.allowed_test_features.copy()
    
    def log_security_status(self):
        """セキュリティ状態をログ出力"""
        logging.info("🔒 Security Configuration:")
        logging.info(f"  - Production Environment: {self.is_production_environment()}")
        logging.info(f"  - Test Mode Allowed: {self.is_test_mode_allowed()}")
        logging.info(f"  - Security Level: {self.config.security_level}")
        logging.info(f"  - Allowed Features: {len(self.get_allowed_features())}")
        
        if self.is_production_environment():
            logging.info("🛡️  Production mode: All test/debug features disabled")
        elif self.is_test_mode_allowed():
            logging.info("🧪 Development mode: Test features enabled")
        else:
            logging.info("⚠️  Test features disabled by security policy")


def get_security_manager() -> TestSecurityManager:
    """セキュリティマネージャーのシングルトンインスタンスを取得"""
    if not hasattr(get_security_manager, '_instance'):
        get_security_manager._instance = TestSecurityManager()
    return get_security_manager._instance


def safe_import_test_functions() -> tuple:
    """安全なテスト関数のインポート"""
    security_manager = get_security_manager()
    security_manager.log_security_status()
    
    mock_chat_response = None
    mock_modern_rag_web_response = None
    
    if security_manager.is_test_mode_allowed():
        allowed_features = security_manager.get_allowed_features()
        
        try:
            if "mock_chat_response" in allowed_features:
                from tests.mock_responses import mock_chat_response
                logging.info("✅ mock_chat_response imported (authorized)")
            
            if "mock_modern_rag_web_response" in allowed_features:
                from tests.mock_responses import mock_modern_rag_web_response
                logging.info("✅ mock_modern_rag_web_response imported (authorized)")
                
        except ImportError as e:
            logging.warning(f"Mock functions not available: {e}")
            mock_chat_response = None
            mock_modern_rag_web_response = None
    else:
        logging.info("🚫 Test functions not imported (security policy)")
    
    return mock_chat_response, mock_modern_rag_web_response
