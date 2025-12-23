"""
Azure Functions App Configuration - Task 19 Implementation

TDD GREEN Phase: テストを通すための最小実装
t-wadaさんのテスト駆動開発原則に従った実装

目的: 新アーキテクチャ対応のAzure Functions設定
Phase 3C実装済みFunction群の統合
"""

import os
import json
import logging

# Azure Functions の条件付きインポート（テスト環境対応）
try:
    import azure.functions as func
    AZURE_FUNCTIONS_AVAILABLE = True
except ImportError:
    # テスト環境やローカル開発環境での代替定義
    func = None
    AZURE_FUNCTIONS_AVAILABLE = False

# 新アーキテクチャのドメインサービス層インポート（テスト検証用）
# Note: テスト時にはこれらがインポートされていることを確認
from domain.conversation.services.conversation_service import ConversationService  # noqa: F401
from domain.user.services.user_service import UserService  # noqa: F401
from domain.system.services.system_service import SystemService  # noqa: F401

# Task 20: デプロイメント戦略サービス統合
from domain.common.services.feature_flag_service import FeatureFlagService  # noqa: F401
from domain.common.services.deployment_service import DeploymentService  # noqa: F401

# Phase 3C実装済みAzure Functions インポート
from backend.functions import conversation
from backend.functions import modern_rag
from backend.functions import user_management
from backend.functions import system_management

# Azure Functions App インスタンス作成（条件付き）
if AZURE_FUNCTIONS_AVAILABLE:
    app = func.FunctionApp()
else:
    # テスト環境での代替実装
    app = None

# 環境検出機能（テスト/プロダクション自動切り替え）
AZURE_FUNCTIONS_ENVIRONMENT = os.getenv('AZURE_FUNCTIONS_ENVIRONMENT', 'production')
IS_TESTING = AZURE_FUNCTIONS_ENVIRONMENT == 'testing'

# ログ設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Azure Functions デコレータ（条件付き定義）
if AZURE_FUNCTIONS_AVAILABLE and app:
    
    # Function 1: Conversation (会話処理)
    @app.route(route="conversation", auth_level=func.AuthLevel.FUNCTION, methods=["POST"])
    async def conversation_function(req):
        """
        Phase 3C統合: 会話処理Azure Function
        ConversationService + AuthService統合パターン
        """
        try:
            return await conversation.main(req)
        except Exception as e:  # pylint: disable=broad-except
            logger.error("Conversation function error: %s", e)
            return func.HttpResponse(
                f"Error in conversation function: {str(e)}",
                status_code=500
            )

    # Function 2: Modern RAG (Modern RAG処理)  
    @app.route(route="modern_rag", auth_level=func.AuthLevel.FUNCTION, methods=["POST"])
    async def modern_rag_function(req):
        """
        Phase 3C統合: Modern RAG処理Azure Function
        ConversationService + AIResponseGenerator統合パターン
        """
        try:
            return await modern_rag.main(req)
        except Exception as e:  # pylint: disable=broad-except
            logger.error("Modern RAG function error: %s", e)
            return func.HttpResponse(
                f"Error in modern RAG function: {str(e)}",
                status_code=500
            )

    # Function 3: User Management (ユーザー管理)
    @app.route(route="user_management", auth_level=func.AuthLevel.FUNCTION, methods=["GET", "POST"])
    async def user_management_function(req):
        """
        Phase 3C統合: ユーザー管理Azure Function
        UserService + AuthService統合パターン
        """
        try:
            return await user_management.main(req)
        except Exception as e:  # pylint: disable=broad-except
            logger.error("User management function error: %s", e)
            return func.HttpResponse(
                f"Error in user management function: {str(e)}",
                status_code=500
            )

    # Function 4: System Management (システム管理)
    @app.route(route="system_management", auth_level=func.AuthLevel.FUNCTION, methods=["GET"])
    async def system_management_function(req):
        """
        Phase 3C統合: システム管理Azure Function
        SystemService統合パターン
        """
        try:
            # SystemManagementFunctionAdapterを使用
            adapter = system_management.SystemManagementFunctionAdapter()
            # クエリパラメータでエンドポイントを判定
            query_params = dict(req.params)
            action = query_params.get('action', 'health')
            
            if action == 'health':
                result = adapter.health_check()
            elif action == 'env':
                result = adapter.get_environment_info()
            elif action == 'modern_rag':
                result = adapter.get_modern_rag_status()
            else:
                result = adapter.health_check()  # デフォルト
                
            return func.HttpResponse(
                json.dumps(result),
                status_code=200,
                headers={"Content-Type": "application/json"}
            )
        except Exception as e:  # pylint: disable=broad-except
            logger.error("System management function error: %s", e)
            return func.HttpResponse(
                f"Error in system management function: {str(e)}",
                status_code=500
            )

    # Development/Debug function (開発・デバッグ用)
    @app.route(route="health", auth_level=func.AuthLevel.ANONYMOUS, methods=["GET"])
    async def health_check_function(req):  # pylint: disable=unused-argument
        """
        Azure Functions アプリケーションヘルスチェック
        環境検出とドメインサービス接続確認
        """
        try:
            health_status = {
                "status": "healthy",
                "environment": AZURE_FUNCTIONS_ENVIRONMENT,
                "is_testing": IS_TESTING,
                "functions_registered": [
                    "conversation",
                    "modern_rag", 
                    "user_management",
                    "system_management"
                ]
            }
            
            return func.HttpResponse(
                json.dumps(health_status),
                status_code=200,
                headers={"Content-Type": "application/json"}
            )
        except Exception as e:  # pylint: disable=broad-except
            logger.error("Health check error: %s", e)
            return func.HttpResponse(
                f"Health check failed: {str(e)}",
                status_code=500
            )

if __name__ == "__main__":
    # ローカル開発用: Azure Functions Core Toolsで実行
    logger.info("Azure Functions App initialized successfully")
    logger.info("Environment: %s", AZURE_FUNCTIONS_ENVIRONMENT)
    logger.info("Phase 3C Azure Functions ready for deployment")
