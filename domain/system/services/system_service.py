"""
SystemService

システム設定を管理するサービス。
app.py の get_frontend_settings 機能を Domain 層に移行し、
外部コントラクターが使いやすいインターフェースを提供。

Design principles:
- SystemSettings エンティティを活用
- app.py との完全な互換性
- シンプルで使いやすいインターフェース
- 安全なエラーハンドリング
"""

from typing import Dict, Any, Optional
from domain.system.models.system_settings import SystemSettings


class SystemService:
    """
    システム設定を管理するサービス。
    
    責務:
    - SystemSettings エンティティの生成と管理
    - フロントエンド設定の提供
    - 環境変数オーバーライドの処理
    - app.py 互換性の保証
    
    Design patterns:
    - Service Layer パターン: ビジネスロジックの集約
    - Facade パターン: SystemSettings の複雑性を隠蔽
    - Factory パターン: SystemSettings インスタンスの生成
    """
    
    # 環境変数マッピング定数（設定値の一元管理）
    _ENV_MAPPING = {
        'AUTH_ENABLED': ('auth_enabled', 'bool'),
        'FEEDBACK_ENABLED': ('feedback_enabled', 'bool'),
        'UI_TITLE': ('ui.title', 'str'),
        'SANITIZE_ANSWER': ('sanitize_answer', 'bool')
    }
    
    def __init__(self):
        """SystemService を初期化します。"""
        # 将来的な拡張（ログ、メトリクス、キャッシュ等）のため
        # 現在は明示的な初期化処理なし
        self._initialized = True
    
    def get_frontend_settings(self, config_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        フロントエンド設定を取得します。
        app.py の get_frontend_settings と完全に互換性があります。
        
        Args:
            config_data: 設定データ辞書（None 可能）
            
        Returns:
            フロントエンド互換形式の設定辞書
        """
        # SystemSettings エンティティを使用して設定を作成
        system_settings = SystemSettings.from_config_data(config_data)
        
        # フロントエンド互換形式に変換
        return system_settings.to_frontend_dict()
    
    def get_system_configuration(
        self, 
        config_data: Optional[Dict[str, Any]] = None,
        env_overrides: Optional[Dict[str, str]] = None
    ) -> SystemSettings:
        """
        SystemSettings エンティティを取得します。
        
        Args:
            config_data: 基本設定データ
            env_overrides: 環境変数によるオーバーライド
            
        Returns:
            SystemSettings エンティティ
        """
        # 基本設定から SystemSettings を作成
        if config_data is None:
            config_data = {}
        
        # 環境変数オーバーライドを適用
        if env_overrides:
            config_data = self._apply_environment_overrides(config_data, env_overrides)
        
        return SystemSettings.from_config_data(config_data)
    
    def _apply_environment_overrides(
        self, 
        config_data: Dict[str, Any], 
        env_overrides: Dict[str, str]
    ) -> Dict[str, Any]:
        """
        環境変数オーバーライドを設定データに適用します。
        
        Args:
            config_data: 基本設定データ
            env_overrides: 環境変数オーバーライド
            
        Returns:
            オーバーライドが適用された設定データ
            
        Note:
            設定の型変換とネストしたパスの処理を安全に実行
        """
        # 設定データをコピーして変更（元データを保護）
        result = config_data.copy()
        
        for env_key, (config_path, value_type) in self._ENV_MAPPING.items():
            if env_key in env_overrides:
                raw_value = env_overrides[env_key]
                
                # 型変換の安全な実行
                converted_value = self._convert_env_value(raw_value, value_type)
                
                # ネストしたパスの処理
                self._set_nested_config_value(result, config_path, converted_value)
        
        return result
    
    def _convert_env_value(self, value: str, value_type: str) -> Any:
        """
        環境変数の値を指定された型に安全に変換します。
        
        Args:
            value: 環境変数の値（文字列）
            value_type: 変換先の型
            
        Returns:
            変換された値
        """
        if value_type == 'bool':
            return value.lower() in ('true', '1', 'yes', 'on')
        elif value_type == 'int':
            try:
                return int(value)
            except ValueError:
                return 0
        elif value_type == 'float':
            try:
                return float(value)
            except ValueError:
                return 0.0
        else:  # 'str' or default
            return value
    
    def _set_nested_config_value(
        self, 
        config_data: Dict[str, Any], 
        config_path: str, 
        value: Any
    ) -> None:
        """
        ネストしたパスに値を設定します。
        
        Args:
            config_data: 設定データ辞書
            config_path: ドット区切りの設定パス
            value: 設定する値
        """
        if '.' not in config_path:
            # 単純なパス
            config_data[config_path] = value
        else:
            # ネストしたパス
            parts = config_path.split('.')
            current = config_data
            
            # 中間階層を作成
            for part in parts[:-1]:
                if part not in current:
                    current[part] = {}
                current = current[part]
            
            # 最終値を設定
            current[parts[-1]] = value
