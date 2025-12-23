"""
Task 20: Feature Flag Service Implementation

t-wadaさんのテスト駆動開発原則に従った実装
GREEN Phase: テストを通すための最小実装

目的: 段階的デプロイ戦略におけるフィーチャーフラグ管理
テスト容易性・可用性を最重視した安全な実装
"""

import json
import logging
import threading
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime


class FeatureFlagService:
    """
    フィーチャーフラグ管理サービス
    
    段階的デプロイ戦略の核心コンポーネント
    - テスト容易性: 設定外部化、モック対応
    - 可用性: スレッドセーフ、エラー耐性
    - 安全性: デフォルト値による縮退動作
    """
    
    def __init__(self, config_path: Optional[Path] = None):
        """
        フィーチャーフラグサービス初期化
        
        Args:
            config_path: 設定ファイルパス（テスト時のモック対応）
        """
        self.logger = logging.getLogger(__name__)
        self._lock = threading.RLock()  # スレッドセーフ保証
        
        # 設定ファイルパス決定（テスト容易性のため外部化）
        if config_path is None:
            project_root = Path(__file__).parent.parent.parent.parent
            config_path = project_root / "config" / "feature_flags.json"
            
        self.config_path = config_path
        self._config_cache: Optional[Dict[str, Any]] = None
        self._last_loaded: Optional[datetime] = None
        
        # 初期設定読み込み
        self._load_config()
        
    def is_enabled(self, feature_name: str, default: bool = False) -> bool:
        """
        フィーチャーフラグ状態確認
        
        Args:
            feature_name: フィーチャー名
            default: デフォルト値（可用性確保）
            
        Returns:
            bool: フィーチャー有効状態
        """
        try:
            with self._lock:
                config = self.get_config()
                features = config.get("features", {})
                result = features.get(feature_name, default)
                
                self.logger.debug("Feature flag check: %s = %s", feature_name, result)
                return bool(result)
                
        except Exception as e:
            # 可用性重視: エラー時はデフォルト値で継続
            self.logger.error(
                "Feature flag check failed for %s, using default %s: %s", 
                feature_name, default, e
            )
            return default
            
    def get_config(self) -> Dict[str, Any]:
        """
        設定全体取得
        
        Returns:
            Dict[str, Any]: 設定辞書
        """
        with self._lock:
            if self._config_cache is None:
                self._load_config()
            return self._config_cache or {}
            
    def reload_config(self) -> bool:
        """
        設定再読み込み（運用時の動的変更対応）
        
        Returns:
            bool: 再読み込み成功可否
        """
        try:
            with self._lock:
                self._config_cache = None
                self._load_config()
                self.logger.info("Feature flag config reloaded successfully")
                return True
                
        except Exception as e:
            self.logger.error("Feature flag config reload failed: %s", e)
            return False
            
    def _load_config(self) -> None:
        """設定ファイル読み込み（内部実装）"""
        try:
            if not self.config_path.exists():
                self.logger.warning(
                    "Feature flag config file not found: %s", 
                    self.config_path
                )
                self._config_cache = self._get_default_config()
                return
                
            with open(self.config_path, 'r', encoding='utf-8') as f:
                self._config_cache = json.load(f)
                self._last_loaded = datetime.now()
                
            self.logger.info(
                "Feature flag config loaded from %s", 
                self.config_path
            )
            
        except (json.JSONDecodeError, OSError) as e:
            self.logger.error(
                "Failed to load feature flag config: %s", e
            )
            # 可用性確保: エラー時はデフォルト設定
            self._config_cache = self._get_default_config()
            
    def _get_default_config(self) -> Dict[str, Any]:
        """
        デフォルト設定取得（可用性確保）
        
        Returns:
            Dict[str, Any]: デフォルト設定
        """
        return {
            "features": {
                "azure_functions_enabled": False,
                "conversation_service_enabled": True,
                "modern_rag_enabled": True,
                "user_management_enabled": True,
                "system_management_enabled": True,
                "app_py_legacy_mode": True
            },
            "deployment": {
                "rollback_enabled": True,
                "rollback_timeout_minutes": 5,
                "health_check_interval_seconds": 30,
                "max_deployment_retries": 3
            },
            "metadata": {
                "version": "default",
                "description": "Default fallback configuration"
            }
        }
        
    def get_deployment_config(self) -> Dict[str, Any]:
        """
        デプロイ設定取得
        
        Returns:
            Dict[str, Any]: デプロイ設定
        """
        config = self.get_config()
        return config.get("deployment", {})
        
    def is_rollback_enabled(self) -> bool:
        """
        ロールバック機能有効状態確認
        
        Returns:
            bool: ロールバック機能有効可否
        """
        deployment_config = self.get_deployment_config()
        return deployment_config.get("rollback_enabled", True)


# シングルトンインスタンス（テスト時は別インスタンス使用可能）
_feature_flag_service_instance: Optional[FeatureFlagService] = None


def get_feature_flag_service() -> FeatureFlagService:
    """
    フィーチャーフラグサービス取得（シングルトンパターン）
    
    Returns:
        FeatureFlagService: サービスインスタンス
    """
    global _feature_flag_service_instance
    
    if _feature_flag_service_instance is None:
        _feature_flag_service_instance = FeatureFlagService()
        
    return _feature_flag_service_instance


def set_feature_flag_service(service: FeatureFlagService) -> None:
    """
    フィーチャーフラグサービス設定（テスト時のモック対応）
    
    Args:
        service: サービスインスタンス
    """
    global _feature_flag_service_instance
    _feature_flag_service_instance = service
