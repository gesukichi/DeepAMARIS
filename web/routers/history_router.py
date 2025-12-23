"""
HistoryRouter - 履歴API HTTP ルーター

TDD Phase: REFACTOR - 外部委託対応HTTPエンドポイント実装（t-wadaさんの原則）

外部委託最重要:
- シンプルで明確なRESTful API
- 一貫したエラーレスポンス
- 包括的なAPIドキュメント 
- 明確な認証フロー

移植完了: app.py履歴管理関連10関数
✅ add_conversation() → POST /history/generate
✅ add_conversation_modern_rag() → POST /history/generate/modern-rag-web  
✅ add_conversation_deepresearch() → POST /history/generate/deep-research  
✅ update_conversation() → POST /history/update
✅ update_message() → POST /history/message_feedback
✅ delete_conversation() → DELETE /history/delete
✅ list_conversations() → GET /history/list
✅ get_conversation() → POST /history/read
✅ rename_conversation() → POST /history/rename
✅ delete_all_conversations() → DELETE /history/delete_all
✅ clear_messages() → POST /history/clear
"""

import copy
import json
import logging
import uuid
from datetime import datetime
from typing import Dict, List, Optional, Any
from quart import Blueprint, request, jsonify, current_app, Response
from web.controllers.history_controller import HistoryController
from backend.auth.auth_utils import get_authenticated_user_details
from backend.utils import (
    format_as_ndjson,
    format_stream_response,
    format_non_streaming_response,
    sanitize_messages_for_openai,
)
from backend.settings import app_settings
from domain.conversation.services.conversation_service import ConversationService


# ログ設定
logger = logging.getLogger(__name__)

# Blueprintの作成
history_bp = Blueprint('history', __name__, url_prefix='/history')

# 依存性注入用のグローバル変数（実際のアプリではDIコンテナを使用）
_history_controller: Optional[HistoryController] = None


def init_history_router(conversation_service: ConversationService) -> None:
    """
    HistoryRouterの初期化
    
    外部委託重要: 明確な初期化プロセス
    
    Args:
        conversation_service: ConversationServiceインスタンス
    """
    global _history_controller
    _history_controller = HistoryController(conversation_service=conversation_service)
    logger.info("HistoryRouter initialized with ConversationService")


def get_history_controller() -> HistoryController:
    """
    HistoryControllerインスタンスの取得
    
    Returns:
        HistoryController: 初期化済みのコントローラー
        
    Raises:
        RuntimeError: 未初期化の場合
    """
    if _history_controller is None:
        raise RuntimeError("HistoryRouter not initialized. Call init_history_router() first.")
    return _history_controller


