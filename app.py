import copy
import json
import os
import logging
import uuid
import asyncio
import sys
from datetime import datetime
from typing import Tuple, Any, Optional
from quart import (
    Blueprint,
    Quart,
    jsonify,
    make_response,
    request,
    send_from_directory,
    render_template,
    current_app,
    Response,
)

from openai import AsyncAzureOpenAI
from azure.identity.aio import (
    DefaultAzureCredential,
    get_bearer_token_provider
)

# Key Vault imports for secure secret management
from azure.keyvault.secrets import SecretClient
from azure.identity import DefaultAzureCredential as SyncDefaultAzureCredential, ManagedIdentityCredential

# AI Service Factory import for OpenAI client management
from infrastructure.factories.ai_service_factory import create_ai_service_factory

# Initialize logging first to prevent issues
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# Task 20: Feature flag service integration for gradual deployment strategy
# Graceful import to prevent hard dependency
try:
    from application.configuration.phase4_feature_flags import Phase4FeatureFlags
    FeatureFlagService = Phase4FeatureFlags
    logging.info("Phase 4 feature flag service imported successfully")
except ImportError as e:
    FeatureFlagService = None
    logging.warning(f"Feature flag service not available - continuing without feature flags: {e}")

# Phase 4 Day 5: 認証機能削除 - backend.auth.auth_utilsインポート削除済み
from backend.security.ms_defender_utils import get_msdefender_user_json
from backend.history.cosmosdbservice import CosmosConversationClient

# HTTPステータスコード管理システム
from common.http_status import (
    HTTPStatus,
    HTTPStatusManager,
    create_success_response,
    create_error_response,
    create_not_found_response,
    create_unauthorized_response,
    create_forbidden_response,
    create_server_error_response,
    create_service_unavailable_response
)
from backend.history.conversation_service import ConversationHistoryService, ConversationTitleGenerator
from backend.keyvault_utils import KeyVaultService
from backend.settings import (
    app_settings,
    MINIMUM_SUPPORTED_AZURE_OPENAI_PREVIEW_API_VERSION
)
from backend.utils import (
    format_as_ndjson,
    format_stream_response,
    format_non_streaming_response,
    sanitize_messages_for_openai,
    convert_to_pf_format,
    format_pf_non_streaming_response,
)
from backend.deep_research_service import (
    create_service_from_env,
    DeepResearchResult,
    DeepResearchService,
)
from domain.user.services.auth_service import AuthService
from domain.user.interfaces.auth_service import AuthenticationError

# TDD: 削除した履歴エンドポイントを新しいルーターで復元
from web.routers.history_router import history_bp, init_history_router

# ==========================================
# グローバル変数・定数 (Global Variables & Constants)
# ==========================================

bp = Blueprint("routes", __name__, static_folder="static", template_folder="static")

cosmos_db_ready = asyncio.Event()

# Key Vault client for secure secret management
keyvault_client = None

# テスト関数のモック（セキュリティ分離）
mock_chat_response = None
mock_modern_rag_web_response = None

# TDD Phase 4: Key Vault統合サービス層
keyvault_service = None

# Task 20: フィーチャーフラグサービス統合
feature_flag_service = None

# 新アーキテクチャ: 履歴管理サービスのグローバルインスタンス
conversation_history_service = None
conversation_title_generator = None

azure_openai_tools = []
azure_openai_available_tools = []

# Authentication service (enforce production auth headers)
auth_service = AuthService()

# Debug settings - Configure logging level based on environment
DEBUG = os.environ.get("DEBUG", "false")
IS_PRODUCTION = os.environ.get("AZURE_ENV_NAME", "").startswith(("prod", "production")) or os.environ.get("BACKEND_URI", "").startswith("https://")

# Reconfigure logging level based on environment
if DEBUG.lower() == "true" and not IS_PRODUCTION:
    logging.getLogger().setLevel(logging.DEBUG)
elif IS_PRODUCTION:
    # Force production logging level regardless of DEBUG setting
    logging.getLogger().setLevel(logging.WARNING)
else:
    logging.getLogger().setLevel(logging.INFO)

USER_AGENT = "GitHubSampleWebApp/AsyncAzureOpenAI/1.0.0"

# Frontend Settings via Environment Variables
private_networking_enabled = os.environ.get("ENABLE_PRIVATE_NETWORKING", "false").lower() == "true"
cosmosdb_configured = (
    os.environ.get("AZURE_COSMOSDB_ACCOUNT") and 
    os.environ.get("AZURE_COSMOSDB_DATABASE")
)

