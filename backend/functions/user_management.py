"""
Azure Functions User Management Adapter Layer Implementation

TDD Phase 3C Task 17: User Management Function
t-wadaさんのテスト駆動開発原則に従った実装

目的: app.pyの/auth/meエンドポイントをAzure Functions化するアダプター層
Phase 3C: UserService, AuthServiceとの統合
"""

import json
import logging
from typing import Dict, Any, Optional, List, Union, TYPE_CHECKING

if TYPE_CHECKING:
    try:
        import azure.functions as func
    except ImportError:
        pass
import asyncio
from datetime import datetime

# Azure Functions の条件付きインポート（テスト時は None）
try:
    import azure.functions as func
    AZURE_FUNCTIONS_AVAILABLE = True
except ImportError:
    func = None
    AZURE_FUNCTIONS_AVAILABLE = False

# Phase 3C: 新しいアーキテクチャのサービス層インポート
from domain.user.services.user_service import UserService
from domain.user.services.auth_service import AuthService
from domain.user.models.user import User
from domain.user.interfaces.auth_service import UserPrincipal

# ログ設定
logger = logging.getLogger(__name__)


class UserManagementConstants:
    """User Management Function定数クラス（REFACTOR Phase改善）"""
    
    # HTTPステータスコード
    STATUS_OK = 200
    STATUS_BAD_REQUEST = 400
    STATUS_UNAUTHORIZED = 401
    STATUS_FORBIDDEN = 403
    STATUS_INTERNAL_ERROR = 500
    
    # エラーメッセージ
    ERROR_AUTH_FAILED = "Authentication failed"
    ERROR_USER_NOT_FOUND = "User not found"
    ERROR_INVALID_REQUEST = "Invalid request"
    ERROR_INTERNAL = "Internal server error"
    
    # デフォルトユーザー情報
    DEFAULT_DEV_USER_ID = "dev-user"
    DEFAULT_USER_CLAIMS = []
    
    # 設定値（REFACTOR: 設定の外部化）
    DEFAULT_TIMEOUT_SECONDS = 30
    AUTH_REQUIRED_ENV_VAR = "AUTH_REQUIRED"
    DEFAULT_AUTH_REQUIRED = "false"
    
    # REFACTOR追加: ログ設定
    LOG_LEVEL_DEBUG = "DEBUG"
    LOG_LEVEL_INFO = "INFO"
    LOG_LEVEL_WARNING = "WARNING"
    
    # REFACTOR追加: 環境別設定
    TEST_USER_ID = "test_user"
    PRODUCTION_LOG_LEVEL = "INFO"
    TEST_LOG_LEVEL = "DEBUG"
    
    @classmethod
    def get_log_level(cls, is_test_env: bool = False) -> str:
        """
        REFACTOR Phase: 環境に応じたログレベル取得
        
        t-wada原則: 設定の外部化により保守性向上
        """
        import os
        return os.getenv(
            'LOG_LEVEL', 
            cls.TEST_LOG_LEVEL if is_test_env else cls.PRODUCTION_LOG_LEVEL
        )
    
    @classmethod
    def get_auth_required_setting(cls) -> str:
        """
        REFACTOR Phase: 認証設定の統一取得
        
        環境変数アクセスの一元化
        """
        import os
        return os.getenv(cls.AUTH_REQUIRED_ENV_VAR, cls.DEFAULT_AUTH_REQUIRED)


class HttpRequest:
    """テスト用のHTTPリクエストクラス（conversation.py パターン準拠）"""
    def __init__(self, method: str, url: str = "", headers: Dict[str, str] = None, body: Any = None):
        self.method = method
        self.url = url
        self.headers = headers or {}
        self._body = body
    
    def get_json(self) -> Dict[str, Any]:
        if isinstance(self._body, dict):
            return self._body
        elif isinstance(self._body, str):
            return json.loads(self._body)
        elif isinstance(self._body, bytes):
            return json.loads(self._body.decode())
        else:
            return {}
    
    def get_body(self) -> bytes:
        if isinstance(self._body, bytes):
            return self._body
        elif isinstance(self._body, str):
            return self._body.encode('utf-8')
        else:
            return json.dumps(self._body).encode('utf-8')


class HttpResponse:
    """テスト用のHTTPレスポンスクラス"""
    def __init__(self, body: str, status_code: int = 200, headers: Dict[str, str] = None):
        self.body = body
        self.status_code = status_code
        self.headers = headers or {}


