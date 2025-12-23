"""
Task 12: SystemRouter Implementation
TDD GREEN Phase: システム関連APIルーティングの実装

ルートハンドリング:
1. GET /frontend_settings - フロントエンド設定取得
2. GET /healthz - 軽量ヘルスチェック
3. GET /health - 詳細ヘルスチェック

設計方針:
- 軽量実装: シンプルなルーティング
- エラーハンドリング: 適切なHTTPステータス
- 外部委託対応: 明確なインターフェース
"""

import logging
from typing import Dict, Any, Tuple
from backend.application.system.controllers.system_controller import SystemController


class SystemRouter:
    """
    システム関連APIのルーティング処理
    
    責務:
    - HTTPリクエストのルーティング
    - レスポンス形式の統一
    - エラーハンドリング
    """
    
    def __init__(self):
        """SystemRouter初期化"""
        self.controller = SystemController()
        self.logger = logging.getLogger(__name__)
    
    async def handle_frontend_settings(self) -> Tuple[Dict[str, Any], int]:
        """
        GET /frontend_settings エンドポイントハンドラ
        
        Returns:
            Tuple[Dict[str, Any], int]: (レスポンスデータ, HTTPステータスコード)
        """
        try:
            self.logger.info("Processing frontend settings request")
            
            settings = await self.controller.get_frontend_settings()
            
            self.logger.info("Frontend settings retrieved successfully")
            return settings, 200
            
        except Exception as e:
            self.logger.exception("Exception in handle_frontend_settings")
            return {"error": str(e)}, 500
    
    async def handle_lightweight_health_check(self) -> Tuple[Dict[str, Any], int]:
        """
        GET /healthz エンドポイントハンドラ
        
        Returns:
            Tuple[Dict[str, Any], int]: (レスポンスデータ, HTTPステータスコード)
        """
        try:
            health_status = await self.controller.lightweight_health_check()
            
            if health_status.get("status") == "ok":
                return health_status, 200
            else:
                return health_status, 500
                
        except Exception as e:
            self.logger.exception("Exception in handle_lightweight_health_check")
            return {"status": "error", "error": str(e)}, 500
    
    async def handle_detailed_health_check(self) -> Tuple[Dict[str, Any], int]:
        """
        GET /health エンドポイントハンドラ
        
        Returns:
            Tuple[Dict[str, Any], int]: (レスポンスデータ, HTTPステータスコード)
        """
        try:
            self.logger.info("Processing detailed health check request")
            
            health_report = await self.controller.detailed_health_check()
            
            # サービス状態に基づいてステータスコードを決定
            status_code = self._determine_health_status_code(health_report)
            
            self.logger.info(f"Detailed health check completed with status: {health_report.get('status')}")
            return health_report, status_code
            
        except Exception as e:
            self.logger.exception("Exception in handle_detailed_health_check")
            return {
                "status": "unhealthy",
                "error": str(e),
                "timestamp": self._get_current_timestamp()
            }, 500
    
    def _determine_health_status_code(self, health_report: Dict[str, Any]) -> int:
        """
        ヘルスレポートに基づいてHTTPステータスコードを決定
        
        Args:
            health_report: ヘルスチェック結果
            
        Returns:
            int: HTTPステータスコード
        """
        if health_report.get("status") == "healthy":
            return 200
        elif health_report.get("status") == "unhealthy":
            return 500
        else:
            return 503  # Service Unavailable
    
    def _get_current_timestamp(self) -> str:
        """現在のタイムスタンプを取得"""
        from datetime import datetime
        return datetime.utcnow().isoformat()


# =============================================================================
# Integration Helper Functions
# =============================================================================

def create_system_router() -> SystemRouter:
    """
    SystemRouterインスタンスのファクトリ関数
    
    Returns:
        SystemRouter: 初期化済みSystemRouterインスタンス
    """
    return SystemRouter()


def register_system_routes(app, router: SystemRouter) -> None:
    """
    アプリケーションにシステムルートを登録
    
    Args:
        app: Flaskアプリケーションインスタンス
        router: SystemRouterインスタンス
    """
    @app.route("/frontend_settings", methods=["GET"])
    async def frontend_settings():
        """フロントエンド設定取得エンドポイント"""
        from quart import jsonify
        result, status_code = await router.handle_frontend_settings()
        return jsonify(result), status_code
    
    @app.route("/healthz", methods=["GET"])
    async def healthz():
        """軽量ヘルスチェックエンドポイント"""
        from quart import jsonify
        result, status_code = await router.handle_lightweight_health_check()
        return jsonify(result), status_code
    
    @app.route("/health", methods=["GET"])
    async def health():
        """詳細ヘルスチェックエンドポイント"""
        from quart import jsonify
        result, status_code = await router.handle_detailed_health_check()
        return jsonify(result), status_code