try:
    frontend_settings = {
        "auth_enabled": getattr(app_settings.base_settings, 'auth_enabled', False),
        "feedback_enabled": (
            app_settings.chat_history and
            getattr(app_settings.chat_history, 'enable_feedback', False) and
            cosmosdb_configured
        ),
        "ui": {
            "title": getattr(app_settings.ui, 'title', 'Contoso'),
            "logo": getattr(app_settings.ui, 'logo', None),
            "chat_logo": getattr(app_settings.ui, 'chat_logo', None) or getattr(app_settings.ui, 'logo', None),
            "chat_title": getattr(app_settings.ui, 'chat_title', 'Start chatting'),
            "chat_description": "プライベートネットワーク設定のため、一部機能を調整中です。基本的なチャット機能は利用可能です。" if private_networking_enabled else getattr(app_settings.ui, 'chat_description', 'This chatbot is configured to answer your questions'),
            "show_share_button": getattr(app_settings.ui, 'show_share_button', True),
            "show_chat_history_button": cosmosdb_configured and getattr(app_settings.ui, 'show_chat_history_button', True),
        },
        "sanitize_answer": getattr(app_settings.base_settings, 'sanitize_answer', True),
        "oyd_enabled": getattr(app_settings.base_settings, 'datasource_type', None),
    }
except Exception as e:
    logging.warning(f"Failed to initialize frontend settings, using defaults: {e}")
    frontend_settings = {
        "auth_enabled": False,
        "feedback_enabled": False,
        "ui": {
            "title": " ",
            "logo": None,
            "chat_logo": None,
            "chat_title": "Start chatting",
            "chat_description": "プライベートネットワーク設定のため、一部機能を調整中です。基本的なチャット機能は利用可能です。" if private_networking_enabled else "This chatbot is configured to answer your questions",
            "show_share_button": True,
            "show_chat_history_button": False,
        },
        "sanitize_answer": True,
        "oyd_enabled": None,
    }

# Enable Microsoft Defender for Cloud Integration
MS_DEFENDER_ENABLED = os.environ.get("MS_DEFENDER_ENABLED", "true").lower() == "true"


# ==========================================
# 初期化関数群 (Initialization Functions)
# ==========================================

def init_keyvault_service():
    """
    TDD Phase 4: 新しいKey Vaultサービス層の初期化
    """
    global keyvault_service
    try:
        keyvault_service = KeyVaultService.from_environment()
        logging.info("Key Vault service initialized successfully")
        return True
    except Exception as e:
        logging.warning(f"Key Vault service initialization failed: {e}")
        keyvault_service = None
        return False


def init_feature_flag_service():
    """
    Task 20: フィーチャーフラグサービス初期化
    
    t-wadaさんのTDD原則に従った統合実装
    テスト容易性を考慮した初期化処理
    グレースフルデグラデーション対応
    """
    global feature_flag_service
    
    # フィーチャーフラグサービスが利用可能かチェック
    if FeatureFlagService is None:
        logging.info("Feature flag service not available - skipping initialization")
        feature_flag_service = None
        return False
        
    try:
        feature_flag_service = FeatureFlagService()
        logging.info("Feature flag service initialized successfully")
        logging.info("Feature flag service initialized successfully")
        return True
    except Exception as e:
        logging.warning(f"Feature flag service initialization failed: {e}")
        feature_flag_service = None
        return False


async def init_cosmosdb_client():
    """
    CosmosDB会話クライアントの初期化
    
    チャット履歴機能用のCosmosDBクライアントを設定し、
    マネージドアイデンティティまたはアカウントキーを使用して認証する
    """
    cosmos_conversation_client = None
    if app_settings.chat_history:
        try:
            cosmos_endpoint = (
                f"https://{app_settings.chat_history.account}.documents.azure.com:443/"
            )

            if not app_settings.chat_history.account_key:
                # Use managed identity with explicit client ID
                managed_identity_client_id = os.environ.get("AZURE_CLIENT_ID")
                if managed_identity_client_id:
                    # Use specific managed identity
                    from azure.identity.aio import ManagedIdentityCredential
                    credential = ManagedIdentityCredential(client_id=managed_identity_client_id)
                    logging.info(f"Using managed identity with client ID: {managed_identity_client_id}")
                else:
                    # Fallback to default credential
                    credential = DefaultAzureCredential()
                    logging.info("Using DefaultAzureCredential")
                    
            else:
                credential = app_settings.chat_history.account_key
                logging.info("Using account key for Cosmos DB")

            cosmos_conversation_client = CosmosConversationClient(
                cosmosdb_endpoint=cosmos_endpoint,
                credential=credential,
                database_name=app_settings.chat_history.database,
                container_name=app_settings.chat_history.conversations_container,
                enable_message_feedback=app_settings.chat_history.enable_feedback,
            )
            logging.info("CosmosDB client initialized successfully")
        except Exception as e:
            logging.exception("Exception in CosmosDB initialization", e)
            cosmos_conversation_client = None
            raise e
    else:
        logging.debug("CosmosDB not configured")

    return cosmos_conversation_client


