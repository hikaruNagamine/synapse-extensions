"""基底通知クラス"""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict
import logging


logger = logging.getLogger(__name__)


@dataclass
class NotificationResult:
    """通知結果を表すデータクラス"""
    success: bool
    channel: str
    message: str = ""
    error: str = ""

    def __str__(self) -> str:
        if self.success:
            return f"✓ {self.channel.upper()}通知が成功しました"
        else:
            return f"✗ {self.channel.upper()}通知が失敗しました: {self.error}"


class BaseNotifier(ABC):
    """
    通知サービスの基底クラス

    すべての通知サービスはこのクラスを継承する必要があります。
    """

    def __init__(self, config: Dict[str, Any], dry_run: bool = False,
                 enable_retry: bool = True):
        """
        Args:
            config: 通知サービスの設定辞書
            dry_run: True の場合、実際には送信しない
            enable_retry: リトライを有効にするか
        """
        self.config = config
        self.dry_run = dry_run
        self.enable_retry = enable_retry
        self.channel_name = self._get_channel_name()

        # 設定を検証
        self.validate_config()

    @abstractmethod
    def _get_channel_name(self) -> str:
        """
        チャネル名を取得

        Returns:
            チャネル名（例: "slack", "line", "email"）
        """
        pass

    @abstractmethod
    def validate_config(self) -> None:
        """
        設定を検証

        Raises:
            ValidationError: 設定が無効な場合
        """
        pass

    @abstractmethod
    def _send_impl(self, message: str, **kwargs) -> NotificationResult:
        """
        実際の送信処理を実装

        Args:
            message: 送信するメッセージ
            **kwargs: 追加のパラメータ

        Returns:
            NotificationResult: 送信結果
        """
        pass

    def send(self, message: str, **kwargs) -> NotificationResult:
        """
        メッセージを送信（リトライ機能付き）

        Args:
            message: 送信するメッセージ
            **kwargs: 追加のパラメータ

        Returns:
            NotificationResult: 送信結果
        """
        if self.dry_run:
            return self._dry_run_send(message, **kwargs)

        if self.enable_retry:
            return self._send_with_retry(message, **kwargs)
        else:
            return self._send_impl(message, **kwargs)

    def _dry_run_send(self, message: str, **kwargs) -> NotificationResult:
        """
        DRY RUN モードでの送信シミュレーション

        Args:
            message: 送信するメッセージ
            **kwargs: 追加のパラメータ

        Returns:
            NotificationResult: 送信結果（常に成功）
        """
        logger.info(f"[DRY RUN] {self.channel_name.upper()}送信準備完了")
        print(f"[DRY RUN] {self.channel_name.upper()}送信: {message[:50]}...")
        return NotificationResult(
            success=True,
            channel=self.channel_name,
            message=f"DRY RUN: {message[:50]}..."
        )

    def _send_with_retry(self, message: str, max_retries: int = 3,
                        retry_delay: int = 2, **kwargs) -> NotificationResult:
        """
        リトライ機能付きで送信

        Args:
            message: 送信するメッセージ
            max_retries: 最大リトライ回数
            retry_delay: リトライ間の待機時間（秒）
            **kwargs: 追加のパラメータ

        Returns:
            NotificationResult: 送信結果
        """
        import time

        for attempt in range(1, max_retries + 1):
            try:
                result = self._send_impl(message, **kwargs)
                if result.success:
                    return result

                if attempt < max_retries:
                    logger.info(f"リトライ {attempt}/{max_retries - 1} - "
                              f"{retry_delay}秒後に再試行します")
                    time.sleep(retry_delay)
            except Exception as e:
                logger.debug(f"試行 {attempt} でエラー: {type(e).__name__}")
                if attempt < max_retries:
                    logger.info(
                        f"リトライ {attempt}/{max_retries - 1} - "
                        f"{retry_delay}秒後に再試行します"
                    )
                    time.sleep(retry_delay)
                else:
                    logger.error("最大リトライ回数に達しました")
                    return NotificationResult(
                        success=False,
                        channel=self.channel_name,
                        error=f"最大リトライ回数到達: {type(e).__name__}"
                    )

        return NotificationResult(
            success=False,
            channel=self.channel_name,
            error="すべてのリトライが失敗しました"
        )
