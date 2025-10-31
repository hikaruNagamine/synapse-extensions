"""ログ設定ユーティリティ"""
import logging


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
