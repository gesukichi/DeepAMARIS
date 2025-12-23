"""
AI処理サービス インターフェース

stream_chat_request/complete_chat_request関数群の抽象化を提供し、
app.py依存関係を分離してテスト可能性を向上させます。

Created: 2025-08-27
Purpose: Task 3 RED Phase - AI処理機能の抽象化
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, TYPE_CHECKING
from collections.abc import AsyncGenerator

# 循環インポート回避のための条件付きインポート
if TYPE_CHECKING:
    from infrastructure.services.configuration_service import ConfigurationService


class IAIProcessingService(ABC):
    """
    AI処理サービス インターフェース
    
    stream_chat_request/complete_chat_request関数群を抽象化し、
    app.py依存関係を分離してテスト可能性を向上させます。
    """
    
    @abstractmethod
    def __init__(self, configuration_service: 'ConfigurationService') -> None:
        """
        AI処理サービスを初期化します。
        
        Args:
            configuration_service: 設定サービス（Task 1で作成済み）
        """
        raise NotImplementedError
    
    @abstractmethod
    async def process_streaming_request(
        self,
        request_body: Dict[str, Any],
        request_headers: Dict[str, Any]
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        ストリーミングチャットリクエストを処理します。
        
        Args:
            request_body: リクエストボディ（メッセージ履歴等）
            request_headers: リクエストヘッダー
            
        Yields:
            ストリーミング応答のチャンク（辞書形式）
            
        Raises:
            ValueError: リクエストデータが無効な場合
            RuntimeError: AI処理に失敗した場合
        """
        raise NotImplementedError
    
    @abstractmethod
    async def process_complete_request(
        self,
        request_body: Dict[str, Any],
        request_headers: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        非ストリーミングチャットリクエストを処理します。
        
        Args:
            request_body: リクエストボディ（メッセージ履歴等）
            request_headers: リクエストヘッダー
            
        Returns:
            完成した応答（辞書形式）
            
        Raises:
            ValueError: リクエストデータが無効な場合
            RuntimeError: AI処理に失敗した場合
        """
        raise NotImplementedError
    
    @abstractmethod
    async def is_streaming_enabled(self) -> bool:
        """
        ストリーミングが有効かどうかを確認します。
        
        Returns:
            ストリーミングが有効な場合True、そうでなければFalse
        """
        raise NotImplementedError
    
    @abstractmethod
    async def validate_request(self, request_body: Dict[str, Any]) -> bool:
        """
        リクエストデータの妥当性を検証します。
        
        Args:
            request_body: 検証するリクエストボディ
            
        Returns:
            リクエストが有効な場合True、そうでなければFalse
        """
        raise NotImplementedError
