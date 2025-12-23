"""
ConversationFacade - TDD Green フェーズ実装

t-wadaさんのTDD原則に従った最小限の実装:
1. テストを通すための最小限のコード
2. 既存の conversation_internal への完全委譲
3. 既存動作の完全保持（動作変更なし）
"""

import logging
from typing import Dict, Any, Optional
from quart import jsonify


class ConversationFacade:
    """
    会話機能のFacade
    
    TDD原則に従い、既存動作を完全に保持しながら新アーキテクチャへの橋渡しを行う
    """
    
    def __init__(self, feature_flags: Optional[Any] = None):
        """
        Facadeの初期化
        
        Args:
            feature_flags: フィーチャーフラグ（省略可能）
        """
        self._feature_flags = feature_flags
        self._logger = logging.getLogger(__name__)
    
    async def handle_conversation(self, request_body: Dict[str, Any], request_headers: Any):
        """
        会話リクエストを処理する
        
        TDD Green フェーズ: 既存の conversation_internal に完全委譲
        
        Args:
            request_body: リクエストボディ
            request_headers: リクエストヘッダー
            
        Returns:
            conversation_internal と同じレスポンス
        """
        try:
            # TDD Phase 4: ConversationOrchestratorへの移行
            # conversation_internal削除に向けた段階的移行
            from application.conversation.use_cases.orchestrate_conversation import ConversationOrchestrator
            
            self._logger.info("ConversationFacade: Using ConversationOrchestrator (conversation_internal migration)")
            
            # ConversationOrchestratorで既存動作を完全保持
            orchestrator = ConversationOrchestrator()
            result = await orchestrator.handle_conversation_request_with_app_integration(
                request_body, request_headers
            )
            
            return result
            
        except Exception as ex:
            # 既存のエラーハンドリングパターンを保持
            self._logger.exception("ConversationFacade error")
            if hasattr(ex, "status_code"):
                return jsonify({"error": str(ex)}), ex.status_code
            else:
                return jsonify({"error": str(ex)}), 500
