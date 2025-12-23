"""
HistoryController - 履歴API制御

TDD Phase: GREEN - テストを通すための最小実装（t-wadaさんの原則）

外部委託対応重要項目:
- CRUD操作の明確化
- エラーハンドリングの一貫性  
- APIレスポンス形式の統一
- 認証フローの明確化

移植対象: app.py履歴管理関連10関数
- add_conversation(), add_conversation_modern_rag()
- update_conversation(), update_message()
- delete_conversation(), list_conversations()
- get_conversation(), rename_conversation() 
- delete_all_conversations(), clear_messages()
"""

import logging
import uuid
from typing import Dict, List, Optional, Any, Union
from backend.history.conversation_service import ConversationHistoryService


class HistoryController:
    """
    履歴API制御クラス
    
    外部委託最重要: CRUD操作の明確化
    既存活用: HistoryManager実装済み機能の統合
    
    責務:
    - 会話履歴のCRUD操作制御
    - 外部委託に適したシンプルなAPI提供
    - エラーハンドリングの統一
    - 既存ConversationService統合
    """
    
    def __init__(self, conversation_service: Optional[ConversationHistoryService] = None):
        """
        HistoryController初期化
        
        Args:
            conversation_service: ConversationHistoryServiceインスタンス（DI対応）
        """
        self._conversation_service = conversation_service
        self._logger = logging.getLogger(__name__)
    
    def _validate_user_id(self, user_id: str) -> None:
        """user_idの検証"""
        if not user_id or not user_id.strip():
            raise ValueError("Invalid user_id")
    
    def _validate_messages(self, messages: List[Dict]) -> None:
        """メッセージリストの検証"""
        if not messages:
            raise ValueError("Messages cannot be empty")
    
    def _validate_conversation_id(self, conversation_id: str) -> None:
        """conversation_idの検証（UUID形式）"""
        if conversation_id:
            try:
                uuid.UUID(conversation_id)
            except ValueError:
                raise ValueError("Invalid conversation_id format")
    
    async def create_conversation(
        self,
        user_id: str,
        messages: List[Dict[str, Any]],
        conversation_id: Optional[str] = None,
        title_generator_func: Optional[callable] = None
    ) -> Dict[str, Any]:
        """
        会話作成 - add_conversation()の移植
        
        外部委託重要: 会話生成APIの明確化
        
        Args:
            user_id: ユーザーID
            messages: メッセージリスト
            conversation_id: 会話ID（省略時は新規作成）
            title_generator_func: タイトル生成関数
            
        Returns:
            作成結果（success, history_metadata含む）
            
        Raises:
            ValueError: パラメータ検証エラー
            Exception: サービス層エラー
        """
        self._validate_user_id(user_id)
        self._validate_messages(messages)
        if conversation_id:
            self._validate_conversation_id(conversation_id)
        
        try:
            # タイトル生成関数は新規作成時のみ適用
            title_generator = title_generator_func if not conversation_id else None
            
            result = await self._conversation_service.create_conversation_with_message(
                user_id=user_id,
                messages=messages,
                conversation_id=conversation_id,
                title_generator_func=title_generator
            )
            
            if not result.get("success"):
                raise Exception("Failed to create conversation with message")
            
            self._logger.info(f"Created conversation for user {user_id}")
            return result
            
        except Exception as e:
            self._logger.error(f"Failed to create conversation: {str(e)}")
            raise
    
    async def create_modern_rag_conversation(
        self,
        user_id: str,
        messages: List[Dict[str, Any]],
        conversation_id: Optional[str] = None,
        title_generator_func: Optional[callable] = None
    ) -> Dict[str, Any]:
        """
        Modern RAG会話作成 - add_conversation_modern_rag()の移植
        
        外部委託重要: Modern RAG版APIの明確化
        
        Args:
            user_id: ユーザーID
            messages: メッセージリスト
            conversation_id: 会話ID（省略時は新規作成）
            title_generator_func: タイトル生成関数
            
        Returns:
            作成結果（modern_rag_enabled: trueを含む）
        """
        self._validate_user_id(user_id)
        self._validate_messages(messages)
        if conversation_id:
            self._validate_conversation_id(conversation_id)
        
        try:
            # タイトル生成関数は新規作成時のみ適用
            title_generator = title_generator_func if not conversation_id else None
            
            result = await self._conversation_service.create_conversation_with_message(
                user_id=user_id,
                messages=messages,
                conversation_id=conversation_id,
                title_generator_func=title_generator
            )
            
            if not result.get("success"):
                raise Exception("Failed to create conversation with message")
            
            # Modern RAG対応のメタデータ追加
            if "history_metadata" in result:
                result["history_metadata"]["modern_rag_enabled"] = True
            
            self._logger.info(f"Created Modern RAG conversation for user {user_id}")
            return result
            
        except Exception as e:
            self._logger.error(f"Failed to create Modern RAG conversation: {str(e)}")
            raise
    
    async def create_deepresearch_conversation(
        self,
        user_id: str,
        messages: List[Dict[str, Any]],
        conversation_id: Optional[str] = None,
        title_generator_func: Optional[callable] = None
    ) -> Dict[str, Any]:
        """
        DeepResearch 会話作成
        
        Args:
            user_id: ユーザーID
            messages: メッセージリスト
            conversation_id: 既存会話ID（任意）
            title_generator_func: タイトル生成関数
            
        Returns:
            作成結果（deepresearch_enabled: trueを含む）
        """
        self._validate_user_id(user_id)
        self._validate_messages(messages)
        if conversation_id:
            self._validate_conversation_id(conversation_id)
        
        try:
            title_generator = title_generator_func if not conversation_id else None
            
            result = await self._conversation_service.create_conversation_with_message(
                user_id=user_id,
                messages=messages,
                conversation_id=conversation_id,
                title_generator_func=title_generator
            )
            
            if not result.get("success"):
                raise Exception("Failed to create conversation with message")
            
            if "history_metadata" in result:
                result["history_metadata"]["deepresearch_enabled"] = True
            
            self._logger.info(f"Created DeepResearch conversation for user {user_id}")
            return result
            
        except Exception as e:
            self._logger.error(f"Failed to create DeepResearch conversation: {str(e)}")
            raise
    
    async def update_conversation(
        self,
        user_id: str,
        conversation_id: Optional[str],
        messages: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        会話更新 - update_conversation()の移植
        
        外部委託重要: 会話更新APIの明確化
        
        Args:
            user_id: ユーザーID
            conversation_id: 会話ID
            messages: 更新するメッセージリスト
            
        Returns:
            更新結果
        """
        self._validate_user_id(user_id)
        
        if not conversation_id:
            raise Exception("No conversation_id found")
        
        self._validate_conversation_id(conversation_id)
        
        try:
            # assistantメッセージの存在確認
            if not messages or not any(msg.get("role") == "assistant" for msg in messages):
                raise Exception("No bot messages found")
            
            # 最後のメッセージがassistantメッセージの場合のみ処理
            if messages[-1].get("role") == "assistant":
                # tool メッセージがある場合は先に追加
                # NOTE: CosmosDBには完全な履歴を保存し、読み込み時に不要なroleをフィルタリング
                # history_router.pyでtoolロールはOpenAI API送信前に除外される
                if len(messages) > 1 and messages[-2].get("role") == "tool":
                    tool_message = {
                        "uuid": str(uuid.uuid4()),
                        **messages[-2]
                    }
                    await self._conversation_service.add_message_to_conversation(
                        conversation_id, user_id, tool_message
                    )
                
                # assistant メッセージを追加
                assistant_message = {
                    "uuid": messages[-1].get("id", str(uuid.uuid4())),
                    **messages[-1]
                }
                await self._conversation_service.add_message_to_conversation(
                    conversation_id, user_id, assistant_message
                )
            
            self._logger.info(f"Updated conversation {conversation_id} for user {user_id}")
            return {"success": True}
            
        except Exception as e:
            self._logger.error(f"Failed to update conversation: {str(e)}")
            raise
    
    async def update_message_feedback(
        self,
        user_id: str,
        message_id: str,
        message_feedback: str
    ) -> Dict[str, Any]:
        """
        メッセージフィードバック更新 - update_message()の移植
        
        外部委託重要: メッセージフィードバックAPIの明確化
        
        Args:
            user_id: ユーザーID
            message_id: メッセージID
            message_feedback: フィードバック内容
            
        Returns:
            更新結果
        """
        self._validate_user_id(user_id)
        
        if not message_id:
            return {"success": False, "error": "message_id is required"}
        
        if not message_feedback:
            return {"success": False, "error": "message_feedback is required"}
        
        try:
            updated_message = await self._conversation_service.update_message_feedback(
                user_id, message_id, message_feedback
            )
            
            if updated_message:
                self._logger.info(f"Updated message feedback for {message_id}")
                return {
                    "success": True,
                    "message": f"Successfully updated message with feedback {message_feedback}",
                    "message_id": message_id
                }
            else:
                return {
                    "success": False,
                    "error": f"Message {message_id} not found or access denied"
                }
                
        except Exception as e:
            self._logger.error(f"Failed to update message feedback: {str(e)}")
            raise
    
    async def delete_conversation(
        self,
        user_id: str,
        conversation_id: str
    ) -> Dict[str, Any]:
        """
        会話削除 - delete_conversation()の移植
        
        外部委託重要: 会話削除APIの明確化
        
        Args:
            user_id: ユーザーID
            conversation_id: 会話ID
            
        Returns:
            削除結果
        """
        self._validate_user_id(user_id)
        
        if not conversation_id:
            return {"success": False, "error": "conversation_id is required"}
        
        self._validate_conversation_id(conversation_id)
        
        try:
            await self._conversation_service.delete_conversation_and_messages(
                user_id, conversation_id
            )
            
            self._logger.info(f"Deleted conversation {conversation_id} for user {user_id}")
            return {
                "success": True,
                "message": "Successfully deleted conversation and messages",
                "conversation_id": conversation_id
            }
        
        except Exception as e:
            # CosmosDB NotFound (404) means already deleted - treat as success (idempotent)
            from azure.cosmos.exceptions import CosmosResourceNotFoundError
            if isinstance(e, CosmosResourceNotFoundError):
                self._logger.info(f"Conversation {conversation_id} not found (already deleted)")
                return {
                    "success": True,
                    "message": "Conversation already deleted or does not exist",
                    "conversation_id": conversation_id
                }
            
            self._logger.error(f"Failed to delete conversation: {str(e)}")
            raise
    
    async def list_conversations(
        self,
        user_id: str,
        offset: int = 0,
        limit: int = 25
    ) -> List[Dict[str, Any]]:
        """
        会話一覧取得 - list_conversations()の移植
        
        外部委託重要: 会話一覧APIの明確化
        
        Args:
            user_id: ユーザーID
            offset: オフセット
            limit: 制限数
            
        Returns:
            会話リスト
        """
        self._validate_user_id(user_id)
        
        # パラメータ境界値チェック
        offset = max(0, offset)
        limit = min(max(1, limit), 100)  # 1-100の範囲に制限
        
        try:
            conversations = await self._conversation_service.get_user_conversations(
                user_id, offset=offset, limit=limit
            )
            
            self._logger.info(f"Retrieved {len(conversations)} conversations for user {user_id}")
            return conversations
            
        except Exception as e:
            self._logger.error(f"Failed to list conversations: {str(e)}")
            raise
    
    async def get_conversation(
        self,
        user_id: str,
        conversation_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        会話詳細取得 - get_conversation()の移植
        
        外部委託重要: 会話詳細取得APIの明確化
        
        Args:
            user_id: ユーザーID
            conversation_id: 会話ID
            
        Returns:
            会話詳細（存在しない場合はNone）
        """
        self._validate_user_id(user_id)
        
        if not conversation_id:
            return None
        
        self._validate_conversation_id(conversation_id)
        
        try:
            result = await self._conversation_service.get_conversation_with_messages(
                user_id, conversation_id
            )
            
            if result:
                self._logger.info(f"Retrieved conversation {conversation_id} for user {user_id}")
            else:
                self._logger.info(f"Conversation {conversation_id} not found for user {user_id}")
            
            return result
            
        except Exception as e:
            self._logger.error(f"Failed to get conversation: {str(e)}")
            raise
    
    async def rename_conversation(
        self,
        user_id: str,
        conversation_id: str,
        title: str
    ) -> Optional[Dict[str, Any]]:
        """
        会話リネーム - rename_conversation()の移植
        
        外部委託重要: 会話リネームAPIの明確化
        
        Args:
            user_id: ユーザーID
            conversation_id: 会話ID
            title: 新しいタイトル
            
        Returns:
            更新された会話情報（存在しない場合はNone）
        """
        self._validate_user_id(user_id)
        
        if not conversation_id:
            return None
        
        self._validate_conversation_id(conversation_id)
        
        if not title:
            return None
        
        try:
            updated_conversation = await self._conversation_service.update_conversation_title(
                user_id, conversation_id, title
            )
            
            if updated_conversation:
                self._logger.info(f"Renamed conversation {conversation_id} for user {user_id}")
            else:
                self._logger.info(f"Conversation {conversation_id} not found for user {user_id}")
            
            return updated_conversation
            
        except Exception as e:
            self._logger.error(f"Failed to rename conversation: {str(e)}")
            raise
    
    async def delete_all_conversations(
        self,
        user_id: str
    ) -> Dict[str, Any]:
        """
        全会話削除 - delete_all_conversations()の移植
        
        外部委託重要: 全会話削除APIの明確化
        
        Args:
            user_id: ユーザーID
            
        Returns:
            削除結果（削除数を含む）
        """
        self._validate_user_id(user_id)
        
        try:
            deleted_count = await self._conversation_service.delete_all_user_conversations(user_id)
            
            if deleted_count > 0:
                self._logger.info(f"Deleted {deleted_count} conversations for user {user_id}")
                return {
                    "success": True,
                    "deleted_count": deleted_count,
                    "message": f"Successfully deleted {deleted_count} conversations and messages for user {user_id}"
                }
            else:
                self._logger.info(f"No conversations found for user {user_id}")
                return {
                    "success": True,
                    "deleted_count": 0,
                    "message": f"No conversations to delete for user {user_id}"
                }
                
        except Exception as e:
            from azure.cosmos.exceptions import CosmosResourceNotFoundError
            if isinstance(e, CosmosResourceNotFoundError):
                self._logger.info(f"No conversations found for user {user_id} (CosmosDB NotFound)")
                return {
                    "success": True,
                    "deleted_count": 0,
                    "message": "No conversations to delete"
                }
            
            self._logger.error(f"Failed to delete all conversations: {str(e)}")
            raise
    
    async def clear_messages(
        self,
        user_id: str,
        conversation_id: str
    ) -> Dict[str, Any]:
        """
        会話メッセージクリア - clear_messages()の移植
        
        外部委託重要: メッセージクリアAPIの明確化
        
        Args:
            user_id: ユーザーID
            conversation_id: 会話ID
            
        Returns:
            クリア結果
        """
        self._validate_user_id(user_id)
        
        if not conversation_id:
            return {"success": False, "error": "conversation_id is required"}
        
        self._validate_conversation_id(conversation_id)
        
        try:
            deleted_messages = await self._conversation_service.delete_conversation_messages(
                conversation_id, user_id
            )
            
            self._logger.info(f"Cleared messages in conversation {conversation_id} for user {user_id}")
            return {
                "success": True,
                "message": "Successfully deleted messages in conversation",
                "conversation_id": conversation_id
            }
            
        except Exception as e:
            self._logger.error(f"Failed to clear messages: {str(e)}")
            raise


    # ===============================================
    # Day3 Phase4 TDD Green Phase: テスト用エイリアス
    # ===============================================
    
    async def get_user_conversations(
        self,
        user_id: str,
        offset: int = 0,
        limit: int = 25
    ) -> List[Dict[str, Any]]:
        """
        Day3 Green Phase: get_user_conversations エイリアス
        テストが期待するメソッド名との互換性確保
        """
        return await self.list_conversations(user_id, offset, limit)
