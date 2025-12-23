"""
DeepResearch Function Proxy Service

This module integrates the external ``deepresearch-func`` Azure Function with
the AMARIS backend. It provides a thin client that:

* Sends the user's research query to the function endpoint
* Normalizes the response into a chat completion-like shape
* Extracts citation information when available
"""

import json
import logging
import os
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import aiohttp

logger = logging.getLogger(__name__)


@dataclass
class DeepResearchResult:
    """Normalized DeepResearch response."""

    status: str
    response: str
    citations: List[Dict[str, Any]] = field(default_factory=list)
    run_id: Optional[str] = None
    thread_id: Optional[str] = None
    raw: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_payload(cls, payload: Dict[str, Any]) -> "DeepResearchResult":
        """
        Create a ``DeepResearchResult`` from various possible payload shapes.

        The upstream function may return different keys depending on version.
        This parser tries a few common patterns before falling back to a
        stringified payload.
        """

        def _first_existing(keys: List[str]) -> Optional[Any]:
            for key in keys:
                if key in payload and payload.get(key) is not None:
                    return payload.get(key)
            return None

        response_text = _first_existing(
            ["response", "answer", "summary", "result", "content", "report"]
        )
        if response_text is None:
            response_text = json.dumps(payload, ensure_ascii=False)

        citations = _first_existing(["citations", "sources", "references"]) or []
        run_id = _first_existing(["run_id", "id"])
        thread_id = _first_existing(["thread_id", "conversation_id"])

        status = payload.get("status") or payload.get("state") or "success"

        return cls(
            status=str(status),
            response=str(response_text),
            citations=citations if isinstance(citations, list) else [],
            run_id=str(run_id) if run_id else None,
            thread_id=str(thread_id) if thread_id else None,
            raw=payload,
        )


class DeepResearchService:
    """
    Client for the external deepresearch-func Azure Function.

    The service is intentionally lightweight: it posts a JSON body to the
    configured function endpoint and normalizes the response for the chat UI.
    """

    def __init__(
        self,
        function_url: str,
        api_key: Optional[str] = None,
        route: Optional[str] = None,
        session: Optional[aiohttp.ClientSession] = None,
    ):
        if not function_url:
            raise ValueError("DeepResearch function URL is required")

        normalized_url = function_url.rstrip("/")
        normalized_route = (route or "/api/deepresearch").lstrip("/")

        self._endpoint = f"{normalized_url}/{normalized_route}"
        self._api_key = api_key
        self._session = session or aiohttp.ClientSession()

        logger.info("DeepResearchService initialized for endpoint %s", self._endpoint)

    async def aclose(self):
        """Close the underlying HTTP session."""
        if not self._session.closed:
            await self._session.close()

    def format_citations_html(self, citations: List[Dict[str, Any]]) -> str:
        """Render a simple HTML list for citation preview panels."""
        if not citations:
            return ""

        items = []
        for citation in citations:
            title = citation.get("title") or citation.get("source") or "Reference"
            url = citation.get("url") or citation.get("link") or ""
            snippet = citation.get("content") or citation.get("snippet") or ""
            item_html = f"<li><strong>{title}</strong>"
            if url:
                item_html += f' - <a href="{url}" target="_blank" rel="noopener noreferrer">{url}</a>'
            if snippet:
                item_html += f"<div>{snippet}</div>"
            item_html += "</li>"
            items.append(item_html)

        return f"<ul>{''.join(items)}</ul>"

    async def run_research(
        self, query: str, user_id: Optional[str] = None
    ) -> DeepResearchResult:
        """
        Execute a DeepResearch request.

        Args:
            query: User's research question or topic.
            user_id: Optional user identifier for audit or personalization.
        """
        headers = {"Content-Type": "application/json"}
        if self._api_key:
            headers["x-functions-key"] = self._api_key

        payload: Dict[str, Any] = {"query": query}
        if user_id:
            payload["user_id"] = user_id

        try:
            async with self._session.post(
                self._endpoint,
                json=payload,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=60),
            ) as response:
                text = await response.text()

                if response.status >= 400:
                    logger.error(
                        "DeepResearch HTTP error %s: %s", response.status, text
                    )
                    return DeepResearchResult(
                        status="error",
                        response=f"DeepResearch HTTP {response.status}: {text}",
                        citations=[],
                        raw={"status": response.status, "body": text},
                    )

                data = json.loads(text) if text else {}
                return DeepResearchResult.from_payload(data)
        except Exception as exc:  # pragma: no cover - network errors
            logger.exception("DeepResearch request failed: %s", exc)
            return DeepResearchResult(
                status="error",
                response=str(exc),
                citations=[],
                raw={"error": str(exc)},
            )


def create_service_from_env() -> Optional[DeepResearchService]:
    """
    Factory helper that reads environment variables and builds a service instance.

    Environment Variables:
        DEEPRESEARCH_FUNC_URL: Base URL of the deepresearch-func app
        DEEPRESEARCH_FUNC_ROUTE: Optional route path (default: /api/deepresearch)
        DEEPRESEARCH_FUNC_KEY: Optional function key
    """
    func_url = os.environ.get("DEEPRESEARCH_FUNC_URL")
    func_key = os.environ.get("DEEPRESEARCH_FUNC_KEY")
    func_route = os.environ.get("DEEPRESEARCH_FUNC_ROUTE")

    if not func_url:
        logger.info("DeepResearch function URL not configured; service disabled")
        return None

    try:
        return DeepResearchService(func_url, api_key=func_key, route=func_route)
    except Exception:
        logger.exception("Failed to initialize DeepResearchService")
        return None
