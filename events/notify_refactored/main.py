#!/usr/bin/env python3
"""
統合通知スクリプト - メインエントリーポイント
Slack、LINE、Emailへの通知を一括または個別に送信
"""
import argparse
import sys
import logging
import os

# パッケージのルートディレクトリをパスに追加
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config.settings import NotificationSettings
from core.manager import NotificationManager
from utils.logging import setup_logging


# 定数
DEFAULT_MESSAGE = "スクリプトが実行されました"
DEFAULT_SUBJECT = "[通知] スクリプト実行"
MAX_RETRIES = 3


logger = logging.getLogger(__name__)


def parse_channels(channels_str: str) -> list[str]:
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
    settings = NotificationSettings.from_env()
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

    # 通知マネージャーを作成
    manager = NotificationManager(
        settings=settings,
        dry_run=args.dry_run,
        enable_retry=enable_retry
    )

    # メッセージ送信
    results = manager.send_to_channels(
        message=args.message,
        channels=channels,
        subject=args.subject
    )

    # 結果の判定
    if not results:
        logger.error("送信可能なチャネルの設定がありません")
        print("\nエラー: 送信可能なチャネルの設定がありません", file=sys.stderr)
        sys.exit(2)

    # 成功/失敗のサマリー
    success_count = sum(1 for r in results if r.success)
    total_count = len(results)

    print(f"\n=== 送信結果: {success_count}/{total_count} 成功 ===")
    logger.info(f"送信結果: {success_count}/{total_count} 成功")

    if success_count == total_count:
        logger.info("すべての通知が成功しました")
        sys.exit(0)
    elif success_count == 0:
        logger.error("すべての通知が失敗しました")
        sys.exit(2)
    else:
        logger.warning(f"{total_count - success_count}個の通知が失敗しました")
        sys.exit(1)


if __name__ == "__main__":
    main()
