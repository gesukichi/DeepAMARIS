"""
AuthService - User Domain のユーザー認証サービス

従来の backend/auth/auth_utils.py の機能を User Domain として再実装。
UserService と User エンティティを統合し、認証・認可機能を提供。
"""
from typing import Optional, Dict, Any, List, Union
import logging

from domain.user.interfaces.auth_service import (
    UserPrincipal,
    AuthorizationError,
    AuthenticationError
)
from domain.user.models.user import User
from domain.user.services.user_service import UserService

logger = logging.getLogger(__name__)


class AuthService:
    """
    User Domain のメイン認証サービス
    
    UserService と User エンティティを活用して、
    安全で一貫性のある認証・認可機能を提供。
    """
    
    # アクセス制御設定
    KNOWN_RESOURCES = ["", "public", "protected", "conversation", "data", "chat"]
    ADMIN_RESOURCES = ["admin", "protected"]
    
    def __init__(self, user_service: Optional[UserService] = None):
        """
        AuthService の初期化
        
        Args:
            user_service: UserService インスタンス（テスト用にDI対応）
        """
        self._user_service = user_service or UserService()
        logger.debug("AuthService initialized")
    
    def _convert_user_to_principal(self, user: User) -> UserPrincipal:
        """
        User エンティティを UserPrincipal に変換
        
        Args:
            user: User エンティティ
            
        Returns:
            UserPrincipal: 変換されたユーザープリンシパル
        """
        return UserPrincipal(
            user_principal_id=user.user_principal_id,
            user_name=user.user_name,
            auth_provider=user.auth_provider,
            auth_token=user.auth_token,
            client_principal_b64=user.client_principal_b64,
            aad_id_token=user.aad_id_token
        )
    
    def _handle_authentication_error(self, operation: str, error: Exception) -> None:
        """
        認証エラーの共通ハンドリング
        
        Args:
            operation: 操作名
            error: 発生したエラー
            
        Raises:
            AuthenticationError: 認証エラー
        """
        logger.error("Error in %s: %s", operation, str(error))
        raise AuthenticationError(f"{operation}中にエラーが発生しました") from error
    
    def authenticate_user(self, headers: Dict[str, Any]) -> User:
        """
        ヘッダーからユーザーを認証して User エンティティを返す
        
        Args:
            headers: リクエストヘッダー
            
        Returns:
            User: 認証されたユーザー情報
            
        Raises:
            AuthenticationError: 認証失敗時
        """
        logger.debug("Starting user authentication")
        
        if not headers:
            logger.warning("Authentication failed: Empty headers")
            raise AuthenticationError("認証ヘッダーが提供されていません")
        
        try:
            # UserService を使用してユーザー認証
            user = self._user_service.authenticate_user_from_headers(headers)
            
            if not user:
                logger.warning("Authentication failed: No user returned")
                raise AuthenticationError("ユーザーの認証に失敗しました")
            
            logger.info("User authenticated successfully: %s", user.user_name)
            return user
            
        except Exception as e:
            self._handle_authentication_error("認証処理", e)
    
    def get_user_principal(self, headers: Dict[str, Any]) -> UserPrincipal:
        """
        ヘッダーからユーザープリンシパルを取得
        
        Args:
            headers: リクエストヘッダー
            
        Returns:
            UserPrincipal: ユーザープリンシパル情報
            
        Raises:
            AuthenticationError: 認証失敗時
        """
        logger.debug("Getting user principal")
        
        # まず User エンティティを取得
        user = self.authenticate_user(headers)
        
        # User から UserPrincipal を構築
        principal = self._convert_user_to_principal(user)
        
        logger.debug("User principal created for: %s", principal.user_name)
        return principal
    
    def authorize_user(self, user_principal: UserPrincipal, required_permissions: List[str]) -> bool:
        """
        ユーザーの認可を確認
        
        Args:
            user_principal: ユーザープリンシパル
            required_permissions: 必要な権限リスト
            
        Returns:
            bool: 認可成功時 True
            
        Raises:
            AuthorizationError: 認可失敗時
        """
        logger.debug("Authorizing user: %s", user_principal.user_name)
        
        if not user_principal.is_authenticated:
            logger.warning("Authorization failed: User not authenticated")
            raise AuthorizationError("ユーザーが認証されていません")
        
        if not required_permissions:
            # 権限要件なしの場合は認証済みなら許可
            logger.debug("No specific permissions required")
            return True
        
        # 現在は基本的な認証状態のみチェック
        # 将来的には roles/groups 対応の User エンティティと連携予定
        logger.info("Authorization successful for user: %s", user_principal.user_name)
        return True
    
    def get_auth_me_response(self, headers: Dict[str, Any]) -> Dict[str, Any]:
        """
        /auth/me エンドポイント用のレスポンスを生成
        
        Args:
            headers: リクエストヘッダー
            
        Returns:
            Dict[str, Any]: auth/me レスポンス
            
        Raises:
            AuthenticationError: 認証失敗時
        """
        logger.debug("Generating auth/me response")
        
        try:
            # UserService の既存機能を活用
            response = self._user_service.get_auth_me_response(headers)
            logger.debug("Auth/me response generated successfully")
            return response
            
        except Exception as e:
            self._handle_authentication_error("auth/me レスポンス生成", e)
    
    def is_development_mode(self) -> bool:
        """
        開発モードかどうかを確認
        
        Returns:
            bool: 開発モード時 True
        """
        return self._user_service.is_development_mode()
    
    def get_development_user(self) -> User:
        """
        開発モード用のデフォルトユーザーを取得
        
        Returns:
            User: 開発用ユーザー
            
        Raises:
            AuthenticationError: 開発モードでない場合
        """
        logger.debug("Getting development user")
        
        if not self.is_development_mode():
            logger.warning("Development user requested but not in development mode")
            raise AuthenticationError("開発モードではありません")
        
        try:
            # 空のヘッダーで UserService から開発用ユーザーを取得
            user = self._user_service.authenticate_user_from_headers({})
            logger.debug("Development user retrieved successfully")
            return user
            
        except Exception as e:
            self._handle_authentication_error("開発用ユーザー取得", e)
    
    def validate_user_access(self, user: Union[UserPrincipal, User], resource: str) -> bool:
        """
        ユーザーのリソースアクセス権限を検証
        
        Args:
            user: ユーザープリンシパルまたはユーザーエンティティ
            resource: アクセス対象リソース
            
        Returns:
            bool: アクセス可能ならTrue
            
        Raises:
            AuthorizationError: 認可失敗時
        """
        logger.debug("Validating user access to resource: %s", resource)
        
        if user is None:
            logger.warning("Access denied: No user provided")
            return False
        
        # User エンティティの場合は UserPrincipal に変換
        if isinstance(user, User):
            user_principal = self._convert_user_to_principal(user)
        else:
            user_principal = user
        
        if not user_principal.is_authenticated:
            logger.warning("Access denied: User not authenticated")
            return False
        
        # 基本的なアクセス制御ロジック
        if not resource or resource == "":
            logger.debug("Access granted: No specific resource restriction")
            return True
        
        # 保護されたリソースのチェック
        if resource in self.ADMIN_RESOURCES or resource.startswith("admin"):
            # 管理者権限が必要なリソース - 現在は拒否
            logger.warning("Access denied: Administrative privileges required for resource %s", resource)
            return False
        
        # 未知のリソースは安全のためアクセス拒否
        if resource not in self.KNOWN_RESOURCES:
            logger.warning("Access denied: Unknown resource %s", resource)
            return False
        
        # デフォルトでは認証済みユーザーにアクセス許可
        logger.debug("Access granted: Default policy for authenticated user")
        return True
    
    def get_authenticated_user_details(self, request_headers: Dict[str, Any]) -> Dict[str, Any]:
        """
        レガシー互換性用：既存形式でユーザー詳細を取得
        
        Args:
            request_headers: リクエストヘッダー
            
        Returns:
            Dict[str, Any]: 既存形式のユーザー情報
            
        Note: 既存の backend/auth/auth_utils.py との互換性維持用
        """
        logger.debug("Getting authenticated user details (legacy format)")
        
        try:
            # 新しい実装を使用してユーザーを取得
            user = self.authenticate_user(request_headers)
            
            # 既存形式に変換
            user_details = {
                'user_principal_id': user.user_principal_id,
                'user_name': user.user_name,
                'auth_provider': user.auth_provider,
                'auth_token': user.auth_token,
                'client_principal_b64': user.client_principal_b64,
                'aad_id_token': user.aad_id_token
            }
            
            logger.debug("User details retrieved in legacy format")
            return user_details
            
        except Exception as e:
            self._handle_authentication_error("ユーザー詳細取得", e)
