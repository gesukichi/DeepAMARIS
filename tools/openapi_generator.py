"""
OpenAPI仕様書生成ツール

外部委託対応のためのOpenAPI 3.0仕様書を自動生成するツール
TDD Red-Green-Refactorサイクルに従った実装
"""

import json
import inspect
import os
from typing import Dict, Any, List, Type, Optional
from pathlib import Path
import importlib.util
import sys


class OpenAPIGenerator:
    """OpenAPI 3.0仕様書を自動生成するクラス"""
    
    def __init__(self):
        """OpenAPIGeneratorの初期化"""
        self.base_spec = {
            "openapi": "3.0.3",
            "info": {
                "title": "Azure OpenAI Chat App API",
                "description": "Azure OpenAI統合チャットアプリケーションのAPI仕様書。外部委託開発者向けの包括的なAPIドキュメント。",
                "version": "1.0.0",
                "contact": {
                    "name": "API Support",
                    "email": "support@example.com"
                }
            },
            "servers": [
                {
                    "url": "http://127.0.0.1:50505",
                    "description": "ローカル開発環境"
                },
                {
                    "url": "https://your-app.azurewebsites.net",
                    "description": "Azure本番環境"
                }
            ],
            "paths": {},
            "components": {
                "schemas": {},
                "securitySchemes": {
                    "AzureAD": {
                        "type": "oauth2",
                        "description": "Azure Active Directory OAuth2認証",
                        "flows": {
                            "authorizationCode": {
                                "authorizationUrl": "https://login.microsoftonline.com/{tenant}/oauth2/v2.0/authorize",
                                "tokenUrl": "https://login.microsoftonline.com/{tenant}/oauth2/v2.0/token",
                                "scopes": {
                                    "openid": "OpenID Connect認証",
                                    "profile": "ユーザープロファイル情報",
                                    "email": "メールアドレス情報"
                                }
                            }
                        }
                    }
                }
            }
        }
    
    def generate_spec(self) -> Dict[str, Any]:
        """OpenAPI仕様書を生成する
        
        Returns:
            OpenAPI 3.0仕様書の辞書形式
        """
        spec = self.base_spec.copy()
        
        # 各Controllerからエンドポイントを抽出
        self._add_conversation_endpoints(spec)
        self._add_history_endpoints(spec)
        self._add_user_endpoints(spec)
        self._add_system_endpoints(spec)
        
        # スキーマ定義を追加
        self._add_schemas(spec)
        
        return spec
    
    def _add_conversation_endpoints(self, spec: Dict[str, Any]) -> None:
        """会話関連エンドポイントを追加"""
        spec['paths']['/conversation'] = {
            'post': {
                'summary': 'Azure OpenAI基本会話API',
                'description': 'Azure OpenAIを使用した基本的な会話処理。ユーザーの質問に対してAIが応答を生成します。外部委託開発者向けの主要なエンドポイントです。',
                'tags': ['Conversation'],
                'requestBody': {
                    'required': True,
                    'content': {
                        'application/json': {
                            'schema': {'$ref': '#/components/schemas/ConversationRequest'},
                            'example': {
                                'messages': [
                                    {'role': 'user', 'content': 'こんにちは'}
                                ],
                                'stream': False
                            }
                        }
                    }
                },
                'responses': {
                    '200': {
                        'description': '成功レスポンス',
                        'headers': {
                            'Access-Control-Allow-Origin': {
                                'description': 'CORS: オリジンアクセス制御',
                                'schema': {'type': 'string', 'example': '*'}
                            },
                            'Access-Control-Allow-Methods': {
                                'description': 'CORS: 許可されるHTTPメソッド',
                                'schema': {'type': 'string', 'example': 'GET, POST, PUT, DELETE, OPTIONS'}
                            },
                            'Access-Control-Allow-Headers': {
                                'description': 'CORS: 許可されるリクエストヘッダー',
                                'schema': {'type': 'string', 'example': 'Content-Type, Authorization'}
                            }
                        },
                        'content': {
                            'application/json': {
                                'schema': {'$ref': '#/components/schemas/ConversationResponse'}
                            }
                        }
                    },
                    '400': {
                        'description': 'クライアントエラー: 不正なリクエスト形式、必須パラメータの欠如、無効なJSON形式、パラメータ値の範囲外エラーなどが発生した場合に返されます。',
                        'content': {
                            'application/json': {
                                'schema': {'$ref': '#/components/schemas/ErrorResponse'}
                            }
                        }
                    },
                    '500': {
                        'description': 'サーバー内部エラー: Azure OpenAIサービスの一時的な障害、ネットワーク接続エラー、予期しないシステム障害などが発生した場合に返されます。',
                        'content': {
                            'application/json': {
                                'schema': {'$ref': '#/components/schemas/ErrorResponse'}
                            }
                        }
                    }
                },
                'security': [{'AzureAD': []}]
            }
        }
        
        spec['paths']['/modern_rag_web_conversation'] = {
            'post': {
                'summary': 'Modern RAG会話API',
                'description': 'Retrieval-Augmented Generation（RAG）を使用した高度な会話処理。文書検索と組み合わせた回答生成。',
                'tags': ['Conversation'],
                'requestBody': {
                    'required': True,
                    'content': {
                        'application/json': {
                            'schema': {'$ref': '#/components/schemas/ConversationRequest'}
                        }
                    }
                },
                'responses': {
                    '200': {
                        'description': '成功レスポンス',
                        'content': {
                            'application/json': {
                                'schema': {'$ref': '#/components/schemas/ConversationResponse'}
                            }
                        }
                    },
                    '400': {
                        'description': 'クライアントエラー: 不正なリクエスト形式、必須パラメータの欠如、無効なJSON形式、パラメータ値の範囲外エラーなどが発生した場合に返されます。',
                        'content': {
                            'application/json': {
                                'schema': {'$ref': '#/components/schemas/ErrorResponse'}
                            }
                        }
                    },
                    '500': {
                        'description': 'サーバー内部エラー: Azure OpenAIサービスの一時的な障害、ネットワーク接続エラー、予期しないシステム障害などが発生した場合に返されます。',
                        'content': {
                            'application/json': {
                                'schema': {'$ref': '#/components/schemas/ErrorResponse'}
                            }
                        }
                    }
                },
                'security': [{'AzureAD': []}]
            }
        }
    
    def _add_history_endpoints(self, spec: Dict[str, Any]) -> None:
        """履歴関連エンドポイントを追加"""
        history_endpoints = {
            '/history/generate': {
                'post': {
                    'summary': '新規会話履歴生成API',
                    'description': '新しい会話を開始し、履歴として保存します。ユーザーの会話データをAzure Cosmos DBに永続化し、後で参照可能にします。',
                    'tags': ['History'],
                    'requestBody': {
                        'required': True,
                        'content': {
                            'application/json': {
                                'schema': {'$ref': '#/components/schemas/HistoryCreateRequest'}
                            }
                        }
                    },
                    'responses': {
                        '201': {'description': '会話作成成功'},
                        '400': {'description': 'クライアントエラー: 不正なリクエスト形式、必須パラメータの欠如、無効なJSON形式、パラメータ値の範囲外エラーなどが発生した場合に返されます。'},
                        '500': {'description': 'サーバー内部エラー: Azure OpenAIサービスの一時的な障害、ネットワーク接続エラー、予期しないシステム障害などが発生した場合に返されます。'}
                    }
                }
            },
            '/history/generate/modern-rag-web': {
                'post': {
                    'summary': 'Modern RAG会話履歴生成API',
                    'description': 'RAG（Retrieval-Augmented Generation）を使用した新しい会話を開始し、履歴として保存します。文書検索機能と組み合わせた高度な会話処理。',
                    'tags': ['History']
                }
            },
            '/history/generate/deep-research': {
                'post': {
                    'summary': 'DeepResearch会話履歴生成API',
                    'description': 'DeepResearch機能を用いて調査ベースの回答を生成し、会話履歴として保存します。外部情報を深掘りする拡張モードです。',
                    'tags': ['History']
                }
            },
            '/history/update': {
                'post': {
                    'summary': '会話履歴更新API',
                    'description': '既存の会話履歴を更新します。新しいメッセージの追加や既存メッセージの編集が可能です。外部委託開発者が頻繁に使用するエンドポイントです。',
                    'tags': ['History']
                }
            },
            '/history/message_feedback': {
                'post': {
                    'summary': 'メッセージフィードバック記録API',
                    'description': 'AIメッセージに対するフィードバック（いいね・よくない）を記録します。ユーザーエクスペリエンス向上のための重要な機能です。',
                    'tags': ['History']
                }
            },
            '/history/delete': {
                'delete': {
                    'summary': '個別会話削除API',
                    'description': '指定された会話を削除します。プライバシー保護とデータ管理の重要な機能。削除操作は復元不可能です。',
                    'tags': ['History']
                }
            },
            '/history/list': {
                'get': {
                    'summary': '会話履歴一覧取得API',
                    'description': 'ユーザーの会話履歴一覧を取得します。ページネーション、フィルタリング、ソート機能をサポートしています。',
                    'tags': ['History']
                }
            },
            '/history/read': {
                'post': {
                    'summary': '会話詳細取得API',
                    'description': '指定された会話の詳細情報を取得します。全メッセージ、メタデータ、タイムスタンプなどの完全な会話データを返します。',
                    'tags': ['History']
                }
            },
            '/history/rename': {
                'post': {
                    'summary': '会話タイトル変更API',
                    'description': '会話のタイトルを変更します。ユーザーが会話を整理・管理するための重要な機能です。',
                    'tags': ['History']
                }
            },
            '/history/delete_all': {
                'delete': {
                    'summary': '全会話削除API',
                    'description': 'ユーザーの全ての会話履歴を削除します。データプライバシー要件に対応した一括削除機能。操作は復元不可能です。',
                    'tags': ['History']
                }
            },
            '/history/clear': {
                'post': {
                    'summary': 'メッセージクリアAPI',
                    'description': '会話からメッセージをクリアします。会話構造は維持しつつ、メッセージ内容のみを削除する機能です。',
                    'tags': ['History']
                }
            }
        }
        
        spec['paths'].update(history_endpoints)
    
    def _add_user_endpoints(self, spec: Dict[str, Any]) -> None:
        """ユーザー関連エンドポイントを追加"""
        user_endpoints = {
            '/.auth/me': {
                'get': {
                    'summary': 'Azure App Service認証情報取得API',
                    'description': 'Azure App Service認証互換のユーザー情報を取得します。認証されたユーザーの詳細情報、ロール、権限情報を返します。',
                    'tags': ['User']
                }
            },
            '/user/info': {
                'get': {
                    'summary': 'ユーザー詳細情報取得API',
                    'description': 'ユーザーの詳細情報を取得します。プロファイル情報、設定、権限レベルなどの包括的なユーザーデータを提供します。',
                    'tags': ['User']
                }
            },
            '/user/status': {
                'get': {
                    'summary': 'ユーザー認証状態確認API',
                    'description': 'ユーザーの認証状態を確認します。セッション有効性、トークン状態、権限の現在の状況を確認できます。',
                    'tags': ['User']
                }
            },
            '/user/dev-mode': {
                'get': {
                    'summary': '開発モード判定API',
                    'description': 'アプリケーションが開発モードかどうかを確認します。デバッグ機能、テスト機能の有効/無効を判断するために使用します。',
                    'tags': ['User']
                }
            },
            '/user/validate': {
                'post': {
                    'summary': 'アクセス権限検証API',
                    'description': 'ユーザーのアクセス権限を検証します。特定のリソースやアクションに対する権限を確認し、認可判定を行います。',
                    'tags': ['User']
                }
            }
        }
        
        spec['paths'].update(user_endpoints)
    
    def _add_system_endpoints(self, spec: Dict[str, Any]) -> None:
        """システム関連エンドポイントを追加"""
        system_endpoints = {
            '/frontend_settings': {
                'get': {
                    'summary': 'フロントエンド設定情報取得API',
                    'description': 'フロントエンドアプリケーションの設定情報を取得します。Azure Key Vault統合済みで、安全な設定管理を提供します。API キー、エンドポイント情報、UI設定を含みます。',
                    'tags': ['System']
                }
            },
            '/healthz': {
                'get': {
                    'summary': 'Kubernetes probe用軽量ヘルスチェックAPI',
                    'description': 'Kubernetes probeなどの軽量ヘルスチェック。最小限の依存関係でアプリケーションの生存確認を行います。高速レスポンスと低リソース消費が特徴です。',
                    'tags': ['System']
                }
            },
            '/health': {
                'get': {
                    'summary': 'Azure App Service用詳細ヘルスチェックAPI',
                    'description': 'Azure App Service用の詳細ヘルスチェック。各サービス（OpenAI、CosmosDB、Key Vault等）の詳細状態を確認し、包括的な健全性レポートを提供します。',
                    'tags': ['System']
                }
            }
        }
        
        spec['paths'].update(system_endpoints)
    
    def _add_schemas(self, spec: Dict[str, Any]) -> None:
        """スキーマ定義を追加"""
        schemas = {
            'ConversationRequest': {
                'type': 'object',
                'required': ['messages'],
                'properties': {
                    'messages': {
                        'type': 'array',
                        'items': {
                            'type': 'object',
                            'properties': {
                                'role': {'type': 'string', 'enum': ['user', 'assistant', 'system']},
                                'content': {'type': 'string'}
                            }
                        }
                    },
                    'stream': {
                        'type': 'boolean',
                        'default': False,
                        'description': 'ストリーミングレスポンスの有効/無効'
                    }
                }
            },
            'ConversationResponse': {
                'type': 'object',
                'properties': {
                    'id': {'type': 'string'},
                    'object': {'type': 'string'},
                    'choices': {
                        'type': 'array',
                        'items': {
                            'type': 'object',
                            'properties': {
                                'message': {
                                    'type': 'object',
                                    'properties': {
                                        'role': {'type': 'string'},
                                        'content': {'type': 'string'}
                                    }
                                }
                            }
                        }
                    }
                }
            },
            'HistoryCreateRequest': {
                'type': 'object',
                'required': ['messages'],
                'properties': {
                    'messages': {
                        'type': 'array',
                        'items': {'$ref': '#/components/schemas/Message'}
                    }
                }
            },
            'HistoryUpdateRequest': {
                'type': 'object',
                'properties': {
                    'conversation_id': {'type': 'string'},
                    'messages': {
                        'type': 'array',
                        'items': {'$ref': '#/components/schemas/Message'}
                    }
                }
            },
            'Message': {
                'type': 'object',
                'properties': {
                    'role': {'type': 'string', 'enum': ['user', 'assistant', 'system']},
                    'content': {'type': 'string'},
                    'timestamp': {'type': 'string', 'format': 'date-time'}
                }
            },
            'UserAuthResponse': {
                'type': 'object',
                'properties': {
                    'authenticated': {'type': 'boolean'},
                    'user_id': {'type': 'string'},
                    'user_name': {'type': 'string'},
                    'email': {'type': 'string'},
                    'roles': {
                        'type': 'array',
                        'items': {'type': 'string'}
                    }
                }
            },
            'SystemHealthResponse': {
                'type': 'object',
                'properties': {
                    'status': {'type': 'string', 'enum': ['healthy', 'unhealthy', 'unknown']},
                    'timestamp': {'type': 'string', 'format': 'date-time'},
                    'services': {
                        'type': 'object',
                        'additionalProperties': {
                            'type': 'object',
                            'properties': {
                                'status': {'type': 'string'},
                                'response_time': {'type': 'number'},
                                'error': {'type': 'string'}
                            }
                        }
                    }
                }
            },
            'ErrorResponse': {
                'type': 'object',
                'properties': {
                    'error': {
                        'type': 'object',
                        'properties': {
                            'message': {'type': 'string'},
                            'code': {'type': 'string'},
                            'details': {'type': 'string'}
                        }
                    }
                }
            }
        }
        
        spec['components']['schemas'].update(schemas)
    
    def save_spec_to_file(self, spec: Dict[str, Any], file_path: str) -> None:
        """OpenAPI仕様書をJSONファイルに保存
        
        Args:
            spec: OpenAPI仕様書
            file_path: 保存先ファイルパス
        """
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(spec, f, indent=2, ensure_ascii=False)
    
    def generate_html_documentation(self, output_path: str) -> None:
        """HTML形式のAPI ドキュメントを生成
        
        Args:
            output_path: 出力先HTMLファイルパス
        """
        spec = self.generate_spec()
        
        # Swagger UIベースのHTMLドキュメントを生成
        html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <title>Azure OpenAI Chat App API Documentation</title>
    <link rel="stylesheet" type="text/css" href="https://unpkg.com/swagger-ui-dist@4.15.5/swagger-ui.css" />
    <style>
        html {{
            box-sizing: border-box;
            overflow: -moz-scrollbars-vertical;
            overflow-y: scroll;
        }}
        *, *:before, *:after {{
            box-sizing: inherit;
        }}
        body {{
            margin:0;
            background: #fafafa;
        }}
    </style>
