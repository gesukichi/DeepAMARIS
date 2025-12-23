import json
import time
import logging
import os
from typing import Dict, Any

import azure.functions as func
from azure.search.documents.aio import SearchClient
from azure.core.credentials import AzureKeyCredential
from azure.core.exceptions import ClientAuthenticationError, HttpResponseError

logger = logging.getLogger(__name__)


def _get_config():
    endpoint = os.getenv("SEARCH_ENDPOINT")
    index = os.getenv("SEARCH_INDEX", "gptkbindex")
    key = os.getenv("SEARCH_KEY")
    if not endpoint:
        raise ValueError("SEARCH_ENDPOINT environment variable is required")
    if not key:
        raise ValueError("SEARCH_KEY environment variable is required")
    return endpoint, index, key


def _create_response(data: Dict[str, Any], status_code: int) -> func.HttpResponse:
    return func.HttpResponse(
        json.dumps(data), status_code=status_code, mimetype="application/json"
    )


async def main(req: func.HttpRequest) -> func.HttpResponse:
    start_time = time.time()
    request_id = req.headers.get('x-request-id', f"req-{int(start_time * 1000)}")
    logger.info(f"[{request_id}] Search proxy request received")

    # Method check
    if req.method != "POST":
        return _create_response({"error": {"code": "MethodNotAllowed", "message": "Only POST method is supported"}}, 405)

    # Parse JSON
    try:
        body = req.get_json()
    except ValueError:
        return _create_response({"error": {"code": "InvalidJson", "message": "Invalid JSON format"}}, 400)

    if not body:
        return _create_response({"error": {"code": "EmptyRequest", "message": "Request body is empty"}}, 400)

    # Accept legacy aliases as well (q, search)
    search_text = body.get("search_text") or body.get("q") or body.get("search")
    if not search_text:
        return _create_response({"error": {"code": "MissingSearchText", "message": "search_text (or q) parameter is required"}}, 400)

    top = body.get("top", 10)
    if not isinstance(top, int) or top <= 0:
        return _create_response({"error": {"code": "InvalidParameterType", "message": "top must be a positive integer"}}, 400)

    try:
        endpoint, index, key = _get_config()
        client = SearchClient(endpoint=endpoint, index_name=index, credential=AzureKeyCredential(key))
        results = []
        search_results = await client.search(search_text=search_text, top=top, include_total_count=True)
        async for item in search_results:
            results.append({k: v for k, v in item.items()})
        await client.close()

        elapsed_ms = int((time.time() - start_time) * 1000)
        return _create_response({"results": results, "count": len(results), "elapsedMs": elapsed_ms}, 200)

    except ClientAuthenticationError as e:
        logger.error(f"[{request_id}] Authentication failed: {e}")
        return _create_response({"error": {"code": "SearchUpstreamError", "message": "Authentication failed", "upstream": {"stage": "auth"}}}, 500)
    except HttpResponseError as e:
        logger.error(f"[{request_id}] Search service error: {e}")
        msg = str(e)
        if "DNS server returned answer with no data" in msg:
            return _create_response({"error": {"code": "SearchUpstreamError", "message": "DNS resolution failed", "upstream": {"stage": "dns"}}}, 500)
        if hasattr(e, 'response') and getattr(e.response, 'status_code', None) == 429:
            return _create_response({"error": {"code": "SearchUpstreamError", "message": "Rate limit exceeded", "upstream": {"stage": "429"}}}, 500)
        if "timeout" in msg.lower():
            return _create_response({"error": {"code": "SearchUpstreamError", "message": "Request timeout", "upstream": {"stage": "timeout"}}}, 500)
        return _create_response({"error": {"code": "SearchUpstreamError", "message": "Search service error", "upstream": {"stage": "search"}}}, 500)
    except Exception as e:
        logger.exception(f"[{request_id}] Unexpected error: {e}")
        return _create_response({"error": {"code": "InternalServerError", "message": "An unexpected error occurred"}}, 500)