# ==========================================
# ヘルパー・ユーティリティ関数 (Helper & Utility Functions)
# ==========================================

def handle_feature_flag_fallback(
    feature_flag_name: str, 
    controller_import_path: str, 
    controller_class_name: str, 
    controller_method: str, 
    error_context: str
) -> Tuple[bool, Any, bool]:
    """
    フィーチャーフラグ分岐処理の共通化
    
    Args:
        feature_flag_name: フィーチャーフラグ名
        controller_import_path: コントローラーのインポートパス
        controller_class_name: コントローラークラス名
        controller_method: 呼び出すメソッド名
        error_context: エラーコンテキスト（ログ用）
    
    Returns:
        tuple: (success: bool, result: any, should_fallback: bool)
    """
    # Phase4FeatureFlagsクラスとの互換性を確保
    feature_enabled = False
    
    if feature_flag_service:
        if hasattr(feature_flag_service, 'is_enabled'):
            feature_enabled = feature_flag_service.is_enabled(feature_flag_name)
        elif hasattr(feature_flag_service, 'is_new_system_endpoints_enabled') and feature_flag_name in ['new_health_endpoint', 'new_frontend_settings_endpoint', 'new_auth_me_endpoint']:
            # system endpointのフラグとして扱う
            feature_enabled = feature_flag_service.is_new_system_endpoints_enabled()
        elif hasattr(feature_flag_service, 'is_new_conversation_endpoint_enabled') and feature_flag_name == 'new_conversation_endpoint':
            feature_enabled = feature_flag_service.is_new_conversation_endpoint_enabled()
        elif hasattr(feature_flag_service, 'is_new_history_endpoints_enabled') and feature_flag_name in ['new_history_endpoints', 'new_history_endpoint']:
            feature_enabled = feature_flag_service.is_new_history_endpoints_enabled()
        else:
            # Day3: デフォルトケースとして環境変数の直接チェックを追加
            env_mapping = {
                'new_history_endpoints': 'NEW_HISTORY_ENDPOINTS',
                'new_history_endpoint': 'NEW_HISTORY_ENDPOINTS'
            }
            if feature_flag_name in env_mapping:
                import os
                env_value = os.getenv(env_mapping[feature_flag_name], "false").lower()
                feature_enabled = env_value in ("true", "1", "yes", "on")
    
    if not feature_enabled:
        return False, None, True
    
    try:
        # 動的インポート
        module = __import__(controller_import_path, fromlist=[controller_class_name])
        controller_class = getattr(module, controller_class_name)
        controller_instance = controller_class()
        
        # メソッド呼び出し
        method = getattr(controller_instance, controller_method)
        return True, method, False
    except Exception as e:
        logging.warning(
            "New architecture %s failed, falling back to legacy: %s", 
            error_context, e
        )
        return False, None, True

# ==========================================
# エンドポイント関数群 (Endpoint Functions)
# ==========================================

@bp.route("/")
async def index():
    """
    メインページの表示
    """
    return await send_from_directory("static", "index.html")


@bp.route("/favicon.ico")
async def favicon():
    """
    ファビコンの提供
    """
    return await bp.send_static_file("favicon.ico")


@bp.route("/assets/<path:path>")
async def assets(path):
    """
    静的アセットの提供
    """
    return await send_from_directory("static/assets", path)


@bp.route("/healthz", methods=["GET"])
async def healthz():
    """
    軽量ライブネスエンドポイント（外部依存なし）
    プラットフォームプローブ用
    """
    try:
        # Minimal, fast, and side-effect free
        data = {
            "status": "ok",
            "time": datetime.utcnow().isoformat() + "Z"
        }
        response_data, status_code = create_success_response(data)
        return jsonify(response_data), status_code
    except Exception:
        # Should never happen, but keep it explicit
        logging.exception("Exception in /healthz")
        response_data, status_code = create_server_error_response("Health check failed")
        return jsonify(response_data), status_code


@bp.route("/frontend_settings", methods=["GET"])
async def get_frontend_settings():
    """フロントエンド初期化用の設定値を返すシンプルなエンドポイント。"""
    try:
        return jsonify(frontend_settings), HTTPStatus.OK
    except Exception as e:
        logging.warning(f"Failed to serve frontend settings: {e}")
        fallback = {
            "auth_enabled": False,
            "feedback_enabled": False,
            "ui": {
                "title": " ",
                "logo": None,
                "chat_logo": None,
                "chat_title": "Start chatting",
                "chat_description": "This chatbot is configured to answer your questions",
                "show_share_button": True,
                "show_chat_history_button": False,
            },
            "sanitize_answer": True,
            "oyd_enabled": None,
        }
        return jsonify(fallback), HTTPStatus.OK


