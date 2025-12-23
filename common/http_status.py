"""
HTTPステータスコード一括管理モジュール

t-wada氏のテスト駆動開発原則に基づいて設計された
HTTPステータスコードの中央集約管理システム

機能:
- HTTPステータスコードの定数定義と管理
- 意味のある名前でのステータスコード提供
- デバッグとログ用のヘルパー機能
- エラーレスポンス生成の標準化
"""

from enum import IntEnum
from typing import Dict, Optional, Tuple
import logging


class HTTPStatus(IntEnum):
    """
    HTTPステータスコードの列挙型定義
    
    RFC 7231, RFC 6585, RFC 2324に準拠したステータスコード
    プロジェクトで使用される主要なコードのみを定義
    """
    
    # 1xx 情報レスポンス (現在は未使用)
    
    # 2xx 成功レスポンス
    OK = 200                        # 通常の成功レスポンス
    CREATED = 201                   # リソース作成成功
    ACCEPTED = 202                  # 処理受付完了
    NO_CONTENT = 204               # 成功、レスポンスボディなし
    
    # 3xx リダイレクション
    MOVED_PERMANENTLY = 301         # 永続的リダイレクト
    FOUND = 302                     # 一時的リダイレクト
    SEE_OTHER = 303                 # 他のリソースを参照
    TEMPORARY_REDIRECT = 307        # 一時的リダイレクト（メソッド保持）
    PERMANENT_REDIRECT = 308        # 永続的リダイレクト（メソッド保持）
    
    # 4xx クライアントエラー
    BAD_REQUEST = 400               # 不正なリクエスト
    UNAUTHORIZED = 401              # 認証が必要
    FORBIDDEN = 403                 # アクセス禁止
    NOT_FOUND = 404                 # リソースが見つからない
    METHOD_NOT_ALLOWED = 405        # 許可されていないHTTPメソッド
    CONFLICT = 409                  # リクエストの競合
    UNSUPPORTED_MEDIA_TYPE = 415    # サポートされていないメディアタイプ
    UNPROCESSABLE_ENTITY = 422      # 処理不可能なエンティティ
    TOO_MANY_REQUESTS = 429         # レート制限超過
    
    # 5xx サーバーエラー
    INTERNAL_SERVER_ERROR = 500     # 内部サーバーエラー
    NOT_IMPLEMENTED = 501           # 機能未実装
    BAD_GATEWAY = 502               # 不正なゲートウェイ
    SERVICE_UNAVAILABLE = 503       # サービス利用不可
    GATEWAY_TIMEOUT = 504           # ゲートウェイタイムアウト


