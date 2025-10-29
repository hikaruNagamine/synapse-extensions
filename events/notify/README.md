# Python通知スクリプト

Slack、LINE、Emailへの通知を一括または個別に送信できる統合Pythonスクリプトです。

## 目的と機能

このスクリプトは以下の機能を提供します：

- **3チャネル対応**: Slack (Incoming Webhook)、LINE Notify、Email (SMTP)
- **一括送信**: 3チャネルすべてに同時通知
- **個別選択送信**: 任意のチャネルの組み合わせで通知
- **DRY RUNモード**: 実際に送信せず内容を確認
- **エラーハンドリング**: 各チャネルの成功/失敗を個別に判定

## セットアップ手順

### 1. 必要な環境

- Python 3.10 以上
- pip (Pythonパッケージ管理ツール)

### 2. 仮想環境の作成（推奨）

```bash
cd events/notify
python3 -m venv venv
source venv/bin/activate  # Windowsの場合: venv\Scripts\activate
```

### 3. 依存パッケージのインストール

```bash
pip install -r requirements.txt
```

### 4. 環境変数の設定

`.env.example` を `.env` にコピーして編集します：

```bash
cp .env.example .env
```

`.env` ファイルを編集して、使用するチャネルの認証情報を設定してください。

## 使い方

### 基本的な使用方法

```bash
python notify.py -m "送信するメッセージ" [オプション]
```

### コマンドラインオプション

- `-m, --message` (必須): 送信するメッセージ本文
  - デフォルト: "スクリプトが実行されました"
- `--subject` (任意): メール件名（Email送信時のみ使用）
  - デフォルト: "[通知] スクリプト実行"
- `--channels` (任意): 送信先チャネルの指定
  - `all`: 全チャネルに送信（デフォルト）
  - カンマ区切り: `slack,line,email` など任意の組み合わせ
- `--dry-run`: 実際には送信せず、内容のみ表示

### 使用例

#### 3チャネル一括送信

```bash
python notify.py -m "テスト通知" --channels all
```

#### 個別選択送信（SlackとEmailのみ）

```bash
python notify.py -m "温度が閾値を超過しました" --subject "[Alert] 温度異常" --channels slack,email
```

#### LINE のみに送信

```bash
python notify.py -m "処理が完了しました" --channels line
```

#### DRY RUN（送信せずに確認）

```bash
python notify.py -m "テストメッセージ" --channels all --dry-run
```

## 各チャネルの準備方法

### Slack (Incoming Webhook)

