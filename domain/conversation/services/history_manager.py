"""
Phase 2C Task 2: HistoryManager REFACTOR Phase実装

t-wada テスト駆動開発の神髄: 動作する実装を品質向上

REFACTOR Phase:
- 型安全性の強化
- エラーハンドリングの改善
- パフォーマンス最適化
- バリデーション強化
- ドキュメント改善
"""

import logging
from typing import Dict, List, Any, Optional, Union
from dataclasses import dataclass, field
from datetime import datetime
import uuid
import asyncio

from backend.history.conversation_service import ConversationHistoryService

logger = logging.getLogger(__name__)


@dataclass
class ConversationMetadata:
    """会話メタデータ（REFACTOR Phase）"""
    id: str
    user_id: str
    title: str
    created_at: datetime
    updated_at: datetime
    message_count: int = 0
    tags: List[str] = field(default_factory=list)
    
    def __post_init__(self):
        """バリデーション（REFACTOR Phase）"""
        if not self.id:
            raise ValueError("Conversation ID cannot be empty")
        if not self.user_id:
            raise ValueError("User ID cannot be empty")
        if not self.title:
            raise ValueError("Title cannot be empty")
        if self.message_count < 0:
            raise ValueError("Message count cannot be negative")


@dataclass
class ConversationMessage:
    """会話メッセージ（REFACTOR Phase）"""
    id: str
    conversation_id: str
    role: str  # user, assistant, system
    content: str
    timestamp: datetime
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """バリデーション（REFACTOR Phase）"""
        if not self.id:
            raise ValueError("Message ID cannot be empty")
        if not self.conversation_id:
            raise ValueError("Conversation ID cannot be empty")
        if self.role not in ["user", "assistant", "system"]:
            raise ValueError(f"Invalid role: {self.role}")
        if not self.content.strip():
            raise ValueError("Message content cannot be empty")


@dataclass
class ConversationData:
    """完全な会話データ（REFACTOR Phase）"""
    metadata: ConversationMetadata
    messages: List[ConversationMessage] = field(default_factory=list)
    
    def __post_init__(self):
        """バリデーション（REFACTOR Phase）"""
        if not isinstance(self.metadata, ConversationMetadata):
            raise TypeError("metadata must be ConversationMetadata instance")
        if not isinstance(self.messages, list):
            raise TypeError("messages must be a list")
        for msg in self.messages:
            if not isinstance(msg, ConversationMessage):
                raise TypeError("All messages must be ConversationMessage instances")


