# 外部委託開発者向けドキュメント

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
.venv\Scripts\activate  # Windows
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
az webapp config appsettings set --name <app-name>   --resource-group <rg-name>   --settings AZURE_OPENAI_ENDPOINT=<endpoint>
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
不明な点がございましたら、プロジェクトチームまでお気軽にお問い合わせください。