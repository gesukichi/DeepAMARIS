#!/usr/bin/env python3
"""
設定サービス実装
app_settings依存関係のラッパー実装

TDD Refactor Phase: コード品質向上（機能変更なし）
"""

import logging
from typing import Optional, Any

from domain.configuration.interfaces.configuration_service import IConfigurationService
from backend.settings import app_settings

# ロガー設定
logger = logging.getLogger(__name__)


class ConfigurationService(IConfigurationService):
    """
    設定サービスの具象実装
    
    app_settingsへの依存を隠蔽し、テスト可能性を向上させる
    """
    
    def __init__(self, settings: Optional[Any] = None) -> None:
        """
        ConfigurationServiceの初期化
        
        Args:
            settings: 設定オブジェクト（テスト時にモックを注入可能）
        
        Raises:
            ValueError: 設定オブジェクトが無効な場合
        """
        if settings is not None and not hasattr(settings, '__dict__'):
            logger.error("Invalid settings object provided: %s", type(settings))
            raise ValueError("Settings object must have attributes")
        
        self._settings = settings or app_settings
        logger.debug("ConfigurationService initialized with settings type: %s", 
                    type(self._settings).__name__)
    
    def get_stream_enabled(self) -> bool:
        """
        ストリーミング機能が有効かどうかを取得
        
        Returns:
            bool: ストリーミングが有効な場合True
            
        Raises:
            AttributeError: 設定構造が不正な場合
        """
        try:
            result = self._settings.azure_openai.stream
            logger.debug("Stream enabled: %s", result)
            return bool(result)
        except AttributeError as e:
            logger.error("Failed to access azure_openai.stream: %s", e)
            raise AttributeError("Invalid configuration structure for stream setting") from e
    
    def get_use_promptflow(self) -> bool:
        """
        PromptFlow機能が有効かどうかを取得
        
        Returns:
            bool: PromptFlowが有効な場合True
            
        Raises:
            AttributeError: 設定構造が不正な場合
        """
        try:
            result = self._settings.base_settings.use_promptflow
            logger.debug("Use promptflow: %s", result)
            return bool(result)
        except AttributeError as e:
            logger.error("Failed to access base_settings.use_promptflow: %s", e)
            raise AttributeError("Invalid configuration structure for promptflow setting") from e
    
    def get_azure_openai_endpoint(self) -> Optional[str]:
        """
        Azure OpenAIエンドポイントを取得
        
        Returns:
            Optional[str]: エンドポイントURL、未設定の場合None
            
        Note:
            空文字列やNoneの場合はNoneを返す
        """
        try:
            endpoint = getattr(self._settings.azure_openai, 'endpoint', None)
            # 空文字列もNoneとして扱う
            result = endpoint if endpoint else None
            logger.debug("Azure OpenAI endpoint: %s", "***" if result else None)
            return result
        except AttributeError as e:
            logger.warning("Failed to access azure_openai.endpoint: %s", e)
            return None
    
    def get_azure_openai_key(self) -> Optional[str]:
        """
        Azure OpenAIキーを取得
        
        Returns:
            Optional[str]: APIキー、未設定の場合None
            
        Note:
            セキュリティのためキー値はログに出力しない
            空文字列やNoneの場合はNoneを返す
        """
        try:
            key = getattr(self._settings.azure_openai, 'key', None)
            # 空文字列もNoneとして扱う
            result = key if key else None
            logger.debug("Azure OpenAI key: %s", "***" if result else None)
            return result
        except AttributeError as e:
            logger.warning("Failed to access azure_openai.key: %s", e)
            return None
    
    def get_auth_enabled(self) -> bool:
        """
        認証機能が有効かどうかを取得
        
        Returns:
            bool: 認証が有効な場合True、デフォルトはFalse
            
        Note:
            設定が見つからない場合はFalseをデフォルトとして返す
        """
        try:
            result = getattr(self._settings.base_settings, 'auth_enabled', False)
            logger.debug("Auth enabled: %s", result)
            return bool(result)
        except AttributeError as e:
            logger.warning("Failed to access base_settings.auth_enabled: %s", e)
            return False
