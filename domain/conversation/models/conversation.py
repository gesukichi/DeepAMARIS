#!/usr/bin/env python3
"""
会話エンティティ
TDD Green Phase: テストを通すための最小限実装
"""

import uuid
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field

from .message import Message


@dataclass  
class Conversation:
    """
    会話エンティティ
    
    責務:
    - 会話データの保持
    - メッセージの管理
    - 会話状態の追跡
    """
    user_id: str
    conversation_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    title: Optional[str] = None
    messages: List[Message] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def add_message(self, message: Message) -> None:
        """メッセージを追加"""
        self.messages.append(message)
        # updated_atが確実に異なる値になるようにする
        new_time = datetime.now()
        if new_time <= self.updated_at:
            new_time = self.updated_at + timedelta(microseconds=1)
        self.updated_at = new_time
    
    def get_last_message(self) -> Optional[Message]:
        """最新メッセージを取得"""
        if not self.messages:
            return None
        return self.messages[-1]
    
    @property
    def message_count(self) -> int:
        """メッセージ数を取得"""
        return len(self.messages)
    
    def to_dict(self) -> Dict[str, Any]:
        """辞書形式に変換"""
        return {
            "conversation_id": self.conversation_id,
            "user_id": self.user_id,
            "title": self.title,
            "messages": [msg.to_dict() for msg in self.messages],
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "metadata": self.metadata.copy()
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Conversation":
        """辞書から復元"""
        # タイムスタンプの変換
        created_at = data.get("created_at")
        if isinstance(created_at, str):
            try:
                created_at = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
            except Exception:
                created_at = datetime.now()
        elif not isinstance(created_at, datetime):
            created_at = datetime.now()
        
        updated_at = data.get("updated_at")
        if isinstance(updated_at, str):
            try:
                updated_at = datetime.fromisoformat(updated_at.replace("Z", "+00:00"))
            except Exception:
                updated_at = datetime.now()
        elif not isinstance(updated_at, datetime):
            updated_at = datetime.now()
        
        # メッセージの変換
        messages = []
        for msg_data in data.get("messages", []):
            messages.append(Message.from_dict(msg_data))
        
        return cls(
            conversation_id=data.get("conversation_id", str(uuid.uuid4())),
            user_id=data["user_id"],
            title=data.get("title"),
            messages=messages,
            created_at=created_at,
            updated_at=updated_at,
            metadata=data.get("metadata", {})
        )