</head>
<body>
    <div id="swagger-ui"></div>
    <script src="https://unpkg.com/swagger-ui-dist@4.15.5/swagger-ui-bundle.js"></script>
    <script src="https://unpkg.com/swagger-ui-dist@4.15.5/swagger-ui-standalone-preset.js"></script>
    <script>
        window.onload = function() {{
            const ui = SwaggerUIBundle({{
                spec: {json.dumps(spec, indent=2, ensure_ascii=False)},
                dom_id: '#swagger-ui',
                deepLinking: true,
                presets: [
                    SwaggerUIBundle.presets.apis,
                    SwaggerUIStandalonePreset
                ],
                plugins: [
                    SwaggerUIBundle.plugins.DownloadUrl
                ],
                layout: "StandaloneLayout"
            }});
        }};
    </script>
</body>
</html>
"""
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
    
    def discover_controllers(self) -> List[Type]:
        """プロジェクト内のController クラスを自動検出
        
        Returns:
            発見されたControllerクラスのリスト
        """
        controllers = []
        
        # 簡易実装: 既知のControllerクラスを返す
        try:
            from web.controllers.conversation_controller import ConversationController
            controllers.append(ConversationController)
        except ImportError:
            pass
            
        try:
            from web.controllers.history_controller import HistoryController
            controllers.append(HistoryController)
        except ImportError:
            pass
            
        try:
            from web.controllers.user_controller import UserController
            controllers.append(UserController)
        except ImportError:
            pass
            
        try:
            from backend.application.system.controllers.system_controller import SystemController
            controllers.append(SystemController)
        except ImportError:
            pass
        
        return controllers
    
    def extract_endpoints_from_controller(self, controller_class: Type) -> List[Dict[str, Any]]:
        """Controllerクラスからエンドポイント情報を抽出
        
        Args:
            controller_class: Controllerクラス
            
        Returns:
            エンドポイント情報のリスト
        """
        endpoints = []
        
        # 簡易実装: Controller名に基づく推定
        class_name = controller_class.__name__
        
        if 'Conversation' in class_name:
            endpoints.extend([
                {'path': '/conversation', 'method': 'POST'},
                {'path': '/modern_rag_web_conversation', 'method': 'POST'}
            ])
        elif 'History' in class_name:
            endpoints.extend([
                {'path': '/history/generate', 'method': 'POST'},
                {'path': '/history/list', 'method': 'GET'}
            ])
        elif 'User' in class_name:
            endpoints.extend([
                {'path': '/.auth/me', 'method': 'GET'},
                {'path': '/user/info', 'method': 'GET'}
            ])
        elif 'System' in class_name:
            endpoints.extend([
                {'path': '/frontend_settings', 'method': 'GET'},
                {'path': '/healthz', 'method': 'GET'},
                {'path': '/health', 'method': 'GET'}
            ])
        
        return endpoints


if __name__ == "__main__":
    """OpenAPI仕様書生成の実行"""
    generator = OpenAPIGenerator()
    
    # 仕様書生成
    spec = generator.generate_spec()
    
    # ファイル保存
    output_dir = Path("doc") / "api"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    json_path = output_dir / "openapi.json"
    html_path = output_dir / "api_documentation.html"
    
    generator.save_spec_to_file(spec, str(json_path))
    generator.generate_html_documentation(str(html_path))
    
    print(f"✅ OpenAPI仕様書を生成しました:")
    print(f"  JSON: {json_path}")
    print(f"  HTML: {html_path}")