@bp.route("/conversation", methods=["POST"])
async def conversation():
    """
    Standard conversation endpoint (normal chat mode)
    
    IMPORTANT:
    - This endpoint must NOT use Modern RAG / Web search.
    - Web search is only provided by /conversation/modern-rag-web.
    """
    if not request.is_json:
        response_data, status_code = create_error_response(
            "リクエストはJSON形式である必要があります", 
            HTTPStatus.UNSUPPORTED_MEDIA_TYPE,
            "INVALID_CONTENT_TYPE"
        )
        return jsonify(response_data), status_code

    try:
        request_json = await request.get_json()
    except Exception:
        response_data, status_code = create_error_response(
            "不正なJSONです",
            HTTPStatus.BAD_REQUEST,
            "INVALID_JSON"
        )
        return jsonify(response_data), status_code

    messages = request_json.get("messages", []) if isinstance(request_json, dict) else []
    if not isinstance(messages, list) or len(messages) == 0:
        response_data, status_code = create_error_response(
            "メッセージは必須です",
            HTTPStatus.BAD_REQUEST,
            "MISSING_MESSAGES"
        )
        return jsonify(response_data), status_code

    # Ensure a system message exists (aligns with app_settings defaults)
    # Sanitize tool messages so only valid tool_call_id entries are sent to OpenAI
    prepared_messages = sanitize_messages_for_openai(copy.deepcopy(messages))
    if not any(isinstance(m, dict) and m.get("role") == "system" for m in prepared_messages):
        prepared_messages.insert(
            0,
            {"role": "system", "content": app_settings.azure_openai.system_message}
        )

    # Production detection (keep consistent with other endpoints)
    is_production = (
        os.environ.get("AZURE_ENV_NAME", "").startswith(("prod", "production")) or
        os.environ.get("BACKEND_URI", "").startswith("https://") or
        os.environ.get("WEBSITE_SITE_NAME")
    )

    local_mock_mode = os.environ.get("LOCAL_MOCK_MODE", "false").lower() == "true"
    if local_mock_mode and not is_production and mock_chat_response:
        chat_response = await mock_chat_response({"messages": prepared_messages})
        return jsonify(chat_response)

    # Create Azure OpenAI client (no Modern RAG / Bing grounding here)
    try:
        factory = getattr(current_app, "ai_service_factory", None)
        if not factory:
            raise RuntimeError("AI Service Factory is not initialized")
        azure_openai_client = await factory.create_azure_openai_client()
    except Exception as e:
        # In non-production, fall back to mock response to keep local/dev and CI stable
        if not is_production and mock_chat_response:
            chat_response = await mock_chat_response({"messages": prepared_messages})
            return jsonify(chat_response)

        logging.warning(f"Azure OpenAI client unavailable for /conversation: {e}")
        response_data, status_code = create_service_unavailable_response(
            "Azure OpenAI クライアントが利用できません"
        )
        return jsonify(response_data), status_code

    apim_request_id = (
        request.headers.get("apim-request-id") or
        request.headers.get("x-ms-client-request-id") or
        ""
    )
    history_metadata = request_json.get("history_metadata", {}) if isinstance(request_json, dict) else {}
    if not isinstance(history_metadata, dict):
        history_metadata = {}

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

    try:
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

        chat_completion = await azure_openai_client.chat.completions.create(**openai_request)
        response_obj = format_non_streaming_response(chat_completion, history_metadata, apim_request_id)
        return jsonify(response_obj)

    except Exception as e:
        logging.exception("Exception in /conversation")
        response_data, status_code = create_server_error_response(str(e))
        return jsonify(response_data), status_code


