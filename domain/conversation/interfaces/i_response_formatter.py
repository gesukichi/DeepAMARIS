"""
応答フォーマッター インターフェース

Flask関数群（jsonify, make_response等）の抽象化を提供し、
外部依存関係を分離してテスト可能性を向上させます。

Created: 2025-08-27
Purpose: Task 2 RED Phase - Flask応答フォーマット機能の抽象化
"""

from abc import ABC, abstractmethod
from typing import Any, Dict
from flask import Response


class IResponseFormatter(ABC):
    """
    応答フォーマッター インターフェース
    
    Flask関数群を抽象化し、テスト可能性を向上させます。
    """
    
    @abstractmethod
    def format_json_response(
        self, 
        data: Dict[str, Any], 
        status_code: int = 200,
        headers: Dict[str, str] = None
    ) -> Response:
        """
        JSON形式の応答を作成します。
        
        Args:
            data: JSON化するデータ
            status_code: HTTPステータスコード（デフォルト: 200）
            headers: 追加HTTPヘッダー（オプション）
            
        Returns:
            Flask Response オブジェクト
        """
        ...
    
    @abstractmethod
    def format_streaming_response(
        self,
        generator,
        content_type: str = "text/plain",
        headers: Dict[str, str] = None
    ) -> Response:
        """
        ストリーミング応答を作成します。
        
        Args:
            generator: ストリーミングデータのジェネレーター
            content_type: コンテンツタイプ（デフォルト: "text/plain"）
            headers: 追加HTTPヘッダー（オプション）
            
        Returns:
            Flask Response オブジェクト（ストリーミング）
        """
        ...
    
    @abstractmethod
    def format_error_response(
        self,
        error_message: str,
        status_code: int = 500,
        error_code: str = None
    ) -> Response:
        """
        エラー応答を作成します。
        
        Args:
            error_message: エラーメッセージ
            status_code: HTTPステータスコード（デフォルト: 500）
            error_code: アプリケーション固有のエラーコード（オプション）
            
        Returns:
            Flask Response オブジェクト
        """
        ...
