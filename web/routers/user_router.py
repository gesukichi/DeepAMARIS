"""
UserRouter - ユーザーAPI HTTP ルーター

TDD Phase: GREEN - テストを通すHTTPエンドポイント実装（t-wadaさんの原則）

外部委託重要項目:
- 認証フローの明確化（/.auth/me互換）
- シンプルで明確なRESTful API
- 一貫したエラーレスポンス
- Azure App Service /.auth/me 完全互換

移植対象: app.py認証関連関数
✅ auth_me() → GET /.auth/me (Azure App Service互換)
✅ 追加エンドポイント → GET /user/info, /user/status, /user/dev-mode
"""

import logging
from typing import Dict, List, Optional, Any
from quart import Blueprint, request, jsonify, current_app
from web.controllers.user_controller import UserController
from domain.user.services.user_service import UserService
from domain.user.services.auth_service import AuthService


# ログ設定
logger = logging.getLogger(__name__)

# Blueprintの作成（Azure App Service /.auth/me 互換のため root に配置）
user_bp = Blueprint('user', __name__)

# 依存性注入用のグローバル変数（実際のアプリではDIコンテナを使用）
_user_controller: Optional[UserController] = None


def init_user_router(
    user_service: Optional[UserService] = None,
    auth_service: Optional[AuthService] = None
) -> None:
    """
    UserRouterの初期化
    
    外部委託重要: 明確な初期化プロセス
    
    Args:
        user_service: UserServiceインスタンス
        auth_service: AuthServiceインスタンス
    """
    global _user_controller
    _user_controller = UserController(user_service, auth_service)
    logger.info("UserRouter initialized with services")


def _get_user_controller() -> UserController:
    """
    UserControllerインスタンスの取得
    
    外部委託重要: 明確なエラーハンドリング
    
    Returns:
        UserControllerインスタンス
        
    Raises:
        RuntimeError: 初期化されていない場合
    """
    if _user_controller is None:
        logger.error("UserController not initialized. Call init_user_router() first.")
        raise RuntimeError("UserController not initialized. Call init_user_router() first.")
    return _user_controller


def _get_request_headers() -> Dict[str, str]:
    """
    リクエストヘッダーの取得
    
    外部委託重要: 認証ヘッダーの適切な処理
    
    Returns:
        リクエストヘッダーの辞書
    """
    try:
        headers = {}
        for key, value in request.headers:
            headers[key] = value
        return headers
    except Exception as e:
        logger.warning("Failed to extract request headers: %s", str(e))
        return {}


@user_bp.route('/.auth/me', methods=['GET'])
async def auth_me():
    """
    Azure App Service /.auth/me 互換エンドポイント
    
    外部委託最重要: 既存の/.auth/meとの完全互換性
    移植元: app.py auth_me() 関数
    
    Returns:
        JSON: 認証情報の配列（Azure App Service形式）
        - 認証済み: [{"user_id": "...", "user_claims": [...]}]
        - 未認証: []
    """
    try:
        controller = _get_user_controller()
        headers = _get_request_headers()
        
        logger.debug("Processing /.auth/me request")
        
        # UserControllerを使用して認証情報を取得
        auth_response = await controller.get_auth_me_response(headers)
        
        logger.debug("Auth response retrieved: %s items", len(auth_response) if auth_response else 0)
        
        return jsonify(auth_response)
        
    except Exception as e:
        logger.error("Error in /.auth/me endpoint: %s", str(e))
        # セキュリティ上、例外時は空配列を返す（Azure App Service互換）
        return jsonify([])


@user_bp.route('/user/info', methods=['GET'])
async def get_user_info():
    """
    ユーザー情報取得エンドポイント
    
    外部委託重要: ユーザー詳細情報の取得
    
    Returns:
        JSON: ユーザー詳細情報
    """
    try:
        controller = _get_user_controller()
        headers = _get_request_headers()
        
        logger.debug("Processing /user/info request")
        
        # UserControllerを使用してユーザー詳細情報を取得
        user_info = await controller.get_user_details(headers)
        
        logger.debug("User info retrieved for: %s", user_info.get('user_principal_id'))
        
        return jsonify(user_info)
        
    except Exception as e:
        logger.error("Error in /user/info endpoint: %s", str(e))
        return jsonify({
            "user_principal_id": None,
            "user_principal_name": None,
            "authenticated": False,
            "error": "Failed to retrieve user information"
        }), 500


