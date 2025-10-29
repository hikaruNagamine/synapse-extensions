"""カスタム例外クラス"""


class NotificationError(Exception):
    """通知関連のベース例外"""
    pass


class ConfigurationError(NotificationError):
    """設定エラー"""
    pass


class ValidationError(NotificationError):
    """検証エラー"""
    pass


class SendError(NotificationError):
    """送信エラー"""
    pass
