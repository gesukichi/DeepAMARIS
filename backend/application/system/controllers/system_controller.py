"""
Task 12: SystemController Implementation
TDD GREEN Phase: システム関連API制御の実装

移植機能:
1. get_frontend_settings() - フロントエンド設定取得（Key Vault統合）
2. healthz() - 軽量ヘルスチェック  
3. health_check() - 詳細ヘルスチェック

設計方針:
- 軽量実装: 必要最小限の機能
- 外部委託中程度: 明確で保守しやすいコード
- Key Vault統合: セキュアな設定管理
"""

import logging
from datetime import datetime
from typing import Dict, Any, Optional
import copy


class SystemController:
    """
    システム関連API制御のコントローラー
    
    責務:
    - フロントエンド設定の提供（Key Vault統合）
    - システムヘルスチェック（軽量/詳細）
    - システム設定の管理
    """
    
    def __init__(self):
        """SystemController初期化"""
        self.logger = logging.getLogger(__name__)
    
    async def get_frontend_settings(self) -> Dict[str, Any]:
        """
        フロントエンド設定取得（Key Vault統合版）
        
        機能:
        1. 基本フロントエンド設定の取得
        2. Key Vaultからの拡張設定統合
        3. エラー時のフォールバック処理
        
        Returns:
            Dict[str, Any]: フロントエンド設定辞書
            
        Raises:
            Exception: 基本設定取得に失敗した場合
        """
        try:
            # 基本フロントエンド設定を取得
            frontend_settings_copy = get_basic_frontend_settings()
            
            # Key Vaultサービスからの拡張設定統合
            keyvault_service = get_keyvault_service()
            if keyvault_service:
                try:
                    kv_settings = keyvault_service.get_frontend_settings()
                    if kv_settings:
                        frontend_settings_copy.update(kv_settings)
                        self.logger.info("Frontend settings enhanced with Key Vault configuration")
                except Exception as e:
                    self.logger.warning(f"Failed to get frontend settings from Key Vault: {e}")
            else:
                self.logger.debug("Key Vault service not available")
            
            return frontend_settings_copy
            
        except Exception as e:
            self.logger.exception("Exception in get_frontend_settings")
            raise e
    
    async def lightweight_health_check(self) -> Dict[str, Any]:
        """
        軽量ヘルスチェック実装
        
        特徴:
        - 外部依存なし
        - 高速実行
        - 副作用なし
        - Platform probe用途に最適
        
        Returns:
            Dict[str, Any]: ヘルスステータス辞書
        """
        try:
            # 最小限、高速、副作用なしの実装
            return {
                "status": "ok",
                "time": datetime.utcnow().isoformat() + "Z"
            }
        except Exception:
            # 例外が発生することはまずないが、明示的に処理
            self.logger.exception("Exception in lightweight_health_check")
            return {"status": "error"}
    
    async def detailed_health_check(self) -> Dict[str, Any]:
        """
        詳細ヘルスチェック実装
        
        機能:
        - 各種サービスの状態確認
        - タイムスタンプ付きレポート
        - バージョン情報提供
        
        Returns:
            Dict[str, Any]: 詳細ヘルスレポート
            
        Raises:
            Exception: サービスチェッカー初期化に失敗した場合
        """
        try:
            health_status = {
                "status": "healthy",
                "timestamp": datetime.utcnow().isoformat(),
                "version": "1.0.0",
                "services": {
                    "azure_openai": "unknown",
                    "cosmos_db": "unknown",
                    "modern_rag": "unknown"
                }
            }
            
            # サービス健全性チェッカーの取得
            service_checker = get_service_health_checker()
            if service_checker:
                # Azure OpenAI サービス状態確認
                try:
                    health_status["services"]["azure_openai"] = service_checker.check_azure_openai_status()
                except Exception as e:
                    self.logger.warning(f"Azure OpenAI health check failed: {e}")
                    health_status["services"]["azure_openai"] = "error"
                
                # Cosmos DB サービス状態確認
                try:
                    health_status["services"]["cosmos_db"] = service_checker.check_cosmos_db_status()
                except Exception as e:
                    self.logger.warning(f"Cosmos DB health check failed: {e}")
                    health_status["services"]["cosmos_db"] = "error"
                
                # Modern RAG サービス状態確認
                try:
                    health_status["services"]["modern_rag"] = service_checker.check_modern_rag_status()
                except Exception as e:
                    self.logger.warning(f"Modern RAG health check failed: {e}")
                    health_status["services"]["modern_rag"] = "error"
            else:
                self.logger.debug("Service health checker not available")
            
            return health_status
            
        except Exception as e:
            self.logger.exception("Exception in detailed_health_check")
            raise e


# =============================================================================
# Helper Functions (移植元のapp.pyから抽出)
# =============================================================================

