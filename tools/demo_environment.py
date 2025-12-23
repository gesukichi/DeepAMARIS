"""
Task 14: アーキテクチャ図・デモ環境作成
DemoEnvironment - API動作確認デモ環境

外部委託開発者向けのAPI動作確認とサンプル生成ツール
TDD methodology (t-wada方式) GREEN phase implementation
"""

import json
import os
from typing import Dict, Any, List
from pathlib import Path


class DemoEnvironment:
    """API動作確認デモ環境クラス
    
    外部委託開発者向けのAPI使用例とデモ環境構築
    """
    
    def __init__(self):
        """DemoEnvironment初期化"""
        self.base_url = "http://localhost:50505"
        self.endpoints = [
            '/conversation',
            '/modern_rag_web_conversation', 
            '/history/list',
            '/history/generate',
            '/user/info',
            '/.auth/me',
            '/healthz',
            '/frontend_settings'
        ]
    
    def create_api_demo(self) -> str:
        """API動作確認デモを作成
        
        Returns:
            str: APIデモのマークダウン形式
        """
        demo = """# API動作確認デモ

## 概要
Azure OpenAI統合チャットアプリケーションのAPIを実際に動作確認するためのデモ環境です。
外部委託開発者がシステムの動作を理解し、フロントエンド開発を効率的に進めるための実践的なガイドです。

## デモ環境構築

### 前提条件
- Python 3.11以上がインストールされていること
- Azure OpenAI Serviceへのアクセス権があること
- 必要な環境変数が設定されていること

### サーバー起動手順
```bash
# 1. 依存関係インストール
pip install -r requirements.txt

# 2. 環境変数設定
cp .env.template .env
# .envファイルを編集してAzure設定を追加

# 3. サーバー起動
python app.py

# 4. ブラウザで確認
# http://localhost:50505 にアクセス
```

## 主要エンドポイント詳細

### 会話API
"""
        
        for endpoint in self.endpoints:
            demo += f"- **{endpoint}**: "
            if 'conversation' in endpoint:
                demo += "AI会話処理エンドポイント\n"
            elif 'history' in endpoint:
                demo += "会話履歴管理エンドポイント\n"
            elif 'user' in endpoint or 'auth' in endpoint:
                demo += "ユーザー認証・情報管理エンドポイント\n"
            elif 'health' in endpoint or 'frontend' in endpoint:
                demo += "システム状態・設定管理エンドポイント\n"
            else:
                demo += "システム管理エンドポイント\n"
        
        demo += """
## 実践的API使用例

### 1. システムヘルスチェック
```bash
curl -X GET http://localhost:50505/healthz
```
**期待される結果**: システム状態のJSONレスポンス

### 2. フロントエンド設定取得
```bash
curl -X GET http://localhost:50505/frontend_settings
```
**期待される結果**: フロントエンド用設定情報

### 3. ユーザー認証状態確認
```bash
curl -X GET http://localhost:50505/.auth/me
```
**期待される結果**: ユーザー認証情報（Azure AD連携）

### 4. 基本的なAI会話
```bash
curl -X POST http://localhost:50505/conversation \\
  -H "Content-Type: application/json" \\
  -d '{
    "messages": [
      {"role": "user", "content": "こんにちは、Azure OpenAIについて教えてください"}
    ],
    "stream": false,
    "temperature": 0.7,
    "max_tokens": 1000
  }'
```
**期待される結果**: AI生成の応答メッセージ

### 5. RAG機能付き高度会話
```bash
curl -X POST http://localhost:50505/modern_rag_web_conversation \\
  -H "Content-Type: application/json" \\
  -d '{
    "messages": [
      {"role": "user", "content": "会社の最新プロダクトについて教えてください"}
    ],
    "stream": false
  }'
```
**期待される結果**: 企業内文書を参照したAI応答

### 6. 会話履歴一覧取得
```bash
curl -X GET http://localhost:50505/history/list \\
  -H "Content-Type: application/json"
```
**期待される結果**: ユーザーの会話履歴リスト

### 7. 新規会話セッション作成
```bash
curl -X POST http://localhost:50505/history/generate \\
  -H "Content-Type: application/json" \\
  -d '{
    "title": "新しいプロジェクトについての相談",
    "messages": [
      {"role": "user", "content": "新しいプロジェクトを開始したいのですが"}
    ]
  }'
```
**期待される結果**: 新規会話セッションID

## JavaScript/TypeScript サンプル

### React での実装例
```javascript
import React, { useState } from 'react';

const ChatComponent = () => {
  const [message, setMessage] = useState('');
  const [response, setResponse] = useState('');
  const [loading, setLoading] = useState(false);

  const sendMessage = async () => {
    setLoading(true);
    try {
      const response = await fetch('/conversation', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          messages: [
            { role: 'user', content: message }
          ],
          stream: false
        })
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }

      const data = await response.json();
      setResponse(data.choices[0].message.content);
    } catch (error) {
      console.error('API Error:', error);
      setResponse('エラーが発生しました: ' + error.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div>
      <input 
        value={message} 
        onChange={(e) => setMessage(e.target.value)}
        placeholder="メッセージを入力してください"
      />
      <button onClick={sendMessage} disabled={loading}>
        {loading ? '送信中...' : '送信'}
      </button>
      {response && <div>応答: {response}</div>}
    </div>
  );
};
```

### Vue.js での実装例
```javascript
<template>
  <div>
    <input v-model="message" placeholder="メッセージを入力" />
    <button @click="sendMessage" :disabled="loading">
      {{ loading ? '送信中...' : '送信' }}
    </button>
    <div v-if="response">応答: {{ response }}</div>
  </div>
</template>

<script>
export default {
  data() {
    return {
      message: '',
      response: '',
      loading: false
    };
  },
  methods: {
    async sendMessage() {
      this.loading = true;
      try {
        const response = await fetch('/conversation', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            messages: [{ role: 'user', content: this.message }]
          })
        });
        
        const data = await response.json();
        this.response = data.choices[0].message.content;
      } catch (error) {
        this.response = 'エラー: ' + error.message;
      } finally {
        this.loading = false;
      }
    }
  }
};
</script>
```

## エラーハンドリング実例

### 一般的なエラーパターンと対処法

#### 400 Bad Request
```json
{
  "error": {
    "code": "INVALID_REQUEST",
    "message": "リクエストパラメータが不正です",
    "details": "messages フィールドが必須です"
  }
}
```
**対処法**: リクエストボディの形式とパラメータを確認

#### 401 Unauthorized
```json
{
  "error": {
    "code": "AUTHENTICATION_REQUIRED",
    "message": "認証が必要です",
    "details": "有効なAzure ADトークンが必要です"
  }
}
```
**対処法**: Azure AD認証を実行、/.auth/me で認証状態確認

#### 500 Internal Server Error
```json
{
  "error": {
    "code": "AZURE_OPENAI_ERROR", 
    "message": "Azure OpenAI接続エラー",
    "details": "一時的な障害の可能性があります"
  }
}
```
**対処法**: 数秒後にリトライ、システム管理者に連絡

### フロントエンドでのエラーハンドリング実装
```javascript
const handleAPICall = async (endpoint, data) => {
  try {
    const response = await fetch(endpoint, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data)
    });

    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(`${response.status}: ${errorData.error?.message || 'Unknown error'}`);
    }

    return await response.json();
  } catch (error) {
    // ユーザーフレンドリーなエラーメッセージ表示
    if (error.message.includes('401')) {
      alert('認証が必要です。ログインしてください。');
      // ログインページにリダイレクト
      window.location.href = '/.auth/login/aad';
    } else if (error.message.includes('400')) {
      alert('入力内容を確認してください。');
    } else if (error.message.includes('500')) {
      alert('サーバーエラーが発生しました。時間をおいて再試行してください。');
    } else {
      alert('エラーが発生しました: ' + error.message);
    }
    throw error;
  }
};
```

## パフォーマンステスト

### 負荷テスト例
```bash
# Apache Bench を使用した簡易負荷テスト
ab -n 100 -c 10 -H "Content-Type: application/json" \\
   -p post_data.json http://localhost:50505/conversation

# post_data.json の内容:
# {"messages": [{"role": "user", "content": "テストメッセージ"}]}
```

### ストリーミング応答テスト
```javascript
// Server-Sent Events でのストリーミング受信
const streamConversation = async (message) => {
  const response = await fetch('/conversation', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      messages: [{ role: 'user', content: message }],
      stream: true
    })
  });

  const reader = response.body.getReader();
  let result = '';

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    
    const chunk = new TextDecoder().decode(value);
    result += chunk;
    // リアルタイムでUI更新
    updateUI(result);
  }
};
```

## 開発・デバッグのベストプラクティス

### ログ確認
```bash
# アプリケーションログリアルタイム表示
tail -f logs/app.log

# エラーログのみフィルタ
grep "ERROR" logs/app.log

# 特定エンドポイントのログ
grep "/conversation" logs/app.log
```

### API テスト自動化
```python
# pytest での API テスト例
import pytest
import requests

class TestAPI:
    base_url = "http://localhost:50505"
    
    def test_health_check(self):
        response = requests.get(f"{self.base_url}/healthz")
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"
    
    def test_conversation_api(self):
        data = {
            "messages": [{"role": "user", "content": "テスト"}],
            "stream": False
        }
        response = requests.post(f"{self.base_url}/conversation", json=data)
        assert response.status_code == 200
        assert "choices" in response.json()
```

## 外部委託開発者向けチェックリスト

### 開発開始前
- [ ] Azure OpenAI Serviceアクセス権限確認
- [ ] 開発環境構築完了
- [ ] 全エンドポイントの動作確認
- [ ] 認証フローの理解
- [ ] エラーハンドリング実装計画

### 開発中
- [ ] APIレスポンス時間の監視
- [ ] エラーログの定期確認
- [ ] セキュリティベストプラクティス遵守
- [ ] ユーザビリティテスト実施

### デプロイ前
- [ ] 全API機能の結合テスト
- [ ] パフォーマンステスト実施
- [ ] セキュリティ脆弱性チェック
- [ ] ドキュメント更新

外部委託開発者向けの包括的なAPIデモ環境です。実際の開発における参考資料として活用し、
不明な点がございましたら、プロジェクトチームまでお気軽にお問い合わせください。

## 追加リソース
- **OpenAPI仕様書**: `/openapi_spec.json`
- **Swagger UI ドキュメント**: `/openapi_docs.html`  
- **Postman コレクション**: プロジェクトルートの `postman_collection.json`
- **cURL サンプル集**: `curl_examples.sh` スクリプト"""
        
        return demo
    
    def generate_curl_examples(self) -> str:
        """cURL使用例を生成
        
        Returns:
            str: cURL例のシェルスクリプト形式
        """
        curl_examples = """#!/bin/bash
# API動作確認用cURLサンプル

echo "=== Azure OpenAI Chat App API Demo ==="

# ヘルスチェック
echo "1. Health Check"
curl -X GET http://127.0.0.1:50505/healthz

echo -e "\\n\\n2. Frontend Settings"
curl -X GET http://127.0.0.1:50505/frontend_settings

echo -e "\\n\\n3. User Auth Info"
curl -X GET http://127.0.0.1:50505/.auth/me

echo -e "\\n\\n4. History List"
curl -X GET http://127.0.0.1:50505/history/list

echo -e "\\n\\n5. Basic Conversation"
curl -X POST http://127.0.0.1:50505/conversation \\
  -H "Content-Type: application/json" \\
  -d '{
    "messages": [
      {"role": "user", "content": "こんにちは"}
    ],
    "stream": false
  }'

echo -e "\\n\\n=== Demo Complete ==="
"""
        return curl_examples
    
    def create_postman_collection(self) -> Dict[str, Any]:
        """Postmanコレクションを作成
        
        Returns:
            Dict[str, Any]: Postmanコレクションの辞書形式
        """
        collection = {
            "info": {
                "name": "Azure OpenAI Chat App API",
                "description": "外部委託開発者向けAPI動作確認コレクション",
                "version": "1.0.0"
            },
            "item": [
                {
                    "name": "Health Check",
                    "request": {
                        "method": "GET",
                        "header": [],
                        "url": {
                            "raw": f"{self.base_url}/healthz",
                            "host": [self.base_url.split("://")[1].split(":")[0]],
                            "port": "50505",
                            "path": ["healthz"]
                        }
                    }
                },
                {
                    "name": "Basic Conversation",
                    "request": {
                        "method": "POST",
                        "header": [
                            {
                                "key": "Content-Type",
                                "value": "application/json"
                            }
                        ],
                        "body": {
                            "mode": "raw",
                            "raw": json.dumps({
                                "messages": [
                                    {"role": "user", "content": "こんにちは"}
                                ],
                                "stream": False
                            })
                        },
                        "url": {
                            "raw": f"{self.base_url}/conversation",
                            "host": [self.base_url.split("://")[1].split(":")[0]],
                            "port": "50505", 
                            "path": ["conversation"]
                        }
                    }
                },
                {
                    "name": "History List",
                    "request": {
                        "method": "GET",
                        "header": [],
                        "url": {
                            "raw": f"{self.base_url}/history/list",
                            "host": [self.base_url.split("://")[1].split(":")[0]],
                            "port": "50505",
                            "path": ["history", "list"]
                        }
                    }
                }
            ]
        }
        
        return collection
    
    def save_api_demo(self, filename: str) -> str:
        """APIデモをファイルに保存
        
        Args:
            filename: 保存先ファイル名
            
        Returns:
            str: 保存されたファイルパス
        """
        demo = self.create_api_demo()
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(demo)
        return filename
    
    def save_curl_examples(self, filename: str) -> str:
        """cURL例をファイルに保存
        
        Args:
            filename: 保存先ファイル名
            
        Returns:
            str: 保存されたファイルパス
        """
        curl_examples = self.generate_curl_examples()
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(curl_examples)
        return filename
    
    def save_postman_collection(self, filename: str) -> str:
        """Postmanコレクションをファイルに保存
        
        Args:
            filename: 保存先ファイル名
            
        Returns:
            str: 保存されたファイルパス
        """
        collection = self.create_postman_collection()
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(collection, f, indent=2, ensure_ascii=False)
        return filename
