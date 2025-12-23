# 完全ビルド済みデプロイパッケージ作成スクリプト
# このスクリプトは、すべてをローカルでビルドしてZIPパッケージを作成します

param(
    [string]$OutputPath = ".\deployment-package.zip",
    [switch]$CleanBuild = $false
)

Write-Host "=== 完全ビルド済みデプロイパッケージ作成開始 ===" -ForegroundColor Green

# 1. 作業ディレクトリ作成
$TempDir = ".\temp_deployment"
if (Test-Path $TempDir) {
    Remove-Item $TempDir -Recurse -Force
}
New-Item -ItemType Directory -Path $TempDir | Out-Null

try {
    # 2. Python仮想環境の依存関係をインストール
    Write-Host "Step 1: Python依存関係のローカルインストール..." -ForegroundColor Yellow
    
    # 修正版requirements.txtを優先使用
    if (Test-Path ".\requirements-fixed.txt") {
        Write-Host "  修正版requirements-fixed.txtを使用..." -ForegroundColor Cyan
        Copy-Item -Path ".\requirements-fixed.txt" -Destination "$TempDir\requirements.txt"
        Write-Host "  grpcio競合問題回避版を使用" -ForegroundColor Green
    } elseif (Test-Path ".\requirements.txt") {
        Write-Host "  元のrequirements.txtを使用..." -ForegroundColor Yellow
        Copy-Item -Path ".\requirements.txt" -Destination "$TempDir\requirements.txt"
        Write-Host "  警告: grpcio競合の可能性があります" -ForegroundColor Yellow
    } else {
        Write-Host "  エラー: requirements.txtが見つかりません！" -ForegroundColor Red
        # フォールバック: 最小限の依存関係
        $RequirementsFallback = @"
Flask==3.0.3
gunicorn==20.1.0
requests==2.32.3
python-dotenv==1.0.0
openai==1.55.3
azure-identity==1.17.0
azure-keyvault-secrets==4.8.0
"@
        $RequirementsFallback | Out-File -FilePath "$TempDir\requirements.txt" -Encoding UTF8
        Write-Host "  フォールバック版requirements.txtを作成しました" -ForegroundColor Yellow
    }
    
    # 依存関係を一時ディレクトリにインストール（grpcio対策込み）
    Write-Host "  依存関係をインストール中..." -ForegroundColor Cyan
    Write-Host "  注意: grpcio等のコンパイルが必要な場合、時間がかかる可能性があります" -ForegroundColor Yellow
    
    try {
        # プリコンパイル済みバイナリを優先してインストール
        $installResult = pip install -r "$TempDir\requirements.txt" --target "$TempDir\packages" --no-cache-dir --only-binary=:all: --timeout=300 2>&1
        
        if ($LASTEXITCODE -ne 0) {
            Write-Host "  エラー詳細:" -ForegroundColor Red
            Write-Host $installResult -ForegroundColor Red
            throw "プリコンパイル版インストールが失敗しました"
        }
        
        Write-Host "  プリコンパイル済みバイナリでインストール完了" -ForegroundColor Green
    }
    catch {
        Write-Host "  プリコンパイル版で失敗: $($_.Exception.Message)" -ForegroundColor Yellow
        Write-Host "  修正版requirements.txtを試行..." -ForegroundColor Yellow
        
        # 修正版requirements.txtが存在するかチェック
        if (Test-Path ".\requirements-fixed.txt") {
            Copy-Item -Path ".\requirements-fixed.txt" -Destination "$TempDir\requirements.txt" -Force
            Write-Host "  修正版requirements.txtを使用" -ForegroundColor Cyan
            
            try {
                $installResult2 = pip install -r "$TempDir\requirements.txt" --target "$TempDir\packages" --no-cache-dir --timeout=1800 2>&1
                
                if ($LASTEXITCODE -ne 0) {
                    Write-Host "  修正版でもエラー:" -ForegroundColor Red
                    Write-Host $installResult2 -ForegroundColor Red
                    throw "すべてのインストール方法が失敗しました"
                }
                
                Write-Host "  修正版requirements.txtでインストール完了" -ForegroundColor Green
            }
            catch {
                Write-Host "  致命的エラー: 依存関係のインストールに失敗しました" -ForegroundColor Red
                Write-Host "  パッケージ作成を中止します" -ForegroundColor Red
                throw "依存関係インストール失敗: $($_.Exception.Message)"
            }
        } else {
            Write-Host "  修正版requirements.txtが見つかりません" -ForegroundColor Red
            throw "依存関係の解決に失敗しました"
        }
    }
    
    # 3. フロントエンドビルド済みファイルをコピー
    Write-Host "Step 2: ビルド済みフロントエンドファイルのコピー..." -ForegroundColor Yellow
    
    # 既存のstaticフォルダがあればそれを使用（事前ビルド済み）
    if (Test-Path ".\static") {
        Write-Host "  既存のビルド済みファイルを使用..." -ForegroundColor Cyan
        New-Item -ItemType Directory -Path "$TempDir\static" -Force | Out-Null
        Copy-Item -Path ".\static\*" -Destination "$TempDir\static" -Recurse -Force
    } else {
        Write-Host "  staticフォルダが見つかりません。フロントエンドを事前ビルドしてください。" -ForegroundColor Yellow
        Write-Host "  コマンド: cd frontend && npm run build" -ForegroundColor Cyan
    }
    
    # 4. アプリケーションファイルをコピー
    Write-Host "Step 3: アプリケーションファイルのコピー..." -ForegroundColor Yellow
    
    # 必要なPythonファイル
    $AppFiles = @(
        "app.py",
        "function_app.py",
        "gunicorn.conf.py",
        "host.json"
    )
    
    foreach ($file in $AppFiles) {
        if (Test-Path $file) {
            Copy-Item -Path $file -Destination $TempDir
        }
    }
    
    # 必要なPythonモジュールディレクトリをコピー
    Write-Host "  Pythonモジュールディレクトリをコピー中..." -ForegroundColor Cyan
    $ModuleDirs = @(
        "backend",
        "web", 
        "application",
        "domain",
        "infrastructure",
        "common",
        "config"
    )
    
    foreach ($dir in $ModuleDirs) {
        if (Test-Path $dir) {
            Copy-Item -Path $dir -Destination $TempDir -Recurse -Force
            Write-Host "    $dir ディレクトリをコピーしました" -ForegroundColor Green
        } else {
            Write-Host "    警告: $dir ディレクトリが見つかりません" -ForegroundColor Yellow
        }
    }
    
    # 5. 設定ファイルの準備
    Write-Host "Step 4: 本番用設定ファイルの準備..." -ForegroundColor Yellow
    
    # 本番用gunicorn設定
    $GunicornConfig = @"
import os

# Worker設定
workers = int(os.environ.get('WEB_CONCURRENCY', 2))
worker_class = 'sync'  # uvicornは使わない
timeout = 120
keepalive = 2

# バインド設定
bind = "0.0.0.0:8000"

# ログ設定
accesslog = '-'
errorlog = '-'
loglevel = 'info'

# プロセス設定
preload_app = True
"@
    
    $GunicornConfig | Out-File -FilePath "$TempDir\gunicorn.conf.py" -Encoding UTF8
    
    # 6. 起動スクリプト作成
    $StartupScript = @"
#!/bin/bash
cd /home/site/wwwroot
export PYTHONPATH=/home/site/wwwroot/packages:$PYTHONPATH
gunicorn --config gunicorn.conf.py app:app
"@
    
    $StartupScript | Out-File -FilePath "$TempDir\startup.sh" -Encoding UTF8
    
    # 7. ZIPパッケージ作成
    Write-Host "Step 5: ZIPパッケージ作成..." -ForegroundColor Yellow
    
    if (Test-Path $OutputPath) {
        Remove-Item $OutputPath -Force
    }
    
    # PowerShellのCompress-Archiveを使用
    Set-Location $TempDir
    Compress-Archive -Path * -DestinationPath "..\$OutputPath" -CompressionLevel Optimal
    Set-Location ".."
    
    Write-Host "=== パッケージ作成完了 ===" -ForegroundColor Green
    Write-Host "ファイル: $OutputPath" -ForegroundColor Cyan
    Write-Host "サイズ: $((Get-Item $OutputPath).Length / 1MB) MB" -ForegroundColor Cyan
    
} finally {
    # 8. 一時ディレクトリ削除
    if (Test-Path $TempDir) {
        Remove-Item $TempDir -Recurse -Force
    }
}

# 9. デプロイ手順を表示
Write-Host "`n=== デプロイ手順 ===" -ForegroundColor Yellow
Write-Host "1. Azure App Serviceで以下の設定を行う:" -ForegroundColor White
Write-Host "   WEBSITE_RUN_FROM_PACKAGE=1" -ForegroundColor Cyan
Write-Host "   SCM_DO_BUILD_DURING_DEPLOYMENT=false" -ForegroundColor Cyan
Write-Host "`n2. 以下のコマンドでデプロイ:" -ForegroundColor White
Write-Host "   az webapp deploy --resource-group <group-name> --name <app-name> --src-path $OutputPath" -ForegroundColor Cyan
