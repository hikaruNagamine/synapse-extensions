"""Email (SMTP)通知サービス"""
import sys
import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from notifiers.base import BaseNotifier, NotificationResult
from config.validation import validate_email, validate_port
from core.exceptions import ValidationError


logger = logging.getLogger(__name__)


class EmailNotifier(BaseNotifier):
    """Email (SMTP)通知サービス"""

    TIMEOUT_SECONDS = 15

    def _get_channel_name(self) -> str:
        return "email"

    def validate_config(self) -> None:
        """Email設定を検証"""
        host = self.config.get("host", "")
        sender = self.config.get("sender", "")
        to_addrs = self.config.get("to_addrs", [])
        port = self.config.get("port", 587)
        use_ssl = self.config.get("use_ssl", False)
        use_starttls = self.config.get("use_starttls", True)

        if not host:
            raise ValidationError("SMTP_HOSTが設定されていません")
        if not sender:
            raise ValidationError("SMTP_SENDERが設定されていません")
        if not to_addrs:
            raise ValidationError("SMTP_TOが設定されていません")

        # メールアドレス形式検証
        if not validate_email(sender):
            raise ValidationError("SMTP_SENDERのメールアドレス形式が無効です")

        for addr in to_addrs:
            if not validate_email(addr):
                raise ValidationError(f"SMTP_TOのメールアドレス形式が無効です: {addr}")

        # ポート番号検証
        if not validate_port(port):
            raise ValidationError(f"SMTP_PORTが無効な範囲です: {port}")

        # SSL と STARTTLS の排他チェック
        if use_ssl and use_starttls:
            raise ValidationError(
                "SMTP_USE_SSLとSMTP_USE_STARTTLSの両方をtrueにすることはできません"
            )

    def _send_impl(self, message: str, **kwargs) -> NotificationResult:
        """
        SMTPでメールを送信

        Args:
            message: 送信するメッセージ（本文）
            **kwargs: 追加パラメータ
                - subject: メール件名（デフォルト: "[通知] スクリプト実行"）

        Returns:
            NotificationResult: 送信結果
        """
        host = self.config["host"]
        port = self.config["port"]
        username = self.config.get("username", "")
        password = self.config.get("password", "")
        sender = self.config["sender"]
        to_addrs = self.config["to_addrs"]
        use_ssl = self.config.get("use_ssl", False)
        use_starttls = self.config.get("use_starttls", True)

        subject = kwargs.get("subject", "[通知] スクリプト実行")

        try:
            # メッセージ作成
            msg = MIMEMultipart()
            msg["From"] = sender
            msg["To"] = ", ".join(to_addrs)
            msg["Subject"] = subject
            msg.attach(MIMEText(message, "plain", "utf-8"))

            logger.debug(f"SMTPサーバー {host}:{port} へ接続中...")

            # SMTP接続
            if use_ssl:
                smtp = smtplib.SMTP_SSL(host, port, timeout=self.TIMEOUT_SECONDS)
            else:
                smtp = smtplib.SMTP(host, port, timeout=self.TIMEOUT_SECONDS)

            try:
                if use_starttls and not use_ssl:
                    logger.debug("STARTTLS開始")
                    smtp.starttls()

                if username and password:
                    logger.debug("SMTP認証中...")
                    smtp.login(username, password)

                logger.debug("メール送信中...")
                smtp.send_message(msg)
                print("✓ Email通知が成功しました")
                logger.info("Email通知成功")
                return NotificationResult(
                    success=True,
                    channel=self.channel_name,
                    message=message
                )

            finally:
                smtp.quit()

        except smtplib.SMTPAuthenticationError:
            error_msg = "SMTP認証エラー"
            logger.error(error_msg)
            print(f"✗ Email通知が失敗しました: {error_msg}", file=sys.stderr)
            return NotificationResult(
                success=False,
                channel=self.channel_name,
                error=error_msg
            )
        except smtplib.SMTPException as e:
            error_msg = type(e).__name__
            logger.error(f"SMTPエラー: {error_msg}")
            print(f"✗ Email通知が失敗しました: {error_msg}", file=sys.stderr)
            return NotificationResult(
                success=False,
                channel=self.channel_name,
                error=error_msg
            )
        except Exception as e:
            error_msg = type(e).__name__
            logger.error(f"Email通知予期しないエラー: {error_msg}")
            print(f"✗ Email通知で予期しないエラーが発生しました: {error_msg}", file=sys.stderr)
            return NotificationResult(
                success=False,
                channel=self.channel_name,
                error=error_msg
            )
