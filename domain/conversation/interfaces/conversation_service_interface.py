"""
Conversation Service Interface

統合会話ドメインサービスのインターフェース定義
app.pyのconversation_internal関数などを統合した次世代サービス
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, AsyncIterator, Union, Protocol
from dataclasses import dataclass

from domain.conversation.interfaces.ai_service import Message, AIServiceConfig
from domain.conversation.interfaces.conversation_repository import ConversationData, MessageData
from domain.user.interfaces.auth_service import UserPrincipal


@dataclass
class ConversationRequest:
    """会話リクエストエンティティ"""
    messages: List[Message]
    conversation_id: Optional[str] = None
    user: Optional[UserPrincipal] = None
    config: Optional[AIServiceConfig] = None
    stream: bool = True
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None
    
    @property
    def is_new_conversation(self) -> bool:
        """新しい会話かどうかを判定"""
        return self.conversation_id is None


@dataclass
class ConversationResponse:
    """会話レスポンスエンティティ"""
    content: str
    conversation_id: str
    message_id: Optional[str] = None
    citations: Optional[List[Dict[str, Any]]] = None
    usage: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    
    @property
    def is_successful(self) -> bool:
        """レスポンスが成功かどうかを判定"""
        return self.error is None


@dataclass
class StreamChunk:
    """ストリーミングレスポンスのチャンクエンティティ"""
    content: str
    conversation_id: str
    is_final: bool = False
    citations: Optional[List[Dict[str, Any]]] = None
    usage: Optional[Dict[str, Any]] = None
    delta_content: Optional[str] = None


class ConversationServiceError(Exception):
    """会話サービス汎用エラー"""


class ConversationNotFoundError(ConversationServiceError):
    """会話が見つからない場合のエラー"""


class InvalidMessageError(ConversationServiceError):
    """不正なメッセージフォーマットのエラー"""


class ConversationService(Protocol):
    """
    統合会話ドメインサービスのプロトコル
    
    app.pyのconversation_internal関数等を統合し、
    会話の全ライフサイクルを管理する次世代サービス
    """
    
    async def send_message(self, request: ConversationRequest) -> ConversationResponse:
        """
        メッセージを送信して応答を取得（非ストリーミング）
        
        Args:
            request: 会話リクエスト
            
        Returns:
            ConversationResponse: 会話応答
            
        Raises:
            ConversationServiceError: サービスエラー
            InvalidMessageError: メッセージフォーマットエラー
        """
        ...
    
    async def send_message_stream(self, request: ConversationRequest) -> AsyncIterator[StreamChunk]:
        """
        メッセージを送信してストリーミング応答を取得
        
        Args:
            request: 会話リクエスト
            
        Yields:
            StreamChunk: ストリーミングチャンク
            
        Raises:
            ConversationServiceError: サービスエラー
            InvalidMessageError: メッセージフォーマットエラー
        """
        ...
    
    async def get_conversation_history(self, conversation_id: str, user: UserPrincipal) -> ConversationData:
        """
        会話履歴を取得
        
        Args:
            conversation_id: 会話ID
            user: ユーザー主体情報
            
        Returns:
            ConversationData: 会話データ
            
        Raises:
            ConversationNotFoundError: 会話が見つからない場合
            ConversationServiceError: サービスエラー
        """
        ...
    
    async def list_user_conversations(self, user: UserPrincipal, limit: int = 25, offset: int = 0) -> List[ConversationData]:
        """
        ユーザーの会話一覧を取得
        
        Args:
            user: ユーザー主体情報
            limit: 取得上限数
            offset: オフセット
            
        Returns:
            List[ConversationData]: 会話データリスト
            
        Raises:
            ConversationServiceError: サービスエラー
        """
        ...
    
    async def delete_conversation(self, conversation_id: str, user: UserPrincipal) -> bool:
        """
        会話を削除
        
        Args:
            conversation_id: 会話ID
            user: ユーザー主体情報
            
        Returns:
            bool: 削除成功の場合True
            
        Raises:
            ConversationNotFoundError: 会話が見つからない場合
            ConversationServiceError: サービスエラー
        """
        ...


class LegacyConversationService(ABC):
    """
    レガシー会話サービス基底クラス
    
    既存app.pyのconversation_internal関数等との互換性を保持しながら
    段階的に新しいインターフェースに移行するための抽象クラス
    """
    
    @abstractmethod
    async def conversation_internal_legacy(
        self,
        request_json: Dict[str, Any],
        user_headers: Dict[str, Any]
    ) -> Union[Dict[str, Any], AsyncIterator[str]]:
        """
        既存app.pyのconversation_internal関数との互換性メソッド
        
        Args:
            request_json: リクエストJSON辞書
            user_headers: ユーザーヘッダー辞書
            
        Returns:
            Union[Dict[str, Any], AsyncIterator[str]]: 既存フォーマットの応答
        """
        raise NotImplementedError
    
    async def send_message(self, request: ConversationRequest) -> ConversationResponse:
        """
        新しいインターフェースへのアダプター実装
        
        Args:
            request: 会話リクエスト
            
        Returns:
            ConversationResponse: 会話応答
        """
        # ConversationRequestを既存フォーマットに変換
        request_json = {
            'messages': [msg.model_dump() for msg in request.messages],
            'conversation_id': request.conversation_id,
            'stream': request.stream,
            'temperature': request.temperature,
            'max_tokens': request.max_tokens
        }
        
        user_headers = {}
        if request.user:
            user_headers = {
                'X-Ms-Client-Principal-Id': request.user.user_principal_id,
                'X-Ms-Client-Principal-Name': request.user.user_name,
                'X-Ms-Client-Principal-Idp': request.user.auth_provider,
                'X-Ms-Token-Aad-Id-Token': request.user.auth_token,
                'X-Ms-Client-Principal': request.user.client_principal_b64
            }
        
        # レガシーメソッド呼び出し
        legacy_response = await self.conversation_internal_legacy(request_json, user_headers)
        
        # レスポンスを新しいフォーマットに変換
        if isinstance(legacy_response, dict):
            return ConversationResponse(
                content=legacy_response.get('choices', [{}])[0].get('messages', [{}])[0].get('content', ''),
                conversation_id=legacy_response.get('conversation_id', ''),
                citations=legacy_response.get('citations'),
                usage=legacy_response.get('usage'),
                error=legacy_response.get('error')
            )
        else:
            # ストリーミングレスポンスの場合は非対応（別途実装が必要）
            raise NotImplementedError("Streaming response conversion not implemented in legacy adapter")


# 統合管理のためのサービス組み合わせプロトコル
class UnifiedConversationService(Protocol):
    """
    統合会話サービスプロトコル
    
    ConversationService + 履歴管理 + AI応答生成の統合インターフェース
    """
    
    # ConversationServiceの全メソッドを継承
    async def send_message(self, request: ConversationRequest) -> ConversationResponse: ...
    async def send_message_stream(self, request: ConversationRequest) -> AsyncIterator[StreamChunk]: ...
    async def get_conversation_history(self, conversation_id: str, user: UserPrincipal) -> ConversationData: ...
    async def list_user_conversations(self, user: UserPrincipal, limit: int = 25, offset: int = 0) -> List[ConversationData]: ...
    async def delete_conversation(self, conversation_id: str, user: UserPrincipal) -> bool: ...
    
    # 追加のライフサイクル管理メソッド
    async def create_new_conversation(self, user: UserPrincipal, initial_message: Optional[Message] = None) -> str:
        """新しい会話を作成"""
        ...
    
    async def add_feedback_to_message(self, conversation_id: str, message_id: str, feedback: Dict[str, Any]) -> bool:
        """メッセージにフィードバックを追加"""
        ...
    
    async def regenerate_response(self, conversation_id: str, message_id: str) -> ConversationResponse:
        """応答を再生成"""
        ...


# 便利な関数（既存コードとの互換性）
def create_conversation_request_from_json(
    request_json: Dict[str, Any], 
    user: Optional[UserPrincipal] = None
) -> ConversationRequest:
    """
    JSON辞書からConversationRequestを作成する便利関数
    
    既存app.pyのリクエスト処理との互換性を保持
    
    Args:
        request_json: リクエストJSON辞書
        user: ユーザー主体情報（オプション）
        
    Returns:
        ConversationRequest: 会話リクエスト
    """
    messages = []
    for msg_data in request_json.get('messages', []):
        message = Message(
            role=msg_data.get('role', 'user'),
            content=msg_data.get('content', '')
        )
        messages.append(message)
    
    return ConversationRequest(
        messages=messages,
        conversation_id=request_json.get('conversation_id'),
        user=user,
        stream=request_json.get('stream', True),
        temperature=request_json.get('temperature'),
        max_tokens=request_json.get('max_tokens')
    )


def conversation_response_to_json(response: ConversationResponse) -> Dict[str, Any]:
    """
    ConversationResponseをJSON辞書に変換する便利関数
    
    既存app.pyのレスポンス処理との互換性を保持
    
    Args:
        response: 会話レスポンス
        
    Returns:
        Dict[str, Any]: JSON辞書
    """
    result = {
        'choices': [{
            'messages': [{
                'role': 'assistant',
                'content': response.content
            }]
        }],
        'conversation_id': response.conversation_id
    }
    
    if response.message_id:
        result['message_id'] = response.message_id
    
    if response.citations:
        result['citations'] = response.citations
    
    if response.usage:
        result['usage'] = response.usage
    
    if response.error:
        result['error'] = response.error
    
    return result
