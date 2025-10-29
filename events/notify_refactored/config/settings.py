"""設定データクラス"""
import os
from dataclasses import dataclass, field
from typing import Optional, List, Any
from dotenv import load_dotenv

from config.validation import (
    validate_url,
    validate_email,
    validate_token,
    validate_port,
    validate_email_list
)
from core.exceptions import ValidationError


@dataclass
class SlackConfig:
    """Slack設定"""
    webhook_url: str

    def validate(self) -> None:
        """設定を検証"""
        if not self.webhook_url:
            raise ValidationError("SLACK_WEBHOOK_URLが設定されていません")
        if not validate_url(self.webhook_url):
            raise ValidationError("SLACK_WEBHOOK_URLの形式が無効です")
        if not self.webhook_url.startswith("https://hooks.slack.com/"):
            import logging
            logging.getLogger(__name__).warning(
                "Slack Webhook URLが標準の形式ではありません"
            )


@dataclass
class LineConfig:
    """LINE Notify設定"""
    token: str

    def validate(self) -> None:
        """設定を検証"""
        if not self.token:
            raise ValidationError("LINE_NOTIFY_TOKENが設定されていません")
        if not validate_token(self.token):
            raise ValidationError("LINE_NOTIFY_TOKENの形式が無効です（最低20文字必要）")


@dataclass
class EmailConfig:
    """Email設定"""
    host: str
    port: int = 587
    username: str = ""
    password: str = ""
    sender: str = ""
    to_addrs: List[str] = field(default_factory=list)
    use_ssl: bool = False
    use_starttls: bool = True

    def validate(self) -> None:
        """設定を検証"""
        if not self.host:
            raise ValidationError("SMTP_HOSTが設定されていません")
        if not self.sender:
            raise ValidationError("SMTP_SENDERが設定されていません")
        if not self.to_addrs:
            raise ValidationError("SMTP_TOが設定されていません")

        # メールアドレス形式検証
        if not validate_email(self.sender):
            raise ValidationError("SMTP_SENDERのメールアドレス形式が無効です")

        if not validate_email_list(self.to_addrs):
            for addr in self.to_addrs:
                if not validate_email(addr):
                    raise ValidationError(
                        f"SMTP_TOのメールアドレス形式が無効です: {addr}"
                    )

        # ポート番号検証
        if not validate_port(self.port):
            raise ValidationError(f"SMTP_PORTが無効な範囲です: {self.port}")

        # SSL と STARTTLS の排他チェック
        if self.use_ssl and self.use_starttls:
            raise ValidationError(
                "SMTP_USE_SSLとSMTP_USE_STARTTLSの両方をtrueにすることはできません"
            )


@dataclass
class NotificationSettings:
    """統合通知設定"""
    slack: Optional[SlackConfig] = None
    line: Optional[LineConfig] = None
    email: Optional[EmailConfig] = None

    @classmethod
    def from_env(cls) -> 'NotificationSettings':
        """
        環境変数から設定を読み込む

        Returns:
            NotificationSettings: 設定インスタンス
        """
        load_dotenv()

        # Slack設定
        slack_webhook = os.getenv("SLACK_WEBHOOK_URL", "")
        slack_config = SlackConfig(webhook_url=slack_webhook) if slack_webhook else None

        # LINE設定
        line_token = os.getenv("LINE_NOTIFY_TOKEN", "")
        line_config = LineConfig(token=line_token) if line_token else None

        # Email設定
        smtp_host = os.getenv("SMTP_HOST", "")
        if smtp_host:
            smtp_to = os.getenv("SMTP_TO", "")
            to_addrs = [addr.strip() for addr in smtp_to.split(",") if addr.strip()]

            email_config = EmailConfig(
                host=smtp_host,
                port=int(os.getenv("SMTP_PORT", "587")),
                username=os.getenv("SMTP_USERNAME", ""),
                password=os.getenv("SMTP_PASSWORD", ""),
                sender=os.getenv("SMTP_SENDER", ""),
                to_addrs=to_addrs,
                use_ssl=os.getenv("SMTP_USE_SSL", "false").lower() == "true",
                use_starttls=os.getenv("SMTP_USE_STARTTLS", "true").lower() == "true"
            )
        else:
            email_config = None

        return cls(slack=slack_config, line=line_config, email=email_config)

    def get_available_channels(self) -> List[str]:
        """
        利用可能なチャネルのリストを取得

        Returns:
            利用可能なチャネル名のリスト
        """
        channels = []
        if self.slack:
            channels.append("slack")
        if self.line:
            channels.append("line")
        if self.email:
            channels.append("email")
        return channels

    def get_config_for_channel(self, channel: str) -> Optional[Any]:
        """
        指定されたチャネルの設定を取得

        Args:
            channel: チャネル名

        Returns:
            設定オブジェクト、存在しない場合はNone
        """
        if channel == "slack":
            return self.slack
        elif channel == "line":
            return self.line
        elif channel == "email":
            return self.email
        return None
