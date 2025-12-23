# フロントエンド開発ガイド

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

この指針に従うことで、バックエンドAPI との円滑な連携が可能です。