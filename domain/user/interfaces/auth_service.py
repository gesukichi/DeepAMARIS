"""
Auth Service Interface

backend/auth/auth_utils.pyの機能を移植・拡張したドメインインターフェース
Microsoft EasyAuth対応の認証サービス
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, Protocol
from dataclasses import dataclass


@dataclass
class UserPrincipal:
    """
    ユーザー主体情報エンティティ
    
    EasyAuthのヘッダー情報を構造化したドメインエンティティ
    """
    user_principal_id: Optional[str] = None
    user_name: Optional[str] = None
    auth_provider: Optional[str] = None
    auth_token: Optional[str] = None
    client_principal_b64: Optional[str] = None
    aad_id_token: Optional[str] = None
    
    @property
    def is_authenticated(self) -> bool:
        """認証済みかどうかを判定"""
        return self.user_principal_id is not None
    
    @property
    def is_development_user(self) -> bool:
        """開発環境のサンプルユーザーかどうかを判定"""
        return self.user_principal_id is None or self.auth_provider is None


class AuthenticationError(Exception):
    """認証エラー"""


class AuthorizationError(Exception):
    """認可エラー"""


class AuthService(Protocol):
    """
    認証サービスインターフェース
    
    backend/auth/auth_utils.pyのget_authenticated_user_details関数を
    移植・拡張したドメインサービス
    """
    
    def get_authenticated_user(self, request_headers: Dict[str, Any]) -> UserPrincipal:
        """
        リクエストヘッダーから認証済みユーザー情報を取得
        
        Args:
            request_headers: HTTPリクエストヘッダー辞書
            
        Returns:
            UserPrincipal: ユーザー主体情報
            
        Raises:
            AuthenticationError: 認証に失敗した場合
        """
        ...
    
    def validate_user_access(self, user: UserPrincipal, resource: str) -> bool:
        """
        ユーザーのリソースアクセス権限を検証
        
        Args:
            user: ユーザー主体情報
            resource: アクセス対象リソース
            
        Returns:
            bool: アクセス可能ならTrue
            
        Raises:
            AuthorizationError: 認可に失敗した場合
        """
        ...
    
    def is_development_mode(self) -> bool:
        """
        開発モードかどうかを判定
        
        Returns:
            bool: 開発モードならTrue
        """
        ...


class LegacyAuthService(ABC):
    """
    レガシー認証サービス基底クラス
    
    既存backend/auth/auth_utils.pyとの互換性を保持しながら
    段階的に新しいインターフェースに移行するための抽象クラス
    """
    
    @abstractmethod
    def get_authenticated_user_details(self, request_headers: Dict[str, Any]) -> Dict[str, Any]:
        """
        既存実装との互換性を保持したメソッド
        
        Args:
            request_headers: HTTPリクエストヘッダー辞書
            
        Returns:
            Dict[str, Any]: 既存フォーマットのユーザー情報辞書
        """
        raise NotImplementedError
    
    def get_authenticated_user(self, request_headers: Dict[str, Any]) -> UserPrincipal:
        """
        新しいインターフェースへのアダプター実装
        
        Args:
            request_headers: HTTPリクエストヘッダー辞書
            
        Returns:
            UserPrincipal: ユーザー主体情報
        """
        legacy_user = self.get_authenticated_user_details(request_headers)
        
        return UserPrincipal(
            user_principal_id=legacy_user.get('user_principal_id'),
            user_name=legacy_user.get('user_name'),
            auth_provider=legacy_user.get('auth_provider'),
            auth_token=legacy_user.get('auth_token'),
            client_principal_b64=legacy_user.get('client_principal_b64'),
            aad_id_token=legacy_user.get('aad_id_token')
        )


# 既存コードとの互換性のため、関数レベルの移植も提供
def get_authenticated_user_details_from_headers(request_headers: Dict[str, Any]) -> Dict[str, Any]:
    """
    backend/auth/auth_utils.get_authenticated_user_details の移植版
    
    既存のapp.pyとの互換性を保持するための関数
    最終的にはAuthServiceインターフェースに統合される予定
    
    Args:
        request_headers: HTTPリクエストヘッダー辞書
        
    Returns:
        Dict[str, Any]: 既存フォーマットのユーザー情報辞書
    """
    user_object = {}

    # check the headers for the Principal-Id (the guid of the signed in user)
    if "X-Ms-Client-Principal-Id" not in request_headers.keys():
        # if it's not, assume we're in development mode and return a default user
        # Note: sample_userの依存関係は別途解決が必要
        raw_user_object = {
            'X-Ms-Client-Principal-Id': None,
            'X-Ms-Client-Principal-Name': 'Development User',
            'X-Ms-Client-Principal-Idp': 'development',
            'X-Ms-Token-Aad-Id-Token': None,
            'X-Ms-Client-Principal': None
        }
    else:
        # if it is, get the user details from the EasyAuth headers
        raw_user_object = {k: v for k, v in request_headers.items()}

    user_object['user_principal_id'] = raw_user_object.get('X-Ms-Client-Principal-Id')
    user_object['user_name'] = raw_user_object.get('X-Ms-Client-Principal-Name')
    user_object['auth_provider'] = raw_user_object.get('X-Ms-Client-Principal-Idp')
    user_object['auth_token'] = raw_user_object.get('X-Ms-Token-Aad-Id-Token')
    user_object['client_principal_b64'] = raw_user_object.get('X-Ms-Client-Principal')
    user_object['aad_id_token'] = raw_user_object.get('X-Ms-Token-Aad-Id-Token')

    return user_object
