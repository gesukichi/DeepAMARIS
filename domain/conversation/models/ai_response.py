#!/usr/bin/env python3
"""
AI応答エンティティ
TDD Green Phase: テストを通すための最小限実装
"""

import uuid
from datetime import datetime
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field

from .message import Message


@dataclass
class AIResponse:
    """
    AI応答エンティティ
    
    責務:
    - AI応答データの保持
    - レスポンスメタデータの管理
    - メッセージへの変換
    """
    content: str
    model: str
    response_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = field(default_factory=datetime.now)
    usage_tokens: Optional[int] = None
    finish_reason: Optional[str] = None
    citations: List[Dict[str, Any]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_message(self) -> Message:
        """AI応答をメッセージに変換"""
        message_metadata = {
            "model": self.model,
            "response_id": self.response_id,
            **self.metadata
        }
        
        if self.usage_tokens is not None:
            message_metadata["usage_tokens"] = self.usage_tokens
        
        if self.finish_reason:
            message_metadata["finish_reason"] = self.finish_reason
        
        if self.citations:
            message_metadata["citations"] = self.citations
        
        return Message(
            role="assistant",
            content=self.content,
            timestamp=self.timestamp,
            metadata=message_metadata
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """辞書形式に変換"""
        return {
            "response_id": self.response_id,
            "content": self.content,
            "model": self.model,
            "timestamp": self.timestamp.isoformat(),
            "usage_tokens": self.usage_tokens,
            "finish_reason": self.finish_reason,
            "citations": self.citations.copy(),
            "metadata": self.metadata.copy()
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AIResponse":
        """辞書から復元"""
        # タイムスタンプの変換
        timestamp = data.get("timestamp")
        if isinstance(timestamp, str):
            try:
                timestamp = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
            except Exception:
                timestamp = datetime.now()
        elif not isinstance(timestamp, datetime):
            timestamp = datetime.now()
        
        return cls(
            response_id=data.get("response_id", str(uuid.uuid4())),
            content=data["content"],
            model=data["model"],
            timestamp=timestamp,
            usage_tokens=data.get("usage_tokens"),
            finish_reason=data.get("finish_reason"),
            citations=data.get("citations", []),
            metadata=data.get("metadata", {})
        )
