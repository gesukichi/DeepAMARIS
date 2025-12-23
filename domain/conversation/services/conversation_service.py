"""
ConversationService - 統合会話サービス（TDD REFACTOR Phase）

Phase 2C Task 1: app.pyの会話関連機能を新アーキテクチャに統合

t-wadaさんのテスト駆動開発原則:
1. RED Phase: まず失敗するテストを書く ✅ 完了
2. GREEN Phase: テストを通すための最小実装 ✅ 完了
3. REFACTOR Phase: コードの品質向上 🔄 進行中

REFACTOR Phase目標:
- 型安全性の強化
- エラーハンドリングの改善
- パフォーマンス最適化
- コードの可読性向上
- ドキュメント品質向上
"""

import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, Union
from collections.abc import AsyncGenerator
from dataclasses import dataclass, field
import asyncio

# 既存サービスのインポート（Phase 2B実装済み）
from infrastructure.services.configuration_service import ConfigurationService
from infrastructure.formatters.response_formatter import ResponseFormatter  
from infrastructure.services.ai_processing_service import AIProcessingService
from application.conversation.use_cases.orchestrate_conversation import ConversationOrchestrator

# from domain.conversation.models.message import Message
# from domain.conversation.models.ai_response import AIResponse

logger = logging.getLogger(__name__)


@dataclass
class ConversationRequest:
    """
    統合会話リクエスト（REFACTOR Phase）
    
    型安全性とバリデーション強化:
    - 必須フィールドと任意フィールドの明確化
    - デフォルト値の最適化
    - 入力検証の追加
    """
    messages: List[Dict[str, Any]]
    stream: bool = False
    conversation_id: Optional[str] = None
    user_id: Optional[str] = None
    temperature: Optional[float] = field(default=None)
    max_tokens: Optional[int] = field(default=None)
    # Modern RAG対応
    approach: Optional[str] = None
    overrides: Optional[Dict[str, Any]] = field(default_factory=dict)
    
    def __post_init__(self):
        """入力バリデーション（REFACTOR Phase追加）"""
        if not self.messages:
            raise ValueError("Messages cannot be empty")
        
        if self.temperature is not None and not (0.0 <= self.temperature <= 2.0):
            raise ValueError("Temperature must be between 0.0 and 2.0")
        
        if self.max_tokens is not None and self.max_tokens <= 0:
            raise ValueError("Max tokens must be positive")


@dataclass  
class ConversationResponse:
    """
    統合会話レスポンス（REFACTOR Phase）
    
    明確なフィールド定義とデフォルト値:
    - OpenAI互換性の保証
    - Modern RAG対応フィールド
    - ストリーミング対応の明確化
    """
    content: str
    role: str = "assistant"
    conversation_id: Optional[str] = None
    # OpenAI互換フィールド
    choices: Optional[List[Dict[str, Any]]] = field(default_factory=list)
    usage: Optional[Dict[str, Any]] = field(default_factory=dict)
    # Modern RAG対応
    citations: Optional[List[Dict[str, Any]]] = field(default_factory=list)
    data_points: Optional[List[str]] = field(default_factory=list)
    # ストリーミング対応
    is_stream: bool = False
    delta: Optional[Dict[str, Any]] = field(default_factory=dict)


