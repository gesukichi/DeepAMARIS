"""
Azure Functions Configuration Management

TDD Phase 2: Green - 最小限の実装でテストを通す
"""

import os
from typing import Optional
from dataclasses import dataclass


@dataclass
class FunctionsConfig:
    """Azure Functions Search Proxy の設定管理クラス"""
    
    search_endpoint: str
    search_index: str
    search_key: str
    keyvault_uri: Optional[str] = None
    
    @classmethod
    def from_environment(cls) -> "FunctionsConfig":
        """
        環境変数から設定を読み込む
        
        必須環境変数:
        - SEARCH_ENDPOINT: Azure AI Search のエンドポイント
        - SEARCH_INDEX: 検索対象のインデックス名
        - SEARCH_KEY: Azure AI Search のAPIキー（またはKEYVAULT_URIから取得）
        
        Returns:
            FunctionsConfig: 設定インスタンス
            
        Raises:
            ValueError: 必須環境変数が不足している場合
        """
        search_endpoint = os.getenv("SEARCH_ENDPOINT")
        search_index = os.getenv("SEARCH_INDEX", "gptkbindex")  # デフォルト値
        search_key = os.getenv("SEARCH_KEY")
        keyvault_uri = os.getenv("KEYVAULT_URI")
        
        # 必須パラメータの検証
        if not search_endpoint:
            raise ValueError("SEARCH_ENDPOINT environment variable is required")
        
        if not search_key and not keyvault_uri:
            raise ValueError("Either SEARCH_KEY or KEYVAULT_URI environment variable is required")
        
        # URL形式の基本検証
        if not search_endpoint.startswith("https://"):
            raise ValueError("SEARCH_ENDPOINT must be a valid HTTPS URL")
        
        if not search_endpoint.endswith(".search.windows.net"):
            raise ValueError("SEARCH_ENDPOINT must be an Azure Search service URL")
        
        return cls(
            search_endpoint=search_endpoint,
            search_index=search_index,
            search_key=search_key or "",  # Key Vault使用時は空文字
            keyvault_uri=keyvault_uri
        )
    
    def validate(self) -> bool:
        """
        設定値の検証
        
        Returns:
            bool: 設定が有効な場合はTrue
        """
        # 基本的な検証ロジック（最小限実装）
        return (
            bool(self.search_endpoint) and
            bool(self.search_index) and
            (bool(self.search_key) or bool(self.keyvault_uri))
        )


# グローバル設定インスタンス（遅延初期化）
_config_instance: Optional[FunctionsConfig] = None


def get_config() -> FunctionsConfig:
    """
    設定インスタンスを取得（シングルトンパターン）
    
    Returns:
        FunctionsConfig: 設定インスタンス
    """
    global _config_instance
    if _config_instance is None:
        _config_instance = FunctionsConfig.from_environment()
    return _config_instance


def reset_config() -> None:
    """設定インスタンスをリセット（テスト用）"""
    global _config_instance
    _config_instance = None
