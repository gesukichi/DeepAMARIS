---
title: Azure デプロイに最低限必要なフォルダ構成調査
created_date: 2025-12-23
author: GitHub Copilot
purpose: frontendとbackend関係の処理をAzureデプロイするために最低限必要なフォルダとファイルの特定
related_tasks: deployment investigation
---

# Azureデプロイに最低限必要なフォルダ構成調査

## 概要
frontendのビルド後、create_complete_package.ps1を実行するとバックエンドと一緒にZIPファイルが作成される。
このドキュメントでは、Azure App Serviceへのデプロイに最低限必要なフォルダとファイルを特定する。

## デプロイパッケージの構成

### フルデプロイパッケージ (create_complete_package.ps1)

#### 必須ファイル (ルートレベル)
```
app.py                    # メインアプリケーションファイル (Quart app)
function_app.py           # Azure Functions用エントリーポイント
gunicorn.conf.py          # Gunicorn設定ファイル
host.json                 # Azure Functions設定
requirements.txt          # Python依存関係リスト
startup.sh                # 起動スクリプト
```

#### 必須ディレクトリ
```
backend/                  # バックエンドロジック
├── history/              # 会話履歴サービス (CosmosDB)
├── security/             # セキュリティユーティリティ (MS Defender)
├── keyvault_utils.py     # Key Vault連携
├── settings.py           # バックエンド設定
├── utils.py              # 共通ユーティリティ
└── modern_rag_web_service.py  # Modern RAG Webサービス

web/                      # Webルーティングレイヤー
├── routers/              # APIルーター
└── controllers/          # コントローラー

application/              # アプリケーション層
├── configuration/        # 設定管理 (feature flags等)
├── conversation/         # 会話関連ロジック
└── facades/              # ファサードパターン実装

domain/                   # ドメイン層
├── user/                 # ユーザー関連ドメイン
│   ├── services/         # AuthService等
│   └── interfaces/       # インターフェース定義
├── configuration/        # 設定ドメイン
├── conversation/         # 会話ドメイン
├── system/               # システムドメイン
└── common/               # 共通ドメイン

infrastructure/           # インフラストラクチャ層
├── factories/            # ファクトリークラス
│   └── ai_service_factory.py  # AIサービスファクトリー
├── adapters/             # アダプター実装
├── configuration/        # インフラ設定
├── services/             # インフラサービス
└── monitoring/           # モニタリング

common/                   # 共通モジュール
└── http_status.py        # HTTPステータス定義

config/                   # 設定ファイル
└── feature_flags.json    # 機能フラグ設定

static/                   # フロントエンドビルド成果物
├── assets/               # CSS/JS/画像等
└── index.html            # SPA エントリーポイント
```

## app.pyからの依存関係分析

### 直接インポートされるモジュール
[app.py](../app.py)は以下のローカルモジュールに依存:

```python
# Infrastructure層
from infrastructure.factories.ai_service_factory import create_ai_service_factory

# Application層
from application.configuration.phase4_feature_flags import Phase4FeatureFlags

# Backend層
from backend.security.ms_defender_utils import get_msdefender_user_json
from backend.history.cosmosdbservice import CosmosConversationClient
from backend.history.conversation_service import ConversationHistoryService, ConversationTitleGenerator
from backend.keyvault_utils import KeyVaultService
from backend.settings import (...)
from backend.utils import (...)

# Domain層
from domain.user.services.auth_service import AuthService
from domain.user.interfaces.auth_service import AuthenticationError

# Web層
from web.routers.history_router import history_bp, init_history_router

# Common層
from common.http_status import (...)
```

### 動的インポート (条件付き)
```python
from backend.security.test_security import safe_import_test_functions  # デバッグモード時
from backend.modern_rag_web_service import ModernBingGroundingAgentService  # RAG機能使用時
```

## 最低限必要なフォルダとファイル

### レベル1: 絶対に必要（コアシステム）

#### ファイル
- `app.py` - メインアプリケーション
- `requirements.txt` - Python依存関係
- `gunicorn.conf.py` - Webサーバー設定
- `startup.sh` - 起動スクリプト

#### フォルダ
- `static/` - フロントエンドビルド成果物 (frontend build結果)
- `backend/` - バックエンドロジック全体
  - `backend/settings.py`
  - `backend/utils.py`
  - `backend/keyvault_utils.py`
- `common/` - HTTPステータス等の共通定義
  - `common/http_status.py`

### レベル2: 機能別に必要（機能使用時）

#### 会話履歴機能 (CosmosDB)
- `backend/history/` - 会話履歴サービス
  - `backend/history/cosmosdbservice.py`
  - `backend/history/conversation_service.py`

#### セキュリティ機能
- `backend/security/` - MS Defender連携
  - `backend/security/ms_defender_utils.py`

#### 認証機能
- `domain/user/` - ユーザードメイン
  - `domain/user/services/auth_service.py`
  - `domain/user/interfaces/`

#### AIサービス
- `infrastructure/factories/` - AIサービスファクトリー
  - `infrastructure/factories/ai_service_factory.py`