class HTTPStatusManager:
    """
    HTTPステータスコード管理クラス
    
    ステータスコードの取得、説明、およびレスポンス生成の
    一元管理を提供します。
    """
    
    # ステータスコードの説明マップ
    STATUS_DESCRIPTIONS = {
        # 2xx 成功
        HTTPStatus.OK: "リクエストが正常に処理されました",
        HTTPStatus.CREATED: "リソースが正常に作成されました",
        HTTPStatus.ACCEPTED: "リクエストが受け付けられました",
        HTTPStatus.NO_CONTENT: "リクエストは成功しましたが、返すコンテンツはありません",
        
        # 3xx リダイレクト
        HTTPStatus.MOVED_PERMANENTLY: "リソースが永続的に移動しました",
        HTTPStatus.FOUND: "リソースが一時的に移動しました",
        HTTPStatus.SEE_OTHER: "他のリソースを参照してください",
        HTTPStatus.TEMPORARY_REDIRECT: "一時的にリダイレクトされました",
        HTTPStatus.PERMANENT_REDIRECT: "永続的にリダイレクトされました",
        
        # 4xx クライアントエラー
        HTTPStatus.BAD_REQUEST: "リクエストの形式が正しくありません",
        HTTPStatus.UNAUTHORIZED: "認証が必要です",
        HTTPStatus.FORBIDDEN: "アクセスが禁止されています",
        HTTPStatus.NOT_FOUND: "要求されたリソースが見つかりません",
        HTTPStatus.METHOD_NOT_ALLOWED: "このHTTPメソッドは許可されていません",
        HTTPStatus.CONFLICT: "リクエストが競合しています",
        HTTPStatus.UNSUPPORTED_MEDIA_TYPE: "サポートされていないメディアタイプです",
        HTTPStatus.UNPROCESSABLE_ENTITY: "リクエストは理解できますが、処理できません",
        HTTPStatus.TOO_MANY_REQUESTS: "リクエスト数が制限を超えています",
        
        # 5xx サーバーエラー
        HTTPStatus.INTERNAL_SERVER_ERROR: "サーバー内部でエラーが発生しました",
        HTTPStatus.NOT_IMPLEMENTED: "この機能は実装されていません",
        HTTPStatus.BAD_GATEWAY: "上流サーバーから無効なレスポンスを受信しました",
        HTTPStatus.SERVICE_UNAVAILABLE: "サービスが一時的に利用できません",
        HTTPStatus.GATEWAY_TIMEOUT: "上流サーバーからの応答がタイムアウトしました",
    }
    
    @classmethod
    def get_description(cls, status_code: int) -> str:
        """
        ステータスコードの説明を取得
        
        Args:
            status_code: HTTPステータスコード
            
        Returns:
            str: ステータスコードの説明（日本語）
        """
        try:
            status = HTTPStatus(status_code)
            return cls.STATUS_DESCRIPTIONS.get(status, f"ステータスコード {status_code}")
        except ValueError:
            return f"不明なステータスコード {status_code}"
    
    @classmethod
    def is_success(cls, status_code: int) -> bool:
        """
        成功レスポンスかどうかを判定
        
        Args:
            status_code: HTTPステータスコード
            
        Returns:
            bool: 2xx系の場合True
        """
        return 200 <= status_code < 300
    
    @classmethod
    def is_client_error(cls, status_code: int) -> bool:
        """
        クライアントエラーかどうかを判定
        
        Args:
            status_code: HTTPステータスコード
            
        Returns:
            bool: 4xx系の場合True
        """
        return 400 <= status_code < 500
    
    @classmethod
    def is_server_error(cls, status_code: int) -> bool:
        """
        サーバーエラーかどうかを判定
        
        Args:
            status_code: HTTPステータスコード
            
        Returns:
            bool: 5xx系の場合True
        """
        return 500 <= status_code < 600
    
    @classmethod
    def is_redirect(cls, status_code: int) -> bool:
        """
        リダイレクトレスポンスかどうかを判定
        
        Args:
            status_code: HTTPステータスコード
            
        Returns:
            bool: 3xx系の場合True
        """
        return 300 <= status_code < 400
    
    @classmethod
    def log_status(cls, status_code: int, context: str = "") -> None:
        """
        ステータスコードをログに記録
        
        Args:
            status_code: HTTPステータスコード
            context: 追加のコンテキスト情報
        """
        description = cls.get_description(status_code)
        message = f"HTTP {status_code}: {description}"
        if context:
            message += f" - {context}"
        
        if cls.is_server_error(status_code):
            logging.error(message)
        elif cls.is_client_error(status_code):
            logging.warning(message)
        else:
            logging.info(message)
    
    @classmethod
    def create_error_response_data(cls, 
                                   error_message: str, 
                                   status_code: int,
                                   error_code: Optional[str] = None,
                                   details: Optional[Dict] = None) -> Dict:
        """
        エラーレスポンス用のデータ構造を作成
        
        Args:
            error_message: エラーメッセージ
            status_code: HTTPステータスコード
            error_code: アプリケーション固有のエラーコード
            details: 追加の詳細情報
            
        Returns:
            Dict: エラーレスポンス用の辞書
        """
        response_data = {
            "error": error_message,
            "status_code": status_code,
            "status_description": cls.get_description(status_code)
        }
        
        if error_code:
            response_data["error_code"] = error_code
        
        if details:
            response_data["details"] = details
        
        return response_data


# 共通的なレスポンスパターンのためのヘルパー関数

def create_success_response(data: Dict, status_code: int = HTTPStatus.OK) -> Tuple[Dict, int]:
    """
    成功レスポンスを作成
    
    Args:
        data: レスポンスデータ
        status_code: HTTPステータスコード（デフォルト: 200）
        
    Returns:
        Tuple[Dict, int]: (レスポンスデータ, ステータスコード)
    """
    return data, status_code


def create_error_response(error_message: str, 
                         status_code: int,
                         error_code: Optional[str] = None,
                         details: Optional[Dict] = None) -> Tuple[Dict, int]:
    """
    エラーレスポンスを作成
    
    Args:
        error_message: エラーメッセージ
        status_code: HTTPステータスコード
        error_code: アプリケーション固有のエラーコード
        details: 追加の詳細情報
        
    Returns:
        Tuple[Dict, int]: (エラーレスポンスデータ, ステータスコード)
    """
    response_data = HTTPStatusManager.create_error_response_data(
        error_message, status_code, error_code, details
    )
    return response_data, status_code