class IConversationService(ABC):
    """統合会話サービスインターフェース"""
    
    @abstractmethod
    async def handle_conversation_request(
        self, 
        request: ConversationRequest,
        headers: Optional[Dict[str, str]] = None
    ) -> ConversationResponse:
        """
        統合会話処理メイン関数
        
        conversation_internal, modern_rag_web_conversation_internalの
        統合インターフェース
        """
        raise NotImplementedError("Interface method")
    
    @abstractmethod
    async def complete_chat_request(
        self,
        request_body: Dict[str, Any],
        headers: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """
        非ストリーミングチャット処理
        
        app.pyのcomplete_chat_request移植
        """
        raise NotImplementedError("Interface method")
    
    @abstractmethod
    async def stream_chat_request(
        self,
        request_body: Dict[str, Any],
        headers: Optional[Dict[str, str]] = None
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        ストリーミングチャット処理
        
        app.pyのstream_chat_request移植
        """
        # AsyncGeneratorのインターフェース定義のため
        if False:  # pragma: no cover
            yield {}
        raise NotImplementedError("Interface method")
    
    @abstractmethod
    async def send_chat_request(
        self,
        messages: List[Dict[str, Any]],
        model_args: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        基本チャット送信処理
        
        app.pyのsend_chat_request移植
        """
        raise NotImplementedError("Interface method")


class ConversationService(IConversationService):
    """
    統合会話サービス実装
    
    TDD GREEN Phase: 既存サービスを活用した最小実装
    Phase 2Bのサービスを統合してapp.pyの機能を移植
    """
    
    def __init__(
        self,
        # 依存サービス（Phase 2Bで実装済み）
        configuration_service: Optional[ConfigurationService] = None,
        response_formatter: Optional[ResponseFormatter] = None,
        ai_processing_service: Optional[AIProcessingService] = None,
        conversation_orchestrator: Optional[ConversationOrchestrator] = None,
        # 新規サービス（Task 2-3で実装予定）
        history_manager=None,
        ai_response_generator=None,
        message_processor=None
    ):
        """
        ConversationService初期化（REFACTOR Phase）
        
        改善点:
        - 型ヒントの追加
        - 依存性検証の強化
        - エラーハンドリングの改善
        - ログ機能の強化
        """
        try:
            logger.info("ConversationService initialization started")
            
            # Phase 2B実装済みサービスの初期化（依存性検証付き）
            self._configuration_service = configuration_service or ConfigurationService()
            self._response_formatter = response_formatter or ResponseFormatter()
            self._ai_processing_service = ai_processing_service or AIProcessingService(self._configuration_service)
            self._conversation_orchestrator = conversation_orchestrator or ConversationOrchestrator(
                configuration_service=self._configuration_service,
                response_formatter=self._response_formatter,
                ai_processing_service=self._ai_processing_service
            )
            
            # 依存性検証（REFACTOR Phase追加）
            self._validate_dependencies()
            
            # 新規サービス（後で実装）
            self._history_manager = history_manager
            self._ai_response_generator = ai_response_generator
            self._message_processor = message_processor
            
            logger.info("ConversationService initialized successfully with all dependencies")
            
        except Exception as e:
            logger.error(f"ConversationService initialization failed: {e}")
            raise RuntimeError(f"Failed to initialize ConversationService: {e}") from e
    
    def _validate_dependencies(self) -> None:
        """依存性検証（REFACTOR Phase追加）"""
        required_services = {
            "_configuration_service": ConfigurationService,
            "_response_formatter": ResponseFormatter,
            "_ai_processing_service": AIProcessingService,
            "_conversation_orchestrator": ConversationOrchestrator
        }
        
        for attr_name, expected_type in required_services.items():
            service = getattr(self, attr_name, None)
            # テスト環境では Mock オブジェクトを許可
            # 実装クラスまたは Mock オブジェクトのいずれかを受け入れる
            if not (isinstance(service, expected_type) or hasattr(service, '_mock_name')):
                raise TypeError(f"{attr_name} must be an instance of {expected_type.__name__} or a Mock object")
    
    async def handle_conversation_request(
        self, 
        request: ConversationRequest,
        headers: Optional[Dict[str, str]] = None
    ) -> ConversationResponse:
        """
        統合会話処理メイン関数（REFACTOR Phase）
        
        改善点:
        - 入力バリデーション強化
        - エラーハンドリング改善
        - パフォーマンス最適化
        - ログ機能強化
        """
        start_time = asyncio.get_event_loop().time()
        request_id = f"{request.conversation_id or 'temp'}_{start_time:.3f}"
        
        try:
            logger.info(f"[{request_id}] handle_conversation_request started: {len(request.messages)} messages, stream={request.stream}")
            
            # 入力バリデーション（__post_init__で基本検証済み、追加検証）
            self._validate_request(request)
            
            # ConversationRequestをdict形式に変換（既存システム互換性）
            request_body = self._build_request_body(request)
            
            # 既存のConversationOrchestratorを活用
            result = await self._conversation_orchestrator.handle_conversation_request_with_app_integration(
                request_body, headers or {}
            )
            
            # 結果をConversationResponseに変換
            response = self._build_response(result, request)
            
            elapsed_time = asyncio.get_event_loop().time() - start_time
            logger.info(f"[{request_id}] handle_conversation_request completed successfully in {elapsed_time:.3f}s")
            return response
            
        except ValueError as e:
            # バリデーションエラー
            logger.warning(f"[{request_id}] Validation error: {e}")
            return self._create_error_response(f"Invalid request: {str(e)}", request)
        except Exception as e:
            # その他のエラー
            elapsed_time = asyncio.get_event_loop().time() - start_time
            logger.error(f"[{request_id}] handle_conversation_request failed after {elapsed_time:.3f}s: {e}")
            return self._create_error_response(f"Internal error: {str(e)}", request)
    
    def _validate_request(self, request: ConversationRequest) -> None:
        """リクエスト詳細バリデーション（REFACTOR Phase追加）"""
        # メッセージ構造検証
        for i, message in enumerate(request.messages):
            if not isinstance(message, dict):
                raise ValueError(f"Message {i} must be a dictionary")
            if "role" not in message or "content" not in message:
                raise ValueError(f"Message {i} must have 'role' and 'content' fields")
            if message["role"] not in ["user", "assistant", "system"]:
                raise ValueError(f"Message {i} has invalid role: {message['role']}")
    
    def _build_request_body(self, request: ConversationRequest) -> Dict[str, Any]:
        """リクエストボディ構築（REFACTOR Phase分離）"""
        request_body = {
            "messages": request.messages,
            "stream": request.stream,
            "conversation_id": request.conversation_id,
            "user_id": request.user_id,
        }
        
        # 任意パラメータの追加（None値を除外）
        optional_params = {
            "temperature": request.temperature,
            "max_tokens": request.max_tokens,
            "approach": request.approach,
        }
        
        for key, value in optional_params.items():
            if value is not None:
                request_body[key] = value
        
        # overridesの追加（空でない場合のみ）
        if request.overrides:
            request_body["overrides"] = request.overrides
        
        return request_body
    
    def _build_response(self, result: Dict[str, Any], request: ConversationRequest) -> ConversationResponse:
        """レスポンス構築（REFACTOR Phase分離）"""
        return ConversationResponse(
            content=result.get("content", ""),
            role=result.get("role", "assistant"),
            conversation_id=request.conversation_id,
            choices=result.get("choices", []),
            usage=result.get("usage", {}),
            citations=result.get("citations", []),
            data_points=result.get("data_points", []),
            is_stream=request.stream
        )
    
    def _create_error_response(self, error_message: str, request: ConversationRequest) -> ConversationResponse:
        """エラーレスポンス作成（REFACTOR Phase分離）"""
        return ConversationResponse(
            content=error_message,
            role="assistant",
            conversation_id=request.conversation_id,
            is_stream=request.stream
        )
    
    async def complete_chat_request(
        self,
        request_body: Dict[str, Any],
        headers: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """
        非ストリーミングチャット処理（REFACTOR Phase）
        
        改善点:
        - 入力バリデーション追加
        - エラーハンドリング強化
        - パフォーマンス監視
        """
        start_time = asyncio.get_event_loop().time()
        
        try:
            logger.info("complete_chat_request started")
            
            # 入力バリデーション
            if not isinstance(request_body, dict):
                raise ValueError("Request body must be a dictionary")
            if "messages" not in request_body:
                raise ValueError("Request body must contain 'messages'")
            
            # ストリーミングフラグを明示的に無効化
            request_body = request_body.copy()
            request_body["stream"] = False
            
            # AIProcessingServiceによる処理
            result = await self._ai_processing_service.process_complete_request(
                request_body, headers or {}
            )
            
            elapsed_time = asyncio.get_event_loop().time() - start_time
            logger.info(f"complete_chat_request completed successfully in {elapsed_time:.3f}s")
            return result
            
        except ValueError as e:
            logger.warning(f"complete_chat_request validation error: {e}")
            return {"error": f"Invalid request: {str(e)}"}
        except Exception as e:
            elapsed_time = asyncio.get_event_loop().time() - start_time
            logger.error(f"complete_chat_request failed after {elapsed_time:.3f}s: {e}")
            return {"error": f"Internal error: {str(e)}"}
    
    async def stream_chat_request(
        self,
        request_body: Dict[str, Any],
        headers: Optional[Dict[str, str]] = None
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        ストリーミングチャット処理（REFACTOR Phase）
        
        改善点:
        - 入力バリデーション追加
        - エラーハンドリング強化
        - ストリーミング監視
        """
        start_time = asyncio.get_event_loop().time()
        chunk_count = 0
        
        try:
            logger.info("stream_chat_request started")
            
            # 入力バリデーション
            if not isinstance(request_body, dict):
                yield {"error": "Invalid request: Request body must be a dictionary"}
                return
            if "messages" not in request_body:
                yield {"error": "Invalid request: Request body must contain 'messages'"}
                return
            
            # ストリーミングフラグを明示的に有効化
            request_body = request_body.copy()
            request_body["stream"] = True
            
            # AIProcessingServiceによるストリーミング処理
            async for chunk in self._ai_processing_service.process_streaming_request(
                request_body, headers or {}
            ):
                chunk_count += 1
                yield chunk
                
            elapsed_time = asyncio.get_event_loop().time() - start_time
            logger.info(f"stream_chat_request completed successfully: {chunk_count} chunks in {elapsed_time:.3f}s")
            
        except Exception as e:
            elapsed_time = asyncio.get_event_loop().time() - start_time
            logger.error(f"stream_chat_request failed after {elapsed_time:.3f}s, {chunk_count} chunks: {e}")
            yield {"error": f"Internal error: {str(e)}"}
    
    async def send_chat_request(
        self,
        messages: List[Dict[str, Any]],
        model_args: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        基本チャット送信処理（REFACTOR Phase）
        
        改善点:
        - 入力バリデーション追加
        - エラーハンドリング強化
        - パフォーマンス監視
        """
        start_time = asyncio.get_event_loop().time()
        
        try:
            logger.info(f"send_chat_request started with {len(messages)} messages")
            
            # 入力バリデーション
            if not isinstance(messages, list) or not messages:
                raise ValueError("Messages must be a non-empty list")
            if not isinstance(model_args, dict):
                raise ValueError("Model args must be a dictionary")
            
            # リクエストボディを構成
            request_body = {
                "messages": messages,
                **model_args
            }
            
            # complete_chat_requestを内部呼び出し
            result = await self.complete_chat_request(request_body)
            
            elapsed_time = asyncio.get_event_loop().time() - start_time
            logger.info(f"send_chat_request completed successfully in {elapsed_time:.3f}s")
            return result
            
        except ValueError as e:
            logger.warning(f"send_chat_request validation error: {e}")
            return {"error": f"Invalid request: {str(e)}"}
        except Exception as e:
            elapsed_time = asyncio.get_event_loop().time() - start_time
            logger.error(f"send_chat_request failed after {elapsed_time:.3f}s: {e}")
            return {"error": f"Internal error: {str(e)}"}
