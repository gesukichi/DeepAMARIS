# Tool Role フィルタリング修正レポート

作成日: 2025-12-23
作成者: GitHub Copilot
目的: tool role メッセージエラー解決のためのフィルタリング実装箇所まとめ

## 問題概要

**エラー内容**:
```
Error code: 400 - {'error': {'message': "Invalid parameter: messages with role 'tool' must be a response to a preceeding message with 'tool_calls'.", 'type': 'invalid_request_error', 'param': 'messages.[4].role'}}
```

**発生シナリオ**:
1. Chatモード: 正常動作
2. Web検索モード: 正常動作（tool roleメッセージ生成）
3. Chatモード: **エラー発生** (CosmosDBから読み込んだtool roleメッセージをOpenAI APIに送信)

## 実装したフィルタリング箇所

### バックエンド (Python)

#### 1. `/history/generate` エンドポイント - 入力フィルタリング
**ファイル**: web/routers/history_router.py  
**行**: 154-156  
**目的**: フロントエンドから受け取ったメッセージからtool roleを除外してOpenAI APIに送信

```python
# メッセージを準備（システムメッセージを追加、toolロールを除外）
prepared_messages = copy.deepcopy(messages)
# toolロールのメッセージを除外（OpenAI APIはtool_callsなしのtoolメッセージを受け付けない）
prepared_messages = [m for m in prepared_messages if isinstance(m, dict) and m.get("role") != "tool"]
```

#### 2. `/history/generate` エンドポイント - レスポンスフィルタリング
**ファイル**: web/routers/history_router.py  
**行**: 207-219  
**目的**: OpenAI APIレスポンスに含まれるtool roleメッセージを除外してフロントエンドに返却

```python
# 非ストリーミングレスポンス
chat_completion = await azure_openai_client.chat.completions.create(**openai_request)
response_obj = format_non_streaming_response(chat_completion, history_metadata, apim_request_id)

# IMPORTANT: Filter out tool role messages from response before sending to frontend
# Tool messages are stored in CosmosDB but should never be sent to client
if "choices" in response_obj:
    for choice in response_obj["choices"]:
        if "messages" in choice and isinstance(choice["messages"], list):
            choice["messages"] = [
                m for m in choice["messages"]
                if isinstance(m, dict) and m.get("role") != "tool"
            ]

return jsonify(response_obj)
```

#### 3. `/history/read` エンドポイント - レスポンスフィルタリング
**ファイル**: web/routers/history_router.py  
**行**: 530-537  
**目的**: CosmosDBから読み込んだ会話履歴からtool roleメッセージを除外してフロントエンドに返却

```python
# IMPORTANT: Filter out tool role messages before returning to frontend
# Tool messages are stored in CosmosDB but should never be sent to client
# OpenAI API rejects tool messages without preceding tool_calls
if "messages" in result and isinstance(result["messages"], list):
    result["messages"] = [
        m for m in result["messages"] 
        if isinstance(m, dict) and m.get("role") != "tool"
    ]

return jsonify(result), 200
```

#### 4. `/history/generate/modern-rag-web` エンドポイント - 入力フィルタリング
**ファイル**: web/routers/history_router.py  
**行**: 240付近（最新追加）  
**目的**: フロントエンドから受け取ったメッセージからtool roleを除外してModern RAGサービスに送信

```python
messages = request_json.get("messages", [])
# Filter out tool role messages before processing
messages = [m for m in messages if isinstance(m, dict) and m.get("role") != "tool"]
conversation_id = request_json.get("conversation_id")
```

### フロントエンド (TypeScript)

#### 5. `historyRead` 関数 - レスポンスフィルタリング
**ファイル**: frontend/src/api/api.ts  
**行**: 100-104  
**目的**: バックエンドから受け取った会話履歴からtool roleメッセージを除外

```typescript
payload.messages.forEach((msg: any) => {
  // IMPORTANT: Filter out tool role messages on frontend as well
  // Tool messages should never be sent back to API
  if (msg.role === 'tool') {
    return
  }
  const message: ChatMessage = {
    id: msg.id,
    role: msg.role,
    date: msg.createdAt,
    content: msg.content,
    feedback: msg.feedback ?? undefined
  }
  messages.push(message)
})
```

#### 6. `historyGenerate` 関数 - 入力フィルタリング
**ファイル**: frontend/src/api/api.ts  
**行**: 142  
**目的**: バックエンドに送信する前にtool roleメッセージを除外

