"""
Lightweight Dependency Injection Container
軽量依存性注入コンテナ

T-Wada TDD原則に基づく設計:
- シンプルで理解しやすい実装
- テスト時のモック注入が容易
- 既存コードへの影響最小
"""

from typing import Type, TypeVar, Dict, Any, Callable, Optional, Protocol
import logging

# 型変数定義
T = TypeVar('T')

logger = logging.getLogger(__name__)


class IServiceContainer(Protocol):
    """サービスコンテナのインターフェース"""
    
    def register(self, interface: Type[T], implementation: Type[T], singleton: bool = False) -> None:
        """サービスを登録"""
        ...
    
    def resolve(self, interface: Type[T]) -> T:
        """サービスのインスタンスを解決"""
        ...


class ServiceContainer:
    """
    軽量依存性注入コンテナ
    
    特徴:
    - シンプルな設計（過度に複雑にしない）
    - シングルトンサポート
    - ファクトリ関数サポート
    - テスト用のモック注入対応
    """
    
    def __init__(self):
        self._services: Dict[Type[Any], Dict[str, Any]] = {}
        self._singletons: Dict[Type[Any], Any] = {}
        self._factories: Dict[Type[Any], Callable[[], Any]] = {}
    
    def register(self, interface: Type[T], implementation: Type[T], singleton: bool = False) -> None:
        """
        サービスを登録
        
        Args:
            interface: インターフェース型
            implementation: 実装クラス
            singleton: シングルトンかどうか
        """
        self._services[interface] = {
            'implementation': implementation,
            'singleton': singleton
        }
        
        logger.debug(f"Registered {interface.__name__} -> {implementation.__name__} (singleton={singleton})")
    
    def register_factory(self, interface: Type[T], factory: Callable[[], T], singleton: bool = False) -> None:
        """
        ファクトリ関数を登録
        
        Args:
            interface: インターフェース型
            factory: インスタンスを生成する関数
            singleton: シングルトンかどうか
        """
        self._factories[interface] = factory
        self._services[interface] = {
            'factory': factory,
            'singleton': singleton
        }
        
        logger.debug(f"Registered factory for {interface.__name__} (singleton={singleton})")
    
    def register_instance(self, interface: Type[T], instance: T) -> None:
        """
        既存のインスタンスを登録（シングルトンとして）
        
        Args:
            interface: インターフェース型
            instance: インスタンス
        """
        self._singletons[interface] = instance
        self._services[interface] = {
            'instance': instance,
            'singleton': True
        }
        
        logger.debug(f"Registered instance for {interface.__name__}")
    
    def resolve(self, interface: Type[T]) -> T:
        """
        サービスのインスタンスを解決
        
        Args:
            interface: インターフェース型
            
        Returns:
            インスタンス
            
        Raises:
            ValueError: 登録されていないサービス
        """
        # シングルトンキャッシュから確認
        if interface in self._singletons:
            return self._singletons[interface]
        
        # サービス登録から確認
        if interface not in self._services:
            raise ValueError(f"Service {interface.__name__} is not registered")
        
        service_info = self._services[interface]
        
        # インスタンス登録済みの場合
        if 'instance' in service_info:
            return service_info['instance']
        
        # ファクトリ関数がある場合
        if 'factory' in service_info:
            instance = service_info['factory']()
        else:
            # 通常のクラスインスタンス化
            implementation = service_info['implementation']
            instance = implementation()
        
        # シングルトンの場合はキャッシュ
        if service_info.get('singleton', False):
            self._singletons[interface] = instance
        
        logger.debug(f"Resolved {interface.__name__} -> {type(instance).__name__}")
        return instance
    
    def is_registered(self, interface: Type[T]) -> bool:
        """サービスが登録されているかどうか"""
        return interface in self._services
    
    def clear(self) -> None:
        """全サービスをクリア（テスト用）"""
        self._services.clear()
        self._singletons.clear()
        self._factories.clear()
        logger.debug("Container cleared")
    
    def get_registered_services(self) -> Dict[str, str]:
        """登録済みサービス一覧を取得（デバッグ用）"""
        services = {}
        for interface, service_info in self._services.items():
            if 'implementation' in service_info:
                impl_name = service_info['implementation'].__name__
            elif 'factory' in service_info:
                impl_name = "Factory"
            elif 'instance' in service_info:
                impl_name = type(service_info['instance']).__name__
            else:
                impl_name = "Unknown"
            
            services[interface.__name__] = impl_name
        
        return services

    # Phase 2C統合メソッド（Task 5: GREEN Phase実装）
    def get_conversation_service(self):
        """ConversationService取得 - Phase 2C統合"""
        try:
            from domain.conversation.services.conversation_service import ConversationService
            # 既存のConversationServiceを返す（Task 1完了済み）
            return ConversationService()
        except ImportError as e:
            logger.error("ConversationService import failed: %s", e)
            raise NotImplementedError("ConversationService not available") from e
    
    def get_history_manager(self):
        """HistoryManager取得 - Phase 2C統合"""
        try:
            from domain.conversation.services.history_manager import HistoryManager
            # 既存のHistoryManagerを返す（Task 2完了済み）
            return HistoryManager()
        except ImportError as e:
            logger.error("HistoryManager import failed: %s", e)
            raise NotImplementedError("HistoryManager not available") from e
    
    def get_ai_response_generator(self):
        """AIResponseGenerator取得 - Phase 2C統合"""
        try:
            from domain.conversation.services.ai_response_generator import AIResponseGenerator
            from infrastructure.services.configuration_service import ConfigurationService
            
            # ConfigurationServiceを作成してAIResponseGeneratorに注入
            config_service = ConfigurationService()
            return AIResponseGenerator(configuration_service=config_service)
        except ImportError as e:
            logger.error("AIResponseGenerator import failed: %s", e)
            raise NotImplementedError("AIResponseGenerator not available") from e
    
    def get_legacy_conversation_adapter(self):
        """LegacyConversationAdapter取得 - Phase 2C統合"""
        try:
            from infrastructure.adapters.legacy_conversation_adapter import LegacyConversationAdapter
            # 既存のLegacyConversationAdapterを返す（Task 4完了済み）
            return LegacyConversationAdapter()
        except ImportError as e:
            logger.error("LegacyConversationAdapter import failed: %s", e)
            raise NotImplementedError("LegacyConversationAdapter not available") from e


