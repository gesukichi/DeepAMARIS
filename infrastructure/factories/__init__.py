"""
Infrastructure Factories Module

ファクトリパターンの実装
- AIServiceFactory: Azure OpenAI クライアントの作成
"""

from .ai_service_factory import AIServiceFactory, create_ai_service_factory

__all__ = [
    "AIServiceFactory",
    "create_ai_service_factory",
]
