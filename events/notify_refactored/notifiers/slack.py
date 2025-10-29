"""Slack通知サービス"""
import sys
import logging

import requests

from notifiers.base import BaseNotifier, NotificationResult
from config.validation import validate_url
from core.exceptions import ValidationError


logger = logging.getLogger(__name__)


class SlackNotifier(BaseNotifier):
    """Slack Incoming Webhook通知サービス"""

    TIMEOUT_SECONDS = 15

    def _get_channel_name(self) -> str:
        return "slack"

    def validate_config(self) -> None:
        """Slack設定を検証"""
        webhook_url = self.config.get("webhook_url", "")

        if not webhook_url:
            raise ValidationError("SLACK_WEBHOOK_URLが設定されていません")

        if not validate_url(webhook_url):
            raise ValidationError("SLACK_WEBHOOK_URLの形式が無効です")

        if not webhook_url.startswith("https://hooks.slack.com/"):
            logger.warning("Slack Webhook URLが標準の形式ではありません")

    def _send_impl(self, message: str, **kwargs) -> NotificationResult:
        """
        Slackへメッセージを送信

        Args:
            message: 送信するメッセージ
            **kwargs: 追加パラメータ（未使用）

        Returns:
            NotificationResult: 送信結果
        """
        webhook_url = self.config["webhook_url"]

        try:
            payload = {"text": message}
            logger.debug("Slackへ送信中...")

            response = requests.post(
                webhook_url,
                json=payload,
                timeout=self.TIMEOUT_SECONDS
            )

            if response.status_code == 200:
                print("✓ Slack通知が成功しました")
                logger.info("Slack通知成功")
                return NotificationResult(
                    success=True,
                    channel=self.channel_name,
                    message=message
                )
            else:
                error_msg = f"ステータスコード: {response.status_code}"
                logger.warning(f"Slack通知失敗 ({error_msg})")
                print(f"✗ Slack通知が失敗しました ({error_msg})", file=sys.stderr)
                return NotificationResult(
                    success=False,
                    channel=self.channel_name,
                    error=error_msg
                )

        except requests.exceptions.Timeout:
            error_msg = "タイムアウト"
            logger.error("Slack通知タイムアウト")
            print("✗ Slack通知がタイムアウトしました", file=sys.stderr)
            return NotificationResult(
                success=False,
                channel=self.channel_name,
                error=error_msg
            )
        except requests.exceptions.RequestException as e:
            error_msg = type(e).__name__
            logger.error(f"Slack通知エラー: {error_msg}")
            print(f"✗ Slack通知でエラーが発生しました: {error_msg}", file=sys.stderr)
            return NotificationResult(
                success=False,
                channel=self.channel_name,
                error=error_msg
            )
        except Exception as e:
            error_msg = type(e).__name__
            logger.error(f"Slack通知予期しないエラー: {error_msg}")
            print(f"✗ Slack通知で予期しないエラーが発生しました: {error_msg}", file=sys.stderr)
            return NotificationResult(
                success=False,
                channel=self.channel_name,
                error=error_msg
            )
