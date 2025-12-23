"""
Task 14: アーキテクチャ図・デモ環境作成
ArchitectureGenerator - システム構成図自動生成

外部委託開発者向けのシステム構造可視化ツール
TDD methodology (t-wada方式) GREEN phase implementation
"""

import json
import os
from typing import Dict, Any, List
from pathlib import Path


class ArchitectureGenerator:
    """システムアーキテクチャ図自動生成クラス
    
    外部委託開発者向けのシステム構造可視化とドキュメント生成
    """
    
    def __init__(self):
        """ArchitectureGenerator初期化"""
        self.controllers = [
            'ConversationController',
            'HistoryController', 
            'UserController',
            'SystemController'
        ]
        
        self.services = [
            'ConversationService',
            'HistoryManager',
            'UserService',
            'AuthService'
        ]
        
        self.azure_services = [
            'Azure OpenAI',
            'Azure App Service',
            'Azure Key Vault',
            'Cosmos DB'
        ]
    
    def generate_system_diagram(self) -> str:
        """システム構成図を生成
        
        Returns:
            str: システム構成図のマークダウン形式
        """
        diagram = """# システム構成図

## コントローラー層
"""
        
        for controller in self.controllers:
            diagram += f"- {controller}\n"
        
        diagram += "\n## サービス層\n"
        for service in self.services:
            diagram += f"- {service}\n"
        
        diagram += "\n## Azureサービス\n"
        for azure_service in self.azure_services:
            diagram += f"- {azure_service}\n"
        
        return diagram
    
    def generate_api_flow_diagram(self) -> str:
        """APIフロー図を生成
        
        Returns:
            str: APIフロー図のマークダウン形式
        """
        flow_diagram = """# API フロー図

## リクエスト-レスポンス フロー

```
Frontend → Router → Controller → Service → Azure OpenAI
                  ↓
Frontend ← Router ← Controller ← Service ← Azure OpenAI
```

## フロー詳細
1. Frontend: フロントエンドアプリケーション
2. Router: Quart ルーター
3. Controller: ビジネスロジック制御
4. Service: データ処理・外部サービス連携
5. Azure OpenAI: AI推論エンジン
"""
        return flow_diagram
    
    def generate_frontend_backend_diagram(self) -> str:
        """フロントエンド-バックエンド接続図を生成
        
        Returns:
            str: フロントエンド-バックエンド接続図のマークダウン形式
        """
        diagram = """# フロントエンド-バックエンド接続図

## API エンドポイント一覧

### 会話API
- POST /conversation - 基本会話
- POST /modern_rag_web_conversation - RAG会話

### 履歴API  
- GET /history/list - 履歴一覧取得
- POST /history/generate - 新規会話作成
- POST /history/update - 会話更新

### ユーザーAPI
- GET /.auth/me - ユーザー情報取得
- GET /user/info - ユーザー詳細情報

### システムAPI
- GET /healthz - ヘルスチェック
- GET /frontend_settings - フロントエンド設定

## リクエスト/レスポンス形式
- Content-Type: application/json
- CORS対応済み
- Azure AD認証必須

## エラーハンドリング
- 400: クライアントエラー
- 401: 認証エラー  
- 500: サーバーエラー

外部委託開発者向けの詳細な接続情報を提供しています。"""
        return diagram
    
    def save_system_diagram(self, filename: str) -> str:
        """システム図をファイルに保存
        
        Args:
            filename: 保存先ファイル名
            
        Returns:
            str: 保存されたファイルパス
        """
        diagram = self.generate_system_diagram()
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(diagram)
        return filename
    
    def save_api_flow_diagram(self, filename: str) -> str:
        """APIフロー図をファイルに保存
        
        Args:
            filename: 保存先ファイル名
            
        Returns:
            str: 保存されたファイルパス
        """
        diagram = self.generate_api_flow_diagram()
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(diagram)
        return filename
    
    def save_frontend_backend_diagram(self, filename: str) -> str:
        """フロントエンド-バックエンド図をファイルに保存
        
        Args:
            filename: 保存先ファイル名
            
        Returns:
            str: 保存されたファイルパス
        """
        diagram = self.generate_frontend_backend_diagram()
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(diagram)
        return filename
    
    def generate_contractor_documentation(self) -> str:
        """外部委託開発者向けの包括的ドキュメントを生成
        
        Returns:
            str: 外部委託開発者向けドキュメント
        """
        docs = """# 外部委託開発者向けドキュメント

## システム概要
Azure OpenAI統合チャットアプリケーションの開発・保守を行うための包括的なガイドです。
本システムは、Azure OpenAIサービスを活用した高度な会話AI機能を提供し、
企業向けのセキュアなチャットボットソリューションを実現します。

### システムアーキテクチャ
- **フロントエンド**: React/Vue.js/Angular対応のSPAアプリケーション
- **バックエンド**: Python Quart Webフレームワーク
- **AI エンジン**: Azure OpenAI Service (GPT-4, GPT-3.5-turbo)
- **データベース**: Azure Cosmos DB (NoSQL)
- **認証**: Azure App Service Authentication (Azure AD統合)
- **機密管理**: Azure Key Vault
- **ホスティング**: Azure App Service

## API仕様
RESTful APIを使用したフロントエンド-バックエンド通信

### エンドポイント一覧

#### 会話API
- **POST /conversation**: 基本的なAI会話処理
  - **用途**: ユーザーとAIの基本的な対話
  - **リクエスト**: JSON形式のメッセージ配列
  - **レスポンス**: AI生成の応答メッセージ
  - **例**: `{"messages": [{"role": "user", "content": "こんにちは"}]}`

- **POST /modern_rag_web_conversation**: RAG機能付き高度会話
  - **用途**: 文書検索機能付きのAI会話
  - **特徴**: 企業内文書を参照した回答生成
  - **セキュリティ**: Azure AD認証必須

#### 履歴API
- **GET /history/list**: 会話履歴一覧取得
- **POST /history/generate**: 新規会話セッション作成
- **POST /history/update**: 既存会話の更新
- **DELETE /history/delete**: 特定会話の削除
- **POST /history/read**: 会話内容の詳細取得
- **POST /history/rename**: 会話タイトルの変更
- **DELETE /history/delete_all**: 全会話履歴の削除

#### ユーザーAPI
- **GET /.auth/me**: 現在ログイン中のユーザー情報取得
- **GET /user/info**: ユーザー詳細情報とプロファイル
- **GET /user/status**: ユーザーの利用状況・権限確認
- **POST /user/validate**: ユーザー権限の検証

#### システムAPI
- **GET /healthz**: アプリケーションヘルスチェック
- **GET /frontend_settings**: フロントエンド設定情報取得
- **GET /health**: 詳細システム状態確認

### 認証とセキュリティ
#### Azure App Service認証
- **Azure AD統合**: 企業のActive Directoryと連携
- **シングルサインオン**: Office 365アカウントでのログイン
- **多要素認証**: MFA対応
- **/.auth/me エンドポイント**: ユーザー情報の取得

#### セキュリティヘッダー
```
Authorization: Bearer <token>
Content-Type: application/json
X-Requested-With: XMLHttpRequest
```

### エラーハンドリング
標準HTTPステータスコードによる一貫したエラーレスポンス

#### エラーコード詳細
- **400 Bad Request**: リクエスト形式エラー、必須パラメータ欠如
- **401 Unauthorized**: 認証エラー、トークン不正・期限切れ
- **403 Forbidden**: 権限不足、アクセス権限なし
- **404 Not Found**: リソース不存在、無効なエンドポイント
- **429 Too Many Requests**: レート制限超過
- **500 Internal Server Error**: サーバー内部エラー、Azure接続障害
- **502 Bad Gateway**: Azure OpenAI接続エラー
- **503 Service Unavailable**: サービス一時停止

#### エラーレスポンス形式
```json
{
  "error": {
    "code": "INVALID_REQUEST",
    "message": "リクエストパラメータが不正です",
    "details": "messages フィールドが必須です"
  }
}
```

## 開発環境構築

### 必要な環境
1. **Python 3.11以上**: 推奨は3.11.x
2. **Quart Webフレームワーク**: 非同期対応
3. **Azure CLI**: Azure サービス管理用
4. **Visual Studio Code**: 推奨開発環境
5. **Git**: バージョン管理

### Azure サービス設定
1. **Azure OpenAI Service**: GPT-4/3.5デプロイ
2. **Cosmos DB**: NoSQLデータベース
3. **Azure Key Vault**: 機密情報管理
4. **App Service**: Webアプリホスティング
5. **Application Insights**: 監視・ログ

### ローカル開発手順
```bash
# 1. リポジトリクローン
git clone <repository-url>
cd app-aoai-chatGPT_WebSearchDeploy_kai

# 2. Python仮想環境作成
python -m venv .venv
.venv\\Scripts\\activate  # Windows
source .venv/bin/activate  # Linux/Mac

# 3. 依存関係インストール
pip install -r requirements.txt

# 4. 環境変数設定
cp .env.template .env
# .envファイルを編集してAzure接続情報を設定

# 5. アプリケーション起動
python app.py
```

## フロントエンド開発ガイド

### 推奨技術スタック
- **Framework**: React 18+, Vue 3+, Angular 15+
- **Language**: TypeScript (強く推奨)
- **HTTP Client**: Axios, Fetch API
- **State Management**: Redux Toolkit, Vuex, NgRx
- **UI Library**: Material-UI, Ant Design, Vuetify, Chakra UI

### 認証実装
#### Azure AD認証フロー
```javascript
// 1. ユーザー情報取得
const getUserInfo = async () => {
  try {
    const response = await fetch('/.auth/me');
    const userInfo = await response.json();
    return userInfo;
  } catch (error) {
    console.error('認証エラー:', error);
    // ログインページにリダイレクト
    window.location.href = '/.auth/login/aad';
  }
};

// 2. API呼び出し時のヘッダー設定
const callAPI = async (endpoint, data) => {
  const response = await fetch(endpoint, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-Requested-With': 'XMLHttpRequest'
    },
    body: JSON.stringify(data)
  });
  
  if (!response.ok) {
    throw new Error(`HTTP ${response.status}: ${response.statusText}`);
  }
  
  return response.json();
};
```

### CORS対応
全APIエンドポイントでCORS設定済み
- **Origin**: 開発環境・本番環境対応
- **Methods**: GET, POST, PUT, DELETE, OPTIONS
- **Headers**: Content-Type, Authorization, X-Requested-With
- **Credentials**: include (認証Cookie対応)

### API使用例

#### 会話API呼び出し
```javascript
const sendMessage = async (message) => {
  try {
    const response = await fetch('/conversation', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        messages: [
          { role: 'user', content: message }
        ],
        stream: false
      })
    });
    
    const result = await response.json();
    return result.choices[0].message.content;
  } catch (error) {
    console.error('会話API エラー:', error);
    throw error;
  }
};
```

#### 履歴管理
```javascript
// 履歴一覧取得
const getConversations = async () => {
  const response = await fetch('/history/list');
  return response.json();
};

// 新規会話作成
const createConversation = async (title) => {
  const response = await fetch('/history/generate', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ title })
  });
  return response.json();
};
```

## デバッグとトラブルシューティング

### 一般的な問題と解決策

#### 1. 認証エラー
- **症状**: 401 Unauthorized エラー
- **原因**: Azure AD認証の設定不備
- **解決**: /.auth/me でユーザー状態確認

#### 2. CORS エラー
- **症状**: ブラウザコンソールでCORSエラー
- **原因**: フロントエンドとバックエンドのドメイン不一致
- **解決**: 開発時はプロキシ設定またはCORS設定確認

#### 3. API応答遅延
- **症状**: レスポンス時間が長い
- **原因**: Azure OpenAIのレート制限
- **解決**: 非同期処理とストリーミング対応

### ログ確認方法
```bash
# アプリケーションログ
tail -f logs/app.log

# Azure App Service ログ
az webapp log tail --name <app-name> --resource-group <rg-name>
```

## 本番デプロイメント

### Azure App Service デプロイ
```bash
# 1. Azure CLI ログイン
az login

# 2. リソースグループ作成
az group create --name <rg-name> --location japaneast

# 3. App Service デプロイ
az webapp up --sku B1 --name <app-name>
```

### 環境変数設定
```bash
az webapp config appsettings set --name <app-name> \
  --resource-group <rg-name> \
  --settings AZURE_OPENAI_ENDPOINT=<endpoint>
```

## パフォーマンス最適化

### バックエンド最適化
- 非同期処理の活用 (async/await)
- コネクションプールの最適化
- キャッシュ機能の実装
- レート制限の実装

### フロントエンド最適化
- コンポーネントの遅延読み込み
- 状態管理の最適化
- APIコールの最適化（debounce, throttle）
- バンドルサイズの最適化

## 品質保証

### テスト戦略
- **ユニットテスト**: pytest による関数レベルテスト
- **統合テスト**: API エンドポイントテスト
- **E2Eテスト**: Playwright による画面操作テスト
- **負荷テスト**: Azure Load Testing

### コード品質
- **リンター**: flake8, black, mypy
- **セキュリティ**: bandit による脆弱性チェック
- **依存関係**: safety による脆弱な依存関係チェック

## サポートとドキュメント

### 追加リソース
- **OpenAPI仕様書**: `/openapi_spec.json`
- **Swagger UI**: `/openapi_docs.html`
- **API デモ**: cURL サンプル集
- **Postman コレクション**: API テスト用

### 技術サポート
- **Issues**: GitHub Issues でのバグ報告
- **Discussion**: 技術相談・質問
- **Wiki**: 詳細な技術ドキュメント

このドキュメントは外部委託開発者がシステムを理解し、効率的に開発を進めるための包括的なガイドです。
不明な点がございましたら、プロジェクトチームまでお気軽にお問い合わせください。"""
        return docs
    
    def generate_frontend_development_guide(self) -> str:
        """フロントエンド開発ガイドを生成
        
        Returns:
            str: フロントエンド開発ガイド
        """
        guide = """# フロントエンド開発ガイド

## 概要
Azure OpenAI統合チャットアプリケーションのフロントエンド開発指針

## 推奨技術スタック
- **Framework**: React 18+ / Vue 3+ / Angular 15+
- **Language**: TypeScript (強く推奨)
- **HTTP Client**: Axios / Fetch API
- **State Management**: Redux / Vuex / NgRx
- **UI Library**: Material-UI / Ant Design / Vuetify

## 認証 (Authentication)
### Azure AD統合
```javascript
// ユーザー情報取得例
const userInfo = await fetch('/.auth/me')
  .then(response => response.json());
```

### CORS対応
全APIエンドポイントでCORS設定済み
- Origin: * (開発環境)
- Methods: GET, POST, PUT, DELETE, OPTIONS
- Headers: Content-Type, Authorization

## API通信例
### fetch APIを使用した例
```javascript
// 会話API呼び出し
const response = await fetch('/conversation', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    messages: [
      { role: 'user', content: 'こんにちは' }
    ]
  })
});
```

### axios使用例  
```javascript
// 履歴一覧取得
const histories = await axios.get('/history/list');
```

## エラーハンドリング
統一されたエラーレスポンス形式
```javascript
try {
  const response = await fetch('/conversation', options);
  if (!response.ok) {
    throw new Error(`HTTP ${response.status}`);
  }
} catch (error) {
  console.error('API Error:', error);
}
```

## 開発環境構築
1. Node.js 18+インストール
2. プロジェクト作成 (create-react-app / Vue CLI / Angular CLI)
3. API接続設定 (http://localhost:50505)
4. CORS確認

この指針に従うことで、バックエンドAPI との円滑な連携が可能です。"""
        return guide