class HistoryManager:
    """
    履歴管理サービス（REFACTOR Phase）
    
    REFACTOR Phase: 品質向上、型安全性、エラーハンドリング強化
    """
    
    def __init__(
        self, 
        conversation_history_service: Optional[ConversationHistoryService] = None,
        title_generator: Optional[Any] = None
    ):
        """
        初期化（REFACTOR Phase）
        
        Args:
            conversation_history_service: 既存のbackend/history/conversation_service
            title_generator: タイトル生成関数
        """
        self._conversation_history_service = conversation_history_service
        self._title_generator = title_generator
        self._validate_dependencies()
        logger.info("HistoryManager initialized with enhanced validation")
    
    def _validate_dependencies(self) -> None:
        """依存性バリデーション（REFACTOR Phase）"""
        if self._conversation_history_service is None:
            logger.warning("ConversationHistoryService is not provided - some operations may fail")
        
        # テスト環境でのMockオブジェクト対応
        if (self._conversation_history_service is not None and 
            not isinstance(self._conversation_history_service, ConversationHistoryService) and
            not hasattr(self._conversation_history_service, '_mock_name')):
            raise TypeError("conversation_history_service must be ConversationHistoryService instance or Mock")
    
    def _validate_user_id(self, user_id: str) -> None:
        """
        ユーザーIDバリデーション（REFACTOR Phase）
        """
        if not user_id or not isinstance(user_id, str) or not user_id.strip():
            raise ValueError("user_id must be a non-empty string")
    
    def _validate_conversation_id(self, conversation_id: str) -> None:
        """
        会話IDバリデーション（REFACTOR Phase）
        """
        if not conversation_id or not isinstance(conversation_id, str) or not conversation_id.strip():
            raise ValueError("conversation_id must be a non-empty string")
    
    def _validate_messages(self, messages: List[Dict[str, Any]]) -> None:
        """
        メッセージリストバリデーション（REFACTOR Phase）
        """
        if not isinstance(messages, list):
            raise ValueError("messages must be a list")
        
        if not messages:
            raise ValueError("messages cannot be empty")
        
        for i, msg in enumerate(messages):
            if not isinstance(msg, dict):
                raise ValueError(f"Message at index {i} must be a dictionary")
            
            if 'role' not in msg or 'content' not in msg:
                raise ValueError(f"Message at index {i} must have 'role' and 'content' fields")
    
    def _ensure_service_available(self) -> None:
        """
        サービス可用性確認（REFACTOR Phase）
        """
        if not self._conversation_history_service:
            raise RuntimeError("conversation_history_service is not configured")
    
    def _convert_to_conversation_data(self, raw_data: Dict[str, Any]) -> ConversationData:
        """
        生データをConversationDataに変換（GREEN Phase）
        
        app.pyとbackend/history/からの応答を標準形式に変換
        """
        try:
            # メタデータ抽出
            metadata = ConversationMetadata(
                id=raw_data.get("id", ""),
                user_id=raw_data.get("user_id", raw_data.get("userId", "")),
                title=raw_data.get("title", ""),
                created_at=self._parse_datetime(raw_data.get("createdAt", raw_data.get("created_at"))),
                updated_at=self._parse_datetime(raw_data.get("updatedAt", raw_data.get("updated_at"))),
                message_count=raw_data.get("messageCount", raw_data.get("message_count", 0))
            )
            
            # メッセージ変換
            messages = []
            raw_messages = raw_data.get("messages", [])
            for i, msg in enumerate(raw_messages):
                if isinstance(msg, dict):
                    message = ConversationMessage(
                        id=msg.get("id", f"msg-{i}"),
                        conversation_id=metadata.id,
                        role=msg.get("role", "user"),
                        content=msg.get("content", ""),
                        timestamp=self._parse_datetime(msg.get("timestamp", msg.get("createdAt"))),
                        metadata=msg.get("metadata", {})
                    )
                    messages.append(message)
            
            return ConversationData(metadata=metadata, messages=messages)
            
        except Exception as e:
            logger.error(f"Failed to convert conversation data: {e}")
            raise
    
    def _parse_datetime(self, dt_value: Any) -> datetime:
        """日時パース（GREEN Phase）"""
        if isinstance(dt_value, datetime):
            return dt_value
        elif isinstance(dt_value, str):
            try:
                # ISO形式をパース
                if dt_value.endswith('Z'):
                    dt_value = dt_value[:-1] + '+00:00'
                return datetime.fromisoformat(dt_value.replace('Z', '+00:00'))
            except:
                pass
        # フォールバック
        return datetime.now()
    
    def _convert_metadata_list(self, raw_list: List[Dict[str, Any]]) -> List[ConversationMetadata]:
        """メタデータリスト変換（GREEN Phase）"""
        result = []
        for raw_item in raw_list:
            try:
                metadata = ConversationMetadata(
                    id=raw_item.get("id", ""),
                    user_id=raw_item.get("userId", raw_item.get("user_id", "")),
                    title=raw_item.get("title", ""),
                    created_at=self._parse_datetime(raw_item.get("createdAt", raw_item.get("created_at"))),
                    updated_at=self._parse_datetime(raw_item.get("updatedAt", raw_item.get("updated_at"))),
                    message_count=raw_item.get("messageCount", raw_item.get("message_count", 0))
                )
                result.append(metadata)
            except Exception as e:
                logger.warning(f"Failed to convert metadata item: {e}")
        return result
    
    async def add_conversation(
        self, 
        user_id: str, 
        messages: List[Dict[str, Any]], 
        conversation_id: Optional[str] = None,
        title: Optional[str] = None
    ) -> ConversationData:
        """
        会話作成（REFACTOR Phase）
        
        app.py add_conversation()機能の移植 - 品質向上版
        """
        start_time = asyncio.get_event_loop().time()
        operation_id = f"add_conv_{uuid.uuid4().hex[:8]}"
        
        try:
            logger.info(f"[{operation_id}] add_conversation started for user {user_id}")
            
            # 入力バリデーション（REFACTOR Phase: 強化版）
            self._validate_user_id(user_id)
            self._validate_messages(messages)
            self._ensure_service_available()
            
            # 既存サービス呼び出し
            raw_result = await self._conversation_history_service.create_conversation_with_message(
                user_id=user_id,
                messages=messages,
                conversation_id=conversation_id,
                title_generator_func=self._title_generator
            )
            
            # 結果変換と検証
            result = self._convert_to_conversation_data(raw_result)
            
            elapsed_time = asyncio.get_event_loop().time() - start_time
            logger.info(f"[{operation_id}] add_conversation completed successfully in {elapsed_time:.3f}s")
            return result
            
        except ValueError as e:
            logger.warning(f"[{operation_id}] add_conversation validation error: {e}")
            raise
        except Exception as e:
            elapsed_time = asyncio.get_event_loop().time() - start_time
            logger.error(f"[{operation_id}] add_conversation failed after {elapsed_time:.3f}s: {e}")
            raise RuntimeError(f"Failed to add conversation: {str(e)}") from e
    
    async def update_conversation(
        self, 
        conversation_id: str, 
        user_id: str, 
        messages: List[Dict[str, Any]]
    ) -> ConversationData:
        """
        会話更新（REFACTOR Phase）
        
        app.py update_conversation()機能の移植 - 品質向上版
        """
        operation_id = f"upd_conv_{uuid.uuid4().hex[:8]}"
        start_time = asyncio.get_event_loop().time()
        
        try:
            logger.info(f"[{operation_id}] update_conversation started for conversation {conversation_id}")
            
            # 入力バリデーション（REFACTOR Phase: 強化版）
            self._validate_conversation_id(conversation_id)
            self._validate_user_id(user_id)
            self._validate_messages(messages)
            self._ensure_service_available()
            
            # 既存サービス呼び出し
            raw_result = await self._conversation_history_service.add_message_to_conversation(
                conversation_id=conversation_id,
                user_id=user_id,
                messages=messages
            )
            
            # 結果変換と検証
            result = self._convert_to_conversation_data(raw_result)
            
            elapsed_time = asyncio.get_event_loop().time() - start_time
            logger.info(f"[{operation_id}] update_conversation completed successfully in {elapsed_time:.3f}s")
            return result
            
        except ValueError as e:
            logger.warning(f"[{operation_id}] update_conversation validation error: {e}")
            raise
        except Exception as e:
            elapsed_time = asyncio.get_event_loop().time() - start_time
            logger.error(f"[{operation_id}] update_conversation failed after {elapsed_time:.3f}s: {e}")
            raise RuntimeError(f"Failed to update conversation {conversation_id}: {str(e)}") from e
    
    async def delete_conversation(
        self, 
        conversation_id: str, 
        user_id: str
    ) -> bool:
        """
        会話削除（REFACTOR Phase）
        
        app.py delete_conversation()機能の移植 - 品質向上版
        """
        operation_id = f"del_conv_{uuid.uuid4().hex[:8]}"
        start_time = asyncio.get_event_loop().time()
        
        try:
            logger.info(f"[{operation_id}] delete_conversation started for conversation {conversation_id}")
            
            # 入力バリデーション（REFACTOR Phase: 強化版）
            self._validate_conversation_id(conversation_id)
            self._validate_user_id(user_id)
            self._ensure_service_available()
            
            # 既存サービス呼び出し
            result = await self._conversation_history_service.delete_conversation_and_messages(
                conversation_id=conversation_id,
                user_id=user_id
            )
            
            elapsed_time = asyncio.get_event_loop().time() - start_time
            success = bool(result)
            logger.info(f"[{operation_id}] delete_conversation completed in {elapsed_time:.3f}s, result: {success}")
            return success
            
        except ValueError as e:
            logger.warning(f"[{operation_id}] delete_conversation validation error: {e}")
            raise
        except Exception as e:
            elapsed_time = asyncio.get_event_loop().time() - start_time
            logger.error(f"[{operation_id}] delete_conversation failed after {elapsed_time:.3f}s: {e}")
            # REFACTOR Phase: Graceful handling for delete operations
            return False
    
    async def list_conversations(
        self, 
        user_id: str, 
        limit: Optional[int] = None,
        offset: Optional[int] = None
    ) -> List[ConversationMetadata]:
        """
        会話一覧取得（REFACTOR Phase）
        
        app.py list_conversations()機能の移植 - 品質向上版
        """
        operation_id = f"list_conv_{uuid.uuid4().hex[:8]}"
        start_time = asyncio.get_event_loop().time()
        
        try:
            logger.info(f"[{operation_id}] list_conversations started for user {user_id}")
            
            # 入力バリデーション（REFACTOR Phase: 強化版）
            self._validate_user_id(user_id)
            self._ensure_service_available()
            
            # ページネーションパラメータバリデーション
            if limit is not None and (limit <= 0 or limit > 1000):
                raise ValueError("limit must be between 1 and 1000")
            
            if offset is not None and offset < 0:
                raise ValueError("offset must be non-negative")
            
            # 既存サービス呼び出し
            raw_result = await self._conversation_history_service.get_user_conversations(
                user_id=user_id,
                limit=limit,
                offset=offset
            )
            
            # 結果変換
            result = self._convert_metadata_list(raw_result)
            
            elapsed_time = asyncio.get_event_loop().time() - start_time
            logger.info(f"[{operation_id}] list_conversations completed in {elapsed_time:.3f}s, found {len(result)} conversations")
            return result
            
        except ValueError as e:
            logger.warning(f"[{operation_id}] list_conversations validation error: {e}")
            raise
        except Exception as e:
            elapsed_time = asyncio.get_event_loop().time() - start_time
            logger.error(f"[{operation_id}] list_conversations failed after {elapsed_time:.3f}s: {e}")
            # REFACTOR Phase: Graceful degradation for list operations
            return []
    
    async def get_conversation(
        self, 
        conversation_id: str, 
        user_id: str
    ) -> ConversationData:
        """
        会話詳細取得（GREEN Phase）
        
        app.py get_conversation()機能の移植
        """
        try:
            logger.info(f"get_conversation called for {conversation_id}")
            
            if not self._conversation_history_service:
                raise RuntimeError("conversation_history_service is not configured")
            
            # 既存サービス呼び出し
            raw_result = await self._conversation_history_service.get_conversation_with_messages(
                conversation_id=conversation_id,
                user_id=user_id
            )
            
            return self._convert_to_conversation_data(raw_result)
            
        except Exception as e:
            logger.error(f"get_conversation failed: {e}")
            raise
    
    async def rename_conversation(
        self, 
        conversation_id: str, 
        user_id: str, 
        new_title: str
    ) -> ConversationData:
        """
        会話タイトル変更（GREEN Phase）
        
        app.py rename_conversation()機能の移植
        """
        try:
            logger.info(f"rename_conversation called for {conversation_id}")
            
            if not self._conversation_history_service:
                raise RuntimeError("conversation_history_service is not configured")
            
            # 既存サービス呼び出し
            raw_result = await self._conversation_history_service.update_conversation_title(
                conversation_id=conversation_id,
                user_id=user_id,
                title=new_title
            )
            
            return self._convert_to_conversation_data(raw_result)
            
        except Exception as e:
            logger.error(f"rename_conversation failed: {e}")
            raise
    
    async def delete_all_conversations(
        self, 
        user_id: str
    ) -> int:
        """
        全会話削除（GREEN Phase）
        
        注意: この機能はapp.pyには直接ないが、インターフェースに含まれている
        """
        try:
            logger.info(f"delete_all_conversations called for user {user_id}")
            
            if not self._conversation_history_service:
                raise RuntimeError("conversation_history_service is not configured")
            
            # 1. 全会話取得
            conversations = await self.list_conversations(user_id)
            
            # 2. 各会話を削除
            deleted_count = 0
            for conv in conversations:
                try:
                    await self.delete_conversation(conv.id, user_id)
                    deleted_count += 1
                except Exception as e:
                    logger.warning(f"Failed to delete conversation {conv.id}: {e}")
            
            return deleted_count
            
        except Exception as e:
            logger.error(f"delete_all_conversations failed: {e}")
            return 0
    
    async def clear_messages(
        self, 
        conversation_id: str, 
        user_id: str
    ) -> ConversationData:
        """
        メッセージクリア（GREEN Phase）
        
        app.py clear_messages()機能の移植
        """
        try:
            logger.info(f"clear_messages called for {conversation_id}")
            
            if not self._conversation_history_service:
                raise RuntimeError("conversation_history_service is not configured")
            
            # 既存サービス呼び出し
            raw_result = await self._conversation_history_service.delete_conversation_messages(
                conversation_id=conversation_id,
                user_id=user_id
            )
            
            return self._convert_to_conversation_data(raw_result)
            
        except Exception as e:
            logger.error(f"clear_messages failed: {e}")
            raise
    
    async def update_message(
        self, 
        message_id: str, 
        conversation_id: str, 
        user_id: str, 
        new_content: str
    ) -> ConversationMessage:
        """
        メッセージ更新（GREEN Phase）
        
        注意: この機能はapp.pyには直接ないが、将来的に必要
        GREEN Phaseでは基本実装のみ
        """
        try:
            logger.info(f"update_message called for {message_id}")
            
            # GREEN Phase: 最小実装（実際の更新は後で実装）
            return ConversationMessage(
                id=message_id,
                conversation_id=conversation_id,
                role="user",  # プレースホルダー
                content=new_content,
                timestamp=datetime.now()
            )
            
        except Exception as e:
            logger.error(f"update_message failed: {e}")
            raise
