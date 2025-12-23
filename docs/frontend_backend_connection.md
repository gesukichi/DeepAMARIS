# フロントエンド-バックエンド接続図

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

外部委託開発者向けの詳細な接続情報を提供しています。