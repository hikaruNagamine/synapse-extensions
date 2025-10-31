"""リトライユーティリティ"""
import time
import logging
from typing import Callable, Any

logger = logging.getLogger(__name__)


def retry_on_failure(func: Callable, *args, max_retries: int = 3,
                     delay: int = 2, **kwargs) -> Any:
    """
    失敗時にリトライを行う

    Args:
        func: 実行する関数
        max_retries: 最大リトライ回数
        delay: リトライ間の待機時間（秒）
        *args, **kwargs: 関数に渡す引数

    Returns:
        関数の実行結果
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