def create_validation_error_response(field_errors: Dict[str, str]) -> Tuple[Dict, int]:
    """
    バリデーションエラー用のレスポンスを作成
    
    Args:
        field_errors: フィールド名をキーとするエラーメッセージの辞書
        
    Returns:
        Tuple[Dict, int]: (エラーレスポンスデータ, ステータスコード)
    """
    return create_error_response(
        "入力データの検証に失敗しました",
        HTTPStatus.BAD_REQUEST,
        "VALIDATION_ERROR",
        {"field_errors": field_errors}
    )


def create_not_found_response(resource_type: str = "リソース") -> Tuple[Dict, int]:
    """
    Not Foundエラーレスポンスを作成
    
    Args:
        resource_type: リソースの種類
        
    Returns:
        Tuple[Dict, int]: (エラーレスポンスデータ, ステータスコード)
    """
    return create_error_response(
        f"指定された{resource_type}が見つかりません",
        HTTPStatus.NOT_FOUND
    )


def create_unauthorized_response(message: str = "認証が必要です") -> Tuple[Dict, int]:
    """
    認証エラーレスポンスを作成
    
    Args:
        message: エラーメッセージ
        
    Returns:
        Tuple[Dict, int]: (エラーレスポンスデータ, ステータスコード)
    """
    return create_error_response(message, HTTPStatus.UNAUTHORIZED)


def create_forbidden_response(message: str = "アクセスが禁止されています") -> Tuple[Dict, int]:
    """
    アクセス禁止エラーレスポンスを作成
    
    Args:
        message: エラーメッセージ
        
    Returns:
        Tuple[Dict, int]: (エラーレスポンスデータ, ステータスコード)
    """
    return create_error_response(message, HTTPStatus.FORBIDDEN)


def create_server_error_response(message: str = "サーバー内部でエラーが発生しました") -> Tuple[Dict, int]:
    """
    サーバーエラーレスポンスを作成
    
    Args:
        message: エラーメッセージ
        
    Returns:
        Tuple[Dict, int]: (エラーレスポンスデータ, ステータスコード)
    """
    return create_error_response(message, HTTPStatus.INTERNAL_SERVER_ERROR)


def create_service_unavailable_response(message: str = "サービスが一時的に利用できません") -> Tuple[Dict, int]:
    """
    サービス利用不可エラーレスポンスを作成
    
    Args:
        message: エラーメッセージ
        
    Returns:
        Tuple[Dict, int]: (エラーレスポンスデータ, ステータスコード)
    """
    return create_error_response(message, HTTPStatus.SERVICE_UNAVAILABLE)


# 後方互換性のための旧ステータスコード定数（非推奨）
# 既存コードの段階的移行を支援するため一時的に提供
# TODO: すべての移行完了後に削除予定

class LegacyHTTPStatus:
    """
    後方互換性のための旧HTTPステータスコード定数
    
    Warning:
        これらの定数は非推奨です。新しいHTTPStatusクラスを使用してください。
    """
    
    # 成功レスポンス
    HTTP_200_OK = HTTPStatus.OK
    HTTP_201_CREATED = HTTPStatus.CREATED
    HTTP_204_NO_CONTENT = HTTPStatus.NO_CONTENT
    
    # クライアントエラー
    HTTP_400_BAD_REQUEST = HTTPStatus.BAD_REQUEST
    HTTP_401_UNAUTHORIZED = HTTPStatus.UNAUTHORIZED
    HTTP_403_FORBIDDEN = HTTPStatus.FORBIDDEN
    HTTP_404_NOT_FOUND = HTTPStatus.NOT_FOUND
    HTTP_415_UNSUPPORTED_MEDIA_TYPE = HTTPStatus.UNSUPPORTED_MEDIA_TYPE
    
    # サーバーエラー
    HTTP_500_INTERNAL_SERVER_ERROR = HTTPStatus.INTERNAL_SERVER_ERROR
    HTTP_501_NOT_IMPLEMENTED = HTTPStatus.NOT_IMPLEMENTED
    HTTP_503_SERVICE_UNAVAILABLE = HTTPStatus.SERVICE_UNAVAILABLE
