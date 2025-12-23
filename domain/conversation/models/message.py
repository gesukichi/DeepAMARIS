#!/usr/bin/env python3
"""
メッセージエンティティ
TDD Green Phase: テストを通すための最小限実装
"""

import uuid
from datetime import datetime
from typing import Dict, Any
from dataclasses import dataclass, field


@dataclass
class Message:
    """
    会話メッセージエンティティ
    
    責務:
    - メッセージデータの保持
    - バリデーション
    - シリアライゼーション
    """
    role: str
    content: str
    message_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    VALID_ROLES = {"user", "assistant", "system"}
    
    def __post_init__(self):
        """作成後のバリデーション"""
        self._validate_role()
        self._validate_content()
    
    def _validate_role(self):
        """ロールのバリデーション"""
        if self.role not in self.VALID_ROLES:
            raise ValueError(f"role must be one of {self.VALID_ROLES}, got: {self.role}")
    
    def _validate_content(self):
        """コンテンツのバリデーション"""
        if not self.content or not self.content.strip():
            raise ValueError("content cannot be empty")
    
    def to_dict(self) -> Dict[str, Any]:
        """辞書形式に変換"""
        return {
            "message_id": self.message_id,
            "role": self.role,
            "content": self.content,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata.copy()
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Message":
        """辞書から復元"""
        # タイムスタンプの変換
        timestamp = data.get("timestamp")
        if isinstance(timestamp, str):
            # ISO形式からdatetimeに変換（簡単な実装）
            try:
                timestamp = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
            except Exception:
                timestamp = datetime.now()
        elif not isinstance(timestamp, datetime):
            timestamp = datetime.now()
        
        return cls(
            message_id=data.get("message_id", str(uuid.uuid4())),
            role=data["role"],
            content=data["content"],
            timestamp=timestamp,
            metadata=data.get("metadata", {})
        )
