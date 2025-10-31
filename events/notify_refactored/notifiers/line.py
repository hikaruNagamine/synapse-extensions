"""LINE Notify通知サービス"""
import sys
import logging

import requests

from notifiers.base import BaseNotifier, NotificationResult
from config.validation import validate_token
from core.exceptions import ValidationError


logger = logging.getLogger(__name__)


class LineNotifier(BaseNotifier):
    """LINE Notify API通知サービス"""

    TIMEOUT_SECONDS = 15
    API_URL = "https://notify-api.line.me/api/notify"

    def _get_channel_name(self) -> str:
        return "line"

    def validate_config(self) -> None:
        """LINE設定を検証"""
        token = self.config.get("token", "")

        if not token:
            raise ValidationError("LINE_NOTIFY_TOKENが設定されていません")

        if not validate_token(token):
            raise ValidationError("LINE_NOTIFY_TOKENの形式が無効です（最低20文字必要）")

    def _send_impl(self, message: str, **kwargs) -> NotificationResult:
        """
        LINE Notifyへメッセージを送信

        Args:
            message: 送信するメッセージ
            **kwargs: 追加パラメータ（未使用）

        Returns:
            NotificationResult: 送信結果
        """
        try:
            headers = {"Authorization": "******"}
            data = {"message": message}

            logger.debug("LINEへ送信中...")

            response = requests.post(
                self.API_URL,
                headers=headers,
                data=data,
                timeout=self.TIMEOUT_SECONDS
            )

            if response.status_code == 200:
                print("✓ LINE通知が成功しました")
                logger.info("LINE通知成功")
                return NotificationResult(
                    success=True,
                    channel=self.channel_name,
                    message=message
                )
            else:
                error_msg = f"ステータスコード: {response.status_code}"
                logger.warning(f"LINE通知失敗 ({error_msg})")
                print(f"✗ LINE通知が失敗しました ({error_msg})", file=sys.stderr)
                return NotificationResult(
                    success=False,
                    channel=self.channel_name,
                    error=error_msg
                )

        except requests.exceptions.Timeout:
            error_msg = "タイムアウト"
            logger.error("LINE通知タイムアウト")
            print("✗ LINE通知がタイムアウトしました", file=sys.stderr)
            return NotificationResult(
                success=False,
                channel=self.channel_name,
                error=error_msg
            )
        except requests.exceptions.RequestException as e:
            error_msg = type(e).__name__
            logger.error(f"LINE通知エラー: {error_msg}")
            print(f"✗ LINE通知でエラーが発生しました: {error_msg}", file=sys.stderr)
            return NotificationResult(
                success=False,
                channel=self.channel_name,
                error=error_msg
            )
        except Exception as e:
            error_msg = type(e).__name__
            logger.error(f"LINE通知予期しないエラー: {error_msg}")
            print(f"✗ LINE通知で予期しないエラーが発生しました: {error_msg}", file=sys.stderr)
            return NotificationResult(
                success=False,
                channel=self.channel_name,
                error=error_msg
            )
