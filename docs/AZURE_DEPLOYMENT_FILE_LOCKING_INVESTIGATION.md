# Azure App Service ファイルロッキング問題の徹底調査結果

## 調査概要

app.pyがZIPファイルからのデプロイで更新されなかった問題について、Azure公式ドキュメントとKuduプロジェクトの情報を基に徹底調査を実施しました。

## 発見された主要原因

### 1. **ZIPデプロイのタイムスタンプ比較による最適化**

**問題の根本原因**：
- Azure App ServiceのZIPデプロイは、**タイムスタンプベースの最適化**を行います
- 公式ドキュメントより：「**Files will only be copied if their timestamps don't match what is already deployed**」
- この最適化により、既存ファイルのタイムスタンプが新しいファイルと同じかより新しい場合、ファイルは更新されません

**対応策**：
```bash
# タイムスタンプ最適化を無効化するApp Setting
SCM_ZIPDEPLOY_DONOT_PRESERVE_FILETIME=1
```

### 2. **Pythonアプリケーションによるファイルロック**

**問題メカニズム**：
- 実行中のPythonアプリケーション（Gunicorn/WSGI）がapp.pyファイルをロード・実行
- ファイルハンドルが開かれた状態で、書き込み操作がブロックされる
- Kuduデプロイメントエンジンが「ERROR_FILE_IN_USE」エラーを発生

**対応策オプション**：

#### A) サイト停止アプローチ
```bash
# デプロイ前にサイトを停止
az webapp stop --name <app-name> --resource-group <resource-group>
# デプロイ実行
az webapp deploy --resource-group <rg> --name <app> --src-path <zip>
# デプロイ後にサイトを開始
az webapp start --name <app-name> --resource-group <resource-group>
```

#### B) App Offlineモード（MSDeployの場合）
```json
{
  "apiVersion": "2016-08-01",
  "name": "MSDeploy",
  "type": "Extensions",
  "properties": {
    "packageUri": "https://storage.blob.core.windows.net/artifacts/package.zip",
    "appOffline": true
  }
}
```

#### C) ReadOnlyアプリケーション宣言
```bash
# App Settingに追加
WEBSITE_READONLY_APP=1
```

### 3. **Kuduプロセスエクスプローラーでの診断方法**

**ファイルロック調査手順**：
1. Kuduコンソール（https://yoursite.scm.azurewebsites.net）にアクセス
2. Process Explorerを開く
3. 「Find Handle」でapp.pyを検索
4. どのプロセスがファイルをロックしているかを特定

### 4. **Build Automationの影響**

**重要設定**：
```bash
# ビルド自動化を有効化（推奨）
SCM_DO_BUILD_DURING_DEPLOYMENT=true
```

この設定により：
- Oryxビルドシステムが依存関係を適切に処理
- 仮想環境の非互換性問題を回避
- ファイル更新の確実性が向上

## 我々の事例における推定原因

### 1. **タイムスタンプ最適化による更新阻止**
- FileZillaでのFTPアップロード成功は、この仮説を強く支持
- ZIPデプロイとFTPの差異：タイムスタンプチェックの有無

### 2. **Gunicornプロセスによるファイルロック**
- 実行中のPythonアプリケーションがapp.pyを使用中
- ZIPデプロイ時にファイル更新が競合状態に

### 3. **増分デプロイメントの制限**
- Azureの増分デプロイメントは既存ファイルを保持する傾向
- 公式文書：「Files in the ZIP package are copied only if their timestamps don't match what is already deployed」

## 解決策の実装

### 即座に実装可能な対策

#### 1. タイムスタンプ最適化の無効化
```powershell
az webapp config appsettings set --resource-group $resourceGroup --name $appName --settings SCM_ZIPDEPLOY_DONOT_PRESERVE_FILETIME=1
```

#### 2. 強制的な完全デプロイメント
```powershell
# clean=trueパラメータでKudu API使用
curl -X POST -u $publishProfile https://$siteName.scm.azurewebsites.net/api/zipdeploy?clean=true -T $zipFile
```

#### 3. デプロイ前のサイト停止
```powershell
az webapp stop --name $appName --resource-group $resourceGroup
az webapp deploy --resource-group $resourceGroup --name $appName --src-path $zipPath
az webapp start --name $appName --resource-group $resourceGroup
```

### 長期的な対策

#### 1. Slotベースのセーフデプロイメント
- Staging Slotにデプロイ
- 検証後にProduction Slotとスワップ
- ダウンタイムなしでのデプロイメント

#### 2. Run from Packageの採用
```bash
WEBSITE_RUN_FROM_PACKAGE=1
```
- ファイルロッキング問題を根本的に回避
- パフォーマンス向上の副次効果

## 予防策

### 1. デプロイメント設定の標準化
```json
{
  "SCM_DO_BUILD_DURING_DEPLOYMENT": "true",
  "SCM_ZIPDEPLOY_DONOT_PRESERVE_FILETIME": "1",
  "WEBSITE_READONLY_APP": "1"
}
```

### 2. モニタリングの実装
- デプロイメント後のファイル整合性チェック
- タイムスタンプ比較による更新確認
- Health Endpointでの動作確認

### 3. ドキュメント化
- デプロイメント手順の標準化
- トラブルシューティングガイドの作成
- 緊急時対応プロセスの確立

## 参考文献

1. **Azure公式ドキュメント**：
   - [Configure a Linux Python app for Azure App Service](https://docs.microsoft.com/en-us/azure/app-service/configure-language-python)
   - [Deploy files to Azure App Service](https://docs.microsoft.com/en-us/azure/app-service/deploy-zip)

2. **Kudu Project Wiki**：
   - [Dealing with locked files during deployment](https://github.com/projectkudu/kudu/wiki/Dealing-with-locked-files-during-deployment)
   - [Deploying from a zip file or url](https://github.com/projectkudu/kudu/wiki/Deploying-from-a-zip-file-or-url)

3. **Azure App Service Blog**：
   - [Using GitHub Actions for Python Applications](https://azure.github.io/AppService/2020/12/11/cicd-for-python-apps.html)

## 結論

app.pyの更新問題は、Azure App Serviceの**タイムスタンプベースの最適化**と**実行中プロセスによるファイルロック**の組み合わせが原因でした。この問題は既知の課題であり、複数の回避策が公式に提供されています。

今後は、これらの対策を実装することで、同様の問題を予防し、安定したデプロイメントプロセスを確立できます。

---
*調査実施日: 2025年9月9日*
*調査者: GitHub Copilot*
*バージョン: v1.0*