@bp.route("/conversation/deep-research", methods=["POST"])
async def deep_research_conversation():
    """
    DeepResearch integration endpoint
    Proxies user questions to the external deepresearch-func service.
    """
    if not request.is_json:
        response_data, status_code = create_error_response(
            "リクエストはJSON形式である必要があります",
            HTTPStatus.UNSUPPORTED_MEDIA_TYPE,
            "INVALID_CONTENT_TYPE"
        )
        return jsonify(response_data), status_code

    headers = dict(request.headers)
    try:
        principal = auth_service.get_user_principal(headers)
    except AuthenticationError:
        response_data, status_code = create_unauthorized_response("認証に失敗しました")
        return jsonify(response_data), status_code
    except Exception:
        logging.exception("Authentication processing error")
        response_data, status_code = create_unauthorized_response("認証に失敗しました")
        return jsonify(response_data), status_code

    if not principal or not principal.user_principal_id:
        response_data, status_code = create_unauthorized_response("認証ヘッダーが不足しています")
        return jsonify(response_data), status_code

    if not hasattr(current_app, "deepresearch") or not current_app.deepresearch:
        response_data, status_code = create_service_unavailable_response(
            "DeepResearch service not initialized"
        )
        return jsonify(response_data), status_code

    try:
        request_json = await request.get_json()
        messages = request_json.get("messages", [])

        if not messages:
            response_data, status_code = create_error_response(
                "メッセージは必須です",
                HTTPStatus.BAD_REQUEST,
                "MISSING_MESSAGES"
            )
            return jsonify(response_data), status_code

        user_message = None
        for msg in reversed(messages):
            if msg.get("role") == "user":
                user_message = msg.get("content", "")
                break

        if not user_message or (isinstance(user_message, str) and user_message.strip() == ""):
            response_data, status_code = create_error_response(
                "ユーザーメッセージが見つかりません",
                HTTPStatus.BAD_REQUEST,
                "MISSING_USER_MESSAGE"
            )
            return jsonify(response_data), status_code

        service: DeepResearchService = current_app.deepresearch
        result: DeepResearchResult = await service.run_research(user_message, principal.user_principal_id)

        if str(result.status).lower() not in ("success", "succeeded", "ok"):
            response_data, status_code = create_server_error_response(
                f"DeepResearch処理に失敗しました: {result.response}"
            )
            return jsonify(response_data), status_code

        citations_html = service.format_citations_html(result.citations)

        response_message = {
            "role": "assistant",
            "content": result.response,
            "id": str(uuid.uuid4()),
            "date": datetime.now().isoformat(),
        }

        if result.citations:
            response_message["context"] = json.dumps({
                "citations": result.citations,
                "citations_html": citations_html,
            })

        chat_response = {
            "id": result.run_id or str(uuid.uuid4()),
            "model": app_settings.azure_openai.model,
            "created": int(datetime.now().timestamp()),
            "object": "chat.completion",
            "choices": [{
                "messages": [response_message]
            }],
            "history_metadata": {
                "conversation_id": result.thread_id or str(uuid.uuid4()),
                "title": user_message[:50] + "..." if isinstance(user_message, str) and len(user_message) > 50 else user_message,
                "date": datetime.now().isoformat(),
                "deepresearch_enabled": True,
            }
        }

        return jsonify(chat_response)

    except Exception as e:
        logging.exception("Exception in /conversation/deep-research")
        response_data, status_code = create_server_error_response(str(e))
        return jsonify(response_data), status_code