```typescript
export const historyGenerate = async (
  options: ConversationRequest,
  abortSignal: AbortSignal,
  convId?: string
): Promise<Response> => {
  // IMPORTANT: Filter out tool role messages before sending to backend
  // Tool messages should never be sent to OpenAI API
  const filteredMessages = options.messages.filter(m => m.role !== 'tool')
  
  let body
  if (convId) {
    body = JSON.stringify({
      conversation_id: convId,
      messages: filteredMessages
    })
  } else {
    body = JSON.stringify({
      messages: filteredMessages
    })
  }
```

#### 7. `modernRagHistoryGenerate` 関数 - 入力フィルタリング
**ファイル**: frontend/src/api/api.ts  
**行**: 172  
**目的**: バックエンドに送信する前にtool roleメッセージを除外

```typescript
export const modernRagHistoryGenerate = async (
  options: ConversationRequest,
  abortSignal: AbortSignal,
  convId?: string
): Promise<Response> => {
  // IMPORTANT: Filter out tool role messages before sending to backend
  // Tool messages should never be sent to OpenAI API
  const filteredMessages = options.messages.filter(m => m.role !== 'tool')
  
  let body
  if (convId) {
    body = JSON.stringify({
      conversation_id: convId,
      messages: filteredMessages
    })
  } else {
    body = JSON.stringify({
      messages: filteredMessages
    })
  }
```

#### 8. `historyUpdate` 関数 - 入力フィルタリング
**ファイル**: frontend/src/api/api.ts  
**行**: 340  
**目的**: 会話更新時にtool roleメッセージをCosmosDBに保存しないようにフィルタリング

```typescript
export const historyUpdate = async (
  messages: ChatMessage[],
  convId: string
): Promise<Response> => {
  // IMPORTANT: Filter out tool role messages before sending to backend
  // Tool messages should never be stored in conversation history
  const filteredMessages = messages.filter(m => m.role !== 'tool')
  
  const response = await fetch('/history/update', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      conversation_id: convId,
      messages: filteredMessages
    })
  })
```

## 設計方針

### 採用したアプローチ: **フィルタリング方式**

**理由**:
1. **責任の分離**: ストレージ層（CosmosDB）には完全な履歴を保存し、アプリケーション層でフィルタリング
2. **拡張性**: 将来的にtool_callsを使う機能追加時に対応しやすい
3. **完全性**: citationsなどのメタデータを含む完全な会話履歴を保持

**代替案（却下）**:
- tool roleメッセージを生成しない方式
  - 問題: citationsなどのメタデータが失われる
  - 問題: 将来的な拡張性が低い

## フィルタリング実装の多層防御

```
┌─────────────────────────────────────────────────────────┐
│ フロントエンド                                           │
├─────────────────────────────────────────────────────────┤
│ 1. historyRead: レスポンス受信時にフィルタリング         │
│ 2. historyGenerate: 送信前にフィルタリング               │
│ 3. modernRagHistoryGenerate: 送信前にフィルタリング      │
│ 4. historyUpdate: 送信前にフィルタリング                 │
└─────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────┐
│ バックエンド                                             │
├─────────────────────────────────────────────────────────┤
│ 5. /history/generate: 入力フィルタリング                 │
│ 6. /history/generate: レスポンスフィルタリング           │
│ 7. /history/read: レスポンスフィルタリング               │
│ 8. /history/generate/modern-rag-web: 入力フィルタリング  │
└─────────────────────────────────────────────────────────┘
                           ↓
                     OpenAI API
```

## 問題: エラーが継続している理由

**現象**: 8箇所すべてでフィルタリングを実装したにも関わらず、エラーが継続

**可能性**:
1. ✅ デプロイ完了（確認済み）
2. ✅ ブラウザキャッシュクリア済み（ユーザー報告）
3. ❓ フロントエンドのビルド結果が正しくデプロイされていない
4. ❓ バックエンドのコードが正しくデプロイされていない
5. ❓ 既存の会話にtool roleメッセージが残っている

## 次のステップ

1. **デプロイ内容の検証**
   - deployment-package.zipの中身を確認
   - デプロイされたファイルの内容を確認

2. **実際のリクエスト/レスポンスの検証**
   - ブラウザ開発者ツールでNetwork通信を確認
   - バックエンドログでメッセージ内容を確認

3. **CosmosDBデータのクリーンアップ**
   - 既存の会話をすべて削除
   - 新しい会話で1→2→3のテストを実行

## 関連ファイル

- web/routers/history_router.py
- web/controllers/history_controller.py
- frontend/src/api/api.ts
- backend/utils.py
- backend/functions/modern_rag.py