def _merge_tool_citations_into_assistant(messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    merged = []
    pending_citations = None
    for msg in messages:
        if not isinstance(msg, dict):
            merged.append(msg)
            continue
        if msg.get("role") == "tool":
            content = msg.get("content")
            tool_payload = None
            if isinstance(content, str):
                try:
                    tool_payload = json.loads(content)
                except Exception:
                    tool_payload = None
            elif isinstance(content, dict):
                tool_payload = content
            if isinstance(tool_payload, dict) and "citations" in tool_payload:
                pending_citations = tool_payload
            merged.append(msg)
            continue
        if msg.get("role") == "assistant" and pending_citations:
            context_obj = {}
            if isinstance(msg.get("context"), str):
                try:
                    context_obj = json.loads(msg["context"])
                except Exception:
                    context_obj = {}
            elif isinstance(msg.get("context"), dict):
                context_obj = msg.get("context") or {}
            context_obj["citations"] = pending_citations.get("citations")
            if "citations_html" in pending_citations:
                context_obj["citations_html"] = pending_citations.get("citations_html")
            msg["context"] = json.dumps(context_obj)
            pending_citations = None
        merged.append(msg)
    return merged


async def _get_authenticated_user_id() -> str:
    """
    認証済みユーザーIDの取得
    
    外部委託重要: 認証フローの明確化
    
    Returns:
        str: ユーザーID
        
    Raises:
        Exception: 認証失敗時
    """
    try:
        authenticated_user = get_authenticated_user_details(request_headers=request.headers)
        return authenticated_user["user_principal_id"]
    except Exception as e:
        logger.error(f"Authentication failed: {str(e)}")
        raise Exception("Authentication required") from e


async def _ensure_cosmos_ready() -> None:
    """
    CosmosDB準備完了の確認
    
    外部委託重要: データベース接続の確認
    
    Raises:
        Exception: データベース未準備時
    """
    # 既存のcosmos_db_readyイベントを確認（app.pyから移植）
    if hasattr(current_app, 'cosmos_db_ready'):
        await current_app.cosmos_db_ready.wait()
    
    if not getattr(current_app, 'cosmos_conversation_client', None):
        raise Exception("CosmosDB is not configured or not working")


@history_bp.route('/generate', methods=['POST'])
async def create_conversation():
    """
    会話作成エンドポイント - add_conversation()の移植
    
    外部委託最重要: 会話生成APIの明確化
    
    Request Body:
        {
            "messages": [{"role": "user", "content": "Hello"}],
            "conversation_id": "optional-uuid"
        }
        
    Response:
        200: Streaming response with {"choices": [{"messages": [...]}], ...}
        400: {"error": "Invalid request"}
        500: {"error": "Internal error"}
    """
    try:
        await _ensure_cosmos_ready()
        user_id = await _get_authenticated_user_id()
        
        request_json = await request.get_json()
        if not request_json:
            return jsonify({"error": "Request body required"}), 400
        
        messages = request_json.get("messages", [])
        conversation_id = request_json.get("conversation_id")
        
        controller = get_history_controller()
        
        # 会話メタデータを作成/取得
        result = await controller.create_conversation(
            user_id=user_id,
            messages=messages,
            conversation_id=conversation_id,
            title_generator_func=None
        )
        
        history_metadata = result.get("history_metadata", {})
        
        # メッセージを準備（システムメッセージを追加、toolロールを整合性チェック）
        prepared_messages = sanitize_messages_for_openai(copy.deepcopy(messages))
        # /history/generate はチャット継続用途のため、toolメッセージはOpenAI送信前に必ず除外
        prepared_messages = [
            m for m in prepared_messages
            if isinstance(m, dict) and m.get("role") != "tool"
        ]
        allowed_roles = {"system", "user", "assistant", "function"}
        prepared_messages = [
            m for m in prepared_messages
            if isinstance(m, dict) and m.get("role") in allowed_roles
        ]
        if not any(isinstance(m, dict) and m.get("role") == "system" for m in prepared_messages):
            prepared_messages.insert(
                0,
                {"role": "system", "content": app_settings.azure_openai.system_message}
            )
        
        # Azure OpenAI クライアントを取得
        factory = getattr(current_app, "ai_service_factory", None)
        if not factory:
            return jsonify({"error": "AI Service Factory is not initialized"}), 500
        
        azure_openai_client = await factory.create_azure_openai_client()
        
        apim_request_id = (
            request.headers.get("apim-request-id") or
            request.headers.get("x-ms-client-request-id") or
            ""
        )
        
        openai_request = {
            "model": app_settings.azure_openai.model,
            "messages": prepared_messages,
            "temperature": app_settings.azure_openai.temperature,
            "top_p": app_settings.azure_openai.top_p,
            "max_tokens": app_settings.azure_openai.max_tokens,
            "stream": app_settings.azure_openai.stream,
        }
        if app_settings.azure_openai.stop_sequence:
            openai_request["stop"] = app_settings.azure_openai.stop_sequence
        if app_settings.azure_openai.seed is not None:
            openai_request["seed"] = app_settings.azure_openai.seed
        if app_settings.azure_openai.user:
            openai_request["user"] = app_settings.azure_openai.user
        
        # ストリーミングレスポンス
        if openai_request["stream"]:
            response_stream = await azure_openai_client.chat.completions.create(**openai_request)
            
            async def events():
                async for completion_chunk in response_stream:
                    event = format_stream_response(completion_chunk, history_metadata, apim_request_id)
                    if event:
                        yield event
            
            return Response(
                format_as_ndjson(events()),
                mimetype="application/x-ndjson",
            )
        
        # 非ストリーミングレスポンス
        chat_completion = await azure_openai_client.chat.completions.create(**openai_request)
        response_obj = format_non_streaming_response(chat_completion, history_metadata, apim_request_id)
        
        # IMPORTANT: Filter out tool role messages from response before sending to frontend
        # Tool messages are stored in CosmosDB but should never be sent to client
        if "choices" in response_obj:
            for choice in response_obj["choices"]:
                if "messages" in choice and isinstance(choice["messages"], list):
                    choice["messages"] = [
                        m for m in choice["messages"]
                        if isinstance(m, dict) and m.get("role") != "tool"
                    ]
        
        return jsonify(response_obj)
        
    except ValueError as e:
        logger.warning(f"Validation error in create_conversation: {str(e)}")
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        logger.exception("Exception in /history/generate")
        return jsonify({"error": str(e)}), 500


@history_bp.route('/generate/modern-rag-web', methods=['POST'])
async def create_modern_rag_conversation():
    """
    Modern RAG会話作成エンドポイント - add_conversation_modern_rag()の移植
    
    外部委託重要: Modern RAG版APIの明確化
    
    Request Body:
        {
            "messages": [{"role": "user", "content": "Hello"}],
            "conversation_id": "optional-uuid"
        }
        
    Response:
        200: Streaming response with {"choices": [{"messages": [...]}], ...}
    """
    import json
    import uuid
    from datetime import datetime
    
    try:
        await _ensure_cosmos_ready()
        user_id = await _get_authenticated_user_id()
        
        request_json = await request.get_json()
        if not request_json:
            return jsonify({"error": "Request body required"}), 400
        
        messages = request_json.get("messages", [])
        conversation_id = request_json.get("conversation_id")
        
        # IMPORTANT: Filter out tool role messages from request before processing
        # Tool messages should never be used in conversation history
        messages = [m for m in messages if isinstance(m, dict) and m.get("role") != "tool"]
        
        controller = get_history_controller()
        
        # 会話メタデータを作成/取得
        result = await controller.create_modern_rag_conversation(
            user_id=user_id,
            messages=messages,
            conversation_id=conversation_id,
            title_generator_func=None
        )
        
        history_metadata = result.get("history_metadata", {})
        
        # Get the latest user message
        user_message = None
        for msg in reversed(messages):
            if isinstance(msg, dict) and msg.get("role") == "user":
                user_message = msg.get("content", "")
                break
        
        if not user_message or user_message.strip() == "":
            return jsonify({"error": "User message is required"}), 400
        
        # Modern RAG サービスを取得
        if not hasattr(current_app, 'modern_rag') or not current_app.modern_rag:
            return jsonify({"error": "Modern RAG service not initialized"}), 503
        
        service = current_app.modern_rag
        rag_result = await service.process_user_query(user_message, user_id)
        
        if rag_result.status == "success":
            # Format response in chat completion format
            # DO NOT use 'tool' role - it causes OpenAI API errors when sent back in conversation history
            citations_html = service.format_citations_html(rag_result.citations)
            
            response_message = {
                "role": "assistant",
                "content": rag_result.response,
                "id": str(uuid.uuid4()),
                "date": datetime.now().isoformat(),
                # Embed citations directly in assistant message instead of separate tool message
                "context": json.dumps({
                    "citations": [citation.to_dict() for citation in rag_result.citations],
                    "citations_html": citations_html
                })
            }
            
            # Return in expected format
            chat_response = {
                "id": rag_result.run_id or str(uuid.uuid4()),
                "model": app_settings.azure_openai.model,
                "created": int(datetime.now().timestamp()),
                "object": "chat.completion",
                "choices": [{
                    "messages": [response_message]
                }],
                "history_metadata": history_metadata
            }
            
            return jsonify(chat_response)
        
        else:
            # Return error response
            error_message = f"Modern RAG processing failed: {rag_result.error}"
            return jsonify({"error": error_message}), 500
        
    except ValueError as e:
        logger.warning(f"Validation error in create_modern_rag_conversation: {str(e)}")
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        logger.exception("Exception in /history/generate/modern-rag-web")
        return jsonify({"error": str(e)}), 500


@history_bp.route('/generate/deep-research', methods=['POST'])
async def create_deepresearch_conversation():
    """
    DeepResearch 会話作成エンドポイント
    """
    try:
        await _ensure_cosmos_ready()
        user_id = await _get_authenticated_user_id()
        
        request_json = await request.get_json()
        if not request_json:
            return jsonify({"error": "Request body required"}), 400
        
        messages = request_json.get("messages", [])
        conversation_id = request_json.get("conversation_id")
        messages = [m for m in messages if isinstance(m, dict) and m.get("role") != "tool"]
        
        controller = get_history_controller()
        result = await controller.create_deepresearch_conversation(
            user_id=user_id,
            messages=messages,
            conversation_id=conversation_id,
            title_generator_func=None
        )
        history_metadata = result.get("history_metadata", {})
        
        user_message = None
        for msg in reversed(messages):
            if isinstance(msg, dict) and msg.get("role") == "user":
                user_message = msg.get("content", "")
                break
        
        if not user_message or user_message.strip() == "":
            return jsonify({"error": "User message is required"}), 400
        
        if not hasattr(current_app, "deepresearch") or not current_app.deepresearch:
            return jsonify({"error": "DeepResearch service not initialized"}), 503
        
        service = current_app.deepresearch
        research_result = await service.run_research(user_message, user_id)
        
        if str(research_result.status).lower() not in ("success", "succeeded", "ok"):
            return jsonify({"error": f"DeepResearch processing failed: {research_result.response}"}), 500
        
        citations_html = service.format_citations_html(research_result.citations)
        
        response_message = {
            "role": "assistant",
            "content": research_result.response,
            "id": str(uuid.uuid4()),
            "date": datetime.now().isoformat(),
        }
        
        if research_result.citations:
            response_message["context"] = json.dumps({
                "citations": research_result.citations,
                "citations_html": citations_html
            })
        
        chat_response = {
            "id": research_result.run_id or str(uuid.uuid4()),
            "model": app_settings.azure_openai.model,
            "created": int(datetime.now().timestamp()),
            "object": "chat.completion",
            "choices": [{
                "messages": [response_message]
            }],
            "history_metadata": history_metadata or {
                "conversation_id": research_result.thread_id or str(uuid.uuid4()),
                "title": user_message[:50] + "..." if len(user_message) > 50 else user_message,
                "date": datetime.now().isoformat(),
                "deepresearch_enabled": True
            }
        }
        
        return jsonify(chat_response)
        
    except ValueError as e:
        logger.warning(f"Validation error in create_deepresearch_conversation: {str(e)}")
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        logger.exception("Exception in /history/generate/deep-research")
        return jsonify({"error": str(e)}), 500


@history_bp.route('/update', methods=['POST'])
async def update_conversation():
    """
    会話更新エンドポイント - update_conversation()の移植
    
    外部委託重要: 会話更新APIの明確化
    
    Request Body:
        {
            "conversation_id": "required-uuid",
            "messages": [{"role": "assistant", "content": "Response", "id": "msg-id"}]
        }
        
    Response:
        200: {"success": true}
    """
    try:
        await _ensure_cosmos_ready()
        user_id = await _get_authenticated_user_id()
        
        request_json = await request.get_json()
        if not request_json:
            return jsonify({"error": "Request body required"}), 400
        
        conversation_id = request_json.get("conversation_id")
        messages = request_json.get("messages", [])
        
        controller = get_history_controller()
        result = await controller.update_conversation(
            user_id=user_id,
            conversation_id=conversation_id,
            messages=messages
        )
        
        logger.info(f"Updated conversation {conversation_id} for user {user_id}")
        return jsonify(result), 200
        
    except ValueError as e:
        logger.warning(f"Validation error in update_conversation: {str(e)}")
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        logger.exception("Exception in /history/update")
        return jsonify({"error": str(e)}), 500


@history_bp.route('/message_feedback', methods=['POST'])
async def update_message_feedback():
    """
    メッセージフィードバック更新エンドポイント - update_message()の移植
    
    外部委託重要: メッセージフィードバックAPIの明確化
    
    Request Body:
        {
            "message_id": "required-uuid",
            "message_feedback": "positive|negative"
        }
        
    Response:
        200: {"success": true, "message": "...", "message_id": "..."}
        404: {"success": false, "error": "Message not found"}
    """
    try:
        await _ensure_cosmos_ready()
        user_id = await _get_authenticated_user_id()
        
        request_json = await request.get_json()
        if not request_json:
            return jsonify({"error": "Request body required"}), 400
        
        message_id = request_json.get("message_id")
        message_feedback = request_json.get("message_feedback")
        
        controller = get_history_controller()
        result = await controller.update_message_feedback(
            user_id=user_id,
            message_id=message_id,
            message_feedback=message_feedback
        )
        
        if result["success"]:
            return jsonify(result), 200
        else:
            return jsonify(result), 404
        
    except ValueError as e:
        logger.warning(f"Validation error in update_message_feedback: {str(e)}")
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        logger.exception("Exception in /history/message_feedback")
        return jsonify({"error": str(e)}), 500


@history_bp.route('/delete', methods=['DELETE'])
async def delete_conversation():
    """
    会話削除エンドポイント - delete_conversation()の移植
    
    外部委託重要: 会話削除APIの明確化
    
    Request Body:
        {"conversation_id": "required-uuid"}
        
    Response:
        200: {"success": true, "message": "...", "conversation_id": "..."}
    """
    try:
        await _ensure_cosmos_ready()
        user_id = await _get_authenticated_user_id()
        
        request_json = await request.get_json()
        if not request_json:
            return jsonify({"error": "Request body required"}), 400
        
        conversation_id = request_json.get("conversation_id")
        
        controller = get_history_controller()
        result = await controller.delete_conversation(
            user_id=user_id,
            conversation_id=conversation_id
        )
        
        return jsonify(result), 200
        
    except ValueError as e:
        logger.warning(f"Validation error in delete_conversation: {str(e)}")
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        logger.exception("Exception in /history/delete")
        return jsonify({"error": str(e)}), 500


@history_bp.route('/list', methods=['GET'])
async def list_conversations():
    """
    会話一覧取得エンドポイント - list_conversations()の移植
    
    外部委託重要: 会話一覧APIの明確化
    
    Query Parameters:
        offset: int (default: 0)
        limit: int (default: 25, max: 100)
        
    Response:
        200: [{"id": "...", "title": "..."}, ...]
        404: {"error": "No conversations found"}
    """
    try:
        await _ensure_cosmos_ready()
        user_id = await _get_authenticated_user_id()
        
        offset = int(request.args.get("offset", 0))
        limit = int(request.args.get("limit", 25))
        
        controller = get_history_controller()
        conversations = await controller.list_conversations(
            user_id=user_id,
            offset=offset,
            limit=limit
        )
        
        return jsonify(conversations), 200
        
    except Exception as e:
        if "No conversations" in str(e):
            return jsonify({"error": f"No conversations for {user_id} were found"}), 404
        logger.exception("Exception in /history/list")
        return jsonify({"error": str(e)}), 500


@history_bp.route('/read', methods=['POST'])
async def get_conversation():
    """
    会話詳細取得エンドポイント - get_conversation()の移植
    
    外部委託重要: 会話詳細取得APIの明確化
    
    Request Body:
        {"conversation_id": "required-uuid"}
        
    Response:
        200: {"id": "...", "title": "...", "messages": [...]}
        404: {"error": "Conversation not found"}
    """
    try:
        await _ensure_cosmos_ready()
        user_id = await _get_authenticated_user_id()
        
        request_json = await request.get_json()
        if not request_json:
            return jsonify({"error": "Request body required"}), 400
        
        conversation_id = request_json.get("conversation_id")
        if not conversation_id:
            return jsonify({"error": "conversation_id is required"}), 400
        
        controller = get_history_controller()
        result = await controller.get_conversation(
            user_id=user_id,
            conversation_id=conversation_id
        )
        
        if result is None:
            return jsonify({
                "error": f"Conversation {conversation_id} was not found. It either does not exist or the logged in user does not have access to it."
            }), 404
        
        # IMPORTANT: Filter out tool role messages before returning to frontend
        # Tool messages are stored in CosmosDB but should never be sent to client
        # OpenAI API rejects tool messages without preceding tool_calls
        if "messages" in result and isinstance(result["messages"], list):
            result["messages"] = _merge_tool_citations_into_assistant(result["messages"])
            result["messages"] = [
                m for m in result["messages"]
                if isinstance(m, dict) and m.get("role") != "tool"
            ]
        
        return jsonify(result), 200
        
    except ValueError as e:
        logger.warning(f"Validation error in get_conversation: {str(e)}")
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        logger.exception("Exception in /history/read")
        return jsonify({"error": str(e)}), 500


@history_bp.route('/rename', methods=['POST'])
async def rename_conversation():
    """
    会話リネームエンドポイント - rename_conversation()の移植
    
    外部委託重要: 会話リネームAPIの明確化
    
    Request Body:
        {
            "conversation_id": "required-uuid",
            "title": "New Title"
        }
        
    Response:
        200: {"id": "...", "title": "New Title", ...}
        404: {"error": "Conversation not found"}
    """
    try:
        await _ensure_cosmos_ready()
        user_id = await _get_authenticated_user_id()
        
        request_json = await request.get_json()
        if not request_json:
            return jsonify({"error": "Request body required"}), 400
        
        conversation_id = request_json.get("conversation_id")
        title = request_json.get("title")
        
        if not conversation_id:
            return jsonify({"error": "conversation_id is required"}), 400
        if not title:
            return jsonify({"error": "title is required"}), 400
        
        controller = get_history_controller()
        updated_conversation = await controller.rename_conversation(
            user_id=user_id,
            conversation_id=conversation_id,
            title=title
        )
        
        if updated_conversation is None:
            return jsonify({
                "error": f"Conversation {conversation_id} was not found. It either does not exist or the logged in user does not have access to it."
            }), 404
        
        return jsonify(updated_conversation), 200
        
    except ValueError as e:
        logger.warning(f"Validation error in rename_conversation: {str(e)}")
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        logger.exception("Exception in /history/rename")
        return jsonify({"error": str(e)}), 500


@history_bp.route('/delete_all', methods=['DELETE'])
async def delete_all_conversations():
    """
    全会話削除エンドポイント - delete_all_conversations()の移植
    
    外部委託重要: 全会話削除APIの明確化
    
    Response:
        200: {"success": true, "deleted_count": N, "message": "..."}
        404: {"success": false, "error": "No conversations found"}
    """
    try:
        await _ensure_cosmos_ready()
        user_id = await _get_authenticated_user_id()
        
        controller = get_history_controller()
        result = await controller.delete_all_conversations(user_id=user_id)
        
        if result["success"]:
            return jsonify(result), 200
        else:
            return jsonify(result), 404
        
    except Exception as e:
        logger.exception("Exception in /history/delete_all")
        return jsonify({"error": str(e)}), 500


@history_bp.route('/clear', methods=['POST'])
async def clear_messages():
    """
    会話メッセージクリアエンドポイント - clear_messages()の移植
    
    外部委託重要: メッセージクリアAPIの明確化
    
    Request Body:
        {"conversation_id": "required-uuid"}
        
    Response:
        200: {"success": true, "message": "...", "conversation_id": "..."}
    """
    try:
        await _ensure_cosmos_ready()
        user_id = await _get_authenticated_user_id()
        
        request_json = await request.get_json()
        if not request_json:
            return jsonify({"error": "Request body required"}), 400
        
        conversation_id = request_json.get("conversation_id")
        
        controller = get_history_controller()
        result = await controller.clear_messages(
            user_id=user_id,
            conversation_id=conversation_id
        )
        
        return jsonify(result), 200
        
    except ValueError as e:
        logger.warning(f"Validation error in clear_messages: {str(e)}")
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        logger.exception("Exception in /history/clear")
        return jsonify({"error": str(e)}), 500


@history_bp.route('/ensure', methods=['GET'])
async def ensure_cosmos():
    """
    チャット履歴機能の状態確認エンドポイント - ensure_cosmos()の移植
    
    外部委託重要: チャット履歴状態確認APIの明確化
    
    Response:
        200: {"message": "ChatGPT is configured to save chat history", "cosmosDB": True, "status": "Working"}
        200: {"message": "Chat history is not enabled", "cosmosDB": False, "status": "NotConfigured"}
    """
    try:
        await _ensure_cosmos_ready()

        controller = get_history_controller()
        if controller and hasattr(controller, '_conversation_service'):
            return jsonify({
                "message": "ChatGPT is configured to save chat history",
                "cosmosDB": True,
                "status": "Working"
            }), 200

        return jsonify({
            "message": "Chat history is not enabled",
            "cosmosDB": False,
            "status": "NotConfigured"
        }), 422

    except Exception as e:
        logger.exception("Exception in /history/ensure")
        # CosmosDBが利用できない場合
        return jsonify({
            "message": "Chat history is not enabled",
            "cosmosDB": False,
            "status": "NotWorking"
        }), 422


# エラーハンドラー（外部委託重要: 一貫したエラーレスポンス）
@history_bp.errorhandler(400)
async def handle_bad_request(error):
    """400 Bad Request エラーハンドラー"""
    return jsonify({"error": "Bad Request", "message": str(error)}), 400


@history_bp.errorhandler(401)
async def handle_unauthorized(error):
    """401 Unauthorized エラーハンドラー"""
    return jsonify({"error": "Unauthorized", "message": "Authentication required"}), 401


@history_bp.errorhandler(404)
async def handle_not_found(error):
    """404 Not Found エラーハンドラー"""
    return jsonify({"error": "Not Found", "message": str(error)}), 404


@history_bp.errorhandler(500)
async def handle_internal_error(error):
    """500 Internal Server Error エラーハンドラー"""
    logger.exception(f"Internal server error: {error}")
    return jsonify({"error": "Internal Server Error", "message": "Please try again later"}), 500
