#!/usr/bin/env python3
"""
統合通知スクリプト
Slack、LINE、Emailへの通知を一括または個別に送信
"""
import argparse
import logging
import os
import re
import sys
import smtplib
import time
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import List, Dict, Tuple, Any
from urllib.parse import urlparse

import requests
from dotenv import load_dotenv


# 定数
TIMEOUT_SECONDS = 15
DEFAULT_MESSAGE = "スクリプトが実行されました"
DEFAULT_SUBJECT = "[通知] スクリプト実行"
MAX_RETRIES = 3
RETRY_DELAY = 2  # 秒

# ログ設定
logger = logging.getLogger(__name__)


def setup_logging(verbose: bool = False) -> None:
    """
    ロギングを設定

    Args:
        verbose: 詳細ログを有効にするか
    """
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        format='%(asctime)s - %(levelname)s - %(message)s',
        level=level,
        datefmt='%Y-%m-%d %H:%M:%S'
    )


def validate_url(url: str) -> bool:
    """
    URLの形式を検証

    Args:
        url: 検証するURL

    Returns:
        有効なURLであればTrue
    """
    if not url:
        return False
    try:
        result = urlparse(url)
        return all([result.scheme in ('http', 'https'), result.netloc])
    except Exception:
        return False


def validate_email(email: str) -> bool:
    """
    メールアドレスの形式を検証

    Args:
        email: 検証するメールアドレス

    Returns:
        有効なメールアドレスであればTrue
    """
    if not email:
        return False
    # 基本的なメールアドレス形式のチェック
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None


def validate_token(token: str) -> bool:
    """
    トークンの形式を検証

    Args:
        token: 検証するトークン

    Returns:
        有効なトークンであればTrue
    """
    if not token:
        return False
    # トークンは最低限の長さをチェック（LINEトークンは通常40文字以上）
    return len(token.strip()) >= 20


def retry_on_failure(func, *args, max_retries: int = MAX_RETRIES,
                     delay: int = RETRY_DELAY, **kwargs) -> bool:
    """
    失敗時にリトライを行う

    Args:
        func: 実行する関数
        max_retries: 最大リトライ回数
        delay: リトライ間の待機時間（秒）
        *args, **kwargs: 関数に渡す引数

    Returns:
        成功したらTrue、すべて失敗したらFalse
    """
    for attempt in range(1, max_retries + 1):
        try:
            result = func(*args, **kwargs)
            if result:
                return True
            if attempt < max_retries:
                logger.info(f"リトライ {attempt}/{max_retries - 1} - {delay}秒後に再試行します")
                time.sleep(delay)
        except Exception as e:
            logger.debug(f"試行 {attempt} でエラー: {type(e).__name__}")
            if attempt < max_retries:
                logger.info(f"リトライ {attempt}/{max_retries - 1} - {delay}秒後に再試行します")
                time.sleep(delay)
            else:
                logger.error("最大リトライ回数に達しました")
    return False


def notify_slack(webhook_url: str, text: str, dry_run: bool = False,
                 enable_retry: bool = True) -> bool:
    """
    Slack Incoming Webhookへメッセージを送信

    Args:
        webhook_url: Slack Webhook URL
        text: 送信するメッセージ
        dry_run: True の場合、実際には送信しない
        enable_retry: リトライを有効にするか

    Returns:
        成功したら True、失敗したら False
    """
    # URL検証
    if not validate_url(webhook_url):
        logger.error("無効なSlack Webhook URLです")
        print("✗ Slack通知が失敗しました: 無効なWebhook URL", file=sys.stderr)
        return False

    if dry_run:
        print(f"[DRY RUN] Slack送信: {text[:50]}...")
        logger.info("[DRY RUN] Slack送信準備完了")
        return True

    def _send() -> bool:
        try:
            payload = {"text": text}
            logger.debug("Slackへ送信中...")
            response = requests.post(
                webhook_url,
                json=payload,
                timeout=TIMEOUT_SECONDS
            )

            if response.status_code == 200:
                print("✓ Slack通知が成功しました")
                logger.info("Slack通知成功")
                return True
            else:
                logger.warning(f"Slack通知失敗 (ステータスコード: {response.status_code})")
                print(f"✗ Slack通知が失敗しました (ステータスコード: {response.status_code})",
                      file=sys.stderr)
                return False

        except requests.exceptions.Timeout:
            logger.error("Slack通知タイムアウト")
            print("✗ Slack通知がタイムアウトしました", file=sys.stderr)
            return False
        except requests.exceptions.RequestException as e:
            logger.error(f"Slack通知エラー: {type(e).__name__}")
            print(f"✗ Slack通知でエラーが発生しました: {type(e).__name__}",
                  file=sys.stderr)
            return False
        except Exception as e:
            logger.error(f"Slack通知予期しないエラー: {type(e).__name__}")
            print(f"✗ Slack通知で予期しないエラーが発生しました: {type(e).__name__}",
                  file=sys.stderr)
            return False

    if enable_retry:
        return retry_on_failure(_send)
    else:
        return _send()