# グローバルコンテナインスタンス
_container_instance: Optional[ServiceContainer] = None

def get_container() -> ServiceContainer:
    """グローバルコンテナインスタンスを取得"""
    # グローバル変数の使用をlintエラー回避のため必要最小限に
    global _container_instance
    if _container_instance is None:
        _container_instance = ServiceContainer()
        logger.info("Created new ServiceContainer instance")
    return _container_instance


def reset_container() -> None:
    """コンテナをリセット（テスト用）"""
    global _container_instance
    if _container_instance:
        _container_instance.clear()
    _container_instance = None
    logger.info("Container reset")


class ContainerBuilder:
    """
    サービスコンテナの設定ビルダー
    アプリケーション起動時の設定用
    """
    
    def __init__(self, container: ServiceContainer):
        self.container = container
    
    def build_default_services(self):
        """デフォルトサービスの登録"""
        from infrastructure.configuration.feature_flags import get_feature_flags
        
        # FeatureFlagsをシングルトンとして登録
        self.container.register_instance(type(get_feature_flags()), get_feature_flags())
        
        logger.info("Default services registered")
        return self
    
    def build_conversation_services(self):
        """会話関連サービスの登録（段階的実装用）"""
        # 実装予定: 会話関連のサービス登録
        logger.info("Conversation services registration prepared")
        return self
    
    def build_test_services(self):
        """テスト用サービスの登録"""
        # テスト用のモック登録
        logger.info("Test services registration prepared")
        return self


if __name__ == "__main__":
    # コンテナの動作確認
    container = get_container()
    builder = ContainerBuilder(container)
    builder.build_default_services()
    
    print("=== Service Container Status ===")
    print("Registered services:", container.get_registered_services())
    
    # FeatureFlagsの解決テスト
    from infrastructure.configuration.feature_flags import FeatureFlags
    flags = container.resolve(FeatureFlags)
    print(f"FeatureFlags resolved: {type(flags).__name__}")
    print(f"Feature flags: {flags.get_all_flags()}")
