# アーキテクチャ設計書

## 概要

単一ファイル635行のスクリプトを、責任別に分割されたモジュール構造に再設計しました。

## モジュール構成図

```
notify_refactored/
│
├── main.py                         # CLIエントリーポイント
│   └── → NotificationManager
│       └── → 各Notifier (Slack/LINE/Email)
│
├── config/                         # 設定管理層
│   ├── settings.py                 # dataclass設定
│   │   ├── NotificationSettings
│   │   ├── SlackConfig
│   │   ├── LineConfig
│   │   └── EmailConfig
│   └── validation.py               # 検証関数
│       ├── validate_url()
│       ├── validate_email()
│       ├── validate_token()
│       └── validate_port()
│
├── notifiers/                      # 通知サービス層
│   ├── base.py                     # 抽象基底クラス
│   │   ├── BaseNotifier (ABC)
│   │   └── NotificationResult (dataclass)
│   ├── slack.py                    # Slack実装
│   │   └── SlackNotifier
│   ├── line.py                     # LINE実装
│   │   └── LineNotifier
│   └── email.py                    # Email実装
│       └── EmailNotifier
│
├── core/                           # コア機能層
│   ├── manager.py                  # 統合管理
│   │   └── NotificationManager
│   └── exceptions.py               # カスタム例外
│       ├── NotificationError
│       ├── ConfigurationError
│       ├── ValidationError
│       └── SendError
│
└── utils/                          # ユーティリティ層
    ├── logging.py                  # ログ設定
    │   └── setup_logging()
    └── retry.py                    # リトライ機能
        └── retry_on_failure()
```

## クラス図

```
┌─────────────────────────────────────────────────────────────┐
│                    NotificationManager                      │
├─────────────────────────────────────────────────────────────┤
│ - settings: NotificationSettings                            │
│ - _notifiers: Dict[str, BaseNotifier]                      │
├─────────────────────────────────────────────────────────────┤
│ + send_to_channels(message, channels, **kwargs)            │
│ + get_available_channels() -> List[str]                    │
└───────────────┬─────────────────────────────────────────────┘
                │
                │ 管理
                ▼
┌───────────────────────────────────────────────────────┐
│                  BaseNotifier (ABC)                   │
├───────────────────────────────────────────────────────┤
│ # config: Dict[str, Any]                             │
│ # dry_run: bool                                      │
│ # enable_retry: bool                                 │
├───────────────────────────────────────────────────────┤
│ + validate_config() [abstract]                       │
│ + _send_impl(message, **kwargs) [abstract]          │
│ + send(message, **kwargs) -> NotificationResult     │
│ # _send_with_retry() -> NotificationResult          │
└───────────────┬──────────────────────────────────────┘
                │
                │ 継承
    ┌───────────┼───────────┐
    │           │           │
    ▼           ▼           ▼
┌──────────┐ ┌──────────┐ ┌──────────┐
│  Slack   │ │   LINE   │ │  Email   │
│ Notifier │ │ Notifier │ │ Notifier │
└──────────┘ └──────────┘ └──────────┘
```

## データフロー

### 1. 初期化フロー
```
main.py
  └─> NotificationSettings.from_env()
       └─> .env から環境変数読み込み
            └─> 各Config dataclass作成
                 └─> NotificationManager()
                      └─> 各Notifier初期化
```

### 2. 送信フロー
```
main.py
  └─> manager.send_to_channels()
       └─> for each channel:
            ├─> notifier.validate_config()
            └─> notifier.send()
                 └─> if enable_retry:
                      └─> _send_with_retry()
                           └─> _send_impl() (実装固有)
                                └─> NotificationResult
```

## 設計パターン

### 1. テンプレートメソッドパターン
`BaseNotifier`が共通処理を実装し、個別処理を子クラスに委譲：
- `send()`: 共通の送信フロー（リトライ含む）
- `_send_impl()`: 各サービス固有の実装

### 2. ストラテジーパターン
`NotificationManager`が通知戦略を選択して実行：
- 各Notifierは独立した戦略として動作
- 実行時に動的に選択可能

### 3. ファクトリーパターン
`NotificationSettings.from_env()`が設定を生成：
- 環境変数から適切なConfigオブジェクトを生成
- 未設定の場合はNoneを返す

## 依存関係

```
main.py
  ├─> config.settings
  ├─> core.manager
  └─> utils.logging

core.manager
  ├─> config.settings
  ├─> notifiers.*
  └─> core.exceptions

notifiers.*
  ├─> notifiers.base
  ├─> config.validation
  └─> core.exceptions

config.settings
  ├─> config.validation
  └─> core.exceptions
```

## 拡張ポイント

### 新しい通知チャネルの追加

1. **Notifierクラスを作成**
```python
# notifiers/discord.py
class DiscordNotifier(BaseNotifier):
    def _get_channel_name(self) -> str:
        return "discord"
    
    def validate_config(self) -> None:
        # 検証ロジック
        pass
    
    def _send_impl(self, message, **kwargs):
        # Discord固有の送信ロジック
        return NotificationResult(...)
```

2. **Config dataclassを追加**
```python
# config/settings.py
@dataclass
class DiscordConfig:
    webhook_url: str
    def validate(self) -> None:
        # 検証ロジック
        pass
```

3. **Managerに統合**
```python
# core/manager.py
if self.settings.discord:
    self._notifiers["discord"] = DiscordNotifier(...)
```

## テスト戦略

### 単体テスト
- 各Notifierクラスを独立してテスト
- モックを使用してAPI呼び出しを代替
- 設定バリデーションのテスト

### 統合テスト
- NotificationManagerの動作確認
- 複数チャネルの同時送信テスト
- エラーハンドリングのテスト

### E2Eテスト
- 実際のAPIエンドポイントを使用
- DRY RUNモードでの動作確認
- 環境変数読み込みのテスト

## パフォーマンス考慮事項

### 現状
- 各チャネルを順次実行（直列処理）
- タイムアウト: 15秒/チャネル
- リトライ: 最大3回

### 最適化の余地
1. **並列処理**: 複数チャネルを同時送信
2. **非同期処理**: async/awaitの導入
3. **キューイング**: メッセージキューの導入
4. **バッチ処理**: 複数メッセージの一括送信

## セキュリティ考慮事項

### 実装済み
- ✅ 環境変数によるシークレット管理
- ✅ ログからのシークレット除外
- ✅ 入力値のバリデーション

### 今後の改善
- [ ] シークレットの暗号化保存
- [ ] レート制限の実装
- [ ] 監査ログの記録
