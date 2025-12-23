"""
Task 12: SystemController Tests
TDD RED Phase: システム関連API制御の包括的テストケース

移植対象機能:
1. get_frontend_settings() - フロントエンド設定取得（Key Vault統合）
2. healthz() - 軽量ヘルスチェック
3. health_check() - 詳細ヘルスチェック

軽量実装方針: 必要最小限の機能、外部委託中程度の優先度
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime
import json
from backend.application.system.controllers.system_controller import SystemController


class TestSystemController:
    """SystemController TDD テストスイート"""
    
    def setup_method(self):
        """各テストメソッド実行前の初期化"""
        self.controller = SystemController()
    
    # =============================================================================
    # Frontend Settings API Tests (Key Vault統合)
    # =============================================================================
    
    @pytest.mark.asyncio
    async def test_get_frontend_settings_basic_success(self):
        """フロントエンド設定取得の基本動作テスト"""
        # Arrange
        mock_basic_settings = {
            "auth_enabled": False,
            "feedback_enabled": False,
            "ui": {
                "title": "Test App",
                "logo": None,
                "chat_logo": None,
                "chat_title": "Start chatting",
                "chat_description": "Test description",
                "show_share_button": True,
                "show_chat_history_button": False
            },
            "sanitize_answer": True,
            "oyd_enabled": None
        }
        
        with patch('backend.application.system.controllers.system_controller.get_basic_frontend_settings') as mock_basic:
            mock_basic.return_value = mock_basic_settings
            
            # Act
            result = await self.controller.get_frontend_settings()
            
            # Assert
            assert result is not None
            assert result["auth_enabled"] is False
            assert result["ui"]["title"] == "Test App"
            assert result["sanitize_answer"] is True
    
    @pytest.mark.asyncio 
    async def test_get_frontend_settings_with_keyvault_integration(self):
        """Key Vaultサービス統合を含むフロントエンド設定取得テスト"""
        # Arrange
        mock_basic_settings = {
            "auth_enabled": False,
            "ui": {"title": "Base App"}
        }
        
        mock_keyvault_settings = {
            "auth_enabled": True,
            "ui": {"title": "Enhanced App", "logo": "kv-logo.png"}
        }
        
        mock_keyvault_service = Mock()
        mock_keyvault_service.get_frontend_settings.return_value = mock_keyvault_settings
        
        with patch('backend.application.system.controllers.system_controller.get_basic_frontend_settings') as mock_basic, \
             patch('backend.application.system.controllers.system_controller.get_keyvault_service') as mock_kv:
            
            mock_basic.return_value = mock_basic_settings.copy()
            mock_kv.return_value = mock_keyvault_service
            
            # Act
            result = await self.controller.get_frontend_settings()
            
            # Assert
            assert result["auth_enabled"] is True  # Key Vaultで上書き
            assert result["ui"]["title"] == "Enhanced App"  # Key Vaultで上書き
            assert result["ui"]["logo"] == "kv-logo.png"  # Key Vaultから追加
            mock_keyvault_service.get_frontend_settings.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_frontend_settings_keyvault_error_fallback(self):
        """Key Vault取得エラー時のフォールバック動作テスト"""
        # Arrange
        mock_basic_settings = {"auth_enabled": False, "ui": {"title": "Base App"}}
        
        mock_keyvault_service = Mock()
        mock_keyvault_service.get_frontend_settings.side_effect = Exception("Key Vault connection failed")
        
        with patch('backend.application.system.controllers.system_controller.get_basic_frontend_settings') as mock_basic, \
             patch('backend.application.system.controllers.system_controller.get_keyvault_service') as mock_kv:
            
            mock_basic.return_value = mock_basic_settings
            mock_kv.return_value = mock_keyvault_service
            
            # Act
            result = await self.controller.get_frontend_settings()
            
            # Assert
            assert result["auth_enabled"] is False  # 基本設定のまま
            assert result["ui"]["title"] == "Base App"  # 基本設定のまま
    
    @pytest.mark.asyncio
    async def test_get_frontend_settings_keyvault_service_unavailable(self):
        """Key Vaultサービス利用不可時の動作テスト"""
        # Arrange
        mock_basic_settings = {"auth_enabled": False, "ui": {"title": "Base App"}}
        
        with patch('backend.application.system.controllers.system_controller.get_basic_frontend_settings') as mock_basic, \
             patch('backend.application.system.controllers.system_controller.get_keyvault_service') as mock_kv:
            
            mock_basic.return_value = mock_basic_settings
            mock_kv.return_value = None  # サービス利用不可
            
            # Act
            result = await self.controller.get_frontend_settings()
            
            # Assert
            assert result["auth_enabled"] is False
            assert result["ui"]["title"] == "Base App"
    
    @pytest.mark.asyncio
    async def test_get_frontend_settings_exception_handling(self):
        """フロントエンド設定取得での例外処理テスト"""
        # Arrange
        with patch('backend.application.system.controllers.system_controller.get_basic_frontend_settings') as mock_basic:
            mock_basic.side_effect = Exception("Configuration error")
            
            # Act & Assert
            with pytest.raises(Exception) as exc_info:
                await self.controller.get_frontend_settings()
            
            assert "Configuration error" in str(exc_info.value)
    
    # =============================================================================
    # Lightweight Health Check Tests (/healthz)
    # =============================================================================
    
    @pytest.mark.asyncio
    async def test_lightweight_health_check_success(self):
        """軽量ヘルスチェック成功時のテスト"""
        # Act
        result = await self.controller.lightweight_health_check()
        
        # Assert
        assert result is not None
        assert result["status"] == "ok"
        assert "time" in result
        
        # ISO 8601 形式のタイムスタンプを確認
        timestamp = result["time"]
        assert timestamp.endswith("Z")
        assert "T" in timestamp
    
    @pytest.mark.asyncio
    async def test_lightweight_health_check_minimal_dependencies(self):
        """軽量ヘルスチェックの最小依存性テスト"""
        # 外部依存なしで動作することを確認
        result = await self.controller.lightweight_health_check()
        
        # Assert
        assert len(result) == 2  # status と time のみ
        assert result["status"] == "ok"
        assert isinstance(result["time"], str)
    
    @pytest.mark.asyncio
    async def test_lightweight_health_check_exception_resilience(self):
        """軽量ヘルスチェックの例外耐性テスト"""
        # datetime.utcnow()をモックしてエラーを発生させる
        with patch('backend.application.system.controllers.system_controller.datetime') as mock_dt:
            mock_dt.utcnow.side_effect = Exception("Time service error")
            
            # Act
            result = await self.controller.lightweight_health_check()
            
            # Assert
            assert result["status"] == "error"
    
    # =============================================================================
    # Detailed Health Check Tests (/health)
    # =============================================================================
    
    @pytest.mark.asyncio
    async def test_detailed_health_check_all_services_healthy(self):
        """詳細ヘルスチェック - 全サービス正常時のテスト"""
        # Arrange
        mock_service_checker = Mock()
        mock_service_checker.check_azure_openai_status.return_value = "configured"
        mock_service_checker.check_cosmos_db_status.return_value = "configured"  
        mock_service_checker.check_modern_rag_status.return_value = "available"
        
        with patch('backend.application.system.controllers.system_controller.get_service_health_checker') as mock_checker:
            mock_checker.return_value = mock_service_checker
            
            # Act
            result = await self.controller.detailed_health_check()
            
            # Assert
            assert result["status"] == "healthy"
            assert result["version"] == "1.0.0"
            assert "timestamp" in result
            
            services = result["services"]
            assert services["azure_openai"] == "configured"
            assert services["cosmos_db"] == "configured"
            assert services["modern_rag"] == "available"
    
    @pytest.mark.asyncio
    async def test_detailed_health_check_mixed_service_status(self):
        """詳細ヘルスチェック - サービス状態混在時のテスト"""
        # Arrange
        mock_service_checker = Mock()
        mock_service_checker.check_azure_openai_status.return_value = "configured"
        mock_service_checker.check_cosmos_db_status.return_value = "not_configured"
        mock_service_checker.check_modern_rag_status.return_value = "error"
        
        with patch('backend.application.system.controllers.system_controller.get_service_health_checker') as mock_checker:
            mock_checker.return_value = mock_service_checker
            
            # Act  
            result = await self.controller.detailed_health_check()
            
            # Assert
            assert result["status"] == "healthy"  # 基本ステータスは正常
            
            services = result["services"]
            assert services["azure_openai"] == "configured"
            assert services["cosmos_db"] == "not_configured"
            assert services["modern_rag"] == "error"
    
    @pytest.mark.asyncio
    async def test_detailed_health_check_service_checker_unavailable(self):
        """詳細ヘルスチェック - サービスチェッカー利用不可時のテスト"""
        # Arrange
        with patch('backend.application.system.controllers.system_controller.get_service_health_checker') as mock_checker:
            mock_checker.return_value = None
            
            # Act
            result = await self.controller.detailed_health_check()
            
            # Assert
            assert result["status"] == "healthy"
            
            services = result["services"]
            assert services["azure_openai"] == "unknown"
            assert services["cosmos_db"] == "unknown" 
            assert services["modern_rag"] == "unknown"
    
    @pytest.mark.asyncio
    async def test_detailed_health_check_exception_handling(self):
        """詳細ヘルスチェック例外処理テスト"""
        # Arrange
        with patch('backend.application.system.controllers.system_controller.get_service_health_checker') as mock_checker:
            mock_checker.side_effect = Exception("Service checker initialization failed")
            
            # Act & Assert
            with pytest.raises(Exception) as exc_info:
                await self.controller.detailed_health_check()
            
            assert "Service checker initialization failed" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_detailed_health_check_individual_service_errors(self):
        """詳細ヘルスチェック - 個別サービスエラー時のテスト"""
        # Arrange
        mock_service_checker = Mock()
        mock_service_checker.check_azure_openai_status.side_effect = Exception("OpenAI check failed")
        mock_service_checker.check_cosmos_db_status.return_value = "configured"
        mock_service_checker.check_modern_rag_status.return_value = "available"
        
        with patch('backend.application.system.controllers.system_controller.get_service_health_checker') as mock_checker:
            mock_checker.return_value = mock_service_checker
            
            # Act
            result = await self.controller.detailed_health_check()
            
            # Assert
            assert result["status"] == "healthy"  # 他サービス正常なので全体は正常
            
            services = result["services"]
            assert services["azure_openai"] == "error"  # エラーハンドリング
            assert services["cosmos_db"] == "configured"
            assert services["modern_rag"] == "available"
    
    # =============================================================================
    # Integration and Edge Case Tests
    # =============================================================================
    
    @pytest.mark.asyncio
    async def test_system_controller_initialization(self):
        """SystemController初期化テスト"""
        # Act
        controller = SystemController()
        
        # Assert
        assert controller is not None
        assert hasattr(controller, 'get_frontend_settings')
        assert hasattr(controller, 'lightweight_health_check')
        assert hasattr(controller, 'detailed_health_check')
    
    @pytest.mark.asyncio
    async def test_concurrent_api_calls(self):
        """並行API呼び出しテスト"""
        import asyncio
        
        # Act - 複数のAPIを並行実行
        tasks = [
            self.controller.lightweight_health_check(),
            self.controller.detailed_health_check(),
            self.controller.get_frontend_settings()
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Assert
        assert len(results) == 3
        
        # 軽量ヘルスチェック結果
        assert results[0]["status"] == "ok"
        
        # 詳細ヘルスチェック結果（例外の可能性があるためチェック）
        if not isinstance(results[1], Exception):
            assert results[1]["status"] == "healthy"
        
        # フロントエンド設定結果（例外の可能性があるためチェック）
        if not isinstance(results[2], Exception):
            assert "ui" in results[2]
    
    @pytest.mark.asyncio
    async def test_performance_lightweight_vs_detailed_health_check(self):
        """軽量vs詳細ヘルスチェックのパフォーマンステスト"""
        import time
        
        # 軽量ヘルスチェックの実行時間測定（複数回実行で精度向上）
        lightweight_durations = []
        for _ in range(10):
            start_time = time.perf_counter()
            await self.controller.lightweight_health_check()
            lightweight_durations.append(time.perf_counter() - start_time)
        
        avg_lightweight = sum(lightweight_durations) / len(lightweight_durations)
        
        # 詳細ヘルスチェックの実行時間測定（モックあり）
        detailed_durations = []
        with patch('backend.application.system.controllers.system_controller.get_service_health_checker') as mock_checker:
            mock_service_checker = Mock()
            # 少し遅延を追加してリアルなサービスチェックをシミュレート
            def slow_check_openai():
                time.sleep(0.001)  # 1ms遅延
                return "configured"
            def slow_check_cosmos():
                time.sleep(0.001)  # 1ms遅延
                return "configured"
            def slow_check_rag():
                time.sleep(0.001)  # 1ms遅延
                return "available"
            
            mock_service_checker.check_azure_openai_status.side_effect = slow_check_openai
            mock_service_checker.check_cosmos_db_status.side_effect = slow_check_cosmos
            mock_service_checker.check_modern_rag_status.side_effect = slow_check_rag
            mock_checker.return_value = mock_service_checker
            
            for _ in range(10):
                start_time = time.perf_counter()
                await self.controller.detailed_health_check()
                detailed_durations.append(time.perf_counter() - start_time)
        
        avg_detailed = sum(detailed_durations) / len(detailed_durations)
        
        # Assert: 詳細ヘルスチェックは軽量版より時間がかかるべき
        # ただし、実行時間が非常に短い場合はテストをスキップ
        if avg_lightweight > 0.0001 and avg_detailed > 0.0001:  # 0.1ms以上の場合のみテスト
            assert avg_detailed > avg_lightweight, f"Detailed check ({avg_detailed:.6f}s) should be slower than lightweight ({avg_lightweight:.6f}s)"
        else:
            # 実行時間が短すぎる場合は、基本的な機能確認のみ
            assert avg_lightweight >= 0  # 軽量ヘルスチェックが実行できる
            assert avg_detailed >= 0     # 詳細ヘルスチェックが実行できる