def notify_line_notify(token: str, text: str, dry_run: bool = False,
                       enable_retry: bool = True) -> bool:
    """
    LINE Notify APIへメッセージを送信

    Args:
        token: LINE Notify トークン
        text: 送信するメッセージ
        dry_run: True の場合、実際には送信しない
        enable_retry: リトライを有効にするか

    Returns:
        成功したら True、失敗したら False
    """
    # トークン検証
    if not validate_token(token):
        logger.error("無効なLINE Notifyトークンです")
        print("✗ LINE通知が失敗しました: 無効なトークン", file=sys.stderr)
        return False

    if dry_run:
        print(f"[DRY RUN] LINE送信: {text[:50]}...")
        logger.info("[DRY RUN] LINE送信準備完了")
        return True

    def _send() -> bool:
        try:
            url = "https://notify-api.line.me/api/notify"
            headers = {"Authorization": f"Bearer {token}"}
            data = {"message": text}

            logger.debug("LINEへ送信中...")
            response = requests.post(
                url,
                headers=headers,
                data=data,
                timeout=TIMEOUT_SECONDS
            )

            if response.status_code == 200:
                print("✓ LINE通知が成功しました")
                logger.info("LINE通知成功")
                return True
            else:
                logger.warning(f"LINE通知失敗 (ステータスコード: {response.status_code})")
                print(f"✗ LINE通知が失敗しました (ステータスコード: {response.status_code})",
                      file=sys.stderr)
                return False

        except requests.exceptions.Timeout:
            logger.error("LINE通知タイムアウト")
            print("✗ LINE通知がタイムアウトしました", file=sys.stderr)
            return False
        except requests.exceptions.RequestException as e:
            logger.error(f"LINE通知エラー: {type(e).__name__}")
            print(f"✗ LINE通知でエラーが発生しました: {type(e).__name__}",
                  file=sys.stderr)
            return False
        except Exception as e:
            logger.error(f"LINE通知予期しないエラー: {type(e).__name__}")
            print(f"✗ LINE通知で予期しないエラーが発生しました: {type(e).__name__}",
                  file=sys.stderr)
            return False

    if enable_retry:
        return retry_on_failure(_send)
    else:
        return _send()


def notify_email(
    host: str,
    port: int,
    username: str,
    password: str,
    sender: str,
    to_addrs: List[str],
    subject: str,
    body: str,
    use_ssl: bool,
    use_starttls: bool,
    dry_run: bool = False,
    enable_retry: bool = True
) -> bool:
    """
    SMTPでメールを送信

    Args:
        host: SMTPサーバーホスト
        port: SMTPポート
        username: SMTP認証ユーザー名
        password: SMTP認証パスワード
        sender: 送信者メールアドレス
        to_addrs: 宛先メールアドレスのリスト
        subject: メール件名
        body: メール本文
        use_ssl: SSL/TLS接続を使用するか
        use_starttls: STARTTLSを使用するか
        dry_run: True の場合、実際には送信しない
        enable_retry: リトライを有効にするか

    Returns:
        成功したら True、失敗したら False
    """
    # メールアドレス検証
    if not validate_email(sender):
        logger.error(f"無効な送信者メールアドレス: {sender}")
        print("✗ Email通知が失敗しました: 無効な送信者アドレス", file=sys.stderr)
        return False

    for addr in to_addrs:
        if not validate_email(addr):
            logger.error(f"無効な宛先メールアドレス: {addr}")
            print(f"✗ Email通知が失敗しました: 無効な宛先アドレス ({addr})", file=sys.stderr)
            return False

    # ポート番号検証
    if not (1 <= port <= 65535):
        logger.error(f"無効なポート番号: {port}")
        print("✗ Email通知が失敗しました: 無効なポート番号", file=sys.stderr)
        return False

    if dry_run:
        print(f"[DRY RUN] Email送信: {subject} -> {', '.join(to_addrs)}")
        print(f"[DRY RUN] 本文: {body[:50]}...")
        logger.info("[DRY RUN] Email送信準備完了")
        return True

    def _send() -> bool:
        try:
            # メッセージ作成
            msg = MIMEMultipart()
            msg["From"] = sender
            msg["To"] = ", ".join(to_addrs)
            msg["Subject"] = subject
            msg.attach(MIMEText(body, "plain", "utf-8"))

            logger.debug(f"SMTPサーバー {host}:{port} へ接続中...")
            # SMTP接続
            if use_ssl:
                smtp = smtplib.SMTP_SSL(host, port, timeout=TIMEOUT_SECONDS)
            else:
                smtp = smtplib.SMTP(host, port, timeout=TIMEOUT_SECONDS)

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
                return True

            finally:
                smtp.quit()

        except smtplib.SMTPAuthenticationError:
            logger.error("SMTP認証エラー")
            print("✗ Email通知が失敗しました: SMTP認証エラー", file=sys.stderr)
            return False
        except smtplib.SMTPException as e:
            logger.error(f"SMTPエラー: {type(e).__name__}")
            print(f"✗ Email通知が失敗しました: {type(e).__name__}", file=sys.stderr)
            return False
        except Exception as e:
            logger.error(f"Email通知予期しないエラー: {type(e).__name__}")
            print(f"✗ Email通知で予期しないエラーが発生しました: {type(e).__name__}",
                  file=sys.stderr)
            return False

    if enable_retry:
        return retry_on_failure(_send)
    else:
        return _send()


