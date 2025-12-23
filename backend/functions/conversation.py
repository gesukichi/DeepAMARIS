"""
Azure Functions Conversation Adapter Layer Implementation

TDD Phase 3C REFACTOR Phase: 新アーキテクチャとの統合
t-wadaさんのテスト駆動開発原則に従った実装

目的: app.pyの/conversationエンドポイントをAzure Functions化するアダプター層
Phase 3C: ConversationService, UserServiceとの統合
"""

import json
import time
import logging
from typing import Dict, Any, Optional, Union
import asyncio

# Azure Functions の条件付きインポート（テスト時は None）
try:
    import azure.functions as func
    AZURE_FUNCTIONS_AVAILABLE = True
except ImportError:
    func = None
    AZURE_FUNCTIONS_AVAILABLE = False

# Phase 3C: 新しいアーキテクチャのサービス層インポート
from domain.conversation.services.conversation_service import ConversationService
from domain.conversation.interfaces.conversation_service_interface import ConversationRequest
from domain.user.services.user_service import UserService
from domain.user.services.auth_service import AuthService
from domain.user.interfaces.auth_service import AuthenticationError
from domain.user.models.user import User
from domain.user.interfaces.auth_service import UserPrincipal

# ログ設定
logger = logging.getLogger(__name__)


class HttpRequest:
    """テスト用のHTTPリクエストクラス（search_proxy.py パターン準拠）"""
    def __init__(self, method: str, headers: Dict[str, str] = None, body: Any = None):
        self.method = method
        self.headers = headers or {}
        self._body = body
    
    def get_json(self) -> Dict[str, Any]:
        if isinstance(self._body, dict):
            return self._body
        elif isinstance(self._body, str):
            return json.loads(self._body)
        else:
            raise ValueError("Invalid JSON")


class HttpResponse:
    """テスト用のHTTPレスポンスクラス（search_proxy.py パターン準拠）"""
    def __init__(self, body: str, status_code: int = 200, mimetype: str = "application/json"):
        self._body = body
        self.status_code = status_code
        self.mimetype = mimetype
    
    def get_body(self) -> str:
        return self._body


async def main(req: Union[Any, HttpRequest]) -> Union[Any, HttpResponse]:
    """
    Azure Functions HTTP Trigger Entry Point
    
    TDD Phase 3C REFACTOR: 新しいアーキテクチャとの統合
    
    Args:
        req: HTTPリクエスト
        
    Returns:
        HTTPレスポンス
    """
    start_time = time.time()
    request_id = req.headers.get('x-request-id', f"conv-req-{int(start_time * 1000)}")
    
    logger.info(f"[{request_id}] Conversation function request received")
    
    try:
        # 1. リクエスト形式の検証
        if req.method != "POST":
            return _create_response(
                {"error": {"code": "MethodNotAllowed", "message": "Only POST method is supported"}},
                405
            )
        
        # 2. 認証: EasyAuthヘッダー必須（開発フォールバックを禁止）
        headers = dict(req.headers) if hasattr(req, 'headers') else {}
        principal_id = headers.get("X-Ms-Client-Principal-Id")
        if not principal_id:
            return _create_response(
                {"error": {"code": "Unauthorized", "message": "EasyAuth headers are required"}},
                401
            )

        try:
            auth_service = AuthService()
            user_principal = auth_service.get_user_principal(headers)
            if not user_principal or not user_principal.user_principal_id:
                return _create_response(
                    {"error": {"code": "Unauthorized", "message": "Invalid authorization token"}},
                    401
                )
        except AuthenticationError as e:
            logger.warning(f"[{request_id}] Authentication failed: {e}")
            return _create_response(
                {"error": {"code": "Unauthorized", "message": "Authentication failed"}},
                401
            )
        except Exception as e:
            logger.error(f"[{request_id}] Authentication error: {e}")
            return _create_response(
                {"error": {"code": "Unauthorized", "message": "Authentication failed"}},
                401
            )
        
        # 3. JSONペイロードの解析
        try:
            request_data = req.get_json()
        except ValueError as e:
            logger.error(f"[{request_id}] Invalid JSON: {e}")
            return _create_response(
                {"error": {"code": "InvalidJson", "message": "Invalid JSON format"}},
                400
            )
        
        # 4. Phase 3C: 新しいサービス層への委譲（アダプター層として機能）
        try:
            # 既存のリクエスト形式をConversationServiceに渡す
            request_body = {
                "messages": request_data.get("messages", []),
                "conversation_id": request_data.get("conversation_id"),
                "user_id": user_principal.user_principal_id if user_principal else None,
                "stream": request_data.get("stream", False),
                "temperature": request_data.get("temperature"),
                "max_tokens": request_data.get("max_tokens"),
                "approach": request_data.get("approach"),
                "overrides": request_data.get("overrides", {})
            }
            
            # Phase 3C: ConversationServiceの既存メソッドを使用
            conversation_service = ConversationService()
            if request_body.get("stream", False):
                # ストリーミングレスポンス（現在は非対応、将来の拡張用）
                result = await conversation_service.complete_chat_request(
                    request_body,
                    headers=dict(req.headers) if hasattr(req, 'headers') else {}
                )
            else:
                # 通常のレスポンス
                result = await conversation_service.complete_chat_request(
                    request_body,
                    headers=dict(req.headers) if hasattr(req, 'headers') else {}
                )
            
            elapsed_ms = int((time.time() - start_time) * 1000)
            
            logger.info(f"[{request_id}] Conversation completed successfully in {elapsed_ms}ms")
            
            return _create_response(result, 200)
            
        except Exception as e:
            logger.error(f"[{request_id}] Service layer error: {e}")
            return _create_response({
                "error": {
                    "code": "InternalServerError",
                    "message": "An internal server error occurred"
                }
            }, 500)
    
    except Exception as e:
        logger.error(f"[{request_id}] Critical error: {e}")
        return _create_response({
            "error": {
                "code": "CriticalError",
                "message": "A critical error occurred"
            }
        }, 500)


def _create_response(data: Dict[str, Any], status_code: int) -> Union[Any, HttpResponse]:
    """HTTPレスポンスを作成（search_proxy.py パターン準拠）"""
    body = json.dumps(data)
    
    if AZURE_FUNCTIONS_AVAILABLE and func:
        return func.HttpResponse(
            body,
            status_code=status_code,
            mimetype="application/json"
        )
    else:
        return HttpResponse(
            body,
            status_code=status_code,
            mimetype="application/json"
        )


# Azure Functions での使用のためのエクスポート
__all__ = ["main"]
