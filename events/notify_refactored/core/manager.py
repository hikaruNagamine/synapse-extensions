"""通知統合管理"""
import sys
import logging
from typing import List, Dict, Any

from core.exceptions import ValidationError
from config.settings import NotificationSettings
from notifiers.base import NotificationResult
from notifiers.slack import SlackNotifier
from notifiers.line import LineNotifier
from notifiers.email import EmailNotifier


logger = logging.getLogger(__name__)


class NotificationManager:
    """
    通知統合管理クラス

    複数の通知チャネルを統合的に管理し、メッセージを送信します。
    """

    def __init__(self, settings: NotificationSettings, dry_run: bool = False,
                 enable_retry: bool = True):
        """
        Args:
            settings: 通知設定
            dry_run: DRY RUNモード
            enable_retry: リトライを有効にするか
        """
        self.settings = settings
        self.dry_run = dry_run
        self.enable_retry = enable_retry
        self._notifiers: Dict[str, Any] = {}

        # 各チャネルの通知サービスを初期化
        self._initialize_notifiers()

    def _initialize_notifiers(self) -> None:
        """利用可能な通知サービスを初期化"""
        # Slack
        if self.settings.slack:
            try:
                self._notifiers["slack"] = SlackNotifier(
                    config={"webhook_url": self.settings.slack.webhook_url},
                    dry_run=self.dry_run,
                    enable_retry=self.enable_retry
                )
                logger.debug("Slack通知サービスを初期化しました")
            except ValidationError as e:
                logger.warning(f"Slack設定エラー: {e}")

        # LINE
        if self.settings.line:
            try:
                self._notifiers["line"] = LineNotifier(
                    config={"token": self.settings.line.token},
                    dry_run=self.dry_run,
                    enable_retry=self.enable_retry
                )
                logger.debug("LINE通知サービスを初期化しました")
            except ValidationError as e:
                logger.warning(f"LINE設定エラー: {e}")

        # Email
        if self.settings.email:
            try:
                self._notifiers["email"] = EmailNotifier(
                    config={
                        "host": self.settings.email.host,
                        "port": self.settings.email.port,
                        "username": self.settings.email.username,
                        "password": self.settings.email.password,
                        "sender": self.settings.email.sender,
                        "to_addrs": self.settings.email.to_addrs,
                        "use_ssl": self.settings.email.use_ssl,
                        "use_starttls": self.settings.email.use_starttls,
                    },
                    dry_run=self.dry_run,
                    enable_retry=self.enable_retry
                )
                logger.debug("Email通知サービスを初期化しました")
            except ValidationError as e:
                logger.warning(f"Email設定エラー: {e}")

    def get_available_channels(self) -> List[str]:
        """
        利用可能なチャネルのリストを取得

        Returns:
            利用可能なチャネル名のリスト
        """
        return list(self._notifiers.keys())

    def send_to_channels(self, message: str, channels: List[str],
                        **kwargs) -> List[NotificationResult]:
        """
        指定されたチャネルにメッセージを送信

        Args:
            message: 送信するメッセージ
            channels: 送信先チャネルのリスト
            **kwargs: 追加パラメータ（例: subject for email）

        Returns:
            各チャネルの送信結果のリスト
        """
        results = []

        for channel in channels:
            logger.info(f"チャネル '{channel}' を処理中...")

            # チャネルが利用可能かチェック
            if channel not in self._notifiers:
                error_msg = self._get_channel_error_message(channel)
                logger.warning(
                    f"チャネル '{channel}' の設定エラー: {error_msg}"
                )
                print(f"⊘ {channel.upper()}: {error_msg}", file=sys.stderr)
                results.append(NotificationResult(
                    success=False,
                    channel=channel,
                    error=error_msg
                ))
                continue

            logger.debug(f"チャネル '{channel}' の設定検証完了")

            # メッセージ送信
            notifier = self._notifiers[channel]
            result = notifier.send(message, **kwargs)
            results.append(result)

        return results

    def _get_channel_error_message(self, channel: str) -> str:
        """
        チャネルが利用できない理由のメッセージを取得

        Args:
            channel: チャネル名

        Returns:
            エラーメッセージ
        """
        if channel == "slack":
            if not self.settings.slack:
                return "SLACK_WEBHOOK_URLが設定されていません"
            return "Slack設定の検証に失敗しました"
        elif channel == "line":
            if not self.settings.line:
                return "LINE_NOTIFY_TOKENが設定されていません"
            return "LINE設定の検証に失敗しました"
        elif channel == "email":
            if not self.settings.email:
                return "SMTP_HOSTが設定されていません"
            return "Email設定の検証に失敗しました"
        else:
            return f"未知のチャネル: {channel}"