@user_bp.route('/user/status', methods=['GET'])
async def get_user_status():
    """
    ユーザー認証状態確認エンドポイント
    
    外部委託重要: 認証状態の簡単確認
    
    Returns:
        JSON: 認証状態情報
    """
    try:
        controller = _get_user_controller()
        headers = _get_request_headers()
        
        logger.debug("Processing /user/status request")
        
        # UserControllerを使用して認証状態を確認
        is_authenticated = await controller.is_authenticated(headers)
        
        logger.debug("User authentication status: %s", is_authenticated)
        
        return jsonify({
            "authenticated": is_authenticated,
            "timestamp": None  # 必要に応じて追加
        })
        
    except Exception as e:
        logger.error("Error in /user/status endpoint: %s", str(e))
        return jsonify({
            "authenticated": False,
            "error": "Failed to check authentication status"
        }), 500


@user_bp.route('/user/dev-mode', methods=['GET'])
async def get_development_mode():
    """
    開発モード確認エンドポイント
    
    外部委託重要: 開発・本番環境の明確な識別
    
    Returns:
        JSON: 開発モード情報
    """
    try:
        controller = _get_user_controller()
        
        logger.debug("Processing /user/dev-mode request")
        
        # UserControllerを使用して開発モードを確認
        is_dev_mode = controller.is_development_mode()
        
        logger.debug("Development mode status: %s", is_dev_mode)
        
        return jsonify({
            "development_mode": is_dev_mode
        })
        
    except Exception as e:
        logger.error("Error in /user/dev-mode endpoint: %s", str(e))
        return jsonify({
            "development_mode": False,
            "error": "Failed to check development mode"
        }), 500


@user_bp.route('/user/validate', methods=['POST'])
async def validate_user_access():
    """
    ユーザーアクセス権限検証エンドポイント
    
    外部委託重要: リソースアクセス権限の確認
    
    Request Body:
        JSON: {"resource": "optional_resource_name"}
    
    Returns:
        JSON: アクセス権限情報
    """
    try:
        controller = _get_user_controller()
        headers = _get_request_headers()
        
        logger.debug("Processing /user/validate request")
        
        # リクエストボディからリソース情報を取得
        request_data = await request.get_json() if request.is_json else {}
        resource = request_data.get('resource') if request_data else None
        
        # UserControllerを使用してアクセス権限を検証
        has_access = await controller.validate_user_access(headers, resource)
        
        logger.debug("User access validation for resource '%s': %s", resource, has_access)
        
        return jsonify({
            "has_access": has_access,
            "resource": resource
        })
        
    except Exception as e:
        logger.error("Error in /user/validate endpoint: %s", str(e))
        return jsonify({
            "has_access": False,
            "resource": None,
            "error": "Failed to validate user access"
        }), 500


# エラーハンドラー
@user_bp.errorhandler(404)
async def not_found(error):
    """404エラーハンドラー"""
    logger.warning("User router 404 error: %s", str(error))
    return jsonify({
        "error": "Endpoint not found",
        "message": "The requested user endpoint does not exist"
    }), 404


@user_bp.errorhandler(405)
async def method_not_allowed(error):
    """405エラーハンドラー"""
    logger.warning("User router 405 error: %s", str(error))
    return jsonify({
        "error": "Method not allowed",
        "message": "The HTTP method is not supported for this endpoint"
    }), 405


@user_bp.errorhandler(500)
async def internal_server_error(error):
    """500エラーハンドラー"""
    logger.error("User router 500 error: %s", str(error))
    return jsonify({
        "error": "Internal server error",
        "message": "An unexpected error occurred while processing the request"
    }), 500
