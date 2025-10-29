#!/usr/bin/env python3
"""
統合通知スクリプト
Slack、LINE、Emailへの通知を一括または個別に送信
"""
import argparse
import os
import sys
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import List, Dict, Tuple, Any

import requests
from dotenv import load_dotenv


# 定数
TIMEOUT_SECONDS = 15
DEFAULT_MESSAGE = "スクリプトが実行されました"
DEFAULT_SUBJECT = "[通知] スクリプト実行"


def notify_slack(webhook_url: str, text: str, dry_run: bool = False) -> bool:
    """
    Slack Incoming Webhookへメッセージを送信

    Args:
        webhook_url: Slack Webhook URL
        text: 送信するメッセージ
        dry_run: True の場合、実際には送信しない

    Returns:
        成功したら True、失敗したら False
    """
    if dry_run:
        print(f"[DRY RUN] Slack送信: {text[:50]}...")
        return True

    try:
        payload = {"text": text}
        response = requests.post(
            webhook_url,
            json=payload,
            timeout=TIMEOUT_SECONDS
        )

        if response.status_code == 200:
            print("✓ Slack通知が成功しました")
            return True
        else:
            print(f"✗ Slack通知が失敗しました (ステータスコード: {response.status_code})",
                  file=sys.stderr)
            return False

    except requests.exceptions.Timeout:
        print("✗ Slack通知がタイムアウトしました", file=sys.stderr)
        return False
    except requests.exceptions.RequestException as e:
        print(f"✗ Slack通知でエラーが発生しました: {type(e).__name__}",
              file=sys.stderr)
        return False
    except Exception as e:
        print(f"✗ Slack通知で予期しないエラーが発生しました: {type(e).__name__}",
              file=sys.stderr)
        return False


def notify_line_notify(token: str, text: str, dry_run: bool = False) -> bool:
    """
    LINE Notify APIへメッセージを送信

    Args:
        token: LINE Notify トークン
        text: 送信するメッセージ
        dry_run: True の場合、実際には送信しない

    Returns:
        成功したら True、失敗したら False
    """
    if dry_run:
        print(f"[DRY RUN] LINE送信: {text[:50]}...")
        return True

    try:
        url = "https://notify-api.line.me/api/notify"
        headers = {"Authorization": f"Bearer {token}"}
        data = {"message": text}

        response = requests.post(
            url,
            headers=headers,
            data=data,
            timeout=TIMEOUT_SECONDS
        )

        if response.status_code == 200:
            print("✓ LINE通知が成功しました")
            return True
        else:
            print(f"✗ LINE通知が失敗しました (ステータスコード: {response.status_code})",
                  file=sys.stderr)
            return False

    except requests.exceptions.Timeout:
        print("✗ LINE通知がタイムアウトしました", file=sys.stderr)
        return False
    except requests.exceptions.RequestException as e:
        print(f"✗ LINE通知でエラーが発生しました: {type(e).__name__}",
              file=sys.stderr)
        return False
    except Exception as e:
        print(f"✗ LINE通知で予期しないエラーが発生しました: {type(e).__name__}",
              file=sys.stderr)
        return False


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
    dry_run: bool = False
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

    Returns:
        成功したら True、失敗したら False
    """
    if dry_run:
        print(f"[DRY RUN] Email送信: {subject} -> {', '.join(to_addrs)}")
        print(f"[DRY RUN] 本文: {body[:50]}...")
        return True

    try:
        # メッセージ作成
        msg = MIMEMultipart()
        msg["From"] = sender
        msg["To"] = ", ".join(to_addrs)
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "plain", "utf-8"))

        # SMTP接続
        if use_ssl:
            smtp = smtplib.SMTP_SSL(host, port, timeout=TIMEOUT_SECONDS)
        else:
            smtp = smtplib.SMTP(host, port, timeout=TIMEOUT_SECONDS)

        try:
            if use_starttls and not use_ssl:
                smtp.starttls()

            if username and password:
                smtp.login(username, password)

            smtp.send_message(msg)
            print("✓ Email通知が成功しました")
            return True

        finally:
            smtp.quit()

    except smtplib.SMTPAuthenticationError:
        print("✗ Email通知が失敗しました: SMTP認証エラー", file=sys.stderr)
        return False
    except smtplib.SMTPException as e:
        print(f"✗ Email通知が失敗しました: {type(e).__name__}", file=sys.stderr)
        return False
    except Exception as e:
        print(f"✗ Email通知で予期しないエラーが発生しました: {type(e).__name__}",
              file=sys.stderr)
        return False


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
    指定チャネルの設定が有効かチェック

    Args:
        channel: チャネル名
        config: 設定辞書

    Returns:
        (設定が有効か, エラーメッセージ)
    """
    if channel == "slack":
        if not config["slack_webhook_url"]:
            return False, "SLACK_WEBHOOK_URLが設定されていません"
    elif channel == "line":
        if not config["line_notify_token"]:
            return False, "LINE_NOTIFY_TOKENが設定されていません"
    elif channel == "email":
        if not config["smtp_host"]:
            return False, "SMTP_HOSTが設定されていません"
        if not config["smtp_sender"]:
            return False, "SMTP_SENDERが設定されていません"
        if not config["smtp_to"]:
            return False, "SMTP_TOが設定されていません"

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

    args = parser.parse_args()

    # 設定読み込み
    config = load_env_config()

    # チャネルをパース
    channels = parse_channels(args.channels)

    if not channels:
        print("エラー: 有効なチャネルが指定されていません", file=sys.stderr)
        print("使用可能なチャネル: slack, line, email, all", file=sys.stderr)
        sys.exit(64)

    # DRY RUNモードの表示
    if args.dry_run:
        print("=== DRY RUN モード ===")
        print(f"メッセージ: {args.message}")
        print(f"件名: {args.subject}")
        print(f"送信先チャネル: {', '.join(channels)}")
        print()

    # 各チャネルの設定チェックと送信
    results = {}
    any_channel_configured = False

    for channel in channels:
        # 設定チェック
        is_valid, error_msg = check_channel_config(channel, config)

        if not is_valid:
            print(f"⊘ {channel.upper()}: {error_msg}", file=sys.stderr)
            results[channel] = False
            continue

        any_channel_configured = True

        # 送信実行
        if channel == "slack":
            success = notify_slack(
                config["slack_webhook_url"],
                args.message,
                args.dry_run
            )
            results[channel] = success

        elif channel == "line":
            success = notify_line_notify(
                config["line_notify_token"],
                args.message,
                args.dry_run
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
                args.dry_run
            )
            results[channel] = success

    # 結果の判定
    if not any_channel_configured:
        print("\nエラー: 送信可能なチャネルの設定がありません", file=sys.stderr)
        sys.exit(2)

    # 成功/失敗のサマリー
    success_count = sum(1 for v in results.values() if v)
    total_count = len(results)

    print(f"\n=== 送信結果: {success_count}/{total_count} 成功 ===")

    if success_count == total_count:
        sys.exit(0)
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()