def load_env_config() -> Dict[str, Any]:
    """
    環境変数から設定を読み込む

    Returns:
        設定の辞書
    """
    load_dotenv()

    config = {
        # Slack
        "slack_webhook_url": os.getenv("SLACK_WEBHOOK_URL", ""),
        # LINE
        "line_notify_token": os.getenv("LINE_NOTIFY_TOKEN", ""),
        # Email
        "smtp_host": os.getenv("SMTP_HOST", ""),
        "smtp_port": os.getenv("SMTP_PORT", "587"),
        "smtp_username": os.getenv("SMTP_USERNAME", ""),
        "smtp_password": os.getenv("SMTP_PASSWORD", ""),
        "smtp_sender": os.getenv("SMTP_SENDER", ""),
        "smtp_to": os.getenv("SMTP_TO", ""),
        "smtp_use_ssl": os.getenv("SMTP_USE_SSL", "false").lower() == "true",
        "smtp_use_starttls": os.getenv("SMTP_USE_STARTTLS", "true").lower() == "true",
    }

    return config


def parse_channels(channels_str: str) -> List[str]:
    """
    チャネル指定文字列をパース

    Args:
        channels_str: "all" または "slack,line,email" などのカンマ区切り文字列

    Returns:
        チャネルのリスト
    """
    if channels_str.lower() == "all":
        return ["slack", "line", "email"]
    else:
        # カンマ区切りで分割し、小文字化・トリム
        channels = [ch.strip().lower() for ch in channels_str.split(",")]
        # 有効なチャネルのみフィルタ
        valid_channels = ["slack", "line", "email"]
        return [ch for ch in channels if ch in valid_channels]


def check_channel_config(channel: str, config: Dict[str, Any]) -> Tuple[bool, str]:
    """
    指定チャネルの設定が有効かチェック（バリデーション強化）

    Args:
        channel: チャネル名
        config: 設定辞書

    Returns:
        (設定が有効か, エラーメッセージ)
    """
    if channel == "slack":
        if not config["slack_webhook_url"]:
            return False, "SLACK_WEBHOOK_URLが設定されていません"
        if not validate_url(config["slack_webhook_url"]):
            return False, "SLACK_WEBHOOK_URLの形式が無効です"
        if not config["slack_webhook_url"].startswith("https://hooks.slack.com/"):
            logger.warning("Slack Webhook URLが標準の形式ではありません")

    elif channel == "line":
        if not config["line_notify_token"]:
            return False, "LINE_NOTIFY_TOKENが設定されていません"
        if not validate_token(config["line_notify_token"]):
            return False, "LINE_NOTIFY_TOKENの形式が無効です（最低20文字必要）"

    elif channel == "email":
        if not config["smtp_host"]:
            return False, "SMTP_HOSTが設定されていません"
        if not config["smtp_sender"]:
            return False, "SMTP_SENDERが設定されていません"
        if not config["smtp_to"]:
            return False, "SMTP_TOが設定されていません"

        # メールアドレス形式検証
        if not validate_email(config["smtp_sender"]):
            return False, "SMTP_SENDERのメールアドレス形式が無効です"

        to_addrs = [addr.strip() for addr in config["smtp_to"].split(",") if addr.strip()]
        for addr in to_addrs:
            if not validate_email(addr):
                return False, f"SMTP_TOのメールアドレス形式が無効です: {addr}"

        # ポート番号検証
        try:
            port = int(config["smtp_port"])
            if not (1 <= port <= 65535):
                return False, f"SMTP_PORTが無効な範囲です: {port}"
        except ValueError:
            return False, f"SMTP_PORTが数値ではありません: {config['smtp_port']}"

        # SSL と STARTTLS の排他チェック
        if config["smtp_use_ssl"] and config["smtp_use_starttls"]:
            return False, "SMTP_USE_SSLとSMTP_USE_STARTTLSの両方をtrueにすることはできません"

    return True, ""


