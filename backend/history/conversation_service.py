"""
履歴管理サービス - TDD Green Phase実装

目的:
- 既存のapp.py履歴管理ロジックをテスタブルなサービスとして抽出
- Webフレームワーク依存を排除
- 最小限の変更で既存テストを通す（Green Phase）

設計原則:
- 単一責任原則：履歴管理に特化
- 依存性注入：CosmosDBクライアントを外部から注入
- フレームワーク非依存：純粋なビジネスロジック
"""
import logging
import uuid
from typing import Optional, List, Dict, Any
from datetime import datetime


class ConversationHistoryService:
    """
    会話履歴管理サービス
    
    責務:
    - 会話の作成・取得・更新・削除
    - メッセージの管理
    - ビジネスルールの適用
    """
    
    def __init__(self, cosmos_client):
        """
        Args:
            cosmos_client: CosmosDBクライアント（既存のCosmosConversationClient）
        """
        self.cosmos_client = cosmos_client
        self.logger = logging.getLogger(__name__)
    
    async def create_conversation_with_message(
        self, 
        user_id: str, 
        messages: List[Dict[str, Any]], 
        conversation_id: Optional[str] = None,
        title_generator_func = None
    ) -> Dict[str, Any]:
        """
        会話作成またはメッセージ追加
        
        既存のadd_conversationとadd_conversation_modern_rag関数のロジックを共通化して移植
        """
        try:
            # CosmosDB設定確認
            if not self.cosmos_client:
                raise Exception("CosmosDB is not configured or not working")
            
            # 履歴メタデータの準備
            history_metadata = {}
            
            # 新規会話の場合
            if not conversation_id:
                if title_generator_func:
                    title = await title_generator_func(messages)
                else:
                    title = "新しい会話"
                
                conversation_dict = await self.cosmos_client.create_conversation(
                    user_id=user_id, title=title
                )
                conversation_id = conversation_dict["id"]
                history_metadata["title"] = title
                history_metadata["date"] = conversation_dict["createdAt"]
            
            # メッセージをCosmosDBに保存
            if len(messages) > 0 and messages[-1]["role"] == "user":
                created_message_value = await self.cosmos_client.create_message(
                    uuid=str(uuid.uuid4()),
                    conversation_id=conversation_id,
                    user_id=user_id,
                    input_message=messages[-1],
                )
                if created_message_value == "Conversation not found":
                    raise Exception(
                        f"Conversation not found for the given conversation ID: {conversation_id}."
                    )
            else:
                raise Exception("No user message found")
            
            history_metadata["conversation_id"] = conversation_id
            return {
                "conversation_id": conversation_id,
                "history_metadata": history_metadata,
                "success": True
            }
            
        except Exception as e:
            self.logger.exception("Exception in create_conversation_with_message")
            raise e
    
    async def get_user_conversations(
        self, 
        user_id: str, 
        offset: int = 0, 
        limit: int = 25
    ) -> List[Dict[str, Any]]:
        """
        ユーザーの会話一覧を取得
        
        既存のlist_conversations関数のロジックを移植
        """
        if not self.cosmos_client:
            raise Exception("CosmosDB is not configured or not working")
        
        conversations = await self.cosmos_client.get_conversations(
            user_id, offset=offset, limit=limit
        )
        
        if not isinstance(conversations, list):
            raise Exception(f"No conversations for {user_id} were found")
        
        return conversations
    
    async def get_conversation_with_messages(
        self, 
        user_id: str, 
        conversation_id: str
    ) -> Dict[str, Any]:
        """
        会話の詳細とメッセージを取得
        
        既存のget_conversation関数のロジックを移植
        """
        if not self.cosmos_client:
            raise Exception("CosmosDB is not configured or not working")
        
        # 会話の存在確認
        conversation = await self.cosmos_client.get_conversation(user_id, conversation_id)
        if not conversation:
            raise Exception(
                f"Conversation {conversation_id} was not found. It either does not exist or the logged in user does not have access to it."
            )
        
        # メッセージ取得
        conversation_messages = await self.cosmos_client.get_messages(user_id, conversation_id)
        
        # フロントエンド形式に整形
        messages = [
            {
                "id": msg["id"],
                "role": msg["role"],
                "content": msg["content"],
                "createdAt": msg["createdAt"],
                "feedback": msg.get("feedback"),
            }
            for msg in conversation_messages
        ]
        
        return {
            "conversation_id": conversation_id,
            "messages": messages
        }
    
    async def delete_conversation_and_messages(
        self, 
        user_id: str, 
        conversation_id: str
    ) -> Dict[str, Any]:
        """
        会話とメッセージを削除
        
        既存のdelete_conversation関数のロジックを移植
        """
        if not self.cosmos_client:
            raise Exception("CosmosDB is not configured or not working")
        
        # まずメッセージを削除
        deleted_messages = await self.cosmos_client.delete_messages(conversation_id, user_id)
        
        # 次に会話を削除
        deleted_conversation = await self.cosmos_client.delete_conversation(user_id, conversation_id)
        
        return {
            "message": "Successfully deleted conversation and messages",
            "conversation_id": conversation_id,
            "deleted_messages_count": len(deleted_messages) if deleted_messages else 0,
            "deleted_conversation": bool(deleted_conversation)
        }
    
    async def update_conversation_title(
        self, 
        user_id: str, 
        conversation_id: str, 
        new_title: str
    ) -> Dict[str, Any]:
        """
        会話タイトルを更新
        
        既存のrename_conversation関数のロジックを移植
        """
        if not self.cosmos_client:
            raise Exception("CosmosDB is not configured or not working")
        
        if not new_title:
            raise ValueError("title is required")
        
        # 会話の存在確認
        conversation = await self.cosmos_client.get_conversation(user_id, conversation_id)
        if not conversation:
            raise Exception(
                f"Conversation {conversation_id} was not found. It either does not exist or the logged in user does not have access to it."
            )
        
        # タイトル更新
        conversation["title"] = new_title
        updated_conversation = await self.cosmos_client.upsert_conversation(conversation)
        
        return updated_conversation
    
    async def clear_conversation_messages(
        self, 
        user_id: str, 
        conversation_id: str
    ) -> Dict[str, Any]:
        """
        会話のメッセージをクリア
        
        既存のclear_messages関数のロジックを移植
        """
        if not self.cosmos_client:
            raise Exception("CosmosDB is not configured or not working")
        
        deleted_messages = await self.cosmos_client.delete_messages(conversation_id, user_id)
        
        return {
            "message": "Successfully deleted messages in conversation",
            "conversation_id": conversation_id,
            "deleted_messages_count": len(deleted_messages) if deleted_messages else 0
        }
    
    async def delete_all_user_conversations(
        self, 
        user_id: str
    ) -> Dict[str, Any]:
        """
        ユーザーの全会話を削除
        
        既存のdelete_all_conversations関数のロジックを移植
        """
        if not self.cosmos_client:
            raise Exception("CosmosDB is not configured or not working")
        
        # ユーザーの全会話を取得
        conversations = await self.cosmos_client.get_conversations(
            user_id, offset=0, limit=None
        )
        
        if not conversations:
            raise Exception(f"No conversations for {user_id} were found")
        
        deleted_count = 0
        # 各会話を削除
        for conversation in conversations:
            # メッセージを削除
            await self.cosmos_client.delete_messages(conversation["id"], user_id)
            # 会話を削除
            await self.cosmos_client.delete_conversation(user_id, conversation["id"])
            deleted_count += 1
        
        return {
            "message": "Successfully deleted all conversations and messages",
            "deleted_conversations_count": deleted_count
        }

    # ============================================
    # TDD Phase 3.1: 履歴管理機能拡張 (Green Phase)
    # ============================================
    
    async def update_message_feedback(
        self, 
        user_id: str, 
        message_id: str, 
        feedback: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        メッセージフィードバックの更新
        
        Green Phase: 最小実装で既存動作を再現
        
        Args:
            user_id: ユーザーID
            message_id: メッセージID  
            feedback: フィードバックデータ
            
        Returns:
            更新されたメッセージ（存在しない場合はNone）
        """
        try:
            self.logger.info(f"Updating message feedback: user_id={user_id}, message_id={message_id}")
            
            # 既存の cosmos_client.update_message_feedback() を直接呼び出し
            updated_message = await self.cosmos_client.update_message_feedback(
                user_id, message_id, feedback
            )
            
            return updated_message
            
        except Exception as e:
            self.logger.exception(
                f"Exception while updating message feedback: user_id={user_id}, message_id={message_id}, error={e}"
            )
            raise
    
    async def add_message_to_conversation(
        self, 
        conversation_id: str, 
        user_id: str, 
        message_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        会話へのメッセージ追加
        
        Green Phase: 最小実装で既存動作を再現
        
        Args:
            conversation_id: 会話ID
            user_id: ユーザーID
            message_data: メッセージデータ
            
        Returns:
            作成されたメッセージ
        """
        try:
            self.logger.info(f"Adding message to conversation: conv_id={conversation_id}, user_id={user_id}")
            
            # message_data から uuid を取得（なければ生成）
            import uuid as uuid_module
            message_uuid = message_data.get("uuid", str(uuid_module.uuid4()))
            
            # 既存の cosmos_client.create_message() を直接呼び出し
            created_message = await self.cosmos_client.create_message(
                message_uuid, conversation_id, user_id, message_data
            )
            
            return created_message
            
        except Exception as e:
            self.logger.exception(
                f"Exception while adding message to conversation: conv_id={conversation_id}, user_id={user_id}, error={e}"
            )
            raise
    
    async def delete_conversation_messages(
        self, 
        conversation_id: str, 
        user_id: str
    ) -> int:
        """
        会話のメッセージ一括削除
        
        Green Phase: 最小実装で既存動作を再現
        
        Args:
            conversation_id: 会話ID
            user_id: ユーザーID
            
        Returns:
            削除されたメッセージ数
        """
        try:
            self.logger.info(f"Deleting messages from conversation: conv_id={conversation_id}, user_id={user_id}")
            
            # 既存の cosmos_client.delete_messages() を直接呼び出し
            deleted_count = await self.cosmos_client.delete_messages(
                conversation_id, user_id
            )
            
            return deleted_count
            
        except Exception as e:
            self.logger.exception(
                f"Exception while deleting messages: conv_id={conversation_id}, user_id={user_id}, error={e}"
            )
            raise


class ConversationTitleGenerator:
    """
    会話タイトル生成サービス
    
    責務:
    - OpenAI APIを使用したタイトル自動生成
    - フォールバック処理
    """
    
    def __init__(self, openai_client):
        """
        Args:
            openai_client: Azure OpenAIクライアント
        """
        self.openai_client = openai_client
        self.logger = logging.getLogger(__name__)
    
    async def generate_title(self, messages: List[Dict[str, Any]]) -> str:
        """
        会話メッセージからタイトルを生成
        
        既存のgenerate_title関数のロジックを移植
        """
        try:
            # タイトル生成用のシステムメッセージ
            title_prompt = [
                {
                    "role": "system",
                    "content": "会話の内容を元に、簡潔で分かりやすいタイトルを生成してください。20文字以内でお願いします。"
                }
            ]
            
            # 最初のユーザーメッセージを追加
            if messages and len(messages) > 0:
                title_prompt.append({
                    "role": "user", 
                    "content": f"この会話のタイトルを生成してください: {messages[0].get('content', '')}"
                })
            
            response = await self.openai_client.chat.completions.create(
                model="turbo",  # デプロイメント名
                messages=title_prompt,
                temperature=0.3,
                max_tokens=50
            )
            
            title = response.choices[0].message.content
            return title.strip()
            
        except Exception as e:
            self.logger.exception("Exception while generating title: %s", e)
            # フォールバック: メッセージの一部またはデフォルトタイトル
            if messages and len(messages) > 0:
                content = messages[0].get("content", "")
                if len(content) > 20:
                    return content[:17] + "..."
                return content if content else "新しい会話"
            return "新しい会話"
