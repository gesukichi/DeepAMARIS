"""
Feature Flags Configuration for gradual refactoring and safe rollback
フィーチャーフラグによる段階的リファクタリングとロールバック機能

T-Wada TDD原則に基づく設計:
- 既存機能は変更せず、新機能を段階的に有効化
- 問題発生時の即座なロールバック対応
- 本番環境での安全な機能切り替え
"""

import os
from typing import Dict, Any


class FeatureFlags:
    """
    機能フラグ管理クラス
    
    設計原則:
    - 環境変数による設定制御
    - 既定値は安全側（無効）
    - 明示的有効化の前提
    - 単一ソースでの管理
    """
    
    def __init__(self):
        # 計画書のFeatureFlags統一方針に基づく実装
        
        # 既存機能の段階的置き換え用フラグ
        self.new_conversation_enabled = self._get_bool("NEW_CONVERSATION", False)
        self.new_history_enabled = self._get_bool("NEW_HISTORY", False)
        
        # Phase 2C統合フラグ（Task 5: GREEN Phase追加）
        self.phase2c_enabled = self._get_bool("PHASE2C_ENABLED", False)
        self.phase2c_migration_percentage = int(os.environ.get("PHASE2C_MIGRATION_PERCENTAGE", "0"))
        self.phase2c_e2e_integration_enabled = self._get_bool("PHASE2C_E2E_INTEGRATION", False)
        
        # リファクタリング安全機能
        self.rollback_enabled = self._get_bool("ROLLBACK_ENABLED", True)
        
        # 機能拡張フラグ（将来用）
        self.modern_rag_enabled = self._get_bool("FEATURE_MODERN_RAG", False)
        self.stream_response_enabled = self._get_bool("FEATURE_STREAMING", True)
        self.function_calling_enabled = self._get_bool("FEATURE_FUNCTION_CALL", False)
        self.multi_ai_enabled = self._get_bool("FEATURE_MULTI_AI", False)
        self.enterprise_auth_enabled = self._get_bool("FEATURE_ENTERPRISE_AUTH", False)
        
        # 開発・テスト用フラグ
        self.debug_mode_enabled = self._get_bool("DEBUG_MODE", False)
        self.mock_mode_enabled = self._get_bool("LOCAL_MOCK_MODE", False)
        
    def _get_bool(self, env_key: str, default_value: bool) -> bool:
        """環境変数からbool値を安全に取得"""
        env_value = os.environ.get(env_key, str(default_value)).lower()
        return env_value in ("true", "1", "yes", "on")
    
    def is_production_environment(self) -> bool:
        """プロダクション環境の判定"""
        return (
            os.environ.get("AZURE_ENV_NAME", "").startswith(("prod", "production")) or 
            os.environ.get("BACKEND_URI", "").startswith("https://") or
            bool(os.environ.get("WEBSITE_SITE_NAME"))
        )
    
    def should_use_new_conversation(self) -> bool:
        """新しい会話システムを使用するか"""
        return self.new_conversation_enabled and not self._force_legacy_mode()
    
    def should_use_new_history(self) -> bool:
        """新しい履歴システムを使用するか"""
        return self.new_history_enabled and not self._force_legacy_mode()
    
    def should_rollback_on_error(self) -> bool:
        """エラー時にロールバックするか"""
        return self.rollback_enabled
    
    # Phase 2C統合メソッド（Task 5: GREEN Phase追加）
    def should_use_phase2c_architecture(self) -> bool:
        """Phase 2C新アーキテクチャを使用するか"""
        return self.phase2c_enabled and not self._force_legacy_mode()
    
    def get_phase2c_migration_percentage(self) -> int:
        """Phase 2C移行率を取得"""
        return max(0, min(100, self.phase2c_migration_percentage))
    
    def should_enable_phase2c_e2e_integration(self) -> bool:
        """Phase 2C E2E統合を有効にするか"""
        return (self.phase2c_e2e_integration_enabled and 
                self.should_use_phase2c_architecture())
    
    def determine_system_routing(self, user_id: str) -> str:
        """ユーザーIDに基づいてシステムルーティングを決定"""
        if not self.should_use_phase2c_architecture():
            return "legacy"
        
        # 移行率に基づいたルーティング（簡単なハッシュベース）
        migration_rate = self.get_phase2c_migration_percentage()
        if migration_rate == 0:
            return "legacy"
        elif migration_rate == 100:
            return "phase2c_new"
        else:
            # ユーザーIDのハッシュに基づいて段階的移行
            import hashlib
            user_hash = int(hashlib.md5(user_id.encode()).hexdigest(), 16)
            if (user_hash % 100) < migration_rate:
                return "phase2c_new"
            else:
                return "legacy"
    
    def _force_legacy_mode(self) -> bool:
        """強制的に既存システムを使用するか（緊急時用）"""
        return self._get_bool("FORCE_LEGACY_MODE", False)
    
    def get_all_flags(self) -> Dict[str, Any]:
        """全フラグの状態を取得（監視・デバッグ用）"""
        return {
            "new_conversation_enabled": self.new_conversation_enabled,
            "new_history_enabled": self.new_history_enabled,
            "rollback_enabled": self.rollback_enabled,
            "modern_rag_enabled": self.modern_rag_enabled,
            "stream_response_enabled": self.stream_response_enabled,
            "function_calling_enabled": self.function_calling_enabled,
            "multi_ai_enabled": self.multi_ai_enabled,
            "enterprise_auth_enabled": self.enterprise_auth_enabled,
            "debug_mode_enabled": self.debug_mode_enabled,
            "mock_mode_enabled": self.mock_mode_enabled,
            "is_production": self.is_production_environment(),
            "force_legacy_mode": self._force_legacy_mode(),
            # Phase 2C統合フラグ追加
            "phase2c_enabled": self.phase2c_enabled,
            "phase2c_migration_percentage": self.phase2c_migration_percentage,
            "phase2c_e2e_integration_enabled": self.phase2c_e2e_integration_enabled
        }
    
    def validate_configuration(self) -> bool:
        """設定の妥当性を検証"""
        # プロダクション環境では危険なフラグを無効化
        if self.is_production_environment():
            if self.debug_mode_enabled or self.mock_mode_enabled:
                return False
                
        return True


# グローバルインスタンス（シングルトン）
_feature_flags_instance = None

def get_feature_flags() -> FeatureFlags:
    """FeatureFlagsのシングルトンインスタンスを取得"""
    global _feature_flags_instance
    if _feature_flags_instance is None:
        _feature_flags_instance = FeatureFlags()
    return _feature_flags_instance


def reset_feature_flags():
    """テスト用: フラグのリセット"""
    global _feature_flags_instance
    _feature_flags_instance = None


if __name__ == "__main__":
    # 設定確認用スクリプト
    flags = get_feature_flags()
    print("=== Feature Flags Configuration ===")
    for key, value in flags.get_all_flags().items():
        print(f"{key}: {value}")
    print(f"Configuration valid: {flags.validate_configuration()}")