def main():
    """メイン処理"""
    parser = argparse.ArgumentParser(
        description="Slack、LINE、Emailへの統合通知スクリプト",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "-m", "--message",
        default=DEFAULT_MESSAGE,
        help=f"送信するメッセージ (デフォルト: {DEFAULT_MESSAGE})"
    )
    parser.add_argument(
        "--subject",
        default=DEFAULT_SUBJECT,
        help=f"メール件名 (デフォルト: {DEFAULT_SUBJECT})"
    )
    parser.add_argument(
        "--channels",
        default="all",
        help="送信先チャネル: 'all' または 'slack,line,email' のカンマ区切り (デフォルト: all)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="実際には送信せず、内容のみ表示"
    )
    parser.add_argument(
        "--no-retry",
        action="store_true",
        help="リトライ機能を無効化（即座に失敗として扱う）"
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="詳細ログを出力"
    )

    args = parser.parse_args()

    # ロギング設定
    setup_logging(args.verbose)
    logger.info("通知スクリプト開始")

    # 設定読み込み
    config = load_env_config()
    logger.debug("環境変数読み込み完了")

    # チャネルをパース
    channels = parse_channels(args.channels)
    logger.debug(f"選択されたチャネル: {channels}")

    if not channels:
        logger.error("有効なチャネルが指定されていません")
        print("エラー: 有効なチャネルが指定されていません", file=sys.stderr)
        print("使用可能なチャネル: slack, line, email, all", file=sys.stderr)
        sys.exit(64)

    # リトライ設定
    enable_retry = not args.no_retry
    if enable_retry:
        logger.info(f"リトライ機能: 有効 (最大{MAX_RETRIES}回)")
    else:
        logger.info("リトライ機能: 無効")

    # DRY RUNモードの表示
    if args.dry_run:
        print("=== DRY RUN モード ===")
        print(f"メッセージ: {args.message}")
        print(f"件名: {args.subject}")
        print(f"送信先チャネル: {', '.join(channels)}")
        print()
        logger.info("DRY RUNモードで実行中")

    # 各チャネルの設定チェックと送信
    results = {}
    any_channel_configured = False

    for channel in channels:
        logger.info(f"チャネル '{channel}' を処理中...")
        # 設定チェック
        is_valid, error_msg = check_channel_config(channel, config)

        if not is_valid:
            logger.warning(f"チャネル '{channel}' の設定エラー: {error_msg}")
            print(f"⊘ {channel.upper()}: {error_msg}", file=sys.stderr)
            results[channel] = False
            continue

        any_channel_configured = True
        logger.debug(f"チャネル '{channel}' の設定検証完了")

        # 送信実行
        if channel == "slack":
            success = notify_slack(
                config["slack_webhook_url"],
                args.message,
                args.dry_run,
                enable_retry
            )
            results[channel] = success

        elif channel == "line":
            success = notify_line_notify(
                config["line_notify_token"],
                args.message,
                args.dry_run,
                enable_retry
            )
            results[channel] = success

        elif channel == "email":
            to_addrs = [addr.strip() for addr in config["smtp_to"].split(",") if addr.strip()]
            success = notify_email(
                config["smtp_host"],
                int(config["smtp_port"]),
                config["smtp_username"],
                config["smtp_password"],
                config["smtp_sender"],
                to_addrs,
                args.subject,
                args.message,
                config["smtp_use_ssl"],
                config["smtp_use_starttls"],
                args.dry_run,
                enable_retry
            )
            results[channel] = success

    # 結果の判定
    if not any_channel_configured:
        logger.error("送信可能なチャネルの設定がありません")
        print("\nエラー: 送信可能なチャネルの設定がありません", file=sys.stderr)
        sys.exit(2)

    # 成功/失敗のサマリー
    success_count = sum(1 for v in results.values() if v)
    total_count = len(results)

    print(f"\n=== 送信結果: {success_count}/{total_count} 成功 ===")
    logger.info(f"送信結果: {success_count}/{total_count} 成功")

    if success_count == total_count:
        logger.info("すべての通知が成功しました")
        sys.exit(0)
    else:
        logger.warning(f"{total_count - success_count}個の通知が失敗しました")
        sys.exit(1)


if __name__ == "__main__":
    main()
