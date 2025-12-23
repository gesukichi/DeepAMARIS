# API フロー図

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