1. Slackワークスペースにログイン
2. [Slack API](https://api.slack.com/apps) にアクセス
3. "Create New App" → "From scratch" を選択
4. アプリ名とワークスペースを選択して作成
5. "Incoming Webhooks" を有効化
6. "Add New Webhook to Workspace" でチャネルを選択
7. 生成されたWebhook URLを `.env` の `SLACK_WEBHOOK_URL` に設定

### LINE Notify

1. [LINE Notify](https://notify-bot.line.me/) にアクセス
2. LINE アカウントでログイン
3. マイページから "トークンを発行する" を選択
4. トークン名と通知先トークルームを選択
5. 発行されたトークンを `.env` の `LINE_NOTIFY_TOKEN` に設定

**注意**: トークンは一度しか表示されないため、必ず保存してください。

### Email (SMTP)

#### Gmail の場合

1. Googleアカウントで2段階認証を有効化
2. [アプリパスワード](https://myaccount.google.com/apppasswords) を生成
3. `.env` に以下を設定：
   ```
   SMTP_HOST=smtp.gmail.com
   SMTP_PORT=587
   SMTP_USERNAME=your-email@gmail.com
   SMTP_PASSWORD=your-app-password
   SMTP_SENDER=your-email@gmail.com
   SMTP_TO=recipient@example.com
   SMTP_USE_SSL=false
   SMTP_USE_STARTTLS=true
   ```

#### SendGrid の場合

1. [SendGrid](https://sendgrid.com/) でアカウント作成
2. API Keyを生成
3. `.env` に以下を設定：
   ```
   SMTP_HOST=smtp.sendgrid.net
   SMTP_PORT=587
   SMTP_USERNAME=apikey
   SMTP_PASSWORD=your-sendgrid-api-key
   SMTP_SENDER=your-verified-sender@example.com
   SMTP_TO=recipient@example.com
   SMTP_USE_SSL=false
   SMTP_USE_STARTTLS=true
   ```

#### SSL/STARTTLS の設定

- **STARTTLS** (推奨): ポート587を使用
  ```
  SMTP_PORT=587
  SMTP_USE_SSL=false
  SMTP_USE_STARTTLS=true
  ```

- **SSL/TLS**: ポート465を使用
  ```
  SMTP_PORT=465
  SMTP_USE_SSL=true
  SMTP_USE_STARTTLS=false
  ```

**注意**: `SMTP_USE_SSL` と `SMTP_USE_STARTTLS` の両方を `true` にすることはできません。

## 終了コード

スクリプトは以下の終了コードを返します：

- **0**: 選択した全チャネルの送信に成功
- **1**: 少なくとも1つのチャネルが失敗
- **2**: 送信先設定が不足していて送信できない
- **64**: 使い方エラー（引数不正など）

### 終了コードの確認方法

```bash
python notify.py -m "テスト"
echo $?  # Linuxの場合
echo %ERRORLEVEL%  # Windowsの場合
```

## 典型的なエラーと対処

### 認証エラー

**エラー**: `SMTP認証エラー` または `ステータスコード: 401`

**原因**:
- トークンやパスワードが間違っている
- Gmailでアプリパスワードを使用していない

**対処**:
- `.env` ファイルの認証情報を再確認
- Gmailの場合は2段階認証とアプリパスワードを使用

### タイムアウトエラー

**エラー**: `タイムアウトしました`

**原因**:
- ネットワーク接続が不安定
- SMTPサーバーが応答しない
- ファイアウォールでブロックされている

**対処**:
- ネットワーク接続を確認
- SMTPポート（587または465）がファイアウォールで許可されているか確認
- VPN使用時は設定を確認

### 宛先未設定エラー

**エラー**: `送信可能なチャネルの設定がありません`

**原因**:
- 選択したチャネルの環境変数が設定されていない

**対処**:
- `.env` ファイルで必要な環境変数が設定されているか確認
- `.env.example` を参考に不足している変数を追加

### DNS解決エラー

**エラー**: `Name or service not known`

**原因**:
- SMTPホスト名が間違っている
- DNS解決ができない

**対処**:
- `.env` の `SMTP_HOST` を確認
- `ping smtp.gmail.com` などで接続確認

### SSL/STARTTLS設定エラー

**エラー**: `SMTP_USE_SSLとSMTP_USE_STARTTLSの両方をtrueにすることはできません`

**原因**:
- 排他的な設定が両方trueになっている

**対処**:
- ポート587の場合: `SMTP_USE_SSL=false`, `SMTP_USE_STARTTLS=true`
- ポート465の場合: `SMTP_USE_SSL=true`, `SMTP_USE_STARTTLS=false`

## セキュリティに関する注意

- `.env` ファイルは絶対にGitにコミットしないでください（`.gitignore` に含まれています）
- 認証情報を含むファイルは適切なパーミッション（600など）で保護してください
- スクリプトはシークレット情報をログに出力しません
- 本番環境では環境変数を適切に管理してください

## トラブルシューティング

### デバッグ方法

1. **DRY RUNモードで確認**:
   ```bash
   python notify.py -m "テスト" --dry-run
   ```

2. **1チャネルずつテスト**:
   ```bash
   python notify.py -m "Slackテスト" --channels slack
   python notify.py -m "LINEテスト" --channels line
   python notify.py -m "Emailテスト" --channels email
   ```

3. **環境変数の確認**:
   ```bash
   # .envファイルが読み込まれているか確認
   python -c "from dotenv import load_dotenv; import os; load_dotenv(); print(os.getenv('SLACK_WEBHOOK_URL', 'NOT SET')[:20])"
   ```

## ライセンス

このスクリプトはMITライセンスの下で公開されています。
