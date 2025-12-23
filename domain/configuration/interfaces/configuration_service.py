#!/usr/bin/env python3
"""
設定サービスインターフェース
app_settings依存関係を分離するための抽象化

TDD Red Phase: インターフェース定義
"""

from abc import ABC, abstractmethod
from typing import Optional


class IConfigurationService(ABC):
    """
    アプリケーション設定サービスのインターフェース
    
    app_settings への直接依存を避け、テスト可能性と
    設定ソースの抽象化を提供する
    """
    
    @abstractmethod
    def get_stream_enabled(self) -> bool:
        """
        ストリーミング機能が有効かどうかを取得
        
        Returns:
            bool: ストリーミングが有効な場合True
        """
        raise NotImplementedError
    
    @abstractmethod
    def get_use_promptflow(self) -> bool:
        """
        PromptFlow機能が有効かどうかを取得
        
        Returns:
            bool: PromptFlowが有効な場合True
        """
        raise NotImplementedError
    
    @abstractmethod
    def get_azure_openai_endpoint(self) -> Optional[str]:
        """
        Azure OpenAIエンドポイントを取得
        
        Returns:
            Optional[str]: エンドポイントURL、未設定の場合None
        """
        raise NotImplementedError
    
    @abstractmethod
    def get_azure_openai_key(self) -> Optional[str]:
        """
        Azure OpenAIキーを取得
        
        Returns:
            Optional[str]: APIキー、未設定の場合None
        """
        raise NotImplementedError
    
    @abstractmethod
    def get_auth_enabled(self) -> bool:
        """
        認証機能が有効かどうかを取得
        
        Returns:
            bool: 認証が有効な場合True
        """
        raise NotImplementedError