@bp.route("/conversation/modern-rag-web", methods=["POST"])
async def modern_rag_web_conversation():
    """
    Modern RAG + Web Search integration endpoint
    Uses Azure AI Agents Service for intelligent tool selection and unified responses
    """
    if not request.is_json:
        response_data, status_code = create_error_response(
            "リクエストはJSON形式である必要があります", 
            HTTPStatus.UNSUPPORTED_MEDIA_TYPE,
            "INVALID_CONTENT_TYPE"
        )
        return jsonify(response_data), status_code

    # 認証を必須化: EasyAuthヘッダーが無い場合は拒否
    headers = dict(request.headers)
    principal_id = headers.get("X-Ms-Client-Principal-Id")
    try:
        principal = auth_service.get_user_principal(headers)
    except AuthenticationError:
        response_data, status_code = create_unauthorized_response("認証に失敗しました")
        return jsonify(response_data), status_code
    except Exception:
        logging.exception("Authentication processing error")
        response_data, status_code = create_unauthorized_response("認証に失敗しました")
        return jsonify(response_data), status_code

    if not principal_id or not principal or not principal.user_principal_id:
        response_data, status_code = create_unauthorized_response("認証ヘッダーが不足しています")
        return jsonify(response_data), status_code
    
    # プロダクション環境判定
    is_production = (
        os.environ.get("AZURE_ENV_NAME", "").startswith(("prod", "production")) or 
        os.environ.get("BACKEND_URI", "").startswith("https://") or
        os.environ.get("WEBSITE_SITE_NAME")
    )

    # モックは非本番かつ明示的に許可された場合のみ
    use_mock_response = (
        os.environ.get("LOCAL_MOCK_MODE", "false").lower() == "true"
        and not is_production
    )
    
    if use_mock_response:
        request_json = await request.get_json()
        # 段階3セキュリティ分離: モック処理をtests/mock_responses.pyに委譲
        try:
            from tests.mock_responses import handle_mock_modern_rag_request
            chat_response = await handle_mock_modern_rag_request(
                request_json, 
                mock_modern_rag_web_response, 
                "mock-model"
            )
            return jsonify(chat_response)
        except ImportError:
            # セキュリティモジュールが利用できない場合のフォールバック
            response_data, status_code = create_service_unavailable_response(
                "モックサービスが利用できません"
            )
            return jsonify(response_data), status_code
        except Exception as e:
            response_data, status_code = create_server_error_response(
                f"モック処理エラー: {str(e)}"
            )
            return jsonify(response_data), status_code
    
    # モック不可でサービス未初期化ならエラーを返す
    if not use_mock_response and (not hasattr(current_app, 'modern_rag') or not current_app.modern_rag):
        response_data, status_code = create_service_unavailable_response(
            "Modern RAG service not initialized"
        )
        return jsonify(response_data), status_code

    # 実際のModern RAG処理（本番環境用）
    try:
        request_json = await request.get_json()
        messages = request_json.get("messages", [])
        
        if not messages:
            response_data, status_code = create_error_response(
                "メッセージは必須です", 
                HTTPStatus.BAD_REQUEST,
                "MISSING_MESSAGES"
            )
            return jsonify(response_data), status_code
        
        # Get the latest user message
        user_message = None
        for msg in reversed(messages):
            if msg.get("role") == "user":
                user_message = msg.get("content", "")
                break
        
        if not user_message or user_message.strip() == "":
            response_data, status_code = create_error_response(
                "ユーザーメッセージが見つかりません", 
                HTTPStatus.BAD_REQUEST,
                "MISSING_USER_MESSAGE"
            )
            return jsonify(response_data), status_code
        
        # 認証済みユーザーIDを利用
        user_id = principal.user_principal_id
        
        # Process with Modern RAG service from app instance
        if not hasattr(current_app, 'modern_rag') or not current_app.modern_rag:
            # Modern RAG service not available, fall back to mock response
            logging.warning("Modern RAG service not available, using mock response")
            request_json = await request.get_json()
            try:
                from tests.mock_responses import handle_mock_modern_rag_request
                chat_response = await handle_mock_modern_rag_request(
                    request_json, 
                    mock_modern_rag_web_response, 
                    app_settings.azure_openai.model
                )
                return jsonify(chat_response)
            except ImportError:
                # セキュリティモジュールが利用できない場合のフォールバック
                response_data, status_code = create_service_unavailable_response(
                    "モックサービスが利用できません"
                )
                return jsonify(response_data), status_code
            
        service = current_app.modern_rag
        result = await service.process_user_query(user_message, user_id)
        
        if result.status == "success":
            # Format response in chat completion format with citations embedded in assistant message
            # DO NOT use 'tool' role - it causes OpenAI API errors when sent back in conversation history
            citations_html = service.format_citations_html(result.citations)
            
            response_message = {
                "role": "assistant",
                "content": result.response,
                "id": str(uuid.uuid4()),
                "date": datetime.now().isoformat(),
                # Embed citations directly in assistant message instead of separate tool message
                "context": json.dumps({
                    "citations": [citation.to_dict() for citation in result.citations],
                    "citations_html": citations_html
                })
            }
            
            # Return in expected format
            chat_response = {
                "id": result.run_id or str(uuid.uuid4()),
                "model": app_settings.azure_openai.model,
                "created": int(datetime.now().timestamp()),
                "object": "chat.completion",
                "choices": [{
                    "messages": [response_message]
                }],
                "history_metadata": {
                    "conversation_id": result.thread_id or str(uuid.uuid4()),
                    "title": user_message[:50] + "..." if len(user_message) > 50 else user_message,
                    "date": datetime.now().isoformat()
                }
            }
            
            return jsonify(chat_response)
        
        else:
            # Return error response
            error_message = f"Modern RAG処理に失敗しました: {result.error}"
            response_data, status_code = create_server_error_response(error_message)
            return jsonify(response_data), status_code
            
    except ImportError as e:
        logging.error(f"Modern RAG service not available: {e}")
        response_data, status_code = create_error_response(
            "Modern RAG機能が利用できません", 
            HTTPStatus.NOT_IMPLEMENTED,
            "FEATURE_NOT_AVAILABLE"
        )
        return jsonify(response_data), status_code
        
    except Exception as e:
        logging.exception("Exception in /conversation/modern-rag-web")
        response_data, status_code = create_server_error_response(str(e))
        return jsonify(response_data), status_code


