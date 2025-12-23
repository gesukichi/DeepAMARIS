"""
Azure Functions Search Proxy Implementation

TDD Phase 2: Green - 最小限の実装でテストを通す
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

from azure.search.documents.aio import SearchClient
from azure.core.credentials import AzureKeyCredential
from azure.core.exceptions import ClientAuthenticationError, HttpResponseError

from .config import get_config

# ログ設定
logger = logging.getLogger(__name__)


class HttpRequest:
    """テスト用のHTTPリクエストクラス"""
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
    """テスト用のHTTPレスポンスクラス"""
    def __init__(self, body: str, status_code: int = 200, mimetype: str = "application/json"):
        self._body = body
        self.status_code = status_code
        self.mimetype = mimetype
    
    def get_body(self) -> str:
        return self._body


async def main(req: Union[Any, HttpRequest]) -> Union[Any, HttpResponse]:
    """
    Azure Functions HTTP Trigger Entry Point
    
    Args:
        req: HTTPリクエスト
        
    Returns:
        HTTPレスポンス
    """
    start_time = time.time()
    request_id = req.headers.get('x-request-id', f"req-{int(start_time * 1000)}")
    
    logger.info(f"[{request_id}] Search proxy request received")
    
    try:
        # リクエスト形式の検証
        if req.method != "POST":
            return _create_response(
                {"error": {"code": "MethodNotAllowed", "message": "Only POST method is supported"}},
                405
            )
        
        # JSONペイロードの解析
        try:
            request_data = req.get_json()
        except ValueError as e:
            logger.error(f"[{request_id}] Invalid JSON: {e}")
            return _create_response(
                {"error": {"code": "InvalidJson", "message": "Invalid JSON format"}},
                400
            )
        
        if not request_data:
            return _create_response(
                {"error": {"code": "EmptyRequest", "message": "Request body is empty"}},
                400
            )
        
        # 必須パラメータの検証
        search_text = request_data.get("search_text")
        if not search_text:
            return _create_response(
                {"error": {"code": "MissingSearchText", "message": "search_text parameter is required"}},
                400
            )
        
        # オプションパラメータ
        top = request_data.get("top", 10)
        filters = request_data.get("filters", {})
        
        # パラメータの型検証
        if not isinstance(top, int) or top <= 0:
            return _create_response(
                {"error": {"code": "InvalidParameterType", "message": "top must be a positive integer"}},
                400
            )
        
        if not isinstance(filters, dict):
            return _create_response(
                {"error": {"code": "InvalidParameterType", "message": "filters must be a dictionary"}},
                400
            )
        
        # Azure AI Search実行
        try:
            results = await perform_search(search_text, top, filters, request_id)
            
            elapsed_ms = int((time.time() - start_time) * 1000)
            
            response_data = {
                "results": results,
                "count": len(results),
                "elapsedMs": elapsed_ms
            }
            
            logger.info(f"[{request_id}] Search completed successfully: {len(results)} results in {elapsed_ms}ms")
            
            return _create_response(response_data, 200)
            
        except ClientAuthenticationError as e:
            logger.error(f"[{request_id}] Authentication failed: {e}")
            return _create_response({
                "error": {
                    "code": "SearchUpstreamError",
                    "message": "Authentication failed",
                    "upstream": {"stage": "auth"}
                }
            }, 500)
        
        except HttpResponseError as e:
            logger.error(f"[{request_id}] Search service error: {e}")
            
            # DNS解決失敗の検出
            if "DNS server returned answer with no data" in str(e):
                return _create_response({
                    "error": {
                        "code": "SearchUpstreamError",
                        "message": "DNS resolution failed",
                        "upstream": {"stage": "dns"}
                    }
                }, 500)
            
            # 429 スロットリングの検出
            if hasattr(e, 'response') and hasattr(e.response, 'status_code') and e.response.status_code == 429:
                return _create_response({
                    "error": {
                        "code": "SearchUpstreamError",
                        "message": "Rate limit exceeded",
                        "upstream": {"stage": "429"}
                    }
                }, 500)
            
            # タイムアウトの検出
            if "timeout" in str(e).lower():
                return _create_response({
                    "error": {
                        "code": "SearchUpstreamError",
                        "message": "Request timeout",
                        "upstream": {"stage": "timeout"}
                    }
                }, 500)
            
            return _create_response({
                "error": {
                    "code": "SearchUpstreamError",
                    "message": "Search service error",
                    "upstream": {"stage": "search"}
                }
            }, 500)
        
        except Exception as e:
            logger.error(f"[{request_id}] Unexpected error: {e}")
            return _create_response({
                "error": {
                    "code": "InternalServerError",
                    "message": "An unexpected error occurred"
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
    """HTTPレスポンスを作成"""
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


async def perform_search(search_text: str, top: int, filters: Dict[str, Any], request_id: str) -> list:
    """
    Azure AI Search の実行
    
    Args:
        search_text: 検索テキスト
        top: 取得件数
        filters: フィルター条件
        request_id: リクエストID
        
    Returns:
        list: 検索結果
    """
    config = get_config()
    
    # SearchClient の初期化
    search_client = SearchClient(
        endpoint=config.search_endpoint,
        index_name=config.search_index,
        credential=AzureKeyCredential(config.search_key)
    )
    
    try:
        # 検索実行
        logger.info(f"[{request_id}] Executing search: '{search_text}' (top={top})")
        
        results = []
        search_results = await search_client.search(
            search_text=search_text,
            top=top,
            include_total_count=True
        )
        
        async for result in search_results:
            # 結果を辞書形式に変換
            result_dict = {
                "id": result.get("id", ""),
                "score": result.get("@search.score", 0.0),
                "fields": {k: v for k, v in result.items() if not k.startswith("@")}
            }
            results.append(result_dict)
        
        return results
        
    finally:
        await search_client.close()


# Azure Functions での使用のためのエクスポート
__all__ = ["main", "perform_search"]
