# Python通知スクリプト v2.0 - モジュール化版

Slack、LINE、Emailへの通知を一括または個別に送信できる統合Pythonスクリプト（モジュール化版）。

## 🏗️ アーキテクチャ

### モジュール構成

```
notify_refactored/
├── __init__.py             # パッケージ初期化
├── main.py                 # エントリーポイント（CLI処理）
├── config/                 # 設定管理
│   ├── __init__.py
│   ├── settings.py         # 設定dataclass
│   └── validation.py       # 設定検証ロジック
├── notifiers/              # 通知サービス
│   ├── __init__.py
│   ├── base.py            # 基底クラス（ABC使用）
│   ├── slack.py           # Slack通知クラス
│   ├── line.py            # LINE通知クラス
│   └── email.py           # Email通知クラス
├── core/                   # コア機能
│   ├── __init__.py
│   ├── manager.py         # 通知統合管理
│   └── exceptions.py      # カスタム例外
└── utils/                  # ユーティリティ
    ├── __init__.py
    ├── logging.py         # ログ設定
    └── retry.py           # リトライ機能
```

### 設計原則

1. **責任の分離**: 各モジュールが明確な責任を持つ
2. **依存性注入**: テストしやすい設計
3. **拡張性**: 新しい通知チャネルを容易に追加可能
4. **型安全性**: 完全な型ヒント対応

## 🚀 使い方

### 基本的な使用方法

```bash
# モジュールディレクトリに移動
cd events/notify_refactored

# 3チャネル一括送信
python main.py -m "テスト通知" --channels all

# 個別選択（SlackとEmailのみ）
python main.py -m "温度異常" --subject "[Alert]" --channels slack,email

# DRY RUN
python main.py -m "テスト" --dry-run

# 詳細ログ付き
python main.py -m "デバッグ用" -v
```

### 環境変数設定

`.env.example`を`.env`にコピーして設定：

```bash
cp ../notify/.env.example .env
```

## 📚 主要クラスの説明

### BaseNotifier（基底クラス）

すべての通知サービスが継承する抽象基底クラス。

```python
from notifiers.base import BaseNotifier, NotificationResult

class CustomNotifier(BaseNotifier):
    def _get_channel_name(self) -> str:
        return "custom"
    
    def validate_config(self) -> None:
        # 設定検証ロジック
        pass
    
    def _send_impl(self, message: str, **kwargs) -> NotificationResult:
        # 送信ロジック
        pass
```

**主要メソッド:**
- `validate_config()`: 設定の検証
- `_send_impl()`: 実際の送信処理
- `send()`: リトライ機能付き送信（自動実装済み）

### NotificationSettings（設定管理）

環境変数から設定を読み込むdataclass。

```python
from config.settings import NotificationSettings

# 環境変数から自動読み込み
settings = NotificationSettings.from_env()

# 利用可能なチャネルを取得
channels = settings.get_available_channels()
```

### NotificationManager（統合管理）

複数の通知チャネルを統合管理。

```python
from core.manager import NotificationManager

manager = NotificationManager(
    settings=settings,
    dry_run=False,
    enable_retry=True
)

# 複数チャネルに送信
results = manager.send_to_channels(
    message="テストメッセージ",
    channels=["slack", "email"],
    subject="件名"  # Emailの場合のみ使用
)
```

## 🧪 テスト方法

### 単体テスト例

```python
import pytest
from config.settings import SlackConfig
from notifiers.slack import SlackNotifier

def test_slack_notifier_validation():
    # 無効な設定
    with pytest.raises(ValidationError):
        SlackNotifier(
            config={"webhook_url": "invalid-url"},
            dry_run=True
        )

def test_slack_notifier_dry_run():
    # DRY RUNモード
    notifier = SlackNotifier(
        config={"webhook_url": "https://hooks.slack.com/test"},
        dry_run=True
    )
    result = notifier.send("テストメッセージ")
    assert result.success
```

## 🔧 新しい通知チャネルの追加方法

1. **新しい通知クラスを作成**

```python
# notifiers/discord.py
from .base import BaseNotifier, NotificationResult
import requests

class DiscordNotifier(BaseNotifier):
    def _get_channel_name(self) -> str:
        return "discord"
    
    def validate_config(self) -> None:
        webhook_url = self.config.get("webhook_url", "")
        if not webhook_url:
            raise ValidationError("Discord Webhook URLが設定されていません")
    
    def _send_impl(self, message: str, **kwargs) -> NotificationResult:
        # Discord送信ロジック
        pass
```

2. **設定クラスを追加**

```python
# config/settings.py
@dataclass
class DiscordConfig:
    webhook_url: str
    
    def validate(self) -> None:
        # 検証ロジック
        pass
```

3. **NotificationManagerに統合**

```python
# core/manager.py
if self.settings.discord:
    self._notifiers["discord"] = DiscordNotifier(...)
```

## 🎯 利点

### 従来版（notify.py 635行）との比較

| 項目 | 従来版 | モジュール化版 |
|------|--------|---------------|
| ファイル構成 | 単一ファイル | 14ファイル |
| 総行数 | 635行 | ~500行（分散） |
| テスト容易性 | 低い | 高い |
| 拡張性 | 中程度 | 高い |
| 保守性 | 中程度 | 高い |
| 責任分離 | なし | 明確 |

### 主な改善点

1. **テスタビリティ向上**
   - 各クラスが独立してテスト可能
   - モックやスタブの使用が容易

2. **拡張性向上**
   - 新しい通知チャネル追加が簡単
   - 基底クラスで共通機能を提供

3. **保守性向上**
   - 変更影響が局所化
   - コードの見通しが良い

4. **型安全性**
   - dataclassによる型安全な設定管理
   - 完全な型ヒント

## 🔄 既存スクリプトとの互換性

従来の`notify.py`も引き続き使用可能です。段階的な移行を推奨します。

```bash
# 従来版
python ../notify/notify.py -m "テスト"

# 新版
python main.py -m "テスト"
```

## 📋 今後の拡張計画

- [ ] 単体テストスイートの追加
- [ ] 統合テストの追加
- [ ] CI/CDパイプラインの設定
- [ ] パフォーマンス最適化
- [ ] 追加通知チャネル（Discord、Teams等）

## 🤝 貢献

新しい通知チャネルの追加や改善提案を歓迎します。
