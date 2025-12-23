---
title: Frontendビルド方法調査
created_date: 2025-12-23
author: GitHub Copilot
purpose: frontendのビルド方法およびビルド環境の調査
related_tasks: frontend investigation
---

# Frontendビルド方法調査

## 概要
このプロジェクトのフロントエンドビルド方法について調査した結果を記載する。

## フロントエンド構成

### ディレクトリ構造
- **ルートディレクトリ**: `frontend/`
- **ソースコード**: `frontend/src/`
- **公開ファイル**: `frontend/public/`
- **ビルド出力先**: `../static/` (ルートディレクトリの `static/` フォルダ)

### 使用技術スタック
- **ビルドツール**: Vite (v7.0.6)
- **フレームワーク**: React (v18.2.0)
- **言語**: TypeScript (v4.9.5)
- **UIライブラリ**: Fluent UI React (v8.109.0)
- **パッケージマネージャ**: npm (package-lock.jsonが存在)

## ビルド方法

### 1. ローカル開発ビルド

#### 基本的なビルドコマンド
```bash
cd frontend
npm install      # 依存関係のインストール
npm run build    # プロダクションビルド
```

#### package.jsonで定義されているスクリプト
- `dev`: 開発サーバー起動 (`vite`)
- `build`: TypeScriptコンパイル + Viteビルド (`tsc && vite build`)
- `watch`: ウォッチモード付きビルド (`tsc && vite build --watch`)
- `test`: Jestテスト実行
- `lint`: ESLintによる静的解析
- `lint:fix`: ESLint自動修正
- `prettier`: Prettierチェック
- `prettier:fix`: Prettier自動整形
- `format`: PrettierとESLintの自動修正実行

### 2. Vite設定

[frontend/vite.config.ts](../frontend/vite.config.ts)の主要設定:

```typescript
export default defineConfig({
  plugins: [react()],
  build: {
    outDir: '../static',        // 出力先はプロジェクトルートのstaticフォルダ
    emptyOutDir: true,          // ビルド前に出力ディレクトリをクリア
    sourcemap: true             // ソースマップを生成
  },
  server: {
    proxy: {
      '/ask': 'http://localhost:5000',
      '/chat': 'http://localhost:5000'
    }
  }
})
```

**重要な点**:
- ビルド出力先が `../static` に設定されている
- ビルド時に既存のstaticフォルダは空にされる (`emptyOutDir: true`)
- ソースマップが生成される
- 開発サーバーはプロキシ設定でバックエンド (localhost:5000) に `/ask` と `/chat` をフォワードする

### 3. 自動ビルドスクリプト

#### start.sh (Linux/Mac向け)
[start.sh](../start.sh)では以下の手順でビルドを実行:
1. `cd frontend`
2. `npm install` - 依存関係のインストール
3. `npm run build` - フロントエンドビルド
4. バックエンドサーバー起動

#### deploy_scripts/create_complete_package.ps1 (デプロイパッケージ作成)
[deploy_scripts/create_complete_package.ps1](../deploy_scripts/create_complete_package.ps1)では:
- 既存の `static/` フォルダがあればそれを使用
- なければ `frontend/` ディレクトリで `npm run build` を実行してビルド
- ビルド結果を含むZIPパッケージを作成

### 4. デプロイ戦略

このプロジェクトには複数のデプロイ戦略が存在:

#### 完全ビルド済みパッケージ (create_complete_package.ps1)
- **方法**: ローカルで全てビルドしてZIPにパッケージング
- **対象**: Python依存関係 + フロントエンドビルド済みファイル
- **メリット**: Azureでのビルド不要、デプロイ時間短縮

#### ハイブリッドパッケージ (create_hybrid_package.ps1)
- **Python**: ローカルビルド
- **Frontend**: Azureサーバー側でビルド
- **含まれるもの**: 
  - `frontend/package.json`
  - `frontend/tsconfig.json`
  - `frontend/vite.config.ts`
  - `frontend/src/` (ソースコード)
  - `frontend/public/`

#### バックエンドのみパッケージ (create_backend_only_package.ps1)
- **対象**: バックエンドコードのみ
- **除外**: frontend/, static/, logs/, tests/

## ビルド出力

### 生成される成果物
- **場所**: `static/` (プロジェクトルート)
- **内容**: 
  - HTML/CSS/JSファイル
  - アセット (画像、フォントなど)
  - ソースマップファイル

### index.html
[frontend/index.html](../frontend/index.html)はViteのテンプレートとして使用され:
- `{{ favicon }}` と `{{ title }}` がバックエンドで動的に置換される
- エントリーポイントは `/src/index.tsx`

## 依存関係

### 主要な依存パッケージ
- `react` / `react-dom`: v18.2.0
- `@fluentui/react`: v8.109.0 (Microsoft Fluent UI)
- `react-router-dom`: v6.8.1 (ルーティング)
- `react-markdown`: v7.0.1 (マークダウンレンダリング)
- `react-syntax-highlighter`: v15.6.1 (シンタックスハイライト)
- `dompurify`: v3.0.8 (XSS対策)

### 開発依存パッケージ
- `vite`: v7.0.6
- `@vitejs/plugin-react`: v4.7.0
- `typescript`: v4.9.5
- `eslint`: v8.57.0 (リンター)
- `prettier`: v3.2.5 (コードフォーマッター)
- `jest`: v29.7.0 (テストフレームワーク)

## 注意事項

### ビルド前の確認事項
1. Node.jsがインストールされていること
2. `frontend/` ディレクトリに移動してから作業すること
3. `npm install` で依存関係がインストールされていること

### ビルド時の注意点
1. ビルド出力先の `static/` フォルダは自動的に空にされる
2. TypeScriptのコンパイルが先に実行される (`tsc && vite build`)
3. ソースマップが生成されるため、デバッグが容易

### 開発サーバー
```bash
cd frontend
npm run dev  # http://localhost:5173 で起動
```
- Viteの開発サーバーが起動
- `/ask` と `/chat` のリクエストは `http://localhost:5000` にプロキシされる

## ファイルパス一覧

### 関連設定ファイル
- [frontend/package.json](../frontend/package.json)
- [frontend/vite.config.ts](../frontend/vite.config.ts)
- [frontend/tsconfig.json](../frontend/tsconfig.json)
- [frontend/tsconfig.node.json](../frontend/tsconfig.node.json)
- [frontend/jest.config.ts](../frontend/jest.config.ts)
- [frontend/eslint.config.ts](../frontend/eslint.config.ts)
- [frontend/index.html](../frontend/index.html)

### ビルドスクリプト
- [start.sh](../start.sh)
- [deploy_scripts/create_complete_package.ps1](../deploy_scripts/create_complete_package.ps1)
- [deploy_scripts/create_hybrid_package.ps1](../deploy_scripts/create_hybrid_package.ps1)
- [deploy_scripts/create_backend_only_package.ps1](../deploy_scripts/create_backend_only_package.ps1)

## まとめ

このプロジェクトのフロントエンドは、Vite + React + TypeScriptで構築されており、以下のビルド方法が利用可能:

1. **標準ビルド**: `cd frontend && npm install && npm run build`
2. **開発サーバー**: `cd frontend && npm run dev`
3. **デプロイパッケージ作成**: PowerShellスクリプト経由

ビルド成果物は必ずプロジェクトルートの `static/` フォルダに出力され、Flaskバックエンドから配信される仕組みになっている。