#### 機能フラグ
- `application/configuration/` - 設定管理
  - `application/configuration/phase4_feature_flags.py`
- `config/feature_flags.json` - 機能フラグ設定

#### Web API
- `web/routers/` - APIルーター
  - `web/routers/history_router.py`

### レベル3: オプション（拡張機能）

#### Modern RAG機能
- `backend/modern_rag_web_service.py`

#### Azure Functions対応
- `function_app.py`
- `host.json`

#### その他のドメイン・インフラ層
- `domain/configuration/`
- `domain/conversation/`
- `domain/system/`
- `infrastructure/adapters/`
- `infrastructure/services/`
- `infrastructure/monitoring/`

## デプロイパッケージのサイズ最適化

### Backend-onlyパッケージの構成
[deploy_scripts/create_backend_only_package.ps1](../deploy_scripts/create_backend_only_package.ps1)では以下を含む:

#### 含まれるもの
- 全てのPythonモジュール: `backend/`, `application/`, `domain/`, `infrastructure/`, `common/`, `config/`, `web/`
- 必須ファイル: `app.py`, `function_app.py`, `gunicorn.conf.py`, `requirements.txt`, 起動スクリプト等

#### 除外されるもの
- `frontend/` - フロントエンドソースコード
- `static/` - ビルド済みフロントエンド (別途デプロイ)
- `logs/` - ログファイル
- `tests/` - テストコード

## ミニマル構成の推奨事項

### 最小限で動作するAzureデプロイ構成

```
project-root/
├── app.py                         # 必須
├── requirements.txt               # 必須
├── gunicorn.conf.py              # 必須
├── startup.sh                    # 必須
│
├── static/                       # 必須: frontendビルド成果物
│   ├── index.html
│   └── assets/
│
├── backend/                      # 必須
│   ├── settings.py
│   ├── utils.py
│   ├── keyvault_utils.py
│   ├── history/                  # CosmosDB使用時
│   └── security/                 # MS Defender使用時
│
├── common/                       # 必須
│   └── http_status.py
│
├── infrastructure/               # AIサービス使用時
│   └── factories/
│       └── ai_service_factory.py
│
├── application/                  # 機能フラグ使用時
│   └── configuration/
│
├── domain/                       # 認証機能使用時
│   └── user/
│
├── web/                          # Web API使用時
│   └── routers/
│
└── config/                       # 機能フラグ使用時
    └── feature_flags.json
```

## create_complete_package.ps1の動作フロー

### Step 1: Python依存関係のインストール
- `requirements.txt` または `requirements-fixed.txt` を使用
- `temp_deployment/packages/` に依存関係をインストール

### Step 2: フロントエンドビルド成果物のコピー
- 既存の `static/` フォルダがあればコピー
- なければ警告を表示 (事前に `cd frontend && npm run build` が必要)

### Step 3: アプリケーションファイルのコピー
- 必須Pythonファイル: `app.py`, `function_app.py`, `gunicorn.conf.py`, `host.json`
- 必須ディレクトリ: `backend/`, `web/`, `application/`, `domain/`, `infrastructure/`, `common/`, `config/`

### Step 4: 設定ファイルの準備
- 本番用 `gunicorn.conf.py` を生成
- `startup.sh` を生成

### Step 5: ZIPパッケージ作成
- 全てを `deployment-package.zip` に圧縮

## Azureデプロイ時の設定

### 必須App Service設定
```bash
WEBSITE_RUN_FROM_PACKAGE=1              # ZIPから直接実行
SCM_DO_BUILD_DURING_DEPLOYMENT=false    # ローカルビルド済みのため不要
```

### デプロイコマンド
```bash
az webapp deploy \
  --resource-group <resource-group-name> \
  --name <app-name> \
  --src-path deployment-package.zip
```

## まとめ

### 最低限必要なフォルダとファイル (絶対必須)

**ファイル:**
- `app.py`
- `requirements.txt`
- `gunicorn.conf.py`
- `startup.sh`

**フォルダ:**
- `static/` (フロントエンドビルド成果物)
- `backend/` (コアモジュール: settings.py, utils.py, keyvault_utils.py)
- `common/` (http_status.py)

### 機能に応じて必要なフォルダ

- **CosmosDB会話履歴**: `backend/history/`
- **セキュリティ**: `backend/security/`
- **認証**: `domain/user/`
- **AIサービス**: `infrastructure/factories/`
- **Web API**: `web/routers/`
- **機能フラグ**: `application/configuration/`, `config/`

### デプロイ前の必須作業

1. フロントエンドビルド:
   ```bash
   cd frontend
   npm install
   npm run build
   ```
   - 結果: `static/` フォルダに成果物が生成される

2. デプロイパッケージ作成:
   ```powershell
   .\deploy_scripts\create_complete_package.ps1
   ```
   - 結果: `deployment-package.zip` が生成される

3. Azureデプロイ:
   ```bash
   az webapp deploy --resource-group <rg> --name <app> --src-path deployment-package.zip
   ```

このアプローチにより、フロントエンドとバックエンドの両方を含む完全なデプロイパッケージが作成され、Azure App Serviceで正常に動作する。
