"""設定検証ユーティリティ"""
import re
from urllib.parse import urlparse
from typing import List


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


def validate_token(token: str, min_length: int = 20) -> bool:
    """
    トークンの形式を検証

    Args:
        token: 検証するトークン
        min_length: 最小文字数

    Returns:
        有効なトークンであればTrue
    """
    if not token:
        return False
    return len(token.strip()) >= min_length


def validate_port(port: int) -> bool:
    """
    ポート番号を検証

    Args:
        port: ポート番号

    Returns:
        有効なポート番号であればTrue
    """
    return 1 <= port <= 65535


def validate_email_list(emails: List[str]) -> bool:
    """
    メールアドレスリストを検証

    Args:
        emails: メールアドレスのリスト

    Returns:
        すべて有効であればTrue
    """
    return all(validate_email(email) for email in emails)
