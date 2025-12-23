"""
会話リポジトリインターフェース

app.pyの履歴管理機能とbackend/history/の機能を統合した
包括的なリポジトリインターフェース定義
"""

from typing import Protocol, Any, Optional, List, Dict
from datetime import datetime
from dataclasses import dataclass


@dataclass
class ConversationMetadata:
    """会話メタデータ"""
    id: str
    user_id: str
    title: str
    created_at: datetime
    updated_at: datetime
    message_count: int = 0
    is_deleted: bool = False


@dataclass
class MessageData:
    """メッセージデータ"""
    id: str
    conversation_id: str
    role: str  # system, user, assistant, function, tool
    content: str
    timestamp: datetime
    feedback: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class ConversationData:
    """完全な会話データ"""
    metadata: ConversationMetadata
    messages: List[MessageData]


class IConversationRepository(Protocol):
    """
    会話リポジトリの包括的インターフェース
    
    app.pyの履歴管理関数群とbackend/history/ConversationHistoryServiceを
    統合したドメイン層の抽象化
    """
    
    # === 会話の基本CRUD操作 ===
    
    async def create_conversation(
        self,
        user_id: str,
        title: Optional[str] = None,
        initial_message: Optional[MessageData] = None
    ) -> ConversationMetadata:
        """
        新しい会話を作成
        
        Args:
            user_id: ユーザーID
            title: 会話タイトル（自動生成も可）
            initial_message: 初期メッセージ（オプション）
            
        Returns:
            ConversationMetadata: 作成された会話のメタデータ
        """
        ...
    
    async def get_conversation(
        self,
        conversation_id: str,
        user_id: str,
        include_messages: bool = True
    ) -> Optional[ConversationData]:
        """
        会話を取得
        
        Args:
            conversation_id: 会話ID
            user_id: ユーザーID
            include_messages: メッセージを含めるかどうか
            
        Returns:
            ConversationData: 会話データ、存在しない場合はNone
        """
        ...
    
    async def update_conversation(
        self,
        conversation_id: str,
        user_id: str,
        title: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        会話メタデータを更新
        
        Args:
            conversation_id: 会話ID
            user_id: ユーザーID
            title: 新しいタイトル
            metadata: 追加メタデータ
            
        Returns:
            bool: 更新成功時True
        """
        ...
    
    async def delete_conversation(
        self,
        conversation_id: str,
        user_id: str,
        soft_delete: bool = True
    ) -> bool:
        """
        会話を削除
        
        Args:
            conversation_id: 会話ID
            user_id: ユーザーID
            soft_delete: 論理削除するかどうか
            
        Returns:
            bool: 削除成功時True
        """
        ...
    
    async def list_conversations(
        self,
        user_id: str,
        offset: int = 0,
        limit: int = 25,
        include_deleted: bool = False
    ) -> List[ConversationMetadata]:
        """
        ユーザーの会話一覧を取得
        
        Args:
            user_id: ユーザーID
            offset: オフセット
            limit: 取得件数制限
            include_deleted: 削除済み会話を含めるか
            
        Returns:
            List[ConversationMetadata]: 会話メタデータのリスト
        """
        ...
    
    # === メッセージ管理 ===
    
    async def add_message(
        self,
        conversation_id: str,
        user_id: str,
        role: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> MessageData:
        """
        会話にメッセージを追加
        
        Args:
            conversation_id: 会話ID
            user_id: ユーザーID
            role: メッセージの役割
            content: メッセージ内容
            metadata: 追加メタデータ
            
        Returns:
            MessageData: 追加されたメッセージ
        """
        ...
    
    async def update_message(
        self,
        message_id: str,
        user_id: str,
        content: Optional[str] = None,
        feedback: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        メッセージを更新
        
        Args:
            message_id: メッセージID
            user_id: ユーザーID
            content: 新しい内容
            feedback: フィードバック
            metadata: 追加メタデータ
            
        Returns:
            bool: 更新成功時True
        """
        ...
    
    async def delete_message(
        self,
        message_id: str,
        user_id: str
    ) -> bool:
        """
        メッセージを削除
        
        Args:
            message_id: メッセージID
            user_id: ユーザーID
            
        Returns:
            bool: 削除成功時True
        """
        ...
    
    async def clear_conversation_messages(
        self,
        conversation_id: str,
        user_id: str
    ) -> bool:
        """
        会話の全メッセージを削除
        
        Args:
            conversation_id: 会話ID
            user_id: ユーザーID
            
        Returns:
            bool: 削除成功時True
        """
        ...
    
    # === バッチ操作 ===
    
    async def delete_all_conversations(
        self,
        user_id: str,
        soft_delete: bool = True
    ) -> int:
        """
        ユーザーの全会話を削除
        
        Args:
            user_id: ユーザーID
            soft_delete: 論理削除するかどうか
            
        Returns:
            int: 削除された会話数
        """
        ...
    
    # === app.py互換メソッド（移行期間用） ===
    
    async def save_conversation(self, user_id: str, response: Any) -> None:
        """
        app.pyの既存インターフェース互換メソッド
        
        Args:
            user_id: ユーザーID
            response: 応答データ
        """
        ...
    
    # === 統計・分析 ===
    
    async def get_conversation_count(self, user_id: str) -> int:
        """
        ユーザーの会話数を取得
        
        Args:
            user_id: ユーザーID
            
        Returns:
            int: 会話数
        """
        ...
    
    async def get_message_count(self, conversation_id: str, user_id: str) -> int:
        """
        会話のメッセージ数を取得
        
        Args:
            conversation_id: 会話ID
            user_id: ユーザーID
            
        Returns:
            int: メッセージ数
        """
        ...


class ConversationRepositoryException(Exception):
    """会話リポジトリ関連例外の基底クラス"""


class ConversationNotFound(ConversationRepositoryException):
    """会話が見つからない例外"""


class MessageNotFound(ConversationRepositoryException):
    """メッセージが見つからない例外"""


class PermissionDenied(ConversationRepositoryException):
    """アクセス権限がない例外"""


class ValidationError(ConversationRepositoryException):
    """データ検証エラー例外"""
