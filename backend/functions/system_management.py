"""
Task 18: System Management Function Implementation
TDD実装 - REFACTOR段階: コード品質の向上

System Management Functionの改善実装
app.pyの既存機能を参考に、保守性と可読性を向上
"""

import os
import logging
import sys
from datetime import datetime
from typing import Dict, Any, Optional


class SystemManagementConfig:
    """
    System Management Function Configuration
    設定値の外部化とデフォルト値の管理
    """
    
    # デフォルト値の設定
    DEFAULT_ENV_RESPONSE = "NOT_SET"
    DEBUG_DISABLED_MESSAGE = "Debug endpoint not available"
    
    # セキュリティ設定
    PRODUCTION_ENV_PREFIXES = ("prod", "production")
    HTTPS_PREFIX = "https://"
    
    @staticmethod
    def is_production_environment() -> bool:
        """本番環境の判定"""
        azure_env = os.environ.get("AZURE_ENV_NAME", "")
        backend_uri = os.environ.get("BACKEND_URI", "")
        
        return (
            azure_env.startswith(SystemManagementConfig.PRODUCTION_ENV_PREFIXES) or
            backend_uri.startswith(SystemManagementConfig.HTTPS_PREFIX)
        )
    
    @staticmethod
    def is_debug_enabled() -> bool:
        """デバッグモードの判定"""
        return os.environ.get("DEBUG", "false").lower() == "true"
    
    @staticmethod
    def is_debug_endpoint_available() -> bool:
        """デバッグエンドポイントの利用可能性判定"""
        return (
            SystemManagementConfig.is_debug_enabled() and 
            not SystemManagementConfig.is_production_environment()
        )


class SystemManagementFunctionAdapter:
    """
    System Management Function Adapter
    
    app.pyのシステム管理関連機能をAzure Functionsで提供
    - Health Check
    - Environment Information  
    - Modern RAG Status
    """
    
    def __init__(self):
        """初期化 - ロガー設定と設定クラスの準備"""
        self.logger = logging.getLogger(__name__)
        self.config = SystemManagementConfig()
    
    def health_check(self) -> Dict[str, Any]:
        """
        Health Check Implementation
        app.py /healthz エンドポイントの移植
        
        Returns:
            Dict[str, Any]: ヘルスチェック結果
        """
        try:
            return self._create_health_success_response()
        except (OSError, ValueError) as e:
            self.logger.exception("Specific exception in health_check: %s", str(e))
            return self._create_error_response()
        except Exception as e:
            self.logger.exception("Unexpected exception in health_check: %s", str(e))
            return self._create_error_response()
    
    def get_environment_info(self) -> Dict[str, Any]:
        """
        Environment Information Implementation
        app.py /debug/env エンドポイントの移植
        
        Returns:
            Dict[str, Any]: 環境変数情報またはエラーメッセージ
        """
        if not self.config.is_debug_endpoint_available():
            return self._create_debug_disabled_response()
        
        try:
            return self._collect_environment_variables()
        except (KeyError, ValueError) as e:
            self.logger.exception("Environment variable collection error: %s", str(e))
            return self._create_error_response(str(e))
        except Exception as e:
            self.logger.exception("Unexpected exception in get_environment_info: %s", str(e))
            return self._create_error_response(str(e))
    
    def get_modern_rag_status(self) -> Dict[str, Any]:
        """
        Modern RAG Status Implementation  
        app.py /debug/modern-rag-status エンドポイントの移植
        
        Returns:
            Dict[str, Any]: Modern RAGステータス情報またはエラーメッセージ
        """
        if not self.config.is_debug_endpoint_available():
            return self._create_debug_disabled_response()
        
        try:
            return self._collect_modern_rag_status()
        except (ImportError, AttributeError) as e:
            self.logger.exception("Modern RAG status collection error: %s", str(e))
            return self._create_error_response(str(e))
        except Exception as e:
            self.logger.exception("Unexpected exception in get_modern_rag_status: %s", str(e))
            return self._create_error_response(str(e))
    
    def _create_health_success_response(self) -> Dict[str, Any]:
        """ヘルスチェック成功レスポンスの作成"""
        return {
            "status": "ok",
            "time": datetime.utcnow().isoformat() + "Z"
        }
    
    def _create_error_response(self, error_message: Optional[str] = None) -> Dict[str, Any]:
        """エラーレスポンスの作成"""
        response = {"status": "error"}
        if error_message:
            response["error"] = error_message
        return response
    
    def _create_debug_disabled_response(self) -> Dict[str, Any]:
        """デバッグ無効レスポンスの作成"""
        return {"error": self.config.DEBUG_DISABLED_MESSAGE}
    
    def _collect_environment_variables(self) -> Dict[str, Any]:
        """環境変数の収集"""
        return {
            "AUTH_REQUIRED": os.environ.get("AUTH_REQUIRED", self.config.DEFAULT_ENV_RESPONSE),
            "AZURE_USE_AUTHENTICATION": os.environ.get("AZURE_USE_AUTHENTICATION", self.config.DEFAULT_ENV_RESPONSE),
            "AZURE_ENFORCE_ACCESS_CONTROL": os.environ.get("AZURE_ENFORCE_ACCESS_CONTROL", self.config.DEFAULT_ENV_RESPONSE),
            "LOCAL_MOCK_MODE": os.environ.get("LOCAL_MOCK_MODE", self.config.DEFAULT_ENV_RESPONSE),
        }
    
    def _collect_modern_rag_status(self) -> Dict[str, Any]:
        """Modern RAGステータスの収集"""
        return {
            "timestamp": datetime.now().isoformat(),
            "env_vars": self._collect_modern_rag_env_vars(),
            "modern_rag_service": self._get_modern_rag_service_status(),
            "azure_ai_agents_package": self._check_azure_ai_agents_package()
        }
    
    def _collect_modern_rag_env_vars(self) -> Dict[str, str]:
        """Modern RAG関連環境変数の収集"""
        return {
            "AZURE_AI_AGENT_ENDPOINT": os.getenv("AZURE_AI_AGENT_ENDPOINT", self.config.DEFAULT_ENV_RESPONSE),
            "AZURE_AI_AGENT_KEY": "SET" if os.getenv("AZURE_AI_AGENT_KEY") else "NOT SET",
            "BING_GROUNDING_CONN_ID": os.getenv("BING_GROUNDING_CONN_ID", self.config.DEFAULT_ENV_RESPONSE),
            "AZURE_OPENAI_MODEL": os.getenv("AZURE_OPENAI_MODEL", self.config.DEFAULT_ENV_RESPONSE),
            "AZURE_OPENAI_API_VERSION": os.getenv("AZURE_OPENAI_API_VERSION", self.config.DEFAULT_ENV_RESPONSE),
        }
    
    def _get_modern_rag_service_status(self) -> Dict[str, Any]:
        """Modern RAGサービス状態の取得"""
        return {
            "available": False,  # Azure Functions版では未実装
            "instance": None,
            "error_details": "Not implemented in Azure Functions version"
        }
    
    def _check_azure_ai_agents_package(self) -> Dict[str, Any]:
        """Azure AI Agentsパッケージの確認"""
        package_status = {
            "imported": "azure.ai.agents" in sys.modules,
            "import_error": None
        }
        
        try:
            from azure.ai.agents.aio import AgentsClient  # noqa: F401
        except ImportError as e:
            package_status["import_error"] = str(e)
            
        return package_status
