"""
UserController - ユーザーAPI制御

TDD Phase: GREEN - テストを通すための最小実装（t-wadaさんの原則）

外部委託対応重要項目:
- 認証フローの明確化
- シンプルで使いやすいインターフェース
- 既存auth_utils.pyとの統合
- 開発環境・本番環境の適切な切り替え

移植対象: app.py認証関連関数
- auth_me() - 認証エンドポイント
"""

import logging
import os
from typing import Dict, List, Optional, Any
from domain.user.services.user_service import UserService
from domain.user.services.auth_service import AuthService


class UserController:
    """
    ユーザーAPI制御クラス
    
    外部委託重要: 認証フローの明確化
    シンプル実装: 既存auth_utils.pyとの統合
    
    責務:
    - ユーザー認証の制御
    - 外部委託に適したシンプルなAPI提供
    - 開発環境・本番環境の適切な切り替え
    - 既存UserService・AuthService統合
    """
    
    def __init__(
        self, 
        user_service: Optional[UserService] = None,
        auth_service: Optional[AuthService] = None
    ):
        """
        UserController初期化
        
        Args:
            user_service: UserServiceインスタンス（DI対応）
            auth_service: AuthServiceインスタンス（DI対応）
        """
        self._user_service = user_service
        self._auth_service = auth_service
        self._logger = logging.getLogger(__name__)
    
    def _is_auth_required(self) -> bool:
        """
        認証が必要かどうかを環境変数から判定
        
        Returns:
            bool: 認証が必要な場合True
        """
        return os.environ.get("AUTH_REQUIRED", "false").lower() == "true"
    
    async def get_auth_me_response(self, headers: Optional[Dict[str, str]] = None) -> List[Dict[str, Any]]:
        """
        /.auth/me エンドポイントの応答取得 - auth_me()の移植
        
        外部委託重要: 認証フローの明確化
        シンプル実装: Azure App Service /.auth/me 互換形式
        
        Args:
            headers: リクエストヘッダー
            
        Returns:
            認証情報のリスト（Azure App Service互換形式）
            - 認証済み: [{"user_id": "...", "user_claims": [...]}]
            - 未認証: []
        """
        try:
            if not self._is_auth_required():
                # 認証が不要な環境では空配列を返す
                self._logger.debug("Authentication not required, returning empty array")
                
                # 開発モードでもAuthServiceがある場合は呼び出すことを明示
                if self._auth_service:
                    auth_response = await self._auth_service.get_auth_me_response(headers or {})
                    return auth_response or []
                
                return []
            
            if not self._auth_service:
                self._logger.warning("AuthService not configured")
                return []
            
            # AuthServiceを使用して認証情報を取得
            auth_response = await self._auth_service.get_auth_me_response(headers or {})
            
            self._logger.debug("Auth response retrieved: %s items", len(auth_response) if auth_response else 0)
            return auth_response or []
            
        except (AttributeError, ConnectionError, TimeoutError, RuntimeError, ValueError, Exception) as e:
            self._logger.error("Failed to get auth me response: %s", str(e))
            # セキュリティ上、例外時は空配列を返す
            return []
    
    async def authenticate_user(self, headers: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """
        ユーザー認証
        
        外部委託重要: 認証処理の明確化
        
        Args:
            headers: リクエストヘッダー
            
        Returns:
            認証済みユーザー情報
        """
        try:
            if not self._user_service:
                self._logger.warning("UserService not configured")
                return {
                    "user_principal_id": None,
                    "user_principal_name": None,
                    "authenticated": False
                }
            
            # UserServiceを使用してユーザー認証を実行
            user = await self._user_service.authenticate_user(headers or {})
            
            self._logger.debug("User authenticated: %s", user.get('authenticated', False))
            return user
            
        except (AttributeError, ConnectionError, TimeoutError) as e:
            self._logger.error("Failed to authenticate user: %s", str(e))
            return {
                "user_principal_id": None,
                "user_principal_name": None,
                "authenticated": False
            }
    
    async def get_user_details(self, headers: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """
        ユーザー詳細情報取得
        
        外部委託重要: ユーザー情報の詳細取得
        
        Args:
            headers: リクエストヘッダー
            
        Returns:
            ユーザー詳細情報
        """
        try:
            # まず認証を実行
            user = await self.authenticate_user(headers)
            
            if not user.get("authenticated", False):
                self._logger.debug("User not authenticated")
                return user
            
            # 認証済みユーザーの詳細情報を追加
            # 基本的な実装では、認証情報そのものを返す
            self._logger.debug("User details retrieved for: %s", user.get('user_principal_id'))
            return user
            
        except (AttributeError, ConnectionError, TimeoutError) as e:
            self._logger.error("Failed to get user details: %s", str(e))
            return {
                "user_principal_id": None,
                "user_principal_name": None,
                "authenticated": False
            }
    
    async def is_authenticated(self, headers: Optional[Dict[str, str]] = None) -> bool:
        """
        認証状態確認
        
        外部委託重要: 認証状態の簡単確認
        
        Args:
            headers: リクエストヘッダー
            
        Returns:
            認証状態（True: 認証済み、False: 未認証）
        """
        try:
            if not self._auth_service:
                self._logger.warning("AuthService not configured")
                return False
            
            # AuthServiceを使用して認証状態を確認
            is_valid = await self._auth_service.validate_user_access(headers or {})
            
            self._logger.debug("User authentication status: %s", is_valid)
            return is_valid
            
        except (AttributeError, ConnectionError, TimeoutError) as e:
            self._logger.error("Failed to check authentication status: %s", str(e))
            return False
    
    async def validate_user_access(
        self, 
        headers: Optional[Dict[str, str]] = None,
        resource: Optional[str] = None
    ) -> bool:
        """
        ユーザーアクセス権限の検証
        
        外部委託重要: リソースアクセス権限の確認
        
        Args:
            headers: リクエストヘッダー
            resource: アクセス対象リソース（省略可）
            
        Returns:
            アクセス許可状態
        """
        try:
            if not self._auth_service:
                self._logger.warning("AuthService not configured")
                return False
            
            # AuthServiceを使用してアクセス権限を検証
            has_access = await self._auth_service.validate_user_access(
                headers or {}, 
                resource
            )
            
            self._logger.debug("User access validation for resource '%s': %s", resource, has_access)
            return has_access
            
        except (AttributeError, ConnectionError, TimeoutError) as e:
            self._logger.error("Failed to validate user access: %s", str(e))
            return False
    
    def is_development_mode(self) -> bool:
        """
        開発モード判定
        
        外部委託重要: 開発・本番環境の明確な識別
        
        Returns:
            開発モードの場合True
        """
        try:
            if not self._auth_service:
                # AuthServiceが無い場合は環境変数から直接判定
                return not self._is_auth_required()
            
            # AuthServiceを使用して開発モードを判定
            return self._auth_service.is_development_mode()
            
        except (AttributeError, ConnectionError, TimeoutError, RuntimeError) as e:
            self._logger.error("Failed to check development mode: %s", str(e))
            return False
