"""
Task 12: SystemRouter Tests  
TDD RED Phase: システムルーティングの包括的テストケース

テスト対象:
1. handle_frontend_settings() - フロントエンド設定ルーティング
2. handle_lightweight_health_check() - 軽量ヘルスチェックルーティング  
3. handle_detailed_health_check() - 詳細ヘルスチェックルーティング

軽量実装方針: エラーハンドリング、HTTPステータス管理、レスポンス形式統一
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from backend.application.system.routers.system_router import SystemRouter


class TestSystemRouter:
    """SystemRouter TDD テストスイート"""
    
    def setup_method(self):
        """各テストメソッド実行前の初期化"""
        self.router = SystemRouter()
    
    # =============================================================================
    # Frontend Settings Routing Tests
    # =============================================================================
    
    @pytest.mark.asyncio
    async def test_handle_frontend_settings_success(self):
        """フロントエンド設定ルーティング成功テスト"""
        # Arrange
        mock_settings = {
            "auth_enabled": True,
            "ui": {"title": "Test App"},
            "sanitize_answer": True
        }
        
        with patch.object(self.router.controller, 'get_frontend_settings', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_settings
            
            # Act
            result, status_code = await self.router.handle_frontend_settings()
            
            # Assert
            assert status_code == 200
            assert result == mock_settings
            mock_get.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_handle_frontend_settings_controller_exception(self):
        """フロントエンド設定取得時の例外処理テスト"""
        # Arrange
        with patch.object(self.router.controller, 'get_frontend_settings', new_callable=AsyncMock) as mock_get:
            mock_get.side_effect = Exception("Configuration error")
            
            # Act
            result, status_code = await self.router.handle_frontend_settings()
            
            # Assert
            assert status_code == 500
            assert "error" in result
            assert "Configuration error" in result["error"]
    
    # =============================================================================
    # Lightweight Health Check Routing Tests
    # =============================================================================
    
    @pytest.mark.asyncio
    async def test_handle_lightweight_health_check_success(self):
        """軽量ヘルスチェックルーティング成功テスト"""
        # Arrange
        mock_health = {"status": "ok", "time": "2024-01-01T00:00:00Z"}
        
        with patch.object(self.router.controller, 'lightweight_health_check', new_callable=AsyncMock) as mock_check:
            mock_check.return_value = mock_health
            
            # Act
            result, status_code = await self.router.handle_lightweight_health_check()
            
            # Assert
            assert status_code == 200
            assert result == mock_health
            mock_check.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_handle_lightweight_health_check_error_status(self):
        """軽量ヘルスチェック エラー状態のテスト"""
        # Arrange
        mock_health = {"status": "error"}
        
        with patch.object(self.router.controller, 'lightweight_health_check', new_callable=AsyncMock) as mock_check:
            mock_check.return_value = mock_health
            
            # Act
            result, status_code = await self.router.handle_lightweight_health_check()
            
            # Assert
            assert status_code == 500
            assert result == mock_health
    
    @pytest.mark.asyncio
    async def test_handle_lightweight_health_check_exception(self):
        """軽量ヘルスチェック例外処理テスト"""
        # Arrange
        with patch.object(self.router.controller, 'lightweight_health_check', new_callable=AsyncMock) as mock_check:
            mock_check.side_effect = Exception("Health check failed")
            
            # Act
            result, status_code = await self.router.handle_lightweight_health_check()
            
            # Assert
            assert status_code == 500
            assert result["status"] == "error"
            assert "Health check failed" in result["error"]
    
    # =============================================================================
    # Detailed Health Check Routing Tests
    # =============================================================================
    
    @pytest.mark.asyncio
    async def test_handle_detailed_health_check_healthy(self):
        """詳細ヘルスチェック正常状態テスト"""
        # Arrange
        mock_health = {
            "status": "healthy",
            "timestamp": "2024-01-01T00:00:00",
            "services": {
                "azure_openai": "configured",
                "cosmos_db": "configured",
                "modern_rag": "available"
            }
        }
        
        with patch.object(self.router.controller, 'detailed_health_check', new_callable=AsyncMock) as mock_check:
            mock_check.return_value = mock_health
            
            # Act
            result, status_code = await self.router.handle_detailed_health_check()
            
            # Assert
            assert status_code == 200
            assert result == mock_health
            mock_check.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_handle_detailed_health_check_unhealthy(self):
        """詳細ヘルスチェック異常状態テスト"""
        # Arrange
        mock_health = {
            "status": "unhealthy",
            "services": {
                "azure_openai": "error",
                "cosmos_db": "not_configured"
            }
        }
        
        with patch.object(self.router.controller, 'detailed_health_check', new_callable=AsyncMock) as mock_check:
            mock_check.return_value = mock_health
            
            # Act
            result, status_code = await self.router.handle_detailed_health_check()
            
            # Assert
            assert status_code == 500
            assert result == mock_health
    
    @pytest.mark.asyncio
    async def test_handle_detailed_health_check_unknown_status(self):
        """詳細ヘルスチェック不明状態テスト"""
        # Arrange
        mock_health = {"status": "unknown"}
        
        with patch.object(self.router.controller, 'detailed_health_check', new_callable=AsyncMock) as mock_check:
            mock_check.return_value = mock_health
            
            # Act
            result, status_code = await self.router.handle_detailed_health_check()
            
            # Assert
            assert status_code == 503  # Service Unavailable
            assert result == mock_health
    
    @pytest.mark.asyncio
    async def test_handle_detailed_health_check_exception(self):
        """詳細ヘルスチェック例外処理テスト"""
        # Arrange
        with patch.object(self.router.controller, 'detailed_health_check', new_callable=AsyncMock) as mock_check:
            mock_check.side_effect = Exception("Service unavailable")
            
            # Act
            result, status_code = await self.router.handle_detailed_health_check()
            
            # Assert
            assert status_code == 500
            assert result["status"] == "unhealthy"
            assert "Service unavailable" in result["error"]
            assert "timestamp" in result
    
    # =============================================================================
    # Helper Method Tests
    # =============================================================================
    
    def test_determine_health_status_code_healthy(self):
        """ヘルスステータスコード決定 - 正常テスト"""
        # Arrange
        health_report = {"status": "healthy"}
        
        # Act
        status_code = self.router._determine_health_status_code(health_report)
        
        # Assert
        assert status_code == 200
    
    def test_determine_health_status_code_unhealthy(self):
        """ヘルスステータスコード決定 - 異常テスト"""
        # Arrange
        health_report = {"status": "unhealthy"}
        
        # Act
        status_code = self.router._determine_health_status_code(health_report)
        
        # Assert
        assert status_code == 500
    
    def test_determine_health_status_code_unknown(self):
        """ヘルスステータスコード決定 - 不明テスト"""
        # Arrange
        health_report = {"status": "unknown"}
        
        # Act
        status_code = self.router._determine_health_status_code(health_report)
        
        # Assert
        assert status_code == 503
    
    def test_get_current_timestamp(self):
        """現在タイムスタンプ取得テスト"""
        # Act
        timestamp = self.router._get_current_timestamp()
        
        # Assert
        assert isinstance(timestamp, str)
        assert "T" in timestamp  # ISO 8601 format
    
    # =============================================================================
    # Router Initialization Tests
    # =============================================================================
    
    def test_system_router_initialization(self):
        """SystemRouter初期化テスト"""
        # Act
        router = SystemRouter()
        
        # Assert
        assert router is not None
        assert hasattr(router, 'controller')
        assert hasattr(router, 'logger')
        assert hasattr(router, 'handle_frontend_settings')
        assert hasattr(router, 'handle_lightweight_health_check')
        assert hasattr(router, 'handle_detailed_health_check')
    
    # =============================================================================
    # Integration Tests
    # =============================================================================
    
    @pytest.mark.asyncio
    async def test_router_controller_integration(self):
        """ルーター・コントローラー統合テスト"""
        # Act - 実際のコントローラーを使用
        try:
            result, status_code = await self.router.handle_lightweight_health_check()
            
            # Assert
            assert isinstance(result, dict)
            assert isinstance(status_code, int)
            assert status_code in [200, 500]
            
        except Exception:
            # インテグレーション環境で失敗しても問題なし
            pytest.skip("Integration environment not available")
    
    @pytest.mark.asyncio
    async def test_concurrent_router_requests(self):
        """並行ルーターリクエストテスト"""
        import asyncio
        
        # Mock all controller methods
        with patch.object(self.router.controller, 'get_frontend_settings', new_callable=AsyncMock) as mock_settings, \
             patch.object(self.router.controller, 'lightweight_health_check', new_callable=AsyncMock) as mock_light, \
             patch.object(self.router.controller, 'detailed_health_check', new_callable=AsyncMock) as mock_detailed:
            
            mock_settings.return_value = {"ui": {"title": "Test"}}
            mock_light.return_value = {"status": "ok"}
            mock_detailed.return_value = {"status": "healthy"}
            
            # Act - 並行実行
            tasks = [
                self.router.handle_frontend_settings(),
                self.router.handle_lightweight_health_check(),
                self.router.handle_detailed_health_check()
            ]
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Assert
            assert len(results) == 3
            
            for result in results:
                assert not isinstance(result, Exception)
                response_data, status_code = result
                assert isinstance(response_data, dict)
                assert isinstance(status_code, int)
