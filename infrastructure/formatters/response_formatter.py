"""
ResponseFormatter 実装クラス

Flask関数群（jsonify, make_response等）のラッパー実装
TDD REFACTOR Phase: 型安全性とエラーハンドリング強化

Created: 2025-08-27
Purpose: Task 2 REFACTOR Phase - Flask応答フォーマット機能の品質向上
"""

import json
import logging
from typing import Any, Dict, Generator, Optional, Union
from flask import Response
from domain.conversation.interfaces.i_response_formatter import IResponseFormatter


class ResponseFormatter(IResponseFormatter):
    """
    ResponseFormatter 実装クラス
    
    Flask関数群を抽象化し、テスト可能性を向上させます。
    REFACTOR Phase: 型安全性、エラーハンドリング、ログ機能を強化
    """
    
    def __init__(self) -> None:
        """
        ResponseFormatter を初期化します。
        
        ログ設定を行い、デバッグ支援機能を提供します。
        """
        self._logger = logging.getLogger(__name__)
        self._logger.debug("ResponseFormatter インスタンスを初期化しました")
    
    def format_json_response(
        self, 
        data: Dict[str, Any], 
        status_code: int = 200,
        headers: Optional[Dict[str, str]] = None
    ) -> Response:
        """
        JSON形式の応答を作成します。
        
        Args:
            data: JSON化するデータ（辞書形式）
            status_code: HTTPステータスコード（デフォルト: 200）
            headers: 追加HTTPヘッダー（オプション）
            
        Returns:
            Flask Response オブジェクト
            
        Raises:
            TypeError: dataが辞書でない場合
            ValueError: status_codeが無効な範囲の場合
            RuntimeError: JSON変換に失敗した場合
        """
        try:
            # 入力値検証
            if not isinstance(data, dict):
                raise TypeError(f"data は辞書である必要があります。受信: {type(data).__name__}")
            
            if not (100 <= status_code <= 599):
                raise ValueError(f"status_code は 100-599 の範囲である必要があります。受信: {status_code}")
            
            self._logger.debug(f"JSON応答作成開始 - status_code: {status_code}, データキー数: {len(data)}")
            
            # JSON変換（セキュリティ配慮：ensure_ascii=Falseで非ASCII文字も適切に処理）
            json_data = json.dumps(data, ensure_ascii=False, separators=(',', ':'))
            response = Response(json_data, status=status_code, content_type='application/json; charset=utf-8')
            
            # カスタムヘッダーがある場合は追加
            if headers:
                self._validate_headers(headers)
                for key, value in headers.items():
                    response.headers[key] = value
                self._logger.debug(f"カスタムヘッダー追加: {len(headers)}件")
            
            self._logger.debug(f"JSON応答作成完了 - Content-Length: {len(json_data)}")
            return response
            
        except (TypeError, ValueError) as e:
            self._logger.error(f"JSON応答作成エラー: {e}")
            raise
        except Exception as e:
            self._logger.error(f"JSON応答作成中に予期しないエラー: {e}")
            raise RuntimeError(f"JSON応答の作成に失敗しました: {e}") from e
    
    def format_streaming_response(
        self,
        generator: Union[Generator[str, None, None], Generator[bytes, None, None]],
        content_type: str = "text/plain",
        headers: Optional[Dict[str, str]] = None
    ) -> Response:
        """
        ストリーミング応答を作成します。
        
        Args:
            generator: ストリーミングデータのジェネレーター（str または bytes）
            content_type: コンテンツタイプ（デフォルト: "text/plain"）
            headers: 追加HTTPヘッダー（オプション）
            
        Returns:
            Flask Response オブジェクト（ストリーミング）
            
        Raises:
            TypeError: generatorが適切な型でない場合
            ValueError: content_typeが無効な場合
            RuntimeError: ストリーミング応答の作成に失敗した場合
        """
        try:
            # 入力値検証（文字列は反復可能だが、適切でない）
            if isinstance(generator, str):
                raise TypeError(f"generator は文字列ではなく、適切なイテレーター/ジェネレーターである必要があります")
            
            if not hasattr(generator, '__iter__'):
                raise TypeError(f"generator はイテレーター/ジェネレーターである必要があります。受信: {type(generator).__name__}")
            
            if not content_type or not isinstance(content_type, str):
                raise ValueError(f"content_type は空でない文字列である必要があります。受信: {content_type}")
            
            # セキュリティ配慮：content_typeの基本的な検証
            if '/' not in content_type:
                self._logger.warning(f"無効なcontent_type形式の可能性: {content_type}")
            
            self._logger.debug(f"ストリーミング応答作成開始 - content_type: {content_type}")
            
            # ストリーミング応答作成
            response = Response(generator, content_type=content_type)
            
            # カスタムヘッダーがある場合は追加
            if headers:
                self._validate_headers(headers)
                for key, value in headers.items():
                    response.headers[key] = value
                self._logger.debug(f"カスタムヘッダー追加: {len(headers)}件")
            
            self._logger.debug("ストリーミング応答作成完了")
            return response
            
        except (TypeError, ValueError) as e:
            self._logger.error(f"ストリーミング応答作成エラー: {e}")
            raise
        except Exception as e:
            self._logger.error(f"ストリーミング応答作成中に予期しないエラー: {e}")
            raise RuntimeError(f"ストリーミング応答の作成に失敗しました: {e}") from e
    
    def format_error_response(
        self,
        error_message: str,
        status_code: int = 500,
        error_code: Optional[str] = None
    ) -> Response:
        """
        エラー応答を作成します。
        
        Args:
            error_message: エラーメッセージ
            status_code: HTTPステータスコード（デフォルト: 500）
            error_code: アプリケーション固有のエラーコード（オプション）
            
        Returns:
            Flask Response オブジェクト
            
        Raises:
            TypeError: error_messageが文字列でない場合
            ValueError: status_codeが無効な範囲の場合
            RuntimeError: エラー応答の作成に失敗した場合
        """
        try:
            # 入力値検証
            if not isinstance(error_message, str):
                raise TypeError(f"error_message は文字列である必要があります。受信: {type(error_message).__name__}")
            
            if not error_message.strip():
                raise ValueError("error_message は空文字列であってはいけません")
            
            if not (400 <= status_code <= 599):
                raise ValueError(f"エラー応答のstatus_codeは 400-599 の範囲である必要があります。受信: {status_code}")
            
            self._logger.debug(f"エラー応答作成開始 - status_code: {status_code}, error_code: {error_code}")
            
            # エラー情報構築（セキュリティ配慮：機密情報を含めない）
            error_data = {
                "error": error_message,
                "timestamp": self._get_current_timestamp(),
                "status": status_code
            }
            
            # エラーコードがある場合は追加
            if error_code and isinstance(error_code, str) and error_code.strip():
                error_data["error_code"] = error_code.strip()
            
            # JSON変換
            json_data = json.dumps(error_data, ensure_ascii=False, separators=(',', ':'))
            response = Response(json_data, status=status_code, content_type='application/json; charset=utf-8')
            
            self._logger.debug(f"エラー応答作成完了 - Content-Length: {len(json_data)}")
            return response
            
        except (TypeError, ValueError) as e:
            self._logger.error(f"エラー応答作成エラー: {e}")
            raise
        except Exception as e:
            self._logger.error(f"エラー応答作成中に予期しないエラー: {e}")
            # フォールバック：最小限のエラー応答
            try:
                fallback_data = json.dumps({"error": "Internal server error"})
                return Response(fallback_data, status=500, content_type='application/json')
            except Exception:
                # 最後のフォールバック：プレーンテキスト
                return Response("Internal server error", status=500, content_type='text/plain')
    
    def _validate_headers(self, headers: Dict[str, str]) -> None:
        """
        HTTPヘッダーの妥当性を検証します。
        
        Args:
            headers: 検証するヘッダー辞書
            
        Raises:
            TypeError: headersが辞書でない場合
            ValueError: ヘッダーの形式が無効な場合
        """
        if not isinstance(headers, dict):
            raise TypeError(f"headers は辞書である必要があります。受信: {type(headers).__name__}")
        
        for key, value in headers.items():
            if not isinstance(key, str) or not isinstance(value, str):
                raise ValueError(f"ヘッダーのキーと値は文字列である必要があります。受信: {key}={value}")
            
            if not key.strip():
                raise ValueError("ヘッダーのキーは空文字列であってはいけません")
            
            # セキュリティ配慮：危険なヘッダーの検出
            if key.lower() in ['set-cookie', 'authorization']:
                self._logger.warning(f"機密性の高いヘッダーが検出されました: {key}")
    
    def _get_current_timestamp(self) -> str:
        """
        現在のタイムスタンプを ISO 8601 形式で取得します。
        
        Returns:
            ISO 8601 形式のタイムスタンプ文字列
        """
        from datetime import datetime, timezone
        return datetime.now(timezone.utc).isoformat()