class UserManagementFunctionAdapter:
    """
    Azure Functions User Management アダプター（REFACTOR Phase改善）
    
    目的:
    - app.py auth_me() 機能のAzure Functions化
    - UserService, AuthServiceとの統合
    - 依存性注入による疎結合設計
    
    REFACTOR改善:
    - 環境検出機能の統合
    - エラーハンドリングの統一
    - 設定アクセスの一元化
    """
    
    def __init__(self, user_service: UserService = None, auth_service: AuthService = None):
        """
        初期化（REFACTOR: 依存性注入パターン最適化）
        
        Args:
            user_service: ユーザーサービス（テスト時はモック）
            auth_service: 認証サービス（テスト時はモック）
        """
        # REFACTOR: 環境検出に基づくサービス初期化
        self._is_test_env = self._is_test_environment()
        
        if self._is_test_env and user_service and auth_service:
            # テスト環境: 注入されたモックサービスを使用
            self.user_service = user_service
            self.auth_service = auth_service
        else:
            # プロダクション環境: 実際のサービスを作成
            self.user_service = user_service or self._create_user_service()
            self.auth_service = auth_service or self._create_auth_service()
        
        # REFACTOR: ログ設定の統一
        self._setup_logging()
    
    def _setup_logging(self):
        """REFACTOR Phase: ログ設定の統一"""
        log_level = UserManagementConstants.get_log_level(self._is_test_env)
        logging.getLogger(__name__).setLevel(getattr(logging, log_level, logging.INFO))
    
    def _create_user_service(self) -> UserService:
        """UserService インスタンス作成（プロダクション用）"""
        return UserService()
    
    def _create_auth_service(self) -> AuthService:
        """AuthService インスタンス作成（プロダクション用）"""
        return AuthService()
    
    def _is_test_environment(self) -> bool:
        """
        REFACTOR Phase: テスト環境検出の改善
        
        複数のテスト環境指標を統合的に判定
        """
        import os
        return (
            'pytest' in os.environ.get('_', '') or
            'PYTEST_CURRENT_TEST' in os.environ or
            os.environ.get('TESTING', 'false').lower() == 'true' or
            os.environ.get('TEST_ENVIRONMENT', 'false').lower() == 'true'
        )
    
    async def _check_auth_required(self) -> bool:
        """
        REFACTOR Phase: 認証要求確認の統一
        
        設定アクセスの一元化
        """
        auth_required_str = UserManagementConstants.get_auth_required_setting()
        return auth_required_str.lower() == "true"
    
    def _create_response(self, body: str, status_code: int = 200, headers: Dict[str, str] = None):
        """
        REFACTOR Phase: レスポンス作成の統一
        
        重複コード排除による保守性向上
        """
        default_headers = {'Content-Type': 'application/json'}
        if headers:
            default_headers.update(headers)
        
        if AZURE_FUNCTIONS_AVAILABLE and hasattr(func, 'HttpResponse'):
            return func.HttpResponse(
                body=body,
                status_code=status_code,
                headers=default_headers
            )
        else:
            return HttpResponse(
                body=body,
                status_code=status_code,
                headers=default_headers
            )
    
    async def handle_auth_me_request(self, req) -> Union[HttpResponse, Any]:
        """
        auth/me エンドポイントの処理
        
        app.py auth_me() 機能の完全互換実装
        
        Args:
            req: HTTPリクエスト（Azure Functions または テスト用）
            
        Returns:
            HTTPレスポンス（JSON形式）
        """
        try:
            # 認証が必要かどうかを確認
            auth_required = await self._check_auth_required()
            
            if auth_required:
                # 認証情報を取得・検証
                user_info = await self._get_authenticated_user_info(req)
                response_data = [user_info] if user_info else []
            else:
                # 認証無効時は空配列を返す
                response_data = []
            
            response_body = json.dumps(response_data)
            
            # REFACTOR: 統一されたレスポンス作成
            return self._create_response(response_body, UserManagementConstants.STATUS_OK)
        
        except Exception as e:
            logger.exception("Exception in user management function")
            # REFACTOR: 統一エラーハンドリング
            return await self._create_error_response(
                UserManagementConstants.ERROR_INTERNAL,
                UserManagementConstants.STATUS_INTERNAL_ERROR
            )
    
    async def _get_authenticated_user_info(self, req) -> Optional[Dict[str, Any]]:
        """
        REFACTOR Phase: 認証ユーザー情報取得の改善
        
        app.py auth_me() の認証ロジックと互換
        エラーハンドリングとフォールバック処理の強化
        """
        try:
            # ヘッダーから認証情報を取得
            authorization_header = req.headers.get('Authorization', '')
            
            if not authorization_header:
                # REFACTOR: デフォルト情報生成の統一
                return self._create_default_user_info()
            
            # AuthServiceを使用して認証情報を検証
            user_principal = await self.auth_service.validate_token(authorization_header)
            
            if user_principal and user_principal.is_authenticated:
                # REFACTOR: UserPrincipalからの安全な値取得
                return self._extract_user_info_from_principal(user_principal)
            else:
                # 認証失敗時はデフォルト情報を返す（app.py互換）
                return self._create_default_user_info()
        
        except Exception as e:
            logger.warning(f"Authentication check failed: {e}")
            # エラー時もデフォルト情報を返す（app.py互換）
            return self._create_default_user_info()
    
    def _create_default_user_info(self) -> Dict[str, Any]:
        """
        REFACTOR Phase: デフォルトユーザー情報作成の統一
        
        重複コード排除
        """
        return {
            "user_id": UserManagementConstants.DEFAULT_DEV_USER_ID,
            "user_claims": UserManagementConstants.DEFAULT_USER_CLAIMS
        }
    
    def _extract_user_info_from_principal(self, user_principal: UserPrincipal) -> Dict[str, Any]:
        """
        REFACTOR Phase: UserPrincipalからの安全な情報抽出
        
        型安全性とnull安全性の向上
        """
        user_id = (
            user_principal.user_principal_id or 
            user_principal.user_name or 
            UserManagementConstants.DEFAULT_DEV_USER_ID
        )
        
        user_claims = getattr(
            user_principal, 
            'claims', 
            UserManagementConstants.DEFAULT_USER_CLAIMS
        )
        
        return {
            "user_id": user_id,
            "user_claims": user_claims
        }
    
    async def _create_error_response(self, error_message: str, status_code: int):
        """
        REFACTOR Phase: エラーレスポンス作成の統一
        
        重複コード排除とタイムスタンプ追加
        """
        error_data = {
            "error": error_message,
            "status_code": status_code,
            "timestamp": datetime.utcnow().isoformat()
        }
        response_body = json.dumps(error_data)
        
        return self._create_response(response_body, status_code)


# Azure Functions エントリポイント
async def main(req):
    """
    Azure Functions メイン関数
    
    User Management 処理のエントリポイント
    """
    adapter = UserManagementFunctionAdapter()
    return await adapter.handle_auth_me_request(req)
