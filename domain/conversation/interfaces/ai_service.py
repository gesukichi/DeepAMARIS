"""
AIサービスインターフェース

app.pyのAI関連機能に基づいた包括的なインターフェース定義
"""

from typing import List, Protocol, Any, Optional
from collections.abc import AsyncGenerator
from enum import Enum


class MessageRole(str, Enum):
    """メッセージの役割"""
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    FUNCTION = "function"
    TOOL = "tool"


class Message(dict):
    """メッセージクラス（既存互換性維持）"""
    
    @property
    def role(self) -> str:
        return self.get("role", "user")
    
    @property
    def content(self) -> str:
        return self.get("content", "")
    
    @classmethod
    def create_user_message(cls, content: str) -> "Message":
        return cls({"role": MessageRole.USER, "content": content})
    
    @classmethod
    def create_assistant_message(cls, content: str) -> "Message":
        return cls({"role": MessageRole.ASSISTANT, "content": content})
    
    @classmethod
    def create_system_message(cls, content: str) -> "Message":
        return cls({"role": MessageRole.SYSTEM, "content": content})


class AIServiceConfig:
    """AI サービス設定"""
    def __init__(
        self,
        model: str,
        temperature: float = 0.0,
        max_tokens: int = 1000,
        stream: bool = True,
        **kwargs
    ):
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.stream = stream
        self.extra_params = kwargs


class IAIService(Protocol):
    """
    AIサービスの基本インターフェース
    
    app.pyの関数群を基にした包括的なAIサービス抽象化
    """
    
    async def generate_response(
        self,
        messages: List[Message],
        config: Optional[AIServiceConfig] = None
    ) -> Any:
        """
        非ストリーミングレスポンス生成
        
        Args:
            messages: メッセージ履歴
            config: AI設定（オプション）
            
        Returns:
            Any: AI応答
        """
        ...
    
    async def generate_streaming_response(
        self,
        messages: List[Message],
        config: Optional[AIServiceConfig] = None
    ) -> AsyncGenerator[str, None]:
        """
        ストリーミングレスポンス生成
        
        Args:
            messages: メッセージ履歴
            config: AI設定（オプション）
            
        Yields:
            str: ストリーミングされたレスポンス片
        """
        ...
    
    async def call_function(
        self,
        function_name: str,
        function_args: str
    ) -> Optional[str]:
        """
        外部関数呼び出し（Azure Functions等）
        
        Args:
            function_name: 関数名
            function_args: 関数引数（JSON文字列）
            
        Returns:
            str: 関数実行結果、無効化されている場合はNone
        """
        ...
    
    async def validate_configuration(self) -> bool:
        """
        AI設定の妥当性検証
        
        Returns:
            bool: 設定が有効な場合True
        """
        ...


class IAIServiceFactory(Protocol):
    """
    AIサービスファクトリインターフェース
    
    DIコンテナとの統合用
    """
    
    async def create_ai_service(self) -> IAIService:
        """
        AIサービスインスタンスを作成
        
        Returns:
            IAIService: 設定済みAIサービス
        """
        ...
    
    async def create_client(self) -> Any:
        """
        低レベルAIクライアント作成（Azure OpenAI等）
        
        Returns:
            Any: クライアントインスタンス
        """
        ...


class AIServiceException(Exception):
    """AIサービス関連例外の基底クラス"""


class AIConfigurationException(AIServiceException):
    """AI設定エラー"""


class AIResponseException(AIServiceException):
    """AI応答エラー"""


class AIFunctionCallException(AIServiceException):
    """AI関数呼び出しエラー"""