@bp.route("/api/modern-rag/health", methods=["GET"])
async def modern_rag_health_check():
    """
    Modern RAG サービス専用のヘルスチェックエンドポイント
    """
    try:
        if not hasattr(current_app, 'modern_rag') or not current_app.modern_rag:
            data = {
                "status": "unavailable",
                "message": "Modern RAG service not initialized",
                "timestamp": datetime.utcnow().isoformat()
            }
            response_data, status_code = create_service_unavailable_response()
            response_data.update(data)
            return jsonify(response_data), HTTPStatus.SERVICE_UNAVAILABLE
        
        # Modern RAG サービスのヘルスチェックを実行
        health_result = await current_app.modern_rag.health_check()
        health_result["timestamp"] = datetime.utcnow().isoformat()
        
        if health_result.get("status") == "healthy":
            response_data, status_code = create_success_response(health_result)
            return jsonify(response_data), status_code
        else:
            response_data, status_code = create_service_unavailable_response()
            response_data.update(health_result)
            return jsonify(response_data), HTTPStatus.SERVICE_UNAVAILABLE
            
    except Exception as e:
        logging.exception("Exception in /api/modern-rag/health")
        error_data = {
            "status": "error",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }
        response_data, status_code = create_server_error_response()
        response_data.update(error_data)
        return jsonify(response_data), status_code


# ==========================================
# アプリケーション作成・起動 (App Creation & Startup)
# ==========================================

def create_app():
    """
    Quartアプリケーションの作成と設定
    
    Returns:
        Quart: 設定済みのQuartアプリケーション
    """
    app = Quart(__name__)
    app.register_blueprint(bp)
    
    # TDD: 削除した履歴エンドポイントを新しいルーターで復元
    app.register_blueprint(history_bp)
    
    app.config["TEMPLATES_AUTO_RELOAD"] = True
    
    @app.before_serving
    async def init():
        # 段階3: 設定ベースの安全なテスト関数分離
        global mock_chat_response, mock_modern_rag_web_response
        
        try:
            from backend.security.test_security import safe_import_test_functions
            mock_chat_response, mock_modern_rag_web_response = safe_import_test_functions()
        except ImportError as e:
            logging.warning(f"Security module not available, using fallback: {e}")
            # フォールバック: 基本的なセキュリティチェック
            is_production = (
                os.environ.get("AZURE_ENV_NAME", "").startswith(("prod", "production")) or 
                os.environ.get("BACKEND_URI", "").startswith("https://") or
                os.environ.get("WEBSITE_SITE_NAME")
            )
            
            if not is_production and os.environ.get("LOCAL_MOCK_MODE", "false").lower() == "true":
                try:
                    from tests.mock_responses import mock_chat_response, mock_modern_rag_web_response
                    logging.info("🧪 Mock functions imported (fallback mode)")
                except ImportError:
                    mock_chat_response = None
                    mock_modern_rag_web_response = None
            else:
                mock_chat_response = None
                mock_modern_rag_web_response = None
            
        try:
            # TDD Phase 4: 新しいKey Vaultサービス層初期化
            init_keyvault_service()
            
            # Task 20: フィーチャーフラグサービス初期化
            init_feature_flag_service()
            
            # AI Service Factory 初期化
            app.ai_service_factory = create_ai_service_factory()
            logging.info("AI Service Factory initialized successfully")
            
            # CosmosDB初期化を安全に実行
            try:
                app.cosmos_conversation_client = await init_cosmosdb_client()
                cosmos_db_ready.set()
                logging.info("CosmosDB client initialized successfully")
                
                # 新アーキテクチャ: 履歴管理サービス初期化
                global conversation_history_service, conversation_title_generator
                conversation_history_service = ConversationHistoryService(app.cosmos_conversation_client)
                # OpenAIクライアントは必要時に初期化（タイトル生成用）
                
                # TDD: HistoryRouterの初期化（削除したエンドポイントの復元）
                init_history_router(conversation_history_service)
                
            except Exception as e:
                logging.warning(f"CosmosDB initialization failed, will continue without chat history: {e}")
                logging.warning(f"CosmosDB Account: {os.environ.get('AZURE_COSMOSDB_ACCOUNT', 'NOT_SET')}")
                logging.warning(f"CosmosDB Database: {os.environ.get('AZURE_COSMOSDB_DATABASE', 'NOT_SET')}")
                logging.warning(f"CosmosDB Container: {os.environ.get('AZURE_COSMOSDB_CONVERSATIONS_CONTAINER', 'NOT_SET')}")
                logging.warning("This could be due to database not existing, incorrect permissions, or network connectivity issues")
                app.cosmos_conversation_client = None
                conversation_history_service = None
                cosmos_db_ready.set()  # 続行を許可
            
            # Initialize Modern RAG service with enhanced error handling
            try:
                from backend.modern_rag_web_service import ModernBingGroundingAgentService
                
                # Check if required environment variables are available
                azure_ai_agent_endpoint = os.environ.get("AZURE_AI_AGENT_ENDPOINT")
                bing_grounding_conn_id = os.environ.get("BING_GROUNDING_CONN_ID")
                
                logging.info(f"DEBUG: AZURE_AI_AGENT_ENDPOINT = {'SET' if azure_ai_agent_endpoint else 'NOT_SET'}")
                logging.info(f"DEBUG: BING_GROUNDING_CONN_ID = {'SET' if bing_grounding_conn_id else 'NOT_SET'}")
                
                if azure_ai_agent_endpoint and bing_grounding_conn_id:
                    logging.info("Attempting to initialize Modern RAG service...")
                    app.modern_rag = await ModernBingGroundingAgentService.create()
                    logging.info("Modern RAG service initialized successfully")
                else:
                    logging.warning("Modern RAG service disabled - missing required environment variables")
                    logging.warning(f"  - AZURE_AI_AGENT_ENDPOINT: {'SET' if azure_ai_agent_endpoint else 'NOT_SET'}")
                    logging.warning(f"  - BING_GROUNDING_CONN_ID: {'SET' if bing_grounding_conn_id else 'NOT_SET'}")
                    app.modern_rag = None
            except ImportError as e:
                logging.warning(f"Modern RAG service not available (import error): {e}")
                app.modern_rag = None
            except ValueError as e:
                logging.warning(f"Modern RAG service configuration error: {e}")
                app.modern_rag = None
            except Exception as e:
                logging.exception("Failed to initialize Modern RAG service with full traceback")
                app.modern_rag = None

            # Initialize DeepResearch service
            try:
                app.deepresearch = create_service_from_env()
                if app.deepresearch:
                    logging.info("DeepResearch service initialized successfully")
                else:
                    logging.info("DeepResearch service disabled - missing configuration")
            except Exception:
                logging.exception("Failed to initialize DeepResearch service")
                app.deepresearch = None
                
        except Exception as e:
            logging.exception("Critical error in application initialization")
            # アプリケーションの起動を継続（部分的な機能で）
            app.cosmos_conversation_client = None
            app.modern_rag = None
            cosmos_db_ready.set()
    
    @app.after_serving
    async def cleanup():
        try:
            # Cleanup Modern RAG service
            if hasattr(app, 'modern_rag') and app.modern_rag:
                await app.modern_rag.aclose()
                logging.info("Modern RAG service closed successfully")
            if hasattr(app, 'deepresearch') and app.deepresearch:
                await app.deepresearch.aclose()
                logging.info("DeepResearch service closed successfully")
        except Exception as e:
            logging.exception("Error during service cleanup")
    
    return app


