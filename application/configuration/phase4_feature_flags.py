"""
Phase 4: Advanced Feature Flags Implementation

t-wadaさんのテスト駆動開発原則に従った実装
GREEN Phase: テストを通すための最小実装

目的: Phase 4段階的移行のための高度なフィーチャーフラグ管理
テスト容易性・可用性を最重視した安全な実装
"""

import os
from typing import Dict, Any, Optional
import logging


class Phase4FeatureFlags:
    """
    Phase 4段階的移行用の高度なフィーチャーフラグ
    
    設計原則:
    - 環境変数による設定制御
    - 既定値は安全側（無効）
    - 明示的有効化の前提
    - 段階的移行制御対応
    """
    
    def __init__(self):
        """Phase 4フィーチャーフラグ初期化"""
        self._logger = logging.getLogger(__name__)
        
        # Phase 4メインフラグ
        self.phase4_enabled = self._get_bool("PHASE4_ENABLED", False)
        self.migration_percentage = self._get_int("PHASE4_MIGRATION_PERCENTAGE", 0)
        
        # エンドポイント個別制御フラグ
        self.new_system_endpoints = self._get_bool("NEW_SYSTEM_ENDPOINTS", False)
        self.new_conversation_endpoint = self._get_bool("NEW_CONVERSATION_ENDPOINT", False)
        self.new_history_endpoints = self._get_bool("NEW_HISTORY_ENDPOINTS", False)
        
        # レガシーコード削除制御フラグ
        self.legacy_cleanup_phase1 = self._get_bool("LEGACY_CLEANUP_PHASE1", False)
        self.legacy_cleanup_phase2 = self._get_bool("LEGACY_CLEANUP_PHASE2", False)
        self.legacy_cleanup_phase3 = self._get_bool("LEGACY_CLEANUP_PHASE3", False)
        
        # 安全機構フラグ
        self.emergency_rollback_enabled = self._get_bool("EMERGENCY_ROLLBACK_ENABLED", True)
        self.rollback_timeout_seconds = self._get_int("ROLLBACK_TIMEOUT_SECONDS", 300)
        
        self._logger.info("Phase4FeatureFlags initialized: phase4_enabled=%s", self.phase4_enabled)
    
    def _get_bool(self, env_key: str, default_value: bool) -> bool:
        """環境変数からbool値を安全に取得"""
        env_value = os.environ.get(env_key, str(default_value)).lower()
        return env_value in ("true", "1", "yes", "on")
    
    def _get_int(self, env_key: str, default_value: int) -> int:
        """環境変数からint値を安全に取得"""
        try:
            return int(os.environ.get(env_key, str(default_value)))
        except ValueError:
            return default_value
    
    def is_phase4_enabled(self) -> bool:
        """Phase 4機能が有効か"""
        return self.phase4_enabled
    
    def get_migration_percentage(self) -> int:
        """現在の移行率を取得（0-100%）"""
        return max(0, min(100, self.migration_percentage))
    
    def is_new_system_endpoints_enabled(self) -> bool:
        """新システム系エンドポイントが有効か"""
        # Phase 4 Day2: NEW_SYSTEM_ENDPOINTS の状態を直接確認（t-wada TDD原則対応）
        # より明確な制御: 環境変数の値を再取得して確実性を保つ
        current_value = self._get_bool("NEW_SYSTEM_ENDPOINTS", False)
        return current_value
    
    def is_new_conversation_endpoint_enabled(self) -> bool:
        """新会話エンドポイントが有効か"""
        # Phase 4 Day4: NEW_CONVERSATION_ENDPOINT の状態を直接確認（他のエンドポイントと同パターン）
        current_value = self._get_bool("NEW_CONVERSATION_ENDPOINT", False)
        return current_value
    
    def is_new_history_endpoints_enabled(self) -> bool:
        """新履歴エンドポイントが有効か"""
        # Day3: 環境変数を直接確認（Day2と同様のパターン）
        env_value = os.getenv("NEW_HISTORY_ENDPOINTS", "false").lower()
        return env_value in ("true", "1", "yes", "on")
    
    def is_legacy_cleanup_phase1_enabled(self) -> bool:
        """レガシーコード削除Phase 1が有効か"""
        return self.legacy_cleanup_phase1 and self.is_phase4_enabled()
    
    def is_legacy_cleanup_phase2_enabled(self) -> bool:
        """レガシーコード削除Phase 2が有効か"""
        return self.legacy_cleanup_phase2 and self.is_phase4_enabled()
    
    def is_legacy_cleanup_phase3_enabled(self) -> bool:
        """レガシーコード削除Phase 3が有効か"""
        return self.legacy_cleanup_phase3 and self.is_phase4_enabled()
    
    def is_emergency_rollback_enabled(self) -> bool:
        """緊急ロールバック機能が有効か"""
        return self.emergency_rollback_enabled
    
    def get_rollback_timeout_seconds(self) -> int:
        """ロールバックタイムアウト秒数を取得"""
        return max(30, self.rollback_timeout_seconds)  # 最小30秒
    
    def merge_with_existing_flags(self, existing_flags) -> Dict[str, Any]:
        """既存フィーチャーフラグとマージ"""
        merged_config = {
            "phase4_enabled": self.is_phase4_enabled(),
            "migration_percentage": self.get_migration_percentage(),
            "new_system_endpoints": self.is_new_system_endpoints_enabled(),
            "new_conversation_endpoint": self.is_new_conversation_endpoint_enabled(),
            "new_history_endpoints": self.is_new_history_endpoints_enabled(),
            "legacy_cleanup_phase1": self.is_legacy_cleanup_phase1_enabled(),
            "legacy_cleanup_phase2": self.is_legacy_cleanup_phase2_enabled(),
            "legacy_cleanup_phase3": self.is_legacy_cleanup_phase3_enabled(),
            "emergency_rollback": self.is_emergency_rollback_enabled(),
            "rollback_timeout": self.get_rollback_timeout_seconds()
        }
        
        # 既存フラグと統合
        if hasattr(existing_flags, 'get_all_flags'):
            existing_config = existing_flags.get_all_flags()
            merged_config.update(existing_config)
        
        return merged_config
    
    def get_all_phase4_flags(self) -> Dict[str, Any]:
        """全Phase 4フラグの状態を取得"""
        return {
            "phase4_enabled": self.is_phase4_enabled(),
            "migration_percentage": self.get_migration_percentage(),
            "endpoint_flags": {
                "system_endpoints": self.is_new_system_endpoints_enabled(),
                "conversation_endpoint": self.is_new_conversation_endpoint_enabled(),
                "history_endpoints": self.is_new_history_endpoints_enabled()
            },
            "cleanup_flags": {
                "phase1": self.is_legacy_cleanup_phase1_enabled(),
                "phase2": self.is_legacy_cleanup_phase2_enabled(),
                "phase3": self.is_legacy_cleanup_phase3_enabled()
            },
            "safety_flags": {
                "emergency_rollback": self.is_emergency_rollback_enabled(),
                "rollback_timeout": self.get_rollback_timeout_seconds()
            }
        }


# シングルトンインスタンス（テスト時は別インスタンス使用可能）
_phase4_feature_flags_instance: Optional[Phase4FeatureFlags] = None


def get_phase4_feature_flags() -> Phase4FeatureFlags:
    """Phase4FeatureFlagsのシングルトンインスタンスを取得"""
    global _phase4_feature_flags_instance
    if _phase4_feature_flags_instance is None:
        _phase4_feature_flags_instance = Phase4FeatureFlags()
    return _phase4_feature_flags_instance


def reset_phase4_feature_flags():
    """テスト用: Phase 4フラグのリセット"""
    global _phase4_feature_flags_instance
    _phase4_feature_flags_instance = None


if __name__ == "__main__":
    # 設定確認用スクリプト
    flags = get_phase4_feature_flags()
    print("=== Phase 4 Feature Flags Configuration ===")
    for key, value in flags.get_all_phase4_flags().items():
        print(f"{key}: {value}")
    print(f"Phase 4 enabled: {flags.is_phase4_enabled()}")
    print(f"Migration percentage: {flags.get_migration_percentage()}%")