def get_basic_frontend_settings() -> Dict[str, Any]:
    """
    基本フロントエンド設定の取得
    
    移植元: app.py の frontend_settings グローバル変数
    
    Returns:
        Dict[str, Any]: 基本フロントエンド設定
        
    Raises:
        Exception: 設定取得に失敗した場合
    """
    try:
        # 移植元: app.py lines 286-304, 306-321のロジック
        import os
        
        # app_settingsの取得（フォールバック付き）
        try:
            from backend.application.shared.app_settings import app_settings
        except ImportError:
            # フォールバック: app.pyから直接取得
            import app
            app_settings = app.app_settings
        
        # プライベートネットワーク設定の確認
        private_networking_enabled = os.environ.get("ENABLE_PRIVATE_NETWORKING", "false").lower() == "true"
        
        # Cosmos DB設定の確認
        cosmosdb_configured = (
            app_settings.chat_history and
            app_settings.chat_history.account and
            app_settings.chat_history.database
        )
        
        frontend_settings = {
            "auth_enabled": getattr(app_settings.base_settings, 'auth_enabled', False),
            "feedback_enabled": (
                app_settings.chat_history and
                getattr(app_settings.chat_history, 'enable_feedback', False) and
                cosmosdb_configured
            ),
            "ui": {
                "title": getattr(app_settings.ui, 'title', 'Contoso'),
                "logo": getattr(app_settings.ui, 'logo', None),
                "chat_logo": getattr(app_settings.ui, 'chat_logo', None) or getattr(app_settings.ui, 'logo', None),
                "chat_title": getattr(app_settings.ui, 'chat_title', 'Start chatting'),
                "chat_description": (
                    "プライベートネットワーク設定のため、一部機能を調整中です。基本的なチャット機能は利用可能です。" 
                    if private_networking_enabled 
                    else getattr(app_settings.ui, 'chat_description', 'This chatbot is configured to answer your questions')
                ),
                "show_share_button": getattr(app_settings.ui, 'show_share_button', True),
                "show_chat_history_button": cosmosdb_configured and getattr(app_settings.ui, 'show_chat_history_button', True),
            },
            "sanitize_answer": getattr(app_settings.base_settings, 'sanitize_answer', True),
            "oyd_enabled": getattr(app_settings.base_settings, 'datasource_type', None),
        }
        
        return frontend_settings
        
    except Exception as e:
        logging.warning(f"Failed to initialize frontend settings, using defaults: {e}")
        
        # デフォルト設定を返す（移植元: app.py lines 307-321）
        private_networking_enabled = os.environ.get("ENABLE_PRIVATE_NETWORKING", "false").lower() == "true"
        
        return {
            "auth_enabled": False,
            "feedback_enabled": False,
            "ui": {
                "title": " ",
                "logo": None,
                "chat_logo": None,
                "chat_title": "Start chatting",
                "chat_description": (
                    "プライベートネットワーク設定のため、一部機能を調整中です。基本的なチャット機能は利用可能です。" 
                    if private_networking_enabled 
                    else "This chatbot is configured to answer your questions"
                ),
                "show_share_button": True,
                "show_chat_history_button": False,
            },
            "sanitize_answer": True,
            "oyd_enabled": None,
        }


def get_keyvault_service() -> Optional[Any]:
    """
    Key Vault サービスインスタンスの取得
    
    Returns:
        Optional[Any]: Key VaultサービスまたはNone
    """
    try:
        # フォールバック: app.pyから直接取得
        import app
        return getattr(app, 'keyvault_service', None)
    except Exception as e:
        logging.warning(f"Failed to get Key Vault service: {e}")
        return None


def get_service_health_checker() -> Optional[Any]:
    """
    サービス健全性チェッカーの取得
    
    Returns:
        Optional[Any]: サービスチェッカーまたはNone
    """
    try:
        # 実装: 各種サービスの状態を確認するヘルパー
        return ServiceHealthChecker()
    except Exception as e:
        logging.warning(f"Failed to initialize service health checker: {e}")
        return None


class ServiceHealthChecker:
    """サービス健全性チェック用ヘルパークラス"""
    
    def check_azure_openai_status(self) -> str:
        """Azure OpenAI サービス状態確認"""
        try:
            # app_settingsの取得（フォールバック付き）
            try:
                from backend.application.shared.app_settings import app_settings
            except ImportError:
                import app
                app_settings = app.app_settings
            
            if app_settings.azure_openai.endpoint or app_settings.azure_openai.resource:
                return "configured"
            else:
                return "not_configured"
        except Exception:
            return "error"
    
    def check_cosmos_db_status(self) -> str:
        """Cosmos DB サービス状態確認"""
        try:
            # app_settingsの取得（フォールバック付き）
            try:
                from backend.application.shared.app_settings import app_settings
            except ImportError:
                import app
                app_settings = app.app_settings
            
            if app_settings.chat_history and app_settings.chat_history.account:
                return "configured"
            else:
                return "not_configured"
        except Exception:
            return "error"
    
    def check_modern_rag_status(self) -> str:
        """Modern RAG サービス状態確認"""
        try:
            # アプリインスタンスから Modern RAG サービスの確認
            try:
                from quart import current_app
                if hasattr(current_app, 'modern_rag') and current_app.modern_rag:
                    return "available"
                else:
                    return "not_available"
            except RuntimeError:
                # アプリケーションコンテキスト外の場合
                return "not_available"
        except Exception:
            return "error"