## Conversation History API ##
if __name__ == "__main__":
    # .envファイルを読み込み
    from dotenv import load_dotenv
    load_dotenv()
    
    # デバッグモードの設定
    logging.basicConfig(level=logging.INFO)
    
    # ローカル開発用の設定を出力
    logging.info("Starting Quart application...")
    logging.info(f"AUTH_REQUIRED: {os.environ.get('AUTH_REQUIRED', 'NOT_SET')}")
    logging.info(f"AZURE_USE_AUTHENTICATION: {os.environ.get('AZURE_USE_AUTHENTICATION', 'NOT_SET')}")
    logging.info(f"AZURE_ENFORCE_ACCESS_CONTROL: {os.environ.get('AZURE_ENFORCE_ACCESS_CONTROL', 'NOT_SET')}")
    logging.info(f"LOCAL_MOCK_MODE: {os.environ.get('LOCAL_MOCK_MODE', 'NOT_SET')}")
    
    if os.environ.get("LOCAL_MOCK_MODE", "false").lower() == "true":
        logging.info("🧪 ローカルモックモードが有効です - Azure OpenAIの代わりにテスト用レスポンスを使用します")
    else:
        logging.info("🌐 通常モード - 実際のAzure OpenAIサービスに接続します")
    
    # Quartアプリケーションを起動
    app = create_app()
    app.run(host="127.0.0.1", port=5000, debug=True)
else:
    # ASGIアプリケーションのインスタンスを作成（本番環境用）
    # モジュールレベルでのアプリケーションインスタンス作成
    try:
        app = create_app()
    except Exception as e:
        logging.error("Error creating app: %s", e)
        import traceback
        traceback.print_exc()
        # フォールバック用のシンプルなアプリ
        app = Quart(__name__)
        @app.route('/')
        async def health():
            return {"status": "error", "message": str(e)}
